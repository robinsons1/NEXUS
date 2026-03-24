import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.firestore import init_firebase, save_data
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ID = os.getenv("THINGSPEAK_CHANNEL_ID")
API_KEY = os.getenv("THINGSPEAK_API_KEY")

def get_last_timestamp():
    db = init_firebase()
    docs = (
        db.collection("sensor_data")
        .order_by("created_at", direction="DESCENDING")
        .limit(1)
        .stream()
    )
    for doc in docs:
        last_ts = doc.to_dict().get("created_at")
        print(f"📌 Último dato en Firestore: {last_ts}")
        return last_ts
    return None

def fetch_new_data(since):
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
    params = {
        "api_key": API_KEY,
        "results": 100,
        "start": since.strftime("%Y-%m-%d %H:%M:%S")
    }
    r = requests.get(url, params=params)
    feeds = r.json().get("feeds", [])
    return pd.DataFrame(feeds) if feeds else pd.DataFrame()

def sync():
    print("🔄 Iniciando sincronización incremental...")
    last_ts = get_last_timestamp()

    if last_ts is None:
        print("⚠️ No hay datos previos, corre load_history.py primero")
        return

    df = fetch_new_data(since=last_ts)

    if df.empty:
        print("✅ No hay datos nuevos por sincronizar")
        return

    df["created_at"] = pd.to_datetime(df["created_at"])
    # Excluir el último punto ya guardado
    df = df[df["created_at"] > last_ts]

    if df.empty:
        print("✅ Todo está actualizado")
        return

    print(f"🆕 Datos nuevos encontrados: {len(df)}")
    save_data(df, collection="sensor_data")
    print("✅ Sincronización completada")

if __name__ == "__main__":
    sync()
