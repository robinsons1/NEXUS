import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

CHANNEL_ID = os.getenv("THINGSPEAK_CHANNEL_ID")
API_KEY = os.getenv("THINGSPEAK_API_KEY")

def get_latest_data(results=100):
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
    params = {
        "api_key": API_KEY,
        "results": results
    }
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Error al conectar: {response.status_code}")
        return None

    data = response.json()
    channel_info = data["channel"]
    df = pd.DataFrame(data["feeds"])
    df["created_at"] = pd.to_datetime(df["created_at"])
    
    print(f"Canal: {channel_info['name']}")
    print(f"Puntos obtenidos: {len(df)}")
    print(df.head())
    return df

if __name__ == "__main__":
    get_latest_data()
