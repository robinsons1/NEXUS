import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch.thingspeak import get_latest_data
from database.firestore import init_firebase, save_data
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

def load_all_history():
    print("📥 Iniciando carga histórica completa...")

    # Bloque 1: primeros 8000 puntos (primera mitad de los 20 días)
    print("Descargando bloque 1...")
    df1 = fetch_chunk(start="2026-03-04 00:00:00", end="2026-03-14 23:59:59")
    time.sleep(2)

    # Bloque 2: segunda mitad hasta hoy
    print("Descargando bloque 2...")
    df2 = fetch_chunk(start="2026-03-15 00:00:00")
    time.sleep(2)

    # Unir y limpiar
    df = pd.concat([df1, df2], ignore_index=True)
    df.drop_duplicates(subset="created_at", inplace=True)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df.sort_values("created_at", inplace=True)

    print(f"✅ Total puntos a guardar: {len(df)}")

    save_data(df, collection="sensor_data")
    print("🎉 Carga histórica completada")


if __name__ == "__main__":
    load_all_history()
