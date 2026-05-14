import logging
from fetch.database.postgres_client import get_pg, release_pg

logger = logging.getLogger("nexus.db")

def pg_fetch_all(query: str, params: tuple = ()) -> list | None:
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute(query, params)
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        release_pg(conn)
        return rows
    except Exception as e:
        logger.warning(f"pg_fetch_all falló: {e}")
        return None

def pg_fetch_one(query: str, params: tuple = ()) -> dict | None:
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute(query, params)
        cols = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        cur.close()
        release_pg(conn)
        return dict(zip(cols, row)) if row else None
    except Exception as e:
        logger.warning(f"pg_fetch_one falló: {e}")
        return None
