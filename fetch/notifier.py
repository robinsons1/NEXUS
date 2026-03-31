import os
import httpx
import logging
from datetime import datetime, timezone, timedelta
from fetch.database.supabase_client import supabase
import pytz


logger = logging.getLogger("nexus.notifier")


TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# Umbrales por defecto (puedes ajustarlos según tu sensor en Bogotá)
THRESHOLDS = {
    "temperature": {"above": 23.0, "below": 21.0},  # °C
    "humidity":    {"above": 70.0, "below": 48.0},  # %
    "pressure":    {"above": 755.0, "below": 750.0}, # hPa
}


COOLDOWN_MINUTES = 30  # No repetir alerta del mismo sensor/dirección en X minutos


SENSOR_LABELS = {
    "temperature": ("🌡️", "Temperatura", "°C",  "field1"),
    "humidity":    ("💧", "Humedad",      "%",   "field2"),
    "pressure":    ("🔵", "Presión",      "hPa", "field3"),
}


async def send_telegram(message: str) -> bool:
    """Envía mensaje al bot de Telegram."""
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
    """Retorna el timestamp de la última alerta para ese sensor+dirección."""
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
    """Verifica si está en período de cooldown."""
    last = _last_alert_time(sensor, direction)
    if not last:
        return False
    now = datetime.now(timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last) < timedelta(minutes=COOLDOWN_MINUTES)


def _save_alert(sensor: str, value: float, threshold: float,
                direction: str, message: str):
    """Guarda la alerta en Supabase."""
    try:
        supabase.table("alert_history").insert({
            "sensor":    sensor,
            "value":     value,
            "threshold": threshold,
            "direction": direction,
            "message":   message
        }).execute()
    except Exception as e:
        logger.error(f"Error guardando alerta: {e}")


async def check_and_notify(record: dict):
    """
    Recibe un registro nuevo {field1, field2, field3}
    y evalúa si algún valor supera umbrales.
    """
    # Convertir a float
    mapping = {
        "temperature": float(record.get("field1")) if record.get("field1") else None,
        "humidity":    float(record.get("field2")) if record.get("field2") else None,
        "pressure":    float(record.get("field3")) if record.get("field3") else None,
    }

    for sensor, value in mapping.items():
        if value is None:
            continue

        emoji, label, unit, _ = SENSOR_LABELS[sensor]
        limits = THRESHOLDS[sensor]

        # Verificar estado actual
        if value > limits["above"]:
            attention = "above"
        elif value < limits["below"]:
            attention = "below"
        else:
            attention = "ok"

        # FUERA DE RANGO
        if attention != "ok":
            if _in_cooldown(sensor, attention):
                logger.info(f"Alerta {sensor}/{attention} en cooldown, omitida")
                continue

            arrow = "🔺" if attention == "above" else "🔻"
            bogota_tz = pytz.timezone('America/Bogota')
            now_bogota = datetime.now(bogota_tz)
            
            msg = (
                f"{emoji} <b>{label} FUERA DE RANGO</b>\n"
                f"{arrow} {value:.1f} {unit}\n"
                f"Umbral: {attention} {limits[attention]} {unit}\n"
                f"📍 Bogotá — {now_bogota.strftime('%Y-%m-%d %H:%M')} COT"
            )

            sent = await send_telegram(msg)
            if sent:
                _save_alert(sensor, value, limits[attention], attention, msg)

        # RESTABLECIDO (solo si antes estaba fuera de rango)
        elif _in_cooldown(sensor, "above") or _in_cooldown(sensor, "below"):
            bogota_tz = pytz.timezone('America/Bogota')
            now_bogota = datetime.now(bogota_tz)
            
            msg = (
                f"{emoji} <b>{label} RESTABLECIDO</b>\n"
                f"📥 {value:.1f} {unit} (en rango)\n"
                f"📍 Bogotá — {now_bogota.strftime('%Y-%m-%d %H:%M')} COT"
            )

            sent = await send_telegram(msg)
            if sent:
                _save_alert(sensor, value, limits["above"], "restored", msg)