from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import csv
import logging
from fetch.database.supabase_client import get_supabase
from api.services.db_helpers import pg_fetch_all, pg_fetch_one

router = APIRouter()
logger = logging.getLogger("nexus.router.data")

@router.get("/data")
def get_data(limit: int = 100, offset: int = 0, start: str = None, end: str = None):
    # ── Postgres local ──
    if start or end:
        conditions, params = [], []
        if start:
            conditions.append("created_at >= %s")
            params.append(start)
        if end:
            conditions.append("created_at <= %s")
            params.append(end)
        where = "WHERE " + " AND ".join(conditions)
        rows = pg_fetch_all(
            f"SELECT * FROM sensor_data {where} ORDER BY created_at DESC",
            tuple(params)
        )
    else:
        rows = pg_fetch_all(
            "SELECT * FROM sensor_data ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
    if rows is not None:
        logger.info(f"GET /data ← Postgres local ✅ ({len(rows)} registros)")
        return {"total": len(rows), "data": rows}

    # ── Fallback Supabase ──
    logger.warning("GET /data ← fallback Supabase")
    supabase = get_supabase()
    if start or end:
        all_data, page_size, page_offset = [], 1000, 0
        while True:
            query = supabase.table("sensor_data").select("*").order("created_at", desc=True).range(page_offset, page_offset + page_size - 1)
            if start: query = query.gte("created_at", start)
            if end:   query = query.lte("created_at", end)
            result = query.execute()
            all_data.extend(result.data)
            if len(result.data) < page_size: break
            page_offset += page_size
        logger.info(f"GET /data — rango {start} → {end} — {len(all_data)} registros")
        return {"total": len(all_data), "data": all_data}
    else:
        result = supabase.table("sensor_data").select("*").order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        logger.info(f"GET /data — limit={limit} offset={offset} — {len(result.data)} registros")
        return {"total": len(result.data), "offset": offset, "limit": limit, "data": result.data}

@router.get("/data/latest")
def get_latest():
    # ── Postgres local ──
    row = pg_fetch_one("SELECT * FROM sensor_data ORDER BY created_at DESC LIMIT 1")
    if row:
        logger.info("GET /data/latest ← Postgres local ✅")
        return row

    # ── Fallback Supabase ──
    logger.warning("GET /data/latest ← fallback Supabase")
    supabase = get_supabase()
    result = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No hay datos disponibles")
    logger.info("GET /data/latest OK")
    return result.data[0]


@router.get("/data/stats")
def get_stats(limit: int = 100, start: Optional[str] = None, end: Optional[str] = None):
    try:
        # ── Postgres local ──
        conditions, params = [], []
        if start:
            conditions.append("created_at >= %s")
            params.append(start)
        if end:
            conditions.append("created_at <= %s")
            params.append(end)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        order = "ASC" if (start and end) else "DESC"
        limit_clause = "" if (start and end) else f"LIMIT {limit}"

        rows = pg_fetch_all(
            f"SELECT field1, field2, field3, created_at FROM sensor_data {where} ORDER BY created_at {order} {limit_clause}",
            tuple(params)
        )

        if rows is not None:
            logger.info("GET /data/stats ← Postgres local ✅")
            if not rows:
                raise HTTPException(status_code=404, detail="No hay datos")
            def calc(field):
                vals = [r[field] for r in rows if r.get(field) is not None]
                if not vals: return None
                return {
                    "last":  round(vals[-1] if (start and end) else vals[0], 2),
                    "min":   round(min(vals), 2),
                    "max":   round(max(vals), 2),
                    "avg":   round(sum(vals) / len(vals), 2),
                    "count": len(vals),
                }
            return {"temperature": calc("field1"), "humidity": calc("field2"), "pressure": calc("field3")}

        # ── Fallback Supabase ──
        logger.warning("GET /data/stats ← fallback Supabase")
        supabase = get_supabase()
        if start and end:
            all_rows, page_size, off = [], 1000, 0
            while True:
                result = supabase.table("sensor_data").select("field1, field2, field3, created_at").gte("created_at", start).lte("created_at", end).order("created_at", desc=False).range(off, off + page_size - 1).execute()
                all_rows.extend(result.data)
                if len(result.data) < page_size: break
                off += page_size
            rows = all_rows
        else:
            result = supabase.table("sensor_data").select("field1, field2, field3, created_at").order("created_at", desc=True).limit(limit).execute()
            rows = result.data
        if not rows:
            raise HTTPException(status_code=404, detail="No hay datos")
        def calc_stats(field):
            values = [r[field] for r in rows if r.get(field) is not None]
            if not values: return None
            return {
                "last":  round(values[-1] if (start and end) else values[0], 2),
                "min":   round(min(values), 2),
                "max":   round(max(values), 2),
                "avg":   round(sum(values) / len(values), 2),
                "count": len(values),
            }
        logger.info(f"GET /data/stats — start={start} end={end} limit={limit}")
        return {"temperature": calc_stats("field1"), "humidity": calc_stats("field2"), "pressure": calc_stats("field3")}

    except HTTPException:
        raise
    except Exception:
        logger.error("Error calculando estadísticas", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculando estadísticas")


@router.get("/data/export")
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
