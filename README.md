# 🚀 NEXUS

Sistema IoT híbrido edge/cloud para monitoreo ambiental en tiempo real, analítica avanzada y sincronización resiliente entre infraestructura local y cloud.

🌐 **Demo en vivo:** [nexus-w0yh.onrender.com](https://nexus-w0yh.onrender.com)
🖥️ **Servidor local:** [mechanisms-ave-invention-stakeholders.trycloudflare.com](https://mechanisms-ave-invention-stakeholders.trycloudflare.com)

> **En desarrollo activo** — Versión 0.9.3 | [Historial de cambios](#-roadmap)

***

## 🧭 Acceso rápido

- ⚡ **Principiante** → Ve a [Instalación rápida](#-instalación-rápida)
- 🧑‍💻 **Desarrollador** → Lee [Arquitectura técnica](docs/architecture/readme.md)
- 🔧 **DevOps** → Lee [Deployment e infraestructura](docs/deployment/readme.md)
- 📚 **Todo** → Explora [Documentación técnica](#-documentación-técnica)

***

## 🌟 Características principales

### 📡 Adquisición de datos IoT

- Recepción de datos desde ESP32-S3 vía `POST /ingest`
- Envío paralelo a ThingSpeak (redundancia de envío garantizada)
- Endpoint seguro con autenticación `X-API-Key`
- Validación y normalización automática de lecturas

### 🗄️ Arquitectura híbrida

- PostgreSQL local en Docker como base de datos primaria (multi-tenant ready)
- Supabase cloud como respaldo y sincronización
- Dual-write: escritura simultánea en ambas bases de datos
- Sistema PUSH/PULL bidireccional con reconciliación automática
- Resiliencia offline y fallback automático Postgres → Supabase

### 📊 Dashboard analítico

- Visualización en tiempo real con auto-refresco cada 5 minutos
- Heatmaps de temperatura por hora del día
- Análisis de tendencias, correlación Pearson, ciclos y forecast a 1 hora
- Detección de anomalías (Desviación estándar ± Sigma)
- Exportación de datos en CSV directamente desde el backend
- Modo oscuro / claro con persistencia en localStorage
- Alertas visuales con umbrales configurables

### 🚨 Alertas automáticas

- Watchdog de silencio: alerta Telegram si no llegan datos en 10 minutos
- Alertas Telegram con lógica de estado (sin spam, sin rebote)
- Health checks con UptimeRobot en `/health`
- Endpoint `/sync/status` con observabilidad del estado de sincronización

### ⚡ Optimización y rendimiento

- Caché incremental en RAM con Eager Loading
- TTL de 5 minutos y Thread Locks anti-stampede
- Primera carga descarga 60 días; actualizaciones posteriores solo traen registros nuevos
- Queries optimizadas con índices en `created_at DESC` y `tenant_id`

***

## 🧠 Arquitectura general

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

***

## 🛠️ Stack tecnológico

| Área | Tecnologías |
|---|---|
| Sensores / Fuente | ESP32-S3 + DHT11 + BMP280 |
| Envío de datos | ThingSpeak (buffer) + POST directo al servidor local |
| Base de datos primaria | PostgreSQL local Docker `nexus_postgres` — multi-tenant ready (`tenant_id`) |
| Base de datos respaldo | Supabase (PostgreSQL cloud) |
| Backend API | Python + FastAPI |
| Frontend | HTML5 + CSS3 + Vanilla JS + Plotly.js |
| Sincronización | APScheduler + Threading Locks |
| Notificaciones | Telegram Bot API |
| Hosting actual | Render.com + Servidor doméstico (Debian 12) |
| Túnel público | Cloudflare Tunnel (trycloudflare.com — temporal) |
| Backup / Sync | rclone + Google Drive + Docker cron |
| Analytics | Pandas, NumPy |
| Arquitectura | Graphify, NetworkX |

## ⚡ Instalación rápida

**[📖 Guía completa en `docs/deployment/readme.md`](docs/deployment/readme.md)**

### 1. Clonar repositorio

```bash
git clone https://github.com/robinsons1/NEXUS.git
cd NEXUS
```

### 2. Crear entorno virtual

**Windows:**

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
```

Variables requeridas:

```env
# ThingSpeak
THINGSPEAK_CHANNEL_ID=
THINGSPEAK_READ_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# Seguridad ingest
INGEST_API_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# PostgreSQL local
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
```

### 5. Levantar PostgreSQL con Docker

```bash
docker network create nexus_net

docker run -d \
  --name nexus_postgres \
  --network nexus_net \
  -e POSTGRES_DB=nexus \
  -e POSTGRES_USER=nexus \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16
```

### 6. Ejecutar backend

```bash
python -m uvicorn api.main:app --reload
```

Servidor disponible en: `http://localhost:8000`

> ⚠️ Para pruebas locales, cambiar `const API = "http://127.0.0.1:8000"` en `frontend/app.js`.
> Antes de cualquier commit, revertir a `const API = "https://nexus-w0yh.onrender.com"`.

***

## 🔌 Endpoints disponibles

> 📖 **Referencia completa**: Ver [`docs/deployment/readme.md#observabilidad`](docs/deployment/readme.md#-observabilidad--endpoints-clave) para más detalles sobre sincronización y debugging.

| Endpoint | Método | Descripción |
|---|---|---|
| **Dashboard** |
| `/` | GET | Dashboard web Real-Time |
| `/dashboard` | GET | Alias de `/` — mismo dashboard principal |
| `/analytics` | GET | Dashboard de Análisis Histórico |
| **Datos** |
| `/data` | GET | Registros del sensor. Params: `limit` (def. 100), `offset` (def. 0), `start` (ISO), `end` (ISO) |
| `/data/latest` | GET | Último registro insertado |
| `/data/stats` | GET | Estadísticas agregadas (min/max/avg/last). Params: `limit` (def. 100), `start` (ISO), `end` (ISO) |
| `/data/export` | GET | Exportar datos. Params: `format` (def. `csv`), `start` (ISO), `end` (ISO), `limit` (def. 1000) |
| `/data/heatmap` | GET | Promedio por hora del día (0-23 h COT). Params: `days` (def. 30) |
| `/data/weekly` | GET | Promedio por día de la semana. Params: `days` (def. 60) |
| `/data/anomalies` | GET | Lecturas fuera de media ± σ·std. Params: `days` (def. 7), `sigma` (def. 2.0) |
| `/sensors` | GET | Metadata del canal y sensores (DHT11, BMP280) |
| **Alertas & Monitoreo** |
| `/alerts` | GET | Historial de alertas Telegram. Params: `limit` (def. 50) |
| `/config/thresholds` | GET | Umbrales de alerta configurados (temperatura, humedad, presión) |
| `/health` | GET/HEAD | Health check — usado por UptimeRobot |
| **Sincronización & Estado** |
| `/sync` | GET/HEAD | Sincronización manual ThingSpeak → BDs |
| `/sync/status` | GET | Observabilidad del sync local→Supabase: pendientes, desfase en minutos y estado |
| `/status` | GET | Estado en tiempo real de PostgreSQL local y Supabase: conteo de registros, diff e `in_sync` |
| **Ingestión de datos** |
| `/ingest` | POST | Recepción directa desde ESP32. Requiere header `X-API-Key`. Body: `field1` (°C), `field2` (%), `field3` (hPa, opcional) |
| **Documentación** |
| `/docs` | GET | Documentación interactiva Swagger UI |
| `/robots.txt` | GET | Directivas de indexación para crawlers |

***

## 📂 Estructura del proyecto

```text
NEXUS/
├── .github/                     # Workflows y configuración de GitHub
├── api/
│   ├── routers/                 # Rutas de la API (analytics, data, ingest, system)
│   ├── services/                # Servicios de caché y base de datos
│   └── main.py                  # Punto de entrada de FastAPI
├── fetch/
│   ├── database/                # Clientes de BD (Postgres, Supabase)
│   ├── load_history.py          # Scripts de migración
│   ├── load_history_supabase.py
│   ├── notifier.py              # Gestión de alertas (Telegram y DB)
│   ├── reconciliation.py        # Jobs de reconciliación (PUSH/PULL)
│   ├── recover.py               # Scripts de recuperación
│   ├── sync.py                  # Job principal de sincronización (ThingSpeak)
│   └── thingspeak.py            # Cliente de ThingSpeak
├── frontend/
│   ├── analytics.html           # Vista de análisis histórico
│   ├── analytics.js             # Lógica del dashboard de análisis
│   ├── app.js                   # Lógica del dashboard principal
│   ├── index.html               # Vista del dashboard principal
│   └── style.css                # Estilos globales
├── docs/
│   ├── architecture/            # 🧠 Análisis técnico y Graphify
│   │   └── readme.md
│   ├── deployment/              # 🚀 Guía operacional y deploy
│   │   └── readme.md
│   └── images/                  # Capturas del dashboard
├── docker/
├── backups/
├── .env.example                 # Variables de entorno de ejemplo
├── render.yaml                  # Configuración de despliegue en Render
├── requirements.txt             # Dependencias de Python
└── LICENSE
```

> 📍 **Documentación detallada**:
> - [`docs/architecture/readme.md`](docs/architecture/readme.md) — Análisis arquitectónico profundo
> - [`docs/deployment/readme.md`](docs/deployment/readme.md) — Setup, Docker, deployment y mantenimiento

***

## 🔒 Seguridad

Implementado actualmente:

- API Key (`X-API-Key`) para `POST /ingest` — solo el ESP32 autorizado puede insertar datos
- Sanitización XSS en frontend: escapado de variables dinámicas en `innerHTML`
- RLS (Row Level Security) en Supabase
- Docker network aislada (`nexus_net`) — comunicación interna sin exponer puertos
- Thread Locks anti-stampede en caché
- Fallback automático PostgreSQL ↔ Supabase
- Endpoint `/robots.txt` para proteger rutas de API de indexación

Pendiente:

- JWT Authentication para endpoints de lectura
- Cloudflare Access como capa de red
- Dominio personalizado con Named Tunnel permanente

***

## 📈 Roadmap

### ✅ Implementado (Fases 1–10)

- [x] Backend FastAPI modular (`routers/` y `services/`)
- [x] PostgreSQL local en Docker como BD primaria
- [x] Supabase sync (dual-write + fallback)
- [x] Dashboard analítico multipágina
- [x] Caché incremental con Eager Loading y TTL 5 min
- [x] Watchdog Telegram + historial de alertas
- [x] Arquitectura híbrida edge/cloud
- [x] Backup automatizado a Google Drive (rclone, cron diario)
- [x] Reconciliación PUSH/PULL bidireccional automática
- [x] Idempotencia y unicidad con Upserts sin duplicados
- [x] Observabilidad del sync (`/sync/status`)
- [x] API Key en `/ingest`
- [x] Multi-tenant preparado (`tenant_id`)
- [x] Migración histórica completa: 41,622 registros + 687 alertas

### 🚧 En desarrollo (Fase 9 parcial)

- [ ] JWT Authentication para endpoints de lectura
- [ ] Cloudflare Access

### 🗓️ Pendiente

- [ ] Named Cloudflare Tunnel permanente (Fase 12)
- [ ] Dominio propio
- [ ] Migración al servidor doméstico como hosting principal
- [ ] Dashboards avanzados con métricas históricas estacionales (Fase 11)
- [ ] Forecasting ambiental avanzado
- [ ] Multi-tenant real

### 🧪 Futuras integraciones

- **IoT:** MQTT, Home Assistant, Node-RED
- **Observabilidad:** Grafana, Prometheus, Loki
- **IA:** detección predictiva, forecasting, modelos temporales, Edge AI

***

## 🌿 Ramas Git

| Rama | Uso |
|---|---|
| `main` | Producción (Render) |
| `dev` | Desarrollo activo |

Flujo: trabajar en `dev` → resolver conflictos → merge a `main`.

***

## 📚 Documentación técnica

> 📌 **Guía de lectura**: Comienza por el README raíz, luego elige según tu rol:
> - **Desarrollador backend** → [`docs/architecture/readme.md`](docs/architecture/readme.md)
> - **DevOps / Operador** → [`docs/deployment/readme.md`](docs/deployment/readme.md)
> - **Todos** → Ver sección **Endpoints disponibles** abajo

| Documento | Descripción |
|---|---|
| [`docs/architecture/readme.md`](docs/architecture/readme.md) | Análisis técnico: Graphify, comunidades funcionales, God Nodes, resiliencia y estrategias de rendimiento |
| [`docs/deployment/readme.md`](docs/deployment/readme.md) | Guía operacional: Setup, Docker, PostgreSQL, deployment en Render, sincronización PUSH/PULL y mantenimiento |

***

## 👤 Autor

**Robinson Segura Aponte**
[github.com/robinsons1](https://github.com/robinsons1)

***

## 📄 Licencia

Proyecto bajo licencia MIT.