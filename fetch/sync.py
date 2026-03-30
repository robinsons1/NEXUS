import os
import logging
import requests
import pandas as pd
from dotenv import load_dotenv
from fetch.database.supabase_client import get_supabase

load_dotenv()

logger = logging.getLogger("nexus.sync")

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
    try:
        supabase = get_supabase()
        records = [
            {
                "created_at": row["created_at"].isoformat(),
                "field1": float(row["field1"]) if row["field1"] else None,
                "field2": float(row["field2"]) if row["field2"] else None,
                "field3": float(row["field3"]) if row["field3"] else None,
            }
            for _, row in df.iterrows()
        ]
        supabase.table("sensor_data").upsert(
            records, on_conflict="created_at"
        ).execute()
        logger.info(f"Insertados {len(records)} registros en Supabase")
    except Exception as e:
        logger.error(f"Error guardando en Supabase: {e}", exc_info=True)


def run_sync():
    logger.info("Iniciando sincronización incremental...")
    last_ts = get_last_timestamp()

    if last_ts is None:
        logger.warning("No hay datos previos en Supabase")
        return

    df = fetch_new_data(since=last_ts)

    if df.empty:
        logger.info("No hay datos nuevos por sincronizar")
        return

    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df[df["created_at"] > last_ts]

    if df.empty:
        logger.info("Todo está actualizado")
        return

    logger.info(f"Datos nuevos encontrados: {len(df)}")
    save_to_supabase(df)
    logger.info("Sincronización completada ✅")


if __name__ == "__main__":
    run_sync()