from fastapi import APIRouter
from datetime import datetime, timezone
import logging
from api.services.db_helpers import pg_fetch_one

router = APIRouter()
logger = logging.getLogger("nexus.router.sync")


def _to_utc(val) -> datetime | None:
    """Convierte un timestamp (datetime o str) a datetime UTC-aware."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(
            str(val).replace("+00:00", "").rstrip()
        ).replace(tzinfo=timezone.utc)
    except Exception:
        return None


@router.get("/sync/status")
def sync_status():
    """
    Observabilidad del estado de sincronización local → Supabase.
    Muestra cuántos registros de sensor_data y alert_history están pendientes
    de ser sincronizados y si hay desfase superior a 60 minutos.
    """
    now = datetime.now(timezone.utc)

    sd_row = pg_fetch_one(
        "SELECT COUNT(*) AS cnt, MIN(created_at) AS oldest "
        "FROM sensor_data WHERE synced_to_supabase = FALSE"
    )
    ah_row = pg_fetch_one(
        "SELECT COUNT(*) AS cnt, MIN(created_at) AS oldest "
        "FROM alert_history WHERE synced_to_supabase = FALSE"
    )

    if sd_row is None and ah_row is None:
        return {
            "status": "error",
            "detail": "Postgres local no disponible",
            "checked_at": now.isoformat(),
        }

    sensor_pending = int(sd_row["cnt"]) if sd_row else 0
    alert_pending  = int(ah_row["cnt"]) if ah_row else 0

    sensor_oldest = _to_utc(sd_row.get("oldest")) if sd_row else None
    alert_oldest  = _to_utc(ah_row.get("oldest"))  if ah_row else None

    candidates = [ts for ts in (sensor_oldest, alert_oldest) if ts is not None]
    oldest = min(candidates) if candidates else None

    oldest_minutes = None
    desfasado = False
    if oldest:
        oldest_minutes = round((now - oldest).total_seconds() / 60, 1)
        desfasado = oldest_minutes > 60

    total_pending = sensor_pending + alert_pending
    if total_pending == 0:
        status = "sincronizado"
    elif desfasado:
        status = "desfasado"
    else:
        status = "pendiente"

    logger.info(
        f"GET /sync/status — {status} | "
        f"sensor_pending={sensor_pending} alert_pending={alert_pending} "
        f"oldest={oldest_minutes}min"
    )

    return {
        "status": status,
        "sensor_data_pending": sensor_pending,
        "alert_history_pending": alert_pending,
        "total_pending": total_pending,
        "oldest_unsynced_minutes": oldest_minutes,
        "desfasado": desfasado,
        "checked_at": now.isoformat(),
    }
