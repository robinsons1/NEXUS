import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import get_supabase
import requests
import pandas as pd
from dotenv import load_dotenv
import time

load_dotenv()

CHANNEL_ID = os.getenv("THINGSPEAK_CHANNEL_ID")
API_KEY = os.getenv("THINGSPEAK_API_KEY")
CHUNK_SIZE = 8000


def fetch_chunk(start=None, end=None):
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
    params = {"api_key": API_KEY, "results": CHUNK_SIZE}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    r = requests.get(url, params=params)
    feeds = r.json().get("feeds", [])
    print(f"  → Chunk obtenido: {len(feeds)} puntos")
    return pd.DataFrame(feeds)


def save_to_supabase(df):
    supabase = get_supabase()

    def safe_float(val):
        try:
            f = float(val)
            return None if pd.isna(f) else f
        except (ValueError, TypeError):
            return None

    records = [
        {
            "created_at": row["created_at"],
            "field1": safe_float(row["field1"]),
            "field2": safe_float(row["field2"]),
            "field3": safe_float(row["field3"]),
        }
        for _, row in df.iterrows()
    ]
    for i in range(0, len(records), 500):
        chunk = records[i:i+500]
        supabase.table("sensor_data").insert(chunk).execute()
        print(f"  ✅ {i + len(chunk)} registros insertados...")
        time.sleep(0.5)


def load_history_supabase():
    print("📥 Iniciando carga histórica ThingSpeak → Supabase...")

    print("Descargando bloque 1...")
    df1 = fetch_chunk(start="2026-03-04 00:00:00", end="2026-03-14 23:59:59")
    time.sleep(2)

    print("Descargando bloque 2...")
    df2 = fetch_chunk(start="2026-03-15 00:00:00")
    time.sleep(2)

    df = pd.concat([df1, df2], ignore_index=True)
    df.drop_duplicates(subset="created_at", inplace=True)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df.sort_values("created_at", inplace=True)

    print(f"✅ Total puntos a guardar: {len(df)}")
    save_to_supabase(df)
    print("🎉 Carga histórica en Supabase completada")


if __name__ == "__main__":
    load_history_supabase()