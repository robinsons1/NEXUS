from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from fetch.sync import get_last_received, init_last_received
from fetch.notifier import check_silence
from api.routers import data, analytics, ingest, system

# ─── LOGGING ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-10s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("nexus")

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def watchdog_job():
    """Wrapper síncrono para APScheduler → llama a check_silence async."""
    import asyncio
    asyncio.run(check_silence(get_last_received()))

init_last_received() 

# ─── SCHEDULER ───
scheduler = BackgroundScheduler()
from fetch.sync import run_sync
scheduler.add_job(run_sync, "interval", minutes=5, id="auto_sync")
scheduler.add_job(watchdog_job, "interval", minutes=2, id="watchdog")

from fetch.reconciliation import push_reconciliation, pull_reconciliation
scheduler.add_job(push_reconciliation, "interval", hours=1, id="push_reconciliation")
scheduler.add_job(pull_reconciliation, "cron", hour=3, minute=0, timezone="America/Bogota", id="pull_reconciliation")

scheduler.start()

atexit.register(lambda: scheduler.shutdown(wait=False))

# ─── ROUTERS ───
app.include_router(data.router)
app.include_router(analytics.router)
app.include_router(ingest.router)
app.include_router(system.router)

# ─── VIEWS (HTML) ───
@app.get("/")
def root():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))

@app.get("/dashboard")
def dashboard():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))

@app.get("/analytics")
def analytics_page():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "analytics.html"))

# ─── STATIC ───
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")