import os
import logging
import requests
import pandas as pd
from dotenv import load_dotenv
from fetch.database.supabase_client import get_supabase
from fetch.notifier import check_and_notify
import asyncio

# --- logging inicial
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("nexus.sync")

load_dotenv()

CHANNEL_ID = os.getenv("THINGSPEAK_CHANNEL_ID")
API_KEY    = os.getenv("THINGSPEAK_API_KEY")


def get_last_timestamp():
    supabase = get_supabase()
    result = (
        supabase.table("sensor_data")
        .select("created_at")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        last_ts = pd.to_datetime(result.data[0]["created_at"])
        logger.info(f"Último dato en Supabase: {last_ts}")
        return last_ts
    return None


def fetch_new_data(since):
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
    all_feeds = []
    page = 1

    while True:
        params = {
            "api_key": API_KEY,
            "results": 8000,
            "start": since.strftime("%Y-%m-%d %H:%M:%S"),
            "page": page
        }
        r = requests.get(url, params=params)
        feeds = r.json().get("feeds", [])

        if not feeds:
            break

        all_feeds.extend(feeds)
        logger.info(f"ThingSpeak página {page} — {len(feeds)} registros obtenidos")

        if len(feeds) < 8000:
            break

        page += 1

    logger.info(f"Total obtenido de ThingSpeak: {len(all_feeds)} registros")
    return pd.DataFrame(all_feeds) if all_feeds else pd.DataFrame()

def save_to_supabase(df):
    if df.empty:
        logger.info("run_sync: no hay datos nuevos para insertar")
        return

    try:
        supabase = get_supabase()
        records = []
        for _, row in df.iterrows():
            record = {
                "created_at": row["created_at"].isoformat(),
                "field1": float(row["field1"]) if row["field1"] else None,
                "field2": float(row["field2"]) if row["field2"] else None,
                "field3": float(row["field3"]) if row["field3"] else None,
            }
            records.append(record)

        # upsert en lote (SIN notificación duplicada)
        if records:
            supabase.table("sensor_data").upsert(
                records, on_conflict="created_at"
            ).execute()
            logger.info(f"Insertados/actualizados {len(records)} registros en Supabase")

        # ✅ NOTIFICACIÓN ÚNICA: solo el ÚLTIMO registro
        if records:
            last_record = records[-1]
            asyncio.run(check_and_notify(last_record))

    except Exception as e:
        logger.error(f"Error guardando en Supabase: {e}", exc_info=True)

def run_sync():
    logger.info("run_sync: started")
    last_ts = get_last_timestamp()
    logger.info(f"run_sync: last_ts = {last_ts}")

    if last_ts is None:
        logger.warning("run_sync: no hay datos previos en Supabase")
        return

    df = fetch_new_data(since=last_ts)
    logger.info(f"run_sync: obtenidos {len(df)} registros de ThingSpeak")

    if df.empty:
        logger.info("run_sync: no hay datos nuevos")
        return

    # Convertir las columnas necesarias a Timestamp
    df["created_at"] = pd.to_datetime(df["created_at"])

    # Asegurar que last_ts es Timestamp
    if last_ts is not None:
        last_ts = pd.to_datetime(last_ts)

    # Filtrar solo datos nuevos
    df = df[df["created_at"] > last_ts]
    logger.info(f"run_sync: datos nuevos = {len(df)}")

    # Guardar
    save_to_supabase(df)
    logger.info("run_sync: finalizado ✅")

    # Telegram
    if not df.empty:
        last_record = df.iloc[-1].to_dict()

if __name__ == "__main__":
    run_sync()