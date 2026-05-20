import os
import httpx
import logging
from datetime import datetime, timezone, timedelta
from fetch.database.supabase_client import supabase
from fetch.database.postgres_client import get_pg, release_pg
import pytz

logger = logging.getLogger("nexus.notifier")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NEXUS_BASE_URL = os.getenv("NEXUS_BASE_URL", "https://nexus-w0yh.onrender.com")

THRESHOLDS = {
    "temperature": {"above": 26.0, "below": 20.0},
    "humidity":    {"above": 75.0, "below": 40.0},
    "pressure":    {"above": 756.0, "below": 750.0},
}

# Histéresis: el valor debe alejarse N unidades del umbral para "restablecido"
HYSTERESIS = {
    "temperature": 1.0,
    "humidity":    2.0,
    "pressure":    3.0,
}

COOLDOWN_MINUTES = 30

SENSOR_LABELS = {
    "temperature": ("🌡️", "Temperatura", "°C",  "field1"),
    "humidity":    ("💧", "Humedad",     "%",   "field2"),
    "pressure":    ("🔵", "Presión",     "hPa", "field3"),
}

# ── Estado en memoria ────────────────────────────────────────────────────────
_sensor_state: dict[str, str] = {
    "temperature": "ok",
    "humidity":    "ok",
    "pressure":    "ok",
}

# ── Estado watchdog ──────────────────────────────────────────────────────────
SILENCE_THRESHOLD_MINUTES = 10
_watchdog_state: str = "ok"


async def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }, timeout=10)
            r.raise_for_status()
        logger.info(f"Telegram enviado: {message[:60]}...")
        return True
    except Exception as e:
        logger.error(f"Error enviando Telegram: {e}")
        return False


def _last_alert_time_pg(sensor: str, direction: str) -> datetime | None:
    """Consulta Postgres local para el último tiempo de alerta. Robusto en modo offline."""
    conn = None
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute(
            "SELECT created_at FROM alert_history "
            "WHERE sensor = %s AND direction = %s "
            "ORDER BY created_at DESC LIMIT 1",
            (sensor, direction)
        )
        row = cur.fetchone()
        cur.close()
        if row and row[0]:
            val = row[0]
            if isinstance(val, datetime):
                return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(
                str(val).replace("+00:00", "").rstrip()
            ).replace(tzinfo=timezone.utc)
        return None
    except Exception as e:
        logger.warning(f"_last_alert_time_pg({sensor}/{direction}): {e}")
        return None
    finally:
        if conn:
            release_pg(conn)


def _last_alert_time(sensor: str, direction: str) -> datetime | None:
    """Devuelve el timestamp de la última alerta. Postgres primero, Supabase como fallback."""
    ts = _last_alert_time_pg(sensor, direction)
    if ts is not None:
        return ts
    # Fallback Supabase (cuando Postgres no está disponible)
    try:
        result = supabase.table("alert_history") \
            .select("created_at") \
            .eq("sensor", sensor) \
            .eq("direction", direction) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        if result.data:
            return datetime.fromisoformat(result.data[0]["created_at"])
    except Exception as e:
        logger.error(f"Error consultando historial Supabase: {e}")
    return None


def _get_oldest_data_time() -> datetime:
    """Obtiene el timestamp del dato más antiguo registrado para usar como fallback de inicio."""
    conn = None
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute("SELECT MIN(created_at) FROM sensor_data")
        row = cur.fetchone()
        cur.close()
        if row and row[0]:
            val = row[0]
            if isinstance(val, datetime):
                return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(str(val).replace("+00:00", "").rstrip()).replace(tzinfo=timezone.utc)
    except Exception as e:
        logger.warning(f"_get_oldest_data_time: {e}")
    finally:
        if conn:
            release_pg(conn)
    return datetime.now(timezone.utc) - timedelta(days=1)


def _format_duration(delta: timedelta) -> str:
    """Da formato legible en español a una duración (timedelta)."""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} día{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")
        
    return ", ".join(parts)


def _get_duration_ok(sensor: str) -> str:
    """Calcula cuánto tiempo ha estado el sensor en estado normal (ok)."""
    last_restored = _last_alert_time(sensor, "restored")
    if not last_restored:
        last_restored = _get_oldest_data_time()
    
    now = datetime.now(timezone.utc)
    delta = now - last_restored
    return _format_duration(delta)


def _get_duration_out_of_range(sensor: str, prev_state: str) -> tuple[str, datetime | None]:
    """Calcula cuánto tiempo ha estado el sensor fuera de rango."""
    last_alert = _last_alert_time(sensor, prev_state)
    if not last_alert:
        return "duración desconocida", None
    now = datetime.now(timezone.utc)
    delta = now - last_alert
    return _format_duration(delta), last_alert


def _get_peak_value(sensor: str, col: str, start_time: datetime, prev_state: str) -> float | None:
    """Obtiene el valor pico (máximo o mínimo) registrado en sensor_data durante la anomalía."""
    if not start_time:
        return None
    agg = "MAX" if prev_state == "above" else "MIN"
    conn = None
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute(
            f"SELECT {agg}(CAST({col} AS DOUBLE PRECISION)) FROM sensor_data "
            f"WHERE created_at >= %s AND created_at <= %s",
            (start_time, datetime.now(timezone.utc))
        )
        row = cur.fetchone()
        cur.close()
        if row and row[0] is not None:
            return float(row[0])
    except Exception as e:
        logger.warning(f"_get_peak_value({sensor}/{prev_state}): {e}")
    finally:
        if conn:
            release_pg(conn)
    return None


def _get_previous_reading(sensor: str, col: str) -> tuple[float | None, datetime | None]:
    """Obtiene el valor y timestamp de la lectura inmediatamente anterior en la base de datos."""
    conn = None
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute(
            f"SELECT {col}, created_at FROM sensor_data "
            f"WHERE {col} IS NOT NULL "
            f"ORDER BY created_at DESC LIMIT 1 OFFSET 1"
        )
        row = cur.fetchone()
        cur.close()
        if row and row[0] is not None:
            val = float(row[0])
            ts = row[1]
            if not isinstance(ts, datetime):
                ts = datetime.fromisoformat(str(ts).replace("+00:00", "").rstrip())
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return val, ts
    except Exception as e:
        logger.warning(f"_get_previous_reading({sensor}): {e}")
    finally:
        if conn:
            release_pg(conn)
    return None, None


def _get_trend_string(sensor: str, col: str, current_value: float, unit: str) -> str:
    """Determina la tendencia de cambio del sensor basándose en la lectura anterior."""
    prev_val, prev_ts = _get_previous_reading(sensor, col)
    if prev_val is None or prev_ts is None:
        return ""
    
    diff = current_value - prev_val
    now = datetime.now(timezone.utc)
    time_diff = (now - prev_ts).total_seconds() / 60
    
    if time_diff <= 0:
        return ""
        
    if abs(diff) < 0.05:
        return "➡️ Estable"
        
    arrow = "📈" if diff > 0 else "📉"
    sign = "+" if diff > 0 else ""
    mins = max(1, int(round(time_diff)))
    return f"{arrow} {sign}{diff:.1f} {unit} en los últimos {mins} min"


def _in_cooldown(sensor: str, direction: str) -> bool:
    last = _last_alert_time(sensor, direction)
    if not last:
        return False
    now = datetime.now(timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last) < timedelta(minutes=COOLDOWN_MINUTES)


def init_sensor_states() -> None:
    """
    Al arrancar el servidor, lee el último estado de alerta por sensor desde
    Postgres local para inicializar _sensor_state y _watchdog_state.
    Evita envíos duplicados tras un reinicio del proceso.
    """
    global _sensor_state, _watchdog_state
    sensors_to_check = list(SENSOR_LABELS.keys()) + ["watchdog"]
    for sensor in sensors_to_check:
        conn = None
        try:
            conn = get_pg()
            cur = conn.cursor()
            cur.execute(
                "SELECT direction FROM alert_history "
                "WHERE sensor = %s ORDER BY created_at DESC LIMIT 1",
                (sensor,)
            )
            row = cur.fetchone()
            cur.close()
            if row:
                direction = row[0]
                if sensor == "watchdog":
                    _watchdog_state = "silent" if direction == "silent" else "ok"
                else:
                    _sensor_state[sensor] = direction if direction in ("above", "below") else "ok"
        except Exception as e:
            logger.warning(f"init_sensor_states: no se pudo cargar '{sensor}': {e}")
        finally:
            if conn:
                release_pg(conn)
    logger.info(
        f"Estados de alerta cargados desde BD — "
        f"sensores={_sensor_state}, watchdog={_watchdog_state}"
    )


def _save_alert(sensor: str, value: float, threshold: float,
                direction: str, message: str):
    now_iso = datetime.now(timezone.utc).isoformat()
    row = {
        "sensor":     sensor,
        "value":      value,
        "threshold":  threshold,
        "direction":  direction,
        "message":    message,
        "created_at": now_iso,
    }

    # Supabase (intentar primero para bandera)
    synced_to_supabase = False
    try:
        supabase.table("alert_history").insert(row).execute()
        synced_to_supabase = True
    except Exception as e:
        logger.error(f"Error guardando alerta en Supabase: {e}")

    # Postgres local (primario)
    conn = None
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alert_history
            (created_at, sensor, value, threshold, direction, message, synced_to_supabase)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (now_iso, sensor, value, threshold, direction, message, synced_to_supabase))
        conn.commit()
        cur.close()
        logger.info(f"Alerta guardada en Postgres local ✅ (synced={synced_to_supabase})")
    except Exception as e:
        logger.error(f"Error guardando alerta en Postgres: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn:
            release_pg(conn)


async def check_silence(last_received: datetime | None) -> None:
    global _watchdog_state

    bogota_tz = pytz.timezone("America/Bogota")
    now_bogota = datetime.now(bogota_tz)
    timestamp_str = now_bogota.strftime("%Y-%m-%d %H:%M")

    if last_received is None:
        return

    elapsed = (datetime.now(timezone.utc) - last_received).total_seconds() / 60

    # ── SIN DATOS ────────────────────────────────────────────────────────────
    if elapsed >= SILENCE_THRESHOLD_MINUTES:
        if _watchdog_state == "silent":
            logger.info("Watchdog: sin datos, alerta ya enviada — omitiendo")
            return

        msg = (
            f"📡 NEXUS — Sin datos\n"
            f"⏱ Llevan {int(elapsed)} min sin recibirse lecturas.\n"
            f"Último dato: {last_received.strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"📍 Bogotá — {timestamp_str} COT\n"
            f"Verifica el ESP32 o ThingSpeak."
        )
        sent = await send_telegram(msg)
        if sent:
            _save_alert("watchdog", elapsed, SILENCE_THRESHOLD_MINUTES, "silent", msg)
            _watchdog_state = "silent"
            logger.warning(f"Watchdog: alerta enviada — {int(elapsed)} min sin datos")

    # ── DATOS RESTABLECIDOS ───────────────────────────────────────────────────
    else:
        if _watchdog_state == "silent":
            msg = (
                f"✅ NEXUS — Datos restablecidos\n"
                f"📥 Se recibieron lecturas nuevamente.\n"
                f"📍 Bogotá — {timestamp_str} COT"
            )
            sent = await send_telegram(msg)
            if sent:
                _save_alert("watchdog", 0, SILENCE_THRESHOLD_MINUTES, "restored", msg)
                logger.info("Watchdog: datos restablecidos — estado reseteado")
            _watchdog_state = "ok"


async def check_and_notify(record: dict):
    mapping = {
        "temperature": float(record.get("field1")) if record.get("field1") else None,
        "humidity":    float(record.get("field2")) if record.get("field2") else None,
        "pressure":    float(record.get("field3")) if record.get("field3") else None,
    }

    for sensor, value in mapping.items():
        if value is None:
            continue

        emoji, label, unit, col = SENSOR_LABELS[sensor]
        limits        = THRESHOLDS[sensor]
        hyst          = HYSTERESIS[sensor]
        bogota_tz     = pytz.timezone("America/Bogota")
        now_bogota    = datetime.now(bogota_tz)
        timestamp_str = now_bogota.strftime("%Y-%m-%d %H:%M")

        # ── Determinar estado actual ──────────────────────────────────────
        if value > limits["above"]:
            current = "above"
        elif value < limits["below"]:
            current = "below"
        else:
            current = "ok"

        prev_state = _sensor_state[sensor]

        # ── FUERA DE RANGO ────────────────────────────────────────────────
        if current != "ok":
            already_alerting = (prev_state == current)
            if already_alerting and _in_cooldown(sensor, current):
                logger.info(f"Alerta {sensor}/{current} en cooldown, omitida")
                continue

            duration_ok = _get_duration_ok(sensor)
            trend_str = _get_trend_string(sensor, col, value, unit)
            trend_line = f"Tendencia: <b>{trend_str}</b>\n" if trend_str else ""
            arrow = "🔺" if current == "above" else "🔻"
            status_word = "Elevado" if current == "above" else "Bajo"

            msg = (
                f"{emoji} <b>{label.upper()} FUERA DE RANGO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Estado actual: <b>{value:.1f} {unit}</b> ({status_word} {arrow})\n"
                f"Umbral límite: {limits[current]} {unit}\n"
                f"{trend_line}"
                f"Tiempo en rango OK: <b>{duration_ok}</b>\n\n"
                f"📍 Bogotá — {timestamp_str} COT\n"
                f"🔗 <a href=\"{NEXUS_BASE_URL}\">Ver Dashboard en Vivo</a>"
            )
            sent = await send_telegram(msg)
            if sent:
                _save_alert(sensor, value, limits[current], current, msg)
                _sensor_state[sensor] = current

        # ── RESTABLECIDO con histéresis ───────────────────────────────────
        elif current == "ok" and prev_state != "ok":
            # Exigir que el valor se aleje del umbral antes de notificar
            if prev_state == "above" and value > (limits["above"] - hyst):
                logger.info(f"{sensor} en zona de histéresis ({value:.1f}), esperando...")
                continue
            if prev_state == "below" and value < (limits["below"] + hyst):
                logger.info(f"{sensor} en zona de histéresis ({value:.1f}), esperando...")
                continue

            if _in_cooldown(sensor, "restored"):
                logger.info(f"Restored {sensor} en cooldown, omitido")
                continue

            duration_incident, start_time = _get_duration_out_of_range(sensor, prev_state)
            peak_val = _get_peak_value(sensor, col, start_time, prev_state) if start_time else None
            peak_arrow = "🔺" if prev_state == "above" else "🔻"
            peak_line = f"Valor pico: <b>{peak_val:.1f} {unit}</b> {peak_arrow}\n" if peak_val is not None else ""
            
            trend_str = _get_trend_string(sensor, col, value, unit)
            trend_line = f"Tendencia: <b>{trend_str}</b>\n" if trend_str else ""

            msg = (
                f"{emoji} <b>{label.upper()} RESTABLECIDO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Estado actual: <b>{value:.1f} {unit}</b> (Normal 📥)\n"
                f"{trend_line}"
                f"Duración de anomalía: <b>{duration_incident}</b>\n"
                f"{peak_line}\n"
                f"📍 Bogotá — {timestamp_str} COT\n"
                f"🔗 <a href=\"{NEXUS_BASE_URL}\">Ver Dashboard en Vivo</a>"
            )
            sent = await send_telegram(msg)
            if sent:
                _save_alert(sensor, value, limits["above"], "restored", msg)
                _sensor_state[sensor] = "ok"