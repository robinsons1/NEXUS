from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
import logging
import os
from fetch.database.supabase_client import get_supabase
from api.services.db_helpers import pg_fetch_one, pg_fetch_all
from fetch.sync import run_sync
from fetch.notifier import THRESHOLDS

router = APIRouter()
logger = logging.getLogger("nexus.router.system")

@router.get("/robots.txt", include_in_schema=False)
def robots():
    return PlainTextResponse(
        "User-agent: *\nDisallow: /data\nDisallow: /sync\nDisallow: /ingest\nDisallow: /alerts\nAllow: /\n"
    )

@router.get("/health")
@router.head("/health")
def health():
    logger.info("Health check OK")
    return JSONResponse({"status": "ok"})

@router.get("/status")
def get_status():
    """Estado en tiempo real de ambas bases de datos."""
    result = {
        "postgres_local": {"ok": False, "records": None, "error": None},
        "supabase":       {"ok": False, "records": None, "error": None},
    }

    # ── Postgres local ──
    try:
        row = pg_fetch_one("SELECT COUNT(*) AS total FROM sensor_data")
        result["postgres_local"]["ok"]      = True
        result["postgres_local"]["records"] = row["total"] if row else 0
    except Exception as e:
        result["postgres_local"]["error"] = str(e)

    # ── Supabase ──
    try:
        sb  = get_supabase()
        res = sb.table("sensor_data").select("id", count="exact").limit(1).execute()
        result["supabase"]["ok"]      = True
        result["supabase"]["records"] = res.count
    except Exception as e:
        result["supabase"]["error"] = str(e)

    # ── Diferencia de registros ──
    pg_total = result["postgres_local"]["records"]
    sb_total = result["supabase"]["records"]
    if pg_total is not None and sb_total is not None:
        result["diff"] = abs(pg_total - sb_total)
        result["in_sync"] = result["diff"] < 10  # margen de tolerancia
    else:
        result["diff"]    = None
        result["in_sync"] = False

    logger.info(f"GET /status — PG:{pg_total} SB:{sb_total} diff:{result.get('diff')}")
    return result

@router.get("/sync")
@router.head("/sync")
def sync():
    try:
        run_sync()
        logger.info("Sync manual completado ✅")
        return {"status": "ok", "message": "Sincronización completada ✅"}
    except Exception as e:
        logger.error(f"Error en /sync: {e}", exc_info=True)
        return {"status": "error", "message": "Error interno del servidor. Intente más tarde."}

@router.get("/sensors")
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

@router.get("/alerts")
async def get_alerts(limit: int = 50):
    """Últimas alertas de Telegram."""
    # ── Postgres local ──
    rows = pg_fetch_all(
        "SELECT * FROM alert_history ORDER BY created_at DESC LIMIT %s",
        (limit,)
    )
    if rows is not None:
        logger.info(f"GET /alerts ← Postgres local ✅ ({len(rows)} alertas)")
        return rows

    # ── Fallback Supabase ──
    logger.warning("GET /alerts ← fallback Supabase")
    supabase = get_supabase()
    result = supabase.table("alert_history").select("*").order("created_at", desc=True).limit(limit).execute()
    return result.data

@router.get("/config/thresholds")
def get_thresholds():
    return {
        "temp": {"min": THRESHOLDS["temperature"]["below"], "max": THRESHOLDS["temperature"]["above"]},
        "hum":  {"min": THRESHOLDS["humidity"]["below"],    "max": THRESHOLDS["humidity"]["above"]},
        "pres": {"min": THRESHOLDS["pressure"]["below"],    "max": THRESHOLDS["pressure"]["above"]},
    }
