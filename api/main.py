import os
import sys

from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import os
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
        "https://nexus-w0yh.onrender.com"
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
                    .order("created_at", desc=False)   # ← asc para que values[-1] sea el más reciente
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
                # rows viene desc=True en limit, asc=False en rango → último siempre es values[-1] para rango
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