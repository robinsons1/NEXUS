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


def _last_alert_time(sensor: str, direction: str):
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
        logger.error(f"Error consultando historial: {e}")
    return None


def _in_cooldown(sensor: str, direction: str) -> bool:
    last = _last_alert_time(sensor, direction)
    if not last:
        return False
    now = datetime.now(timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last) < timedelta(minutes=COOLDOWN_MINUTES)


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

    # Postgres local (sin cambios)
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alert_history
            (created_at, sensor, value, threshold, direction, message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (now_iso, sensor, value, threshold, direction, message))
        conn.commit()
        cur.close()
        release_pg(conn)
        logger.info("Alerta guardada en Postgres local ✅")
    except Exception as e:
        logger.error(f"Error guardando alerta en Postgres: {e}")

    # Supabase (respaldo)
    try:
        supabase.table("alert_history").insert(row).execute()
    except Exception as e:
        logger.error(f"Error guardando alerta en Supabase: {e}")


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

        emoji, label, unit, _ = SENSOR_LABELS[sensor]
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

            arrow = "🔺" if current == "above" else "🔻"
            msg = (
                f"{emoji} <b>{label} FUERA DE RANGO</b>\n"
                f"{arrow} {value:.1f} {unit}\n"
                f"Umbral: {current} {limits[current]} {unit}\n"
                f"📍 Bogotá — {timestamp_str} COT"
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

            msg = (
                f"{emoji} <b>{label} RESTABLECIDO</b>\n"
                f"📥 {value:.1f} {unit} (en rango)\n"
                f"📍 Bogotá — {timestamp_str} COT"
            )
            sent = await send_telegram(msg)
            if sent:
                _save_alert(sensor, value, limits["above"], "restored", msg)
                _sensor_state[sensor] = "ok"