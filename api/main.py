from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, PlainTextResponse
from dotenv import load_dotenv
import os
import logging
import io
import csv
from fetch.database.supabase_client import get_supabase
from apscheduler.schedulers.background import BackgroundScheduler
from fetch.sync import run_sync, get_last_received
from fetch.notifier import check_silence
import time
import threading
from datetime import datetime, timezone

# ─── LOGGING ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-10s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("nexus")

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")

def watchdog_job():
    """Wrapper síncrono para APScheduler → llama a check_silence async."""
    import asyncio
    asyncio.run(check_silence(get_last_received()))

# ─── SCHEDULER ───
scheduler = BackgroundScheduler()
scheduler.add_job(run_sync, "interval", minutes=5, id="auto_sync")
scheduler.add_job(watchdog_job, "interval", minutes=2, id="watchdog")
scheduler.start()

import atexit
atexit.register(lambda: scheduler.shutdown(wait=False))

@app.get("/robots.txt", include_in_schema=False)
def robots():
    return PlainTextResponse(
        "User-agent: *\nDisallow: /data\nDisallow: /sync\nAllow: /\n"
    )

@app.get("/")
def root():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))


@app.get("/health")
@app.head("/health")
def health():
    logger.info("Health check OK")
    return JSONResponse({"status": "ok"})


@app.get("/dashboard")
def dashboard():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))


@app.get("/data")
def get_data(
    limit: int = 100,
    offset: int = 0,
    start: str = None,
    end: str = None
):
    supabase = get_supabase()

    if start or end:
        all_data = []
        page_size = 1000
        page_offset = 0

        while True:
            query = (
                supabase.table("sensor_data")
                .select("*")
                .order("created_at", desc=True)
                .range(page_offset, page_offset + page_size - 1)
            )
            if start:
                query = query.gte("created_at", start)
            if end:
                query = query.lte("created_at", end)

            result = query.execute()
            all_data.extend(result.data)

            if len(result.data) < page_size:
                break

            page_offset += page_size

        logger.info(f"GET /data — rango {start} → {end} — {len(all_data)} registros")
        return {"total": len(all_data), "data": all_data}

    else:
        result = (
            supabase.table("sensor_data")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        logger.info(f"GET /data — limit={limit} offset={offset} — {len(result.data)} registros")
        return {
            "total": len(result.data),
            "offset": offset,
            "limit": limit,
            "data": result.data
        }

@app.get("/data/latest")
def get_latest():
    supabase = get_supabase()
    result = (
        supabase.table("sensor_data")
        .select("*")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No hay datos disponibles")
    logger.info("GET /data/latest OK")
    return result.data[0]


@app.get("/sync")
@app.head("/sync")
def sync():
    try:
        run_sync()
        logger.info("Sync manual completado ✅")
        return {"status": "ok", "message": "Sincronización completada ✅"}
    except Exception as e:
        logger.error(f"Error en /sync: {e}", exc_info=True)
        return {"status": "error", "message": "Error interno del servidor. Intente más tarde."}


@app.get("/data/stats")
def get_stats(limit: int = 100, start: Optional[str] = None, end: Optional[str] = None):
    try:
        supabase = get_supabase()

        if start and end:
            all_rows = []
            page_size = 1000
            offset = 0
            while True:
                result = (
                    supabase.table("sensor_data")
                    .select("field1, field2, field3, created_at")
                    .gte("created_at", start)
                    .lte("created_at", end)
                    .order("created_at", desc=False)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                all_rows.extend(result.data)
                if len(result.data) < page_size:
                    break
                offset += page_size
            rows = all_rows
        else:
            result = (
                supabase.table("sensor_data")
                .select("field1, field2, field3, created_at")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            rows = result.data

        if not rows:
            raise HTTPException(status_code=404, detail="No hay datos")

        def calc_stats(field):
            values = [r[field] for r in rows if r.get(field) is not None]
            if not values:
                return None
            return {
                "last":  round(values[-1] if (start and end) else values[0], 2),
                "min":   round(min(values), 2),
                "max":   round(max(values), 2),
                "avg":   round(sum(values) / len(values), 2),
                "count": len(values),
            }

        logger.info(f"GET /data/stats — start={start} end={end} limit={limit}")
        return {
            "temperature": calc_stats("field1"),
            "humidity":    calc_stats("field2"),
            "pressure":    calc_stats("field3"),
        }

    except HTTPException:
        raise
    except Exception:
        logger.error("Error calculando estadísticas", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculando estadísticas")


@app.get("/data/export")
def export_data(format: str = "csv", start: str = None, end: str = None, limit: int = 1000):
    supabase = get_supabase()

    query = supabase.table("sensor_data").select("created_at, field1, field2, field3")

    if start and end:
        query = query.gte("created_at", start).lte("created_at", end).order("created_at", desc=False)
    else:
        query = query.order("created_at", desc=True).limit(limit)

    result = query.execute()
    rows = result.data

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "temperatura_c", "humedad_pct", "presion_hpa"])

    for row in rows:
        writer.writerow([
            row.get("created_at", ""),
            row.get("field1", ""),
            row.get("field2", ""),
            row.get("field3", "")
        ])

    output.seek(0)
    logger.info(f"Export CSV — {len(rows)} registros — start={start} end={end}")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nexus_data.csv"}
    )


@app.get("/sensors")
def get_sensors():
    return {
        "channel": {
            "id": os.getenv("THINGSPEAK_CHANNEL_ID", "3285009"),
            "name": "Estacion",
            "description": "Proyecto estacion en casa",
            "source": "ThingSpeak",
            "access": "Public",
            "tags": ["temperatura", "humedad", "casa", "proyecto", "datos", "colombia", "bmp280", "dht11"],
            "url": "https://thingspeak.mathworks.com/channels/3285009"
        },
        "location": {
            "city": "Bogotá",
            "country": "Colombia"
        },
        "sensors": [
            {"field": "field1", "name": "Temperatura", "unit": "°C", "device": "DHT11", "min_expected": 0, "max_expected": 50},
            {"field": "field2", "name": "Humedad", "unit": "%", "device": "DHT11", "min_expected": 0, "max_expected": 100},
            {"field": "field3", "name": "Presión Atmosférica", "unit": "hPa", "device": "BMP280", "min_expected": 300, "max_expected": 1100}
        ]
    }

@app.get("/alerts")
async def get_alerts(limit: int = 50):
    """Últimas alertas de Telegram."""
    supabase = get_supabase()  # <- USAR get_supabase()
    result = supabase.table("alert_history") \
        .select("*") \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    return result.data

DATA_CACHE = {
    "timestamp": 0,
    "days": 0,
    "data": []
}

# Candado para evitar estampidas de peticiones simultáneas
cache_lock = threading.Lock()

def get_cached_sensor_data(days: int):
    """Obtiene datos. Si el caché está vacío, descarga siempre 60 días para cubrir todo el dashboard."""
    global DATA_CACHE
    
    with cache_lock:
        current_time = time.time()
        
        # ¿Tenemos al menos los días solicitados y pasaron menos de 5 minutos (300 seg)?
        if DATA_CACHE["days"] >= days and (current_time - DATA_CACHE["timestamp"]) < 300:
            logger.info(f"⚡ CACHÉ HIT: Extrayendo {days} días (de {DATA_CACHE['days']} en memoria)")
            
            # Si piden exactamente lo mismo, devolver tal cual
            if DATA_CACHE["days"] == days:
                return DATA_CACHE["data"]
            
            # Si piden menos, filtramos la lista en memoria (fracción de segundo)
            from datetime import datetime, timedelta, timezone
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            filtered_data = [row for row in DATA_CACHE["data"] if row["created_at"] >= cutoff_date]
            return filtered_data
        
        # EAGER LOADING: Si vamos a descargar, bajamos al menos 60 días para llenar el tanque de una vez
        download_days = max(days, 60)
        logger.info(f"☁️ CACHÉ MISS: El tanque está vacío o caducó. Descargando {download_days} días...")
        
        supabase = get_supabase()
        from datetime import datetime, timedelta, timezone
        since = (datetime.now(timezone.utc) - timedelta(days=download_days)).isoformat()

        all_rows = []
        page_size = 1000
        offset = 0
        while True:
            result = (
                supabase.table("sensor_data")
                .select("created_at, field1, field2, field3")
                .gte("created_at", since)
                .order("created_at", desc=False)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            all_rows.extend(result.data)
            if len(result.data) < page_size:
                break
            offset += page_size
            time.sleep(0.1) # Pausa anti-Cloudflare

        # Actualizamos la memoria global con el tanque lleno
        DATA_CACHE["timestamp"] = current_time
        DATA_CACHE["days"] = download_days
        DATA_CACHE["data"] = all_rows
        
        # Si la gráfica que llamó pedía menos de lo que descargamos, lo recortamos antes de enviárselo
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        filtered_data = [row for row in all_rows if row["created_at"] >= cutoff_date]
        return filtered_data

@app.get("/analytics")
def analytics_page():
    import os
    return FileResponse(os.path.join(BASE_DIR, "frontend", "analytics.html"))


@app.get("/data/heatmap")
def get_heatmap(days: int = 30):
    """Promedio por hora del día (0-23h COT) para cada sensor."""
    try:
        all_rows = get_cached_sensor_data(days)

        if not all_rows:
            raise HTTPException(status_code=404, detail="Sin datos")

        import pytz
        from datetime import datetime
        bogota_tz = pytz.timezone("America/Bogota")
        buckets = {h: {"f1": [], "f2": [], "f3": []} for h in range(24)}

        for row in all_rows:
            try:
                dt = datetime.fromisoformat(row["created_at"])
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


@app.get("/data/weekly")
def get_weekly(days: int = 60):
    """Promedio por día de la semana (0=Lun … 6=Dom)."""
    try:
        all_rows = get_cached_sensor_data(days)

        if not all_rows:
            raise HTTPException(status_code=404, detail="Sin datos")

        import pytz
        from datetime import datetime
        bogota_tz = pytz.timezone("America/Bogota")
        DAYS_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        buckets = {d: {"f1": [], "f2": [], "f3": []} for d in range(7)}

        for row in all_rows:
            try:
                dt = datetime.fromisoformat(row["created_at"])
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


@app.get("/data/anomalies")
def get_anomalies(days: int = 7, sigma: float = 2.0):
    """Lecturas fuera de media ± sigma * desviación estándar."""
    try:
        all_rows = get_cached_sensor_data(days)

        if not all_rows:
            raise HTTPException(status_code=404, detail="Sin datos")

        import math

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
    
#Dejar al final
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")