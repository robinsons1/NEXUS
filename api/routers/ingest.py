from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
import os
import logging
from datetime import datetime, timezone
from fetch.database.postgres_client import get_pg, release_pg
from fetch.database.supabase_client import get_supabase
from fetch.sync import update_last_received
from fetch.notifier import check_and_notify
from api.services.cache import DATA_CACHE, cache_lock

router = APIRouter()
logger = logging.getLogger("nexus.router.ingest")

class SensorPayload(BaseModel):
    field1: float           # Temperatura DHT11 (°C)
    field2: float           # Humedad DHT11 (%)
    field3: float | None = None  # Presión BMP280 (hPa) — opcional

INGEST_API_KEY = os.getenv("INGEST_API_KEY")

@router.post("/ingest")
async def ingest(payload: SensorPayload, x_api_key: str = Header(default=None)):
    """Recibe datos de la ESP32. Escribe en Postgres local Y Supabase."""

    # ── Validación API Key ──────────────────────────────────
    if x_api_key != INGEST_API_KEY:
        logger.warning("🚫 /ingest bloqueado — API Key inválida o ausente")
        raise HTTPException(status_code=403, detail="Forbidden")
    
    now_iso = datetime.now(timezone.utc).isoformat()
    row_dict = {
        "field1": payload.field1,
        "field2": payload.field2,
        "field3": payload.field3,
        "created_at": now_iso,
        "tenant_id": "default",
    }

    # ── Supabase (intentar primero para bandera) ───────────────
    synced_to_supabase = False
    try:
        get_supabase().table("sensor_data").insert(row_dict).execute()
        synced_to_supabase = True
        logger.info("POST /ingest → Supabase OK ✅")
    except Exception:
        logger.error("POST /ingest → Supabase FAIL ❌", exc_info=True)

    # ── Postgres local (primario) ───────────────────────────────
    pg_ok = False
    try:
        conn = get_pg()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO sensor_data (created_at, field1, field2, field3, tenant_id, synced_to_supabase)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (created_at) DO NOTHING
        """, (now_iso, payload.field1, payload.field2, payload.field3, "default", synced_to_supabase))
        conn.commit()
        cur.close()
        release_pg(conn)
        pg_ok = True
        logger.info(f"POST /ingest → Postgres local OK ✅ (synced={synced_to_supabase})")
    except Exception:
        logger.error("POST /ingest → Postgres local FAIL ❌", exc_info=True)

    # ── Watchdog + invalidar caché ─────────────────────────────
    update_last_received()
    with cache_lock:
        DATA_CACHE["timestamp"] = 0

    # ── Evaluación de umbrales → Telegram ─────────────────────
    await check_and_notify(row_dict)

    logger.info(
        f"POST /ingest — T={payload.field1}°C  H={payload.field2}%  P={payload.field3}hPa"
    )
    return {"status": "ok", "message": "Dato guardado", "postgres": pg_ok}
