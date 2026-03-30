import os
import pandas as pd
import requests
from dotenv import load_dotenv
from fetch.database.supabase_client import get_supabase

load_dotenv()

CHANNEL_ID = os.getenv("THINGSPEAK_CHANNEL_ID")
API_KEY    = os.getenv("THINGSPEAK_API_KEY")

START = "2026-03-26 20:52:08"
END   = "2026-03-30 15:28:07"

def recover():
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
    all_feeds = []
    page = 1

    while True:
        params = {
            "api_key": API_KEY,
            "results": 8000,
            "start": START,
            "end": END,
            "page": page
        }
        r = requests.get(url, params=params)
        feeds = r.json().get("feeds", [])
        if not feeds:
            break
        all_feeds.extend(feeds)
        print(f"📥 Página {page}: {len(feeds)} registros")
        if len(feeds) < 8000:
            break
        page += 1

    print(f"📥 Total obtenido de ThingSpeak: {len(all_feeds)}")

    if not all_feeds:
        print("⚠️ ThingSpeak no tiene datos en ese rango — el dispositivo no envió")
        return

    df = pd.DataFrame(all_feeds)
    df["created_at"] = pd.to_datetime(df["created_at"])

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
    supabase.table("sensor_data").upsert(records, on_conflict="created_at").execute()
    print(f"✅ {len(records)} registros recuperados en Supabase")

if __name__ == "__main__":
    recover()