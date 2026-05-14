from fastapi import APIRouter, HTTPException
import logging
import pytz
import math
from datetime import datetime
from api.services.cache import get_cached_sensor_data

router = APIRouter()
logger = logging.getLogger("nexus.router.analytics")

@router.get("/data/heatmap")
def get_heatmap(days: int = 30):
    """Promedio por hora del día (0-23h COT) para cada sensor."""
    try:
        all_rows = get_cached_sensor_data(days)

        if not all_rows:
            raise HTTPException(status_code=404, detail="Sin datos")

        bogota_tz = pytz.timezone("America/Bogota")
        buckets = {h: {"f1": [], "f2": [], "f3": []} for h in range(24)}

        for row in all_rows:
            try:
                ca = row["created_at"]
                dt = ca if hasattr(ca, 'hour') else datetime.fromisoformat(str(ca))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.utc)
                hour = dt.astimezone(bogota_tz).hour
                if row.get("field1") is not None:
                    buckets[hour]["f1"].append(float(row["field1"]))
                if row.get("field2") is not None:
                    buckets[hour]["f2"].append(float(row["field2"]))
                if row.get("field3") is not None:
                    buckets[hour]["f3"].append(float(row["field3"]))
            except Exception:
                continue

        result_data = []
        for h in range(24):
            b = buckets[h]
            result_data.append({
                "hour": h,
                "temperature": round(sum(b["f1"]) / len(b["f1"]), 2) if b["f1"] else None,
                "humidity":    round(sum(b["f2"]) / len(b["f2"]), 2) if b["f2"] else None,
                "pressure":    round(sum(b["f3"]) / len(b["f3"]), 2) if b["f3"] else None,
            })

        logger.info(f"GET /data/heatmap procesado — {days} días")
        return {"days": days, "data": result_data}

    except HTTPException:
        raise
    except Exception:
        logger.error("Error en /data/heatmap", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculando heatmap")


@router.get("/data/weekly")
def get_weekly(days: int = 60):
    """Promedio por día de la semana (0=Lun … 6=Dom)."""
    try:
        all_rows = get_cached_sensor_data(days)

        if not all_rows:
            raise HTTPException(status_code=404, detail="Sin datos")

        bogota_tz = pytz.timezone("America/Bogota")
        DAYS_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        buckets = {d: {"f1": [], "f2": [], "f3": []} for d in range(7)}

        for row in all_rows:
            try:
                ca = row["created_at"]
                dt = ca if hasattr(ca, 'hour') else datetime.fromisoformat(str(ca))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.utc)
                day = dt.astimezone(bogota_tz).weekday()
                if row.get("field1") is not None:
                    buckets[day]["f1"].append(float(row["field1"]))
                if row.get("field2") is not None:
                    buckets[day]["f2"].append(float(row["field2"]))
                if row.get("field3") is not None:
                    buckets[day]["f3"].append(float(row["field3"]))
            except Exception:
                continue

        result_data = []
        for d in range(7):
            b = buckets[d]
            result_data.append({
                "day_index": d,
                "day_name": DAYS_ES[d],
                "temperature": round(sum(b["f1"]) / len(b["f1"]), 2) if b["f1"] else None,
                "humidity":    round(sum(b["f2"]) / len(b["f2"]), 2) if b["f2"] else None,
                "pressure":    round(sum(b["f3"]) / len(b["f3"]), 2) if b["f3"] else None,
            })

        logger.info(f"GET /data/weekly procesado — {days} días")
        return {"days": days, "data": result_data}

    except HTTPException:
        raise
    except Exception:
        logger.error("Error en /data/weekly", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculando tendencia semanal")


@router.get("/data/anomalies")
def get_anomalies(days: int = 7, sigma: float = 2.0):
    """Lecturas fuera de media ± sigma * desviación estándar."""
    try:
        all_rows = get_cached_sensor_data(days)

        if not all_rows:
            raise HTTPException(status_code=404, detail="Sin datos")

        def stats(rows, field):
            vals = [float(r[field]) for r in rows if r.get(field) is not None]
            if len(vals) < 2:
                return None, None
            mean = sum(vals) / len(vals)
            std  = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
            return mean, std

        anomalies = []
        for field, name in [("field1","temperature"),("field2","humidity"),("field3","pressure")]:
            mean, std = stats(all_rows, field)
            if mean is None or std == 0:
                continue
            for row in all_rows:
                val = row.get(field)
                if val is None:
                    continue
                val = float(val)
                if abs(val - mean) > sigma * std:
                    anomalies.append({
                        "created_at": row["created_at"],
                        "sensor": name,
                        "value": round(val, 2),
                        "mean":  round(mean, 2),
                        "std":   round(std, 2),
                        "deviation": round(abs(val - mean) / std, 2),
                    })

        anomalies.sort(key=lambda x: x["created_at"], reverse=True)
        logger.info(f"GET /data/anomalies procesado — {len(anomalies)} anomalías — {days} días")
        return {"days": days, "sigma": sigma, "total": len(anomalies), "data": anomalies[:200]}

    except HTTPException:
        raise
    except Exception:
        logger.error("Error en /data/anomalies", exc_info=True)
        raise HTTPException(status_code=500, detail="Error detectando anomalías")
