import os
import logging
import atexit
from typing import Optional

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
    allow_origins=["https://nexus-w0yh.onrender.com"],
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
        logger.error("Error en /sync: %s", str(e), exc_info=True)
        return {"status": "error", "message": "Error interno al sincronizar"}  # ← mensaje genérico


@app.get("/data/stats")
def get_stats(limit: int = 100, start: Optional[str] = None, end: Optional[str] = None):
    try:
        supabase = get_supabase()

        if start and end:
            all_rows = []
            page_size = 1000
            offset = 0
            while True:
                result = (
                    supabase.table("sensor_data")
                    .select("field1, field2, field3, created_at")
                    .gte("created_at", start)
                    .lte("created_at", end)
                    .order("created_at", desc=False)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                all_rows.extend(result.data)
                if len(result.data) < page_size:
                    break
                offset += page_size
            rows = all_rows
        else:
            result = (
                supabase.table("sensor_data")
                .select("field1, field2, field3, created_at")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            rows = result.data

        if not rows:
            raise HTTPException(status_code=404, detail="No hay datos")

        def calc_stats(field):
            values = [r[field] for r in rows if r.get(field) is not None]
            if not values:
                return None
            return {
                "last":  round(values[-1] if (start and end) else values[0], 2),
                "min":   round(min(values), 2),
                "max":   round(max(values), 2),
                "avg":   round(sum(values) / len(values), 2),
                "count": len(values),
            }

        return {
            "temperature": calc_stats("field1"),
            "humidity":    calc_stats("field2"),
            "pressure":    calc_stats("field3"),
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error calculando estadísticas")