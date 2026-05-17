# ⬡ NEXUS — Monitor IoT en Tiempo Real y Análisis Histórico

Plataforma de monitoreo de sensores IoT con visualización de datos en tiempo real,
almacenamiento histórico en la nube, análisis de tendencias y sincronización automática.

🌐 **Demo en vivo:** [nexus-w0yh.onrender.com](https://nexus-w0yh.onrender.com)
🖥️ **Servidor local:** [https://mechanisms-ave-invention-stakeholders.trycloudflare.com]

---

## 🚀 Estado del proyecto

> **En desarrollo activo** — Versión 0.9.1

---

## ✅ Lo que funciona actualmente

- Lectura de datos desde ThingSpeak via API REST
- Almacenamiento histórico en Supabase (PostgreSQL) — +30,000 puntos
- Sincronización incremental automática cada 5 minutos (APScheduler interno)
- Reintentos con backoff exponencial si ThingSpeak falla (hasta 4 intentos)
- API REST con FastAPI que expone los datos
- **Sistema avanzado de Caché en RAM con Eager Loading y Thread Locks para proteger la base de datos.**
- Dashboard web multipágina con UI/UX unificada (Tarjetas modulares, navegación "Píldora").
- Panel **Real-Time**: Gráficas interactivas, barra de estado, reloj de actualización.
- Panel **Analytics**: Análisis de tendencias, correlación (Pearson), ciclos y forecast.
- Visualización de Temperatura (DHT11), Humedad (DHT11) y Presión (BMP280).
- Filtro por rango de fechas con paginación automática.
- Ajuste automático de zona horaria Colombia (America/Bogota).
- Dashboard público desplegado en Render.com.
- Auto-refresco del dashboard cada 5 minutos.
- Exportación de datos en CSV directamente desde el backend.
- Alertas visuales con umbrales configurables y persistentes en localStorage.
- Modo oscuro / claro con persistencia.
- Logging estructurado para trazabilidad en Render logs.
- RLS habilitado en Supabase e índices optimizados por `created_at DESC`.
- Notificaciones Telegram con lógica de estado (sin spam, sin rebote).
- Watchdog de silencio: alerta Telegram si no llegan datos en 10 minutos, con aviso de restablecimiento automático.
- Sanitización XSS en frontend: escapado de variables dinámicas en `innerHTML` (fix CodeQL #5).
- Endpoint `/robots.txt` para proteger rutas de API de indexación.
- **Almacenamiento primario en PostgreSQL local** (Docker) — dual-write con fallback
- **Recepción directa desde ESP32** via `POST /ingest` — sin depender de ThingSpeak
- **Historial de alertas guardado en PostgreSQL local Y Supabase simultáneamente.**
- **Backup automatizado a Google Drive** con rclone en contenedor Docker, cron diario a las 9:10 PM COT con notificación Telegram al completar.
- **Fallback automático Postgres → Supabase** en todos los endpoints de lectura con caché en RAM (Eager Loading, 5 min TTL).
- **Logs del cron visibles** en `docker logs rclone_sync` via redirección a `/proc/1/fd/1`.
- Protección de escritura en `POST /ingest` mediante `X-API-Key` header — solo el ESP32 autorizado puede insertar datos
- Caché incremental — primera carga descarga 60 días, actualizaciones posteriores solo traen registros nuevos desde el último `created_at`
- Endpoint `GET /status` — estado en tiempo real de PostgreSQL local y Supabase con conteo de registros y detección de desincronización
- `tenant_id` en `sensor_data` y `alert_history` — columna multi-tenant preparada, valor `'default'` en PostgreSQL local y Supabase
- **Reconciliación Automática (PUSH/PULL)** — garantiza la consistencia bidireccional entre la base local y Supabase ante fallos de red.

---

## 🗺️ Roadmap

### Fase 1 — Base ✅
- [x] Conexión con ThingSpeak
- [x] ~~Base de datos en Firestore~~ → migrado a Supabase
- [x] Sincronización automática en la nube
- [x] API con FastAPI
- [x] Dashboard básico con gráficas

### Fase 2 — Deploy y disponibilidad ✅
- [x] Deploy del backend en Render.com
- [x] Frontend servido desde FastAPI (ruta raíz `/`)
- [x] UptimeRobot en `/health` para mantener el servicio activo 24/7
- [x] Sincronización automática vía APScheduler interno
- [x] Separación de CSS y JS en archivos independientes
- [x] Layout principal (Temp arriba, Humedad/Presión lado a lado)

### Fase 3 — Visualización ✅
- [x] Selector de rango de fechas para filtrar datos históricos
- [x] Indicadores en tiempo real sobre las gráficas
- [x] Gráfica combinada de los 3 sensores
- [x] Descarga de datos en CSV desde el dashboard
- [x] Alertas visuales de umbrales configurables
- [x] Modo oscuro / claro

### Fase 4 — Backend ✅
- [x] Endpoints de estadísticas y exportación CSV
- [x] Metadata de sensores y logging estructurado
- [x] Índice en Supabase para optimizar queries
- [x] Paginación y backoff exponencial

### Fase 5 — Alertas y notificaciones ✅
- [x] Notificaciones por Telegram al superar umbrales
- [x] Historial de alertas en Supabase (`alert_history`)
- [x] Dashboard con últimas alertas (`/alerts`)
- [x] Lógica de estado en memoria (sin rebote ni spam)
- [x] Watchdog de silencio — alerta si no llegan datos en ≥10 min (APScheduler cada 2 min)

### Fase 6 — Análisis de datos históricos ✅
- [x] Heatmap de temperatura por hora del día
- [x] Tendencia semanal — comportamiento por día de la semana
- [x] Correlación temperatura / humedad (dispersión con coeficiente de Pearson)
- [x] Promedio acumulado por hora — ciclos diarios
- [x] Detección de anomalías (Desviación estándar ± Sigma)
- [x] Forecast predictivo simple de temperatura a 1 hora
- [x] Optimización de Backend con Caché Ansioso (Eager Loading) para reportes pesados

### Fase 7 — Infraestructura local ✅
- [x] Endpoint `POST /ingest` — recepción directa desde ESP32
- [x] PostgreSQL local en Docker (`nexus_postgres`) como BD primaria
- [x] Dual-write: escribe en Postgres local + Supabase simultáneamente
- [x] `alert_history` replicada en Postgres local
- [x] Migración histórica completa: 41,622 registros + 687 alertas
- [x] Red Docker compartida (`nexus_net`) entre contenedores
- [x] ESP32 envía datos a ThingSpeak Y al servidor local en paralelo

### Fase 8 — Lectura local, Caché, Backup y Refactorización ✅
- [x] Todos los endpoints de lectura (`/data`, `/data/latest`, `/data/stats`, `/data/heatmap`, `/data/weekly`, `/data/anomalies`, `/alerts`) leen desde PostgreSQL local con fallback a Supabase.
- [x] Caché en RAM optimizada (incremental y Eager Loading) con descarga de registros nuevos, TTL 5 min y Thread Lock anti-stampede.
- [x] Compatible con `created_at` como `datetime` (Postgres) o `str` (Supabase).
- [x] Contenedor `rclone_sync` para backup automatizado (cron diario) a Google Drive y alertas en Telegram de la operación.
- [x] Preparación Multi-tenant: columna `tenant_id TEXT DEFAULT 'default'` agregada en PostgreSQL local y Supabase.
- [x] Modularización de la API usando `APIRouter` de FastAPI, separando `routers/` y `services/`.

### Fase 9 — Seguridad
- [x] API Key en `POST /ingest` (`X-API-Key` header) — proteger escritura ✅
- [ ] JWT para endpoints de lectura — proteger dashboard
- [ ] Cloudflare Access como capa de red antes del servidor

### Fase 10 — Resiliencia y reconciliación de datos (PENDIENTE)
> Garantizar consistencia entre PostgreSQL local y Supabase ante fallos de red, DNS o contenedor. Sincronización bidireccional automática.
- [x] **Reconciliación PUSH (local → Supabase):** Agregar bandera `synced_to_supabase` en `sensor_data` y `alert_history`. En `/ingest` y con un Job horario, empujar datos pendientes hacia Supabase.
- [x] **Reconciliación PULL (Supabase → local):** Job diario para comparar últimas 24h e insertar registros faltantes en Postgres local.
- [x] **Idempotencia y Unicidad:** Implementación de restricciones únicas compuestas en BD (`tenant_id` + `created_at` + `sensor`) para garantizar Upserts bidireccionales sin duplicados.
- [x] **Observabilidad del sync:** Endpoint `GET /sync/status` (público) con conteo de registros pendientes, desfase en minutos y estado (`sincronizado` / `pendiente` / `desfasado`). Job horario `check_sync_health` envía alerta Telegram si el desfase supera 60 minutos y otra de restablecimiento cuando se corrige.
- [x] **Alertas desde base de datos:** `init_sensor_states()` carga el último estado de alerta por sensor desde Postgres al arrancar, evitando duplicados tras reinicios. `_last_alert_time()` consulta Postgres primero y Supabase como fallback para el cooldown, garantizando robustez en modo offline.

### Fase 11 — Análisis Histórico Avanzado y Épocas (PENDIENTE)
- [ ] Ampliar gráficos analíticos incluyendo promedios detallados por horas, días, semanas y meses.
- [ ] Herramientas para comparar periodos históricos o temporadas (ej. meses secos vs meses de lluvia, años anteriores).
- [ ] Agregar visualizaciones relevantes para análisis a largo plazo, máximos/mínimos absolutos y tendencias estacionales.

### Fase 12 — Dominio y servidor principal (PENDIENTE)
- [ ] Comprar dominio y gestionar DNS en Cloudflare.
- [ ] Crear Named Tunnel permanente (reemplaza trycloudflare.com temporal).
- [ ] Migrar de Render.com al servidor doméstico como hosting principal.

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
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

---

## 🔌 Endpoints disponibles

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | GET | Dashboard web Real-Time |
| `/analytics` | GET | Dashboard de Análisis Histórico |
| `/data?limit=N` | GET | Registros con paginación |
| `/data/latest` | GET | Último registro |
| `/data/stats` | GET | Estadísticas agregadas |
| `/data/export?format=csv` | GET | Exportar CSV |
| `/data/heatmap?days=N` | GET | Agrupación térmica por horas del día |
| `/data/weekly?days=N` | GET | Agrupación promedio por día de la semana |
| `/data/anomalies?days=N&sigma=N` | GET | Detección estadística de atípicos |
| `/sensors` | GET | Metadata de sensores |
| `/alerts` | GET | Últimas alertas Telegram |
| `/sync` | GET/HEAD | Sincronización manual |
| `/health` | GET/HEAD | Health check |
| `/docs` | GET | Documentación Swagger |
| `/robots.txt` | GET | Directivas de indexación para crawlers |
| `ingest` | POST | Recepción directa desde ESP32 — requiere header `X-API-Key` |
| `status` | GET | Estado en tiempo real de ambas BDs — registros, diff y flag `in_sync` |

---

## ⚙️ Instalación local

### Requisitos
- Python 3.11+
- Docker + Docker Compose
- Canal en ThingSpeak
- Cuenta en Supabase
- Cuenta en Google Drive (para backup con rclone — opcional)

### Pasos

```bash
# Clonar el repositorio
git clone [https://github.com/robinsons1/NEXUS.git](https://github.com/robinsons1/NEXUS.git)
cd NEXUS

# Crear entorno virtual
python -m venv venv
venv\Scripts\Activate.ps1  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Agregar `THINGSPEAK_CHANNEL_ID`, `API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `INGEST_API_KEY`
```

### Correr localmente

```bash
python -m uvicorn api.main:app --reload
# http://localhost:8000
```

> Para pruebas locales cambiar `const API = "http://127.0.0.1:8000"` en `frontend/app.js`.
> Antes de cualquier commit revertir a `const API = "https://nexus-w0yh.onrender.com"`.

---

## 📁 Estructura del proyecto

```
├── .github/                     # Workflows y configuración de GitHub
├── api/
│   ├── routers/                 # Rutas de la API (analytics, data, ingest, system)
│   ├── services/                # Servicios de caché y base de datos
│   └── main.py                  # Punto de entrada de FastAPI
├── fetch/
│   ├── database/                # Clientes de BD (Postgres, Supabase, Firestore)
│   ├── load_history.py          # Scripts de migración y utilidades
│   ├── load_history_supabase.py # Scripts de migración y utilidades
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
├── .env.example                 # Variables de entorno de ejemplo
├── p.py                         # Utilidad extra
├── render.yaml                  # Configuración de despliegue en Render
└── requirements.txt             # Dependencias de Python
```
--

## 🌿 Ramas Git

| Rama | Uso |
|---|---|
| `main` | Producción (Render) |
| `dev` | Desarrollo activo |

Flujo: trabajar en `dev` → resolver conflictos → merge a `main`.

---

## 👤 Autor

**Robinson Segura Aponte**  
[github.com/robinsons1](https://github.com/robinsons1)