import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
import subprocess
import logging
from fetch.database.supabase_client import get_supabase
from apscheduler.schedulers.background import BackgroundScheduler
from fetch.sync import run_sync

load_dotenv()

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nexus-w0yh.onrender.com",
        "http://127.0.0.1:5500",
        "http://localhost:5500", #eliminar
        "http://localhost:8000", #eliminar
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")

# ─── SCHEDULER: sync automático cada 5 min ───
scheduler = BackgroundScheduler()
scheduler.add_job(run_sync, "interval", minutes=5, id="auto_sync")
scheduler.start()

import atexit
atexit.register(lambda: scheduler.shutdown(nowait=True))


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
def get_data(limit: int = 100, start: str = None, end: str = None):
    supabase = get_supabase()
    
    if start or end:
        # Paginación automática para rangos de fecha
        all_data = []
        page_size = 1000
        offset = 0

        while True:
            query = (
                supabase.table("sensor_data")
                .select("*")
                .order("created_at", desc=True)
                .range(offset, offset + page_size - 1)
            )
            if start:
                query = query.gte("created_at", start)
            if end:
                query = query.lte("created_at", end)

            result = query.execute()
            all_data.extend(result.data)

            if len(result.data) < page_size:
                break  # ya no hay más páginas

            offset += page_size

        return {"total": len(all_data), "data": all_data}

    else:
        # Sin filtro: retorna solo los últimos N registros
        result = (
            supabase.table("sensor_data")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"total": len(result.data), "data": result.data}


@app.get("/data/latest")
def get_latest():
    supabase = get_supabase()
    result = (
        supabase.table("sensor_data")
        .select("*")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No hay datos disponibles")
    return result.data[0]


@app.get("/sync")
@app.head("/sync")
def sync():
    try:
        run_sync()
        return {"status": "ok", "message": "Sincronización completada ✅"}
    except Exception as e:
        logger.error("Error en /sync: %s", str(e), exc_info=True)
        return {"status": "error", "message": str(e)}