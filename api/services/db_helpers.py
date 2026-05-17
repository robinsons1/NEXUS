import logging
from fetch.database.postgres_client import get_pg, release_pg

logger = logging.getLogger("nexus.db")

def pg_fetch_all(query: str, params: tuple = ()) -> list | None:
    conn = None
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute(query, params)
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        return rows
    except Exception as e:
        logger.warning(f"pg_fetch_all falló: {e}")
        return None
    finally:
        if conn:
            release_pg(conn)

def pg_fetch_one(query: str, params: tuple = ()) -> dict | None:
    conn = None
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute(query, params)
        cols = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        cur.close()
        return dict(zip(cols, row)) if row else None
    except Exception as e:
        logger.warning(f"pg_fetch_one falló: {e}")
        return None
    finally:
        if conn:
            release_pg(conn)
