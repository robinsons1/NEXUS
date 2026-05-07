# fetch/database/postgres_client.py
import os
import logging
import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nexus.postgres")

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        url = os.getenv("POSTGRES_URL")
        if not url:
            raise ValueError("POSTGRES_URL debe estar en el .env")
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 10, dsn=url)
        logger.info("Pool PostgreSQL local iniciado ✅")
    return _pool

def get_pg():
    return get_pool().getconn()

def release_pg(conn):
    get_pool().putconn(conn)

def pg_available() -> bool:
    try:
        conn = get_pg()
        release_pg(conn)
        return True
    except Exception as e:
        logger.warning(f"Postgres local no disponible: {e}")
        return False