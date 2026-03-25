from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
import subprocess

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nexus-w0yh.onrender.com", "http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")

def get_db():
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS"))
        firebase_admin.initialize_app(cred)
    return firestore.client()

@app.get("/")
def root():
    return {"status": "Nexus API funcionando ✅"}

@app.get("/health")
@app.head("/health")
def health():
    return JSONResponse({"status": "ok"})

@app.get("/dashboard")
def dashboard():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))

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

@app.post("/sync")
def sync():
    try:
        result = subprocess.run(
            ["python", "fetch/sync.py"],
            capture_output=True, text=True, cwd=BASE_DIR
        )
        return {"status": "ok", "output": result.stdout, "error": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}