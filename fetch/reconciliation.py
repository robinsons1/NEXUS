import logging
from datetime import datetime, timezone, timedelta
from fetch.database.postgres_client import get_pg, release_pg
from fetch.database.supabase_client import get_supabase
from api.services.cache import DATA_CACHE, cache_lock

logger = logging.getLogger("nexus.reconciliation")

def push_reconciliation():
    """
    Busca registros locales en sensor_data y alert_history donde synced_to_supabase = FALSE.
    Los inserta (upsert) en Supabase por lotes y luego marca TRUE en local.
    """
    logger.info("Iniciando PUSH de reconciliación...")
    push_table_data("sensor_data", ["created_at", "field1", "field2", "field3", "tenant_id"], on_conflict="created_at,tenant_id")
    push_table_data("alert_history", ["created_at", "sensor", "value", "threshold", "direction", "message", "tenant_id"], on_conflict="created_at,sensor,tenant_id")
    # Invalidar caché para que la próxima consulta recargue datos reconciliados
    with cache_lock:
        DATA_CACHE["timestamp"] = 0
    logger.info("Finalizado PUSH de reconciliación.")

def push_table_data(table_name: str, columns: list[str], on_conflict: str | None = "created_at"):
    conn = get_pg()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cols_str = ", ".join(columns)
        cur.execute(f"SELECT {cols_str} FROM {table_name} WHERE synced_to_supabase = FALSE LIMIT 5000")
        rows = cur.fetchall()
        
        if not rows:
            return
            
        logger.info(f"PUSH: {len(rows)} registros pendientes en {table_name}")
        
        # Procesar en lotes de 1000
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            records = []
            created_ats = []
            for row in batch:
                record = {}
                for idx, col in enumerate(columns):
                    val = row[idx]
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    record[col] = val
                records.append(record)
                created_ats.append(record["created_at"])
                
            try:
                if on_conflict:
                    get_supabase().table(table_name).upsert(records, on_conflict=on_conflict).execute()
                else:
                    get_supabase().table(table_name).insert(records).execute()
                
                # Marcar como sincronizados en Postgres
                format_strings = ','.join(['%s'] * len(created_ats))
                cur.execute(f"""
                    UPDATE {table_name} 
                    SET synced_to_supabase = TRUE 
                    WHERE created_at IN ({format_strings})
                """, tuple(created_ats))
                conn.commit()
                logger.info(f"PUSH: Lote de {len(batch)} registros insertado y marcado en {table_name}.")
            except Exception as e:
                logger.error(f"PUSH: Error en lote de {table_name}: {e}")
                conn.rollback() # Solo rollback de los updates locales
                
        cur.close()
    except Exception as e:
        logger.error(f"PUSH: Error leyendo de Postgres: {e}")
    finally:
        release_pg(conn)

def pull_reconciliation():
    """
    Busca registros de las últimas 24 horas en Supabase (sensor_data y alert_history).
    Los inserta en PostgreSQL local si no existen.
    """
    logger.info("Iniciando PULL de reconciliación (últimas 24h)...")
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).isoformat()
    
    pull_table_data("sensor_data", ["created_at", "field1", "field2", "field3", "tenant_id"], yesterday, on_conflict="created_at, tenant_id")
    pull_table_data("alert_history", ["created_at", "sensor", "value", "threshold", "direction", "message", "tenant_id"], yesterday, on_conflict="created_at, sensor, tenant_id")
    # Invalidar caché para que la próxima consulta recargue datos reconciliados
    with cache_lock:
        DATA_CACHE["timestamp"] = 0
    logger.info("Finalizado PULL de reconciliación.")

def pull_table_data(table_name: str, columns: list[str], since_iso: str, on_conflict: str):
    try:
        res = get_supabase().table(table_name).select("*").gte("created_at", since_iso).execute()
        records = res.data
        if not records:
            return
            
        logger.info(f"PULL: Obtenidos {len(records)} registros de {table_name} desde Supabase.")
        
        conn = get_pg()
        if not conn:
            return
        try:
            cur = conn.cursor()
            inserted_count = 0
            
            for record in records:
                cols_str = ", ".join(columns)
                vals_str = ", ".join(["%s"] * len(columns))
                values = tuple(record.get(c) for c in columns)
                
                # Se utiliza la cláusula ON CONFLICT DO NOTHING de Postgres para ignorar duplicados
                cur.execute(f"""
                    INSERT INTO {table_name} ({cols_str}, synced_to_supabase)
                    VALUES ({vals_str}, TRUE)
                    ON CONFLICT ({on_conflict}) DO NOTHING
                """, values)
                inserted_count += cur.rowcount
            
            conn.commit()
            cur.close()
            if inserted_count > 0:
                logger.info(f"PULL: Insertados {inserted_count} nuevos registros en {table_name} local.")
        except Exception as e:
            logger.error(f"PULL: Error insertando en Postgres ({table_name}): {e}")
            if conn:
                conn.rollback()
        finally:
            release_pg(conn)
            
    except Exception as e:
        logger.error(f"PULL: Error obteniendo de Supabase ({table_name}): {e}")


# ── Estado de salud del sync en memoria ──────────────────────────────────────
_sync_health_state: str = "ok"   # "ok" | "desfasado"


def check_sync_health():
    """
    Comprueba si hay registros sin sincronizar con Supabase por más de 60 min.
    Envía alerta Telegram si se detecta desfase y otra cuando se corrige.
    Se ejecuta cada hora desde el scheduler.
    """
    import asyncio
    from fetch.notifier import send_telegram
    global _sync_health_state

    now = datetime.now(timezone.utc)
    conn = get_pg()
    if not conn:
        logger.warning("check_sync_health: Postgres no disponible, omitiendo")
        return

    oldest = None
    count = 0
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT MIN(t.created_at) AS oldest, COUNT(*) AS cnt
            FROM (
                SELECT created_at FROM sensor_data   WHERE synced_to_supabase = FALSE
                UNION ALL
                SELECT created_at FROM alert_history WHERE synced_to_supabase = FALSE
            ) AS t
        """)
        row = cur.fetchone()
        cur.close()
        if row:
            oldest, count = row[0], row[1]
    except Exception as e:
        logger.error(f"check_sync_health: error consultando Postgres: {e}")
        return
    finally:
        release_pg(conn)

    # ── Sin pendientes ────────────────────────────────────────────────────────
    if not oldest or count == 0:
        if _sync_health_state == "desfasado":
            msg = (
                "✅ <b>NEXUS Sync — Sincronización restablecida</b>\n"
                "Todos los registros han sido sincronizados con Supabase."
            )
            asyncio.run(send_telegram(msg))
            _sync_health_state = "ok"
            logger.info("check_sync_health: sincronización restablecida ✅")
        return

    # Normalizar timestamp
    if isinstance(oldest, str):
        oldest = datetime.fromisoformat(
            oldest.replace("+00:00", "").rstrip()
        ).replace(tzinfo=timezone.utc)
    elif oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)

    desfase_min = (now - oldest).total_seconds() / 60

    # ── Desfase > 60 min ─────────────────────────────────────────────────────
    if desfase_min > 60:
        if _sync_health_state == "desfasado":
            logger.info(
                f"check_sync_health: desfase {int(desfase_min)}min — alerta ya enviada"
            )
            return
        msg = (
            f"⚠️ <b>NEXUS Sync — Desfase detectado</b>\n"
            f"📦 {int(count)} registros sin sincronizar con Supabase.\n"
            f"⏱ Desfase: {int(desfase_min)} min (umbral: 60 min)\n"
            f"🕐 Más antiguo: {oldest.strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Verifica la conexión a Supabase o fuerza una reconciliación."
        )
        asyncio.run(send_telegram(msg))
        _sync_health_state = "desfasado"
        logger.warning(
            f"check_sync_health: alerta enviada — "
            f"{int(count)} pendientes, {int(desfase_min)}min de desfase"
        )
    else:
        # Desfase < 60 min pero había estado desfasado → restablecido
        if _sync_health_state == "desfasado":
            msg = (
                "✅ <b>NEXUS Sync — Desfase corregido</b>\n"
                f"Los registros han sido sincronizados. Desfase actual: {int(desfase_min)} min."
            )
            asyncio.run(send_telegram(msg))
            _sync_health_state = "ok"
            logger.info("check_sync_health: desfase corregido ✅")

