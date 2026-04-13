# ⬡ NEXUS — Monitor IoT en Tiempo Real

Plataforma de monitoreo de sensores IoT con visualización de datos en tiempo real,
almacenamiento histórico en la nube y sincronización automática cada 5 minutos.

🌐 **Demo en vivo:** [nexus-w0yh.onrender.com](https://nexus-w0yh.onrender.com)

---

## 🚀 Estado del proyecto

> **En desarrollo activo** — Versión 0.5.0

---

## ✅ Lo que funciona actualmente

- Lectura de datos desde ThingSpeak via API REST
- Almacenamiento histórico en Supabase (PostgreSQL) — +30,000 puntos
- Sincronización incremental automática cada 5 minutos (APScheduler interno)
- Reintentos con backoff exponencial si ThingSpeak falla (hasta 4 intentos)
- API REST con FastAPI que expone los datos
- Paginación en `/data` con parámetros `?limit=N&offset=N`
- Dashboard web con gráficas interactivas (Plotly.js) — Layout: temperatura + humedad/presión
- Visualización de Temperatura (DHT11), Humedad (DHT11) y Presión (BMP280)
- Barra de estado con último dato, rango visible y cuenta regresiva
- Filtro por rango de fechas con paginación automática
- Ajuste automático de zona horaria Colombia (America/Bogota)
- Dashboard público desplegado en Render.com — accesible desde la raíz `/`
- Auto-refresco del dashboard cada 5 minutos si la página está abierta
- UptimeRobot en `/health` para mantener el servidor activo 24/7
- Exportación de datos en CSV directamente desde el backend
- Estadísticas por sensor (último, mín, máx, promedio) en tiempo real
- Alertas visuales con umbrales configurables persistentes en localStorage
- Modo oscuro / claro con persistencia en localStorage
- Logging estructurado para trazabilidad en Render logs
- Índice en Supabase por `created_at DESC` para queries optimizadas
- RLS habilitado en Supabase — acceso anónimo bloqueado
- Notificaciones Telegram con lógica de estado (sin spam, sin rebote)

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
- [x] Sincronización automática cada 5 minutos vía APScheduler interno
- [x] URL pública permanente
- [x] Migración de Firestore a Supabase (PostgreSQL)
- [x] Separación de CSS y JS en archivos independientes
- [x] Barra de estado con cuenta regresiva visible
- [x] Layout: temperatura arriba, humedad y presión lado a lado

### Fase 3 — Visualización ✅
- [x] Selector de rango de fechas para filtrar datos históricos
- [x] Indicadores en tiempo real (último, mín, máx, promedio) sobre las gráficas
- [x] Gráfica combinada de los 3 sensores con rolling average
- [x] Grid 2x2 con las 4 gráficas
- [x] Descarga de datos en CSV desde el dashboard
- [x] Timestamp visible de la última sincronización
- [x] Alertas visuales cuando un sensor supera umbrales configurables
- [x] Modo oscuro / claro con persistencia en localStorage

### Fase 4 — Backend ✅
- [x] Endpoint `GET /data/stats` con estadísticas (último, mín, máx, promedio)
- [x] Endpoint `GET /data/export?format=csv` para exportación directa desde backend
- [x] Endpoint `GET /sensors` con metadata de sensores (nombre, unidad, canal ThingSpeak)
- [x] Logging estructurado para trazabilidad en Render logs
- [x] Índice en Supabase por `created_at DESC` para optimizar queries
- [x] Paginación en `/data` con parámetros `?limit=N&offset=N`
- [x] Reintentos con backoff exponencial en sync si ThingSpeak falla

### Fase 5 — Alertas y notificaciones ✅
- [x] Notificaciones por Telegram cuando se supera umbral (`above`/`below`)
- [x] Notificación "restablecido" cuando vuelve a rango
- [x] Historial de alertas en Supabase (`alert_history`)
- [x] Dashboard con últimas alertas (`/alerts`)
- [x] Hora Bogotá (COT) en alertas
- [x] Cooldown anti-spam (30 min por sensor/dirección)
- [x] Lógica de estado en memoria — sin rebote ni spam por cooldown expirado
- [x] "Restablecido" se envía una sola vez por evento

### Fase 6 — Escalabilidad y seguridad
- [ ] Migración ThingSpeak → POST directo desde ESP32-S3 a `/ingest`
- [ ] Autenticación por API key en endpoint `/ingest`
- [ ] Autenticación JWT para endpoints de lectura
- [ ] Soporte para múltiples canales / dispositivos
- [ ] Panel de administración
- [ ] Soporte para otros protocolos (MQTT, Modbus)

### Fase 7 — Análisis de datos históricos
- [ ] Heatmap de temperatura por hora del día
- [ ] Tendencia semanal — comparar comportamiento por día de la semana
- [ ] Correlación temperatura / humedad (dispersión)
- [ ] Promedio acumulado por hora — ciclos diarios de los 3 sensores
- [ ] Detección de anomalías — lecturas fuera del patrón normal
- [ ] Análisis de presión atmosférica como indicador de clima
- [ ] Forecast simple de temperatura para las próximas horas

### Fase 8 — Personalización
- [ ] Crear y modificar rangos de alerta desde el dashboard

### Fase 9 — Bot Telegram
- [ ] Consultas y respuestas por comando (`/status`, `/stats`, `/alertas`)

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Sensores / Fuente de datos | ESP32-S3 + DHT11 + BMP280 → ThingSpeak |
| Base de datos | Supabase (PostgreSQL) + RLS |
| Backend API | Python + FastAPI |
| Frontend | HTML + CSS + Plotly.js |
| Sincronización | APScheduler (interno en FastAPI) |
| Notificaciones | Telegram Bot |
| Keep-alive | UptimeRobot → `/health` |
| Hosting | Render.com |
| Control de versiones | Git / GitHub |

---

## 🔌 Endpoints disponibles

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | GET | Dashboard web |
| `/dashboard` | GET | Dashboard web (alias) |
| `/data?limit=N&offset=N` | GET | Registros con paginación |
| `/data?start=YYYY-MM-DD&end=YYYY-MM-DD` | GET | Registros por rango de fechas |
| `/data/latest` | GET | Último registro |
| `/data/stats?limit=N` | GET | Estadísticas agregadas |
| `/data/stats?start=...&end=...` | GET | Estadísticas por rango |
| `/data/export?format=csv` | GET | Exportar CSV completo |
| `/data/export?format=csv&start=...&end=...` | GET | Exportar CSV por rango |
| `/sensors` | GET | Metadata de sensores y canal |
| `/alerts` | GET | Últimas alertas Telegram |
| `/sync` | GET/HEAD | Sincronización manual |
| `/health` | GET/HEAD | Health check |
| `/docs` | GET | Documentación Swagger |

---

## 🗃️ Base de datos — Tabla `sensor_data`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | int | PK autoincremental |
| `created_at` | timestamptz | Timestamp UTC — constraint UNIQUE |
| `field1` | float | Temperatura (°C) — DHT11 |
| `field2` | float | Humedad (%) — DHT11 |
| `field3` | float | Presión (hPa) — BMP280 |

**Índice:** `idx_sensor_data_created_at` en `created_at DESC`.

**Tabla `alert_history`:**

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | int | PK autoincremental |
| `created_at` | timestamptz | Timestamp UTC |
| `sensor` | text | `temperature`/`humidity`/`pressure` |
| `value` | float | Valor que disparó alerta |
| `threshold` | float | Umbral configurado |
| `direction` | text | `above`/`below`/`restored` |
| `message` | text | Texto enviado a Telegram |

---

## ⚙️ Instalación local

### Requisitos
- Python 3.11+
- Canal en ThingSpeak
- Cuenta en Supabase

### Pasos

```bash
# Clonar el repositorio
git clone https://github.com/robinsons1/NEXUS.git
cd NEXUS

# Crear entorno virtual
python -m venv venv
venv\Scripts\Activate.ps1  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Agregar: THINGSPEAK_CHANNEL_ID, THINGSPEAK_API_KEY, SUPABASE_URL, SUPABASE_KEY
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
│ └── main.py # FastAPI backend principal
├── fetch/
│ ├── sync.py # Sincronización ThingSpeak → Supabase
│ ├── notifier.py # Alertas Telegram
│ ├── recover.py # Script para recuperar gaps de datos
│ └── database/
│ └── supabase_client.py
├── frontend/
│ ├── index.html # Dashboard web
│ ├── style.css # Estilos
│ └── app.js # JavaScript
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