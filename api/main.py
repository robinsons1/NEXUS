from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from dotenv import load_dotenv
import os
import logging
import io
import csv
from fetch.database.supabase_client import get_supabase
from apscheduler.schedulers.background import BackgroundScheduler
from fetch.sync import run_sync

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
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")

# ─── SCHEDULER ───
scheduler = BackgroundScheduler()
scheduler.add_job(run_sync, "interval", minutes=5, id="auto_sync")
scheduler.start()

import atexit
atexit.register(lambda: scheduler.shutdown(wait=False))


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
def get_data(limit: int = 100, start: str = None, end: str = None):
    supabase = get_supabase()

    if start or end:
        all_data = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                supabase.table("sensor_data")
                .select("*")
                .order("created_at", desc=True)
                .range(offset, offset + page_size - 1)
            )
            if start:
                query = query.gte("created_at", start)
            if end:
                query = query.lte("created_at", end)

            result = query.execute()
            all_data.extend(result.data)

            if len(result.data) < page_size:
                break

            offset += page_size

        logger.info(f"GET /data — rango {start} → {end} — {len(all_data)} registros")
        return {"total": len(all_data), "data": all_data}

    else:
        result = (
            supabase.table("sensor_data")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        logger.info(f"GET /data — limit={limit} — {len(result.data)} registros")
        return {"total": len(result.data), "data": result.data}


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