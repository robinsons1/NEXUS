from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os

load_dotenv()

app = FastAPI(title="Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS"))
        firebase_admin.initialize_app(cred)
    return firestore.client()

@app.get("/")
def root():
    return {"status": "Nexus API funcionando ✅"}

@app.get("/data")
def get_data(limit: int = 100):
    db = get_db()
    docs = (
        db.collection("sensor_data")
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    data = []
    for doc in docs:
        d = doc.to_dict()
        d["created_at"] = str(d["created_at"])
        data.append(d)
    return {"total": len(data), "data": data}

@app.get("/data/latest")
def get_latest():
    db = get_db()
    docs = (
        db.collection("sensor_data")
        .order_by("created_at", direction="DESCENDING")
        .limit(1)
        .stream()
    )
    for doc in docs:
        d = doc.to_dict()
        d["created_at"] = str(d["created_at"])
        return d
