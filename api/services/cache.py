import time
import threading
from datetime import datetime, timedelta, timezone
import logging
from fetch.database.supabase_client import get_supabase
from api.services.db_helpers import pg_fetch_all

logger = logging.getLogger("nexus.cache")

def _normalize_ts(val) -> str:
    """Convierte created_at (datetime o str) a ISO UTC normalizado sin offset '+00:00'."""
    if isinstance(val, datetime):
        return val.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")
    if isinstance(val, str):
        # quitar offset +00:00 o Z para comparación uniforme
        return val.replace("+00:00", "").replace("Z", "").rstrip()
    return str(val)

DATA_CACHE = {
    "timestamp": 0,
    "days": 0,
    "data": [],
    "last_created_at": None
}
cache_lock = threading.Lock()

def get_cached_sensor_data(days: int):
    """Caché incremental: primera vez descarga 60 días, luego solo registros nuevos."""
    global DATA_CACHE

    with cache_lock:
        current_time = time.time()

        # ── CACHÉ HIT: datos frescos (menos de 5 min) ────────────────────────
        if DATA_CACHE["days"] >= days and (current_time - DATA_CACHE["timestamp"]) < 300:
            logger.info(f"⚡ CACHÉ HIT: {len(DATA_CACHE['data'])} registros en memoria")
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            return [r for r in DATA_CACHE["data"] if _normalize_ts(r["created_at"]) >= cutoff]

        # ── CACHÉ INCREMENTAL: ya tenemos datos, solo traer los nuevos ────────
        if DATA_CACHE["data"] and DATA_CACHE["last_created_at"]:
            since = DATA_CACHE["last_created_at"]
            logger.info(f"🔄 CACHÉ INCREMENTAL: descargando desde {since}...")

            new_rows = pg_fetch_all(
                "SELECT created_at, field1, field2, field3 FROM sensor_data "
                "WHERE created_at > %s ORDER BY created_at ASC",
                (since,)
            )

            if new_rows is None:  # fallback Supabase
                logger.warning("get_cached_sensor_data incremental ← fallback Supabase")
                try:
                    sb = get_supabase()
                    res = sb.table("sensor_data") \
                        .select("created_at, field1, field2, field3") \
                        .gt("created_at", since) \
                        .order("created_at", desc=False).execute()
                    new_rows = res.data
                except Exception:
                    new_rows = []

            if new_rows:
                DATA_CACHE["data"].extend(new_rows)
                DATA_CACHE["last_created_at"] = _normalize_ts(new_rows[-1]["created_at"])
                logger.info(f"🔄 INCREMENTAL: +{len(new_rows)} nuevos — total {len(DATA_CACHE['data'])}")

            DATA_CACHE["timestamp"] = current_time
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.%f")
            return [r for r in DATA_CACHE["data"] if _normalize_ts(r["created_at"]) >= cutoff]

        # ── CACHÉ MISS INICIAL: primera carga, descarga 60 días completos ─────
        download_days = max(days, 60)
        since = (datetime.now(timezone.utc) - timedelta(days=download_days)).isoformat()
        logger.info(f"☁️ CACHÉ MISS INICIAL: descargando {download_days} días...")

        all_rows = pg_fetch_all(
            "SELECT created_at, field1, field2, field3 FROM sensor_data "
            "WHERE created_at >= %s ORDER BY created_at ASC",
            (since,)
        )

        if all_rows is None:  # fallback Supabase
            logger.warning("get_cached_sensor_data inicial ← fallback Supabase")
            supabase = get_supabase()
            all_rows, page_size, offset = [], 1000, 0
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
                time.sleep(0.1)

        DATA_CACHE["timestamp"]       = current_time
        DATA_CACHE["days"]            = download_days
        DATA_CACHE["data"]            = all_rows
        DATA_CACHE["last_created_at"] = _normalize_ts(all_rows[-1]["created_at"]) if all_rows else None

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.%f")
        return [r for r in all_rows if _normalize_ts(r["created_at"]) >= cutoff]
