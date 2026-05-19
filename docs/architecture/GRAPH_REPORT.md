# Graph Report - .  (2026-05-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 162 nodes · 271 edges · 16 communities (14 shown, 2 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c8a25a51`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 15|Community 15]]

## God Nodes (most connected - your core abstractions)
1. `get_supabase()` - 15 edges
2. `get_pg()` - 12 edges
3. `release_pg()` - 12 edges
4. `renderCharts()` - 11 edges
5. `get_cached_sensor_data()` - 8 edges
6. `renderHeatmap()` - 8 edges
7. `renderWeekly()` - 8 edges
8. `renderCycles()` - 8 edges
9. `ingest()` - 7 edges
10. `pg_fetch_all()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `sync()` --calls--> `run_sync()`  [INFERRED]
  api/routers/system.py → fetch/sync.py
- `FastAPI Entry Point` --references--> `Local PostgreSQL (Docker)`  [EXTRACTED]
  api/main.py → README.md
- `FastAPI Entry Point` --references--> `Supabase (Cloud PostgreSQL)`  [EXTRACTED]
  api/main.py → README.md
- `ESP32-S3 Sensor Node` --calls--> `FastAPI Entry Point`  [EXTRACTED]
  README.md → api/main.py
- `watchdog_job()` --calls--> `check_silence()`  [INFERRED]
  api/main.py → fetch/notifier.py

## Communities (16 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (22): allData, aplicarFiltro(), applyStats(), applyTheme(), chartLayout(), checkAlerts(), DEFAULT_THRESHOLDS, fillThresholdInputs() (+14 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (27): get_pg(), get_pool(), pg_available(), release_pg(), check_and_notify(), check_silence(), _in_cooldown(), init_sensor_states() (+19 more)

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (12): get_supabase(), save_to_supabase(), recover(), export_data(), get_data(), get_latest(), get_stats(), get_alerts() (+4 more)

### Community 3 - "Community 3"
Cohesion: 0.16
Nodes (12): Wrapper síncrono para APScheduler → llama a check_silence async., watchdog_job(), fetch_new_data(), get_last_received(), get_last_timestamp(), init_last_received(), Llama una sola vez al arrancar para cargar el último timestamp desde Supabase., Se llama después de insertar datos. Actualiza el timestamp en RAM. (+4 more)

### Community 4 - "Community 4"
Cohesion: 0.39
Nodes (16): baseLayout(), cache, clearSpinner(), errMsg(), escHtml(), fetchJSON(), getTheme(), renderAll() (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (11): FastAPI Entry Point, ESP32-S3 Sensor Node, Telegram Notifier, Data Reconciliation Service, ThingSpeak Sync Job, Analytics Dashboard Logic, Real-Time Dashboard Logic, Local PostgreSQL (Docker) (+3 more)

### Community 6 - "Community 6"
Cohesion: 0.20
Nodes (10): get_anomalies(), get_heatmap(), get_weekly(), Lecturas fuera de media ± sigma * desviación estándar., Promedio por hora del día (0-23h COT) para cada sensor., Promedio por día de la semana (0=Lun … 6=Dom)., get_cached_sensor_data(), _normalize_ts() (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.47
Nodes (4): init_firebase(), save_data(), fetch_chunk(), load_all_history()

### Community 8 - "Community 8"
Cohesion: 0.50
Nodes (4): Convierte un timestamp (datetime o str) a datetime UTC-aware., Observabilidad del estado de sincronización local → Supabase.     Muestra cuánt, sync_status(), _to_utc()

## Knowledge Gaps
- **9 isolated node(s):** `themeToggle`, `cache`, `allData`, `DEFAULT_THRESHOLDS`, `NEXUS Platform` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_supabase()` connect `Community 2` to `Community 1`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.199) - this node is a cross-community bridge._
- **Why does `get_cached_sensor_data()` connect `Community 6` to `Community 1`, `Community 2`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Why does `pg_fetch_all()` connect `Community 1` to `Community 2`, `Community 6`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `get_supabase()` (e.g. with `get_data()` and `get_latest()`) actually correct?**
  _`get_supabase()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `get_pg()` (e.g. with `ingest()` and `pg_fetch_all()`) actually correct?**
  _`get_pg()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `release_pg()` (e.g. with `ingest()` and `pg_fetch_all()`) actually correct?**
  _`release_pg()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `get_cached_sensor_data()` (e.g. with `get_heatmap()` and `get_weekly()`) actually correct?**
  _`get_cached_sensor_data()` has 5 INFERRED edges - model-reasoned connections that need verification._