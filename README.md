# ⬡ NEXUS — Monitor IoT en Tiempo Real y Análisis Histórico

Plataforma de monitoreo de sensores IoT con visualización de datos en tiempo real,
almacenamiento histórico en la nube, análisis de tendencias y sincronización automática.

🌐 **Demo en vivo:** [nexus-w0yh.onrender.com](https://nexus-w0yh.onrender.com)
🖥️ **Servidor local:** [https://lincoln-happening-accept-blog.trycloudflare.com/] (https://lincoln-happening-accept-blog.trycloudflare.com/)

---

## 🚀 Estado del proyecto

> **En desarrollo activo** — Versión 0.8.0

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

### Fase 8 — Lectura desde local (PENDIENTE)
- [ ] Migrar endpoints de lectura (`/data`, `/data/latest`, `/data/stats`, etc.) a PostgreSQL local
- [ ] Fallback automático a Supabase si Postgres local no está disponible
- [ ] Migrar lectura de `/alerts` a Postgres local con fallback

### Fase 9 — Seguridad (PENDIENTE)
- [ ] API Key en `POST /ingest` (`X-API-Key` header) — proteger escritura
- [ ] JWT para endpoints de lectura — proteger dashboard
- [ ] Cloudflare Access como capa de red antes del servidor

### Fase 10 — Dominio y servidor fijo (PENDIENTE)
- [ ] Comprar dominio y gestionar DNS en Cloudflare
- [ ] Crear Named Tunnel permanente (reemplaza trycloudflare.com temporal)
- [ ] Migrar de Render.com al servidor doméstico como hosting principal

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Sensores / Fuente | ESP32-S3 + DHT11 + BMP280 |
| Envío de datos | ThingSpeak (buffer) + POST directo al servidor local |
| Base de datos primaria | PostgreSQL local (Docker `nexus_postgres`) |
| Base de datos respaldo | Supabase (PostgreSQL cloud) |
| Backend API | Python + FastAPI |
| Frontend | HTML5 + CSS3 + Vanilla JS + Plotly.js |
| Sincronización | APScheduler + Threading Locks |
| Notificaciones | Telegram Bot API |
| Hosting actual | Render.com + Servidor doméstico (Debian 12) |
| Túnel público | Cloudflare Tunnel (trycloudflare.com — temporal) |

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
| `/ingest` | POST | Recepción directa desde ESP32 (JSON: field1, field2, field3) |

---

## ⚙️ Instalación local

### Requisitos
- Python 3.11+
- Canal en ThingSpeak
- Cuenta en Supabase

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
# Agregar: THINGSPEAK_CHANNEL_ID, API_KEY, SUPABASE_URL, SUPABASE_KEY
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
├── api/
│   └── main.py                  # FastAPI backend, caché, /ingest dual-write
├── fetch/
│   ├── sync.py                  # Sincronización ThingSpeak → Supabase
│   ├── notifier.py              # Alertas Telegram + dual-write alert_history
│   └── database/
│       ├── supabase_client.py   # Cliente Supabase (respaldo cloud)
│       └── postgres_client.py   # Cliente PostgreSQL local (primario)
├── frontend/
├── docker-compose.yml           # nexus_app + nexus_tunnel
├── docker-compose.postgres.yml  # nexus_postgres (BD local)
├── init_db.sql                  # Schema inicial de PostgreSQL local
├── migrate_to_local.py          # Script de migración única (ya ejecutado)
├── .env.example
├── requirements.txt
└── README.md
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