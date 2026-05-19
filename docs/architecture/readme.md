# 🧠 Arquitectura y análisis técnico — NEXUS

Documentación técnica interna del proyecto NEXUS. Esta sección contiene el análisis arquitectónico completo, estructura modular, relaciones internas, análisis Graphify, comunidades funcionales, observabilidad, sincronización híbrida y dependencias críticas.

***

## ⚙️ Filosofía de diseño

El sistema fue diseñado bajo los siguientes principios:

- **Resiliencia offline** — continúa operando sin conexión cloud
- **Sincronización híbrida** — bidireccional y automática entre local y cloud
- **Modularidad** — separación clara de responsabilidades por módulo
- **Observabilidad** — monitoreo continuo del estado de todos los componentes
- **Redundancia** — múltiples capas de respaldo de datos
- **Escalabilidad incremental** — preparado para multi-tenant y crecimiento futuro
- **Desacoplamiento funcional** — bajo acoplamiento entre comunidades

***

## 🧱 Arquitectura general

NEXUS implementa una arquitectura híbrida edge/cloud orientada a monitoreo IoT resiliente.

```text
ESP32-S3
   │
   ├── ThingSpeak
   └── POST /ingest
           │
           ▼
FastAPI Backend
           │
    ┌──────┴──────┐
    ▼             ▼
PostgreSQL     Supabase
(local)         (cloud)
    │
    ▼
Dashboard + Analytics + Telegram
```

### Flujo de datos detallado

```text
ESP32
   │
   ▼
FastAPI /ingest
   │
   ▼
PostgreSQL local
   │
   ├── Dashboard
   ├── Analytics
   ├── Telegram
   └── Sync Service
           │
           ▼
        Supabase
```

***

## 📊 Análisis con Graphify

El proyecto fue analizado utilizando **Graphify**, una herramienta de generación de grafos semánticos para codebases complejas.

Graphify permitió:

- Detectar dependencias críticas entre módulos
- Identificar módulos centrales ("God Nodes") y puntos críticos del sistema
- Visualizar relaciones entre servicios
- Construir comunidades funcionales claramente separadas
- Analizar arquitectura IoT híbrida
- Mapear interacciones backend/frontend
- Detectar conexiones implícitas entre componentes

### Herramientas utilizadas

| Herramienta | Función |
|---|---|
| Graphify | Construcción del knowledge graph |
| Tree-sitter | Extracción AST |
| NetworkX | Motor de grafos |
| Leiden Clustering | Detección de comunidades |
| Gemini API | Extracción semántica |
| PyVis / D3 | Visualización interactiva |

### Archivos generados

| Archivo | Descripción |
|---|---|
| `GRAPH_REPORT.md` | Análisis semántico completo |
| `GRAPH_TREE.html` | Árbol interactivo del proyecto |
| `graph.json` | Grafo estructural completo |

```text
docs/architecture/
├── GRAPH_REPORT.md
├── GRAPH_TREE.html
└── graph.json
```

### Regenerar análisis Graphify

**Instalar dependencias:**

```bash
pip install graphifyy openai pyvis
```

**Configurar API Key:**

```powershell
# PowerShell
$env:GEMINI_API_KEY="TU_API_KEY"
```

**Ejecutar análisis:**

```bash
graphify .
graphify cluster-only .
graphify tree
```

***

## 🧩 Comunidades funcionales detectadas

Graphify detectó múltiples comunidades funcionales claramente separadas con alto grado de cohesión interna y bajo acoplamiento relativo.

### 📥 Ingestión de datos

Responsable de:

- Recibir datos del ESP32 vía `POST /ingest`
- Validación y normalización de lecturas
- Inserción inicial en PostgreSQL

Componentes principales:

```text
/api/ingest
fetch_new_data()
sensor_data
```

### 🗄️ Persistencia

Gestiona almacenamiento híbrido en:

- PostgreSQL local (primario)
- Supabase cloud (respaldo)

Componentes principales:

```text
get_pg()
release_pg()
get_supabase()
```

### 📊 Dashboard y visualización

Responsable de:

- Gráficos y heatmaps
- Métricas y estadísticas
- Render dinámico del frontend

Componentes principales:

```text
renderCharts()
analytics
frontend cache
```

### 🔄 Sincronización

Implementa sincronización bidireccional automática:

**PUSH:**
```text
PostgreSQL → Supabase
```

**PULL:**
```text
Supabase → PostgreSQL
```

Objetivos:
- Evitar pérdida de datos ante fallos de red
- Tolerancia offline
- Reconciliación automática con idempotencia

### 🚨 Alertas y monitoreo

Sistema de alertas automáticas:

- Watchdog de silencio (alerta si no llegan datos en ≥10 min)
- Health checks continuos
- Estado de sincronización en tiempo real
- Alertas Telegram sin rebote ni spam

### 📈 Analítica avanzada

Módulos responsables de:

- Detección de anomalías (± Sigma)
- Análisis de tendencias semanales
- Métricas temporales y ciclos diarios
- Correlación Pearson entre sensores
- Forecast predictivo a 1 hora

***

## 🌟 God Nodes detectados

Graphify identificó los nodos más conectados y críticos del sistema. Estos representan el núcleo operativo que más impacto tiene en la estabilidad global.

| Nodo | Función |
|---|---|
| `get_supabase()` | Acceso cloud — punto central de conexión a Supabase |
| `get_pg()` | Acceso PostgreSQL — conexión a BD primaria |
| `release_pg()` | Liberación de conexiones — evita pool exhaustion |
| `renderCharts()` | Renderizado frontend — punto central de visualización |
| `get_cached_sensor_data()` | Caché principal — reduce carga en PostgreSQL |

***

## 🔍 Hallazgos importantes

### Arquitectura híbrida moderna

El análisis detectó integración directa y desacoplada entre:

- ESP32-S3 (edge)
- FastAPI (backend)
- PostgreSQL (persistencia local)
- Supabase (cloud)
- ThingSpeak (buffer IoT)
- Telegram (notificaciones)

Esto forma una arquitectura edge/cloud resiliente con múltiples capas de redundancia.

### Alta cohesión modular

Las comunidades detectadas muestran:

- Separación funcional clara entre ingestión, sincronización, analítica y alertas
- Bajo acoplamiento relativo entre módulos
- Responsabilidades bien definidas en cada capa

### Componentes experimentales detectados

Graphify detectó algunos nodos parcialmente aislados:

```text
themeToggle
DEFAULT_THRESHOLDS
cache
```

Posibles causas:
- Módulos en desarrollo activo
- Funcionalidades futuras pendientes de integración
- Desacoplamiento parcial intencional

***

## 🧠 Estrategias de rendimiento

El backend implementa múltiples capas de optimización:

- **Caché incremental en RAM** — primera carga descarga 60 días; actualizaciones solo traen registros nuevos desde el último `created_at`
- **TTL caching** — 5 minutos de vida de caché
- **Eager Loading** — carga anticipada de datos frecuentes
- **Thread Locks anti-stampede** — evita múltiples cargas simultáneas de caché
- **Queries optimizadas** con índices en `created_at DESC` y `tenant_id`
- **Descarga parcial** — reduce llamadas cloud costosas

Objetivo: minimizar carga en PostgreSQL, mejorar latencia y reducir costos cloud.

***

## 🔒 Estrategias de resiliencia

NEXUS implementa:

- Fallback PostgreSQL ↔ Supabase en todos los endpoints de lectura
- Sincronización incremental automática vía APScheduler
- Watchdog automático con alertas Telegram
- Backups externos diarios a Google Drive (rclone)
- Redundancia ThingSpeak como buffer de envío del ESP32
- Observabilidad continua vía `/sync/status` y `/status`
- `init_sensor_states()` — carga último estado de alerta al arrancar, evitando duplicados tras reinicios
- `_last_alert_time()` — consulta Postgres primero y Supabase como fallback para cooldown en modo offline

***

## 📂 Estructura lógica del proyecto

```text
NEXUS/
├── api/
│   ├── routers/         # Rutas de la API (analytics, data, ingest, system)
│   ├── services/        # Servicios de caché y base de datos
│   └── main.py
├── fetch/
│   ├── database/        # Clientes BD (Postgres, Supabase)
│   ├── notifier.py
│   ├── reconciliation.py
│   ├── sync.py
│   └── thingspeak.py
├── frontend/
├── analytics/
├── services/
├── sync/
├── docs/
│   ├── architecture/
│   ├── deployment/
│   └── images/
├── backups/
└── docker/
```

***

## 📈 Escalabilidad futura

Planeado:

- Multi-tenant real con aislamiento por `tenant_id`
- JWT Authentication para todos los endpoints
- Named Cloudflare Tunnel permanente
- Métricas históricas avanzadas y estacionales
- Observabilidad avanzada con Grafana + Prometheus + Loki
- Dashboards industriales
- ML para predicción ambiental (forecasting temporal)
- Migración a infraestructura doméstica completa (Debian 12)

***

## 🧪 Futuras integraciones

### IoT

- MQTT
- Home Assistant
- Node-RED

### Observabilidad

- Grafana
- Prometheus
- Loki

### IA

- Detección predictiva de anomalías
- Forecasting ambiental
- Modelos temporales para análisis estacional
- Edge AI en ESP32

***

## 👤 Autor

**Robinson Segura Aponte**
[github.com/robinsons1](https://github.com/robinsons1)