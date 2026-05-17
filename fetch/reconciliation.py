import logging
from datetime import datetime, timezone, timedelta
from fetch.database.postgres_client import get_pg, release_pg
from fetch.database.supabase_client import get_supabase

logger = logging.getLogger("nexus.reconciliation")

def push_reconciliation():
    """
    Busca registros locales en sensor_data y alert_history donde synced_to_supabase = FALSE.
    Los inserta (upsert) en Supabase por lotes y luego marca TRUE en local.
    """
    logger.info("Iniciando PUSH de reconciliación...")
    push_table_data("sensor_data", ["created_at", "field1", "field2", "field3", "tenant_id"], on_conflict="created_at,tenant_id")
    push_table_data("alert_history", ["created_at", "sensor", "value", "threshold", "direction", "message", "tenant_id"], on_conflict="created_at,sensor,tenant_id")
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
