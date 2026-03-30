import os
import sys
import logging
import atexit

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from fetch.database.supabase_client import get_supabase
from fetch.sync import run_sync

load_dotenv()

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nexus-w0yh.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")

# ─── SCHEDULER ───
scheduler = BackgroundScheduler()
scheduler.add_job(run_sync, "interval", minutes=5, id="auto_sync")
scheduler.start()
atexit.register(lambda: scheduler.shutdown(nowait=True))


@app.get("/")
def root():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))

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
                break

            offset += page_size

        return {"total": len(all_data), "data": all_data}

    else:
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
        logger.error("Error en /sync: %s", str(e), exc_info=True)  # detalle solo en logs
        return {"status": "error", "message": "Error interno al sincronizar"}  # ← mensaje genérico al usuario