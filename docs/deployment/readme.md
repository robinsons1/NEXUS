# 🚀 Deployment e Infraestructura — NEXUS

Documentación técnica completa de despliegue, infraestructura, sincronización, servicios auxiliares y mantenimiento del proyecto NEXUS.

***

## 🛠️ Requisitos previos

### Software requerido

- Python 3.11+
- Docker + Docker Compose
- Git
- Cuenta en Supabase
- Canal ThingSpeak configurado
- Bot de Telegram creado
- (Opcional) Cuenta Google Drive para backups con rclone

***

## 📦 Clonar el repositorio

```bash
git clone https://github.com/robinsons1/NEXUS.git
cd NEXUS
```

***

## 🐍 Configuración del entorno Python

### Crear entorno virtual

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

### Instalar dependencias

```bash
pip install -r requirements.txt
```

***

## ⚙️ Variables de entorno

Crear archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
```

### Variables necesarias

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

***

## 🐳 PostgreSQL local con Docker

### Crear red Docker compartida

```bash
docker network create nexus_net
```

### Levantar contenedor PostgreSQL

```bash
docker run -d \
  --name nexus_postgres \
  --network nexus_net \
  -e POSTGRES_DB=nexus \
  -e POSTGRES_USER=nexus \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16
```

> La red `nexus_net` es compartida entre todos los contenedores de NEXUS, permitiendo comunicación interna sin exponer puertos al exterior.

***

## ☁️ Configuración Supabase

### Recomendaciones de configuración

**Activar:**

- RLS (Row Level Security) en todas las tablas
- Índices por `created_at DESC` y `tenant_id`

**Restricción única compuesta recomendada:**

```sql
UNIQUE (tenant_id, created_at)
```

Esta restricción garantiza Upserts bidireccionales sin duplicados en la reconciliación PUSH/PULL.

***

## ▶️ Ejecutar el backend

### Desarrollo local

```bash
python -m uvicorn api.main:app --reload
```

Servidor disponible en: `http://localhost:8000`

> ⚠️ Para pruebas locales, cambiar `const API = "http://127.0.0.1:8000"` en `frontend/app.js`.
> Antes de cualquier commit, revertir a `const API = "https://nexus-w0yh.onrender.com"`.

***

## 🌐 Deploy en Render.com

### Configuración recomendada

**Build Command:**

```bash
pip install -r requirements.txt
```

**Start Command:**

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

El archivo `render.yaml` en la raíz del proyecto contiene la configuración de despliegue lista para usar.

***

## ☁️ Cloudflare Tunnel

El servidor local actualmente usa un túnel temporal:

```text
trycloudflare.com
```

**Pendiente:**

- Crear Named Tunnel permanente
- Asociar dominio propio
- Migrar de Render.com al servidor doméstico como hosting principal

***

## 🔁 Sincronización automática con APScheduler

NEXUS utiliza **APScheduler** integrado en el backend para ejecutar tareas programadas:

| Job | Frecuencia | Función |
|---|---|---|
| Sincronización ThingSpeak | Cada 5 minutos | Descarga datos nuevos |
| Watchdog de silencio | Cada 2 minutos | Alerta si no llegan datos en ≥10 min |
| Health check sync | Cada hora | Alerta Telegram si desfase > 60 min |
| Reconciliación PULL | Diario | Supabase → PostgreSQL local |
| Backup rclone | Diario (9:10 PM COT) | PostgreSQL → Google Drive |

***

## 🔄 Reconciliación de datos PUSH/PULL

El sistema garantiza consistencia bidireccional entre PostgreSQL local y Supabase ante fallos de red, DNS o contenedor.

### PUSH (Local → Supabase)

```text
PostgreSQL local → Supabase
```

- Job horario empuja datos con bandera `synced_to_supabase = false`
- También se ejecuta en cada llamada a `/ingest`
- Usa Upsert con restricción única `(tenant_id, created_at)` para evitar duplicados

### PULL (Supabase → Local)

```text
Supabase → PostgreSQL local
```

- Job diario compara últimas 24h e inserta registros faltantes en Postgres local
- Idempotente: no genera duplicados gracias a restricciones únicas compuestas

### Observabilidad del sync

```bash
# Estado en tiempo real
GET /sync/status
# Retorna: pendientes, desfase en minutos, estado (sincronizado / pendiente / desfasado)

GET /status
# Retorna: conteo de registros en ambas BDs, diff e in_sync
```

***

## 📦 Backup automático con rclone

### Contenedor dedicado

```text
rclone_sync
```

**Funciones:**

- Backup diario a las 9:10 PM COT
- Subida automática a Google Drive
- Notificación Telegram al completar
- Logs redirigidos a Docker

**Ver logs:**

```bash
docker logs rclone_sync
```

***

## 🤖 ESP32 — Configuración de envío

El ESP32 envía datos simultáneamente a dos destinos, garantizando redundancia:

1. **ThingSpeak** — buffer cloud público
2. **Servidor local** (`POST /ingest`) — ingesta directa con `X-API-Key`

Esto asegura que aunque uno de los dos destinos falle, los datos no se pierden.

**Header requerido en `/ingest`:**

```
X-API-Key: TU_INGEST_API_KEY
```

**Body esperado:**

```json
{
  "field1": 25.3,
  "field2": 60.1,
  "field3": 1013.2
}
```

- `field1` → Temperatura (°C) — DHT11
- `field2` → Humedad (%) — DHT11
- `field3` → Presión (hPa) — BMP280 (opcional)

***

## 📊 Observabilidad — Endpoints clave

| Endpoint | Función |
|---|---|
| `/health` | Health check — usado por UptimeRobot |
| `/status` | Estado PostgreSQL/Supabase con conteo y `in_sync` |
| `/sync/status` | Estado de sincronización: pendientes, desfase y estado |
| `/alerts` | Historial de alertas Telegram |

***

## 🧠 Caché y rendimiento

El backend implementa un sistema de caché en múltiples capas:

- **Caché en RAM con Eager Loading** — carga anticipada de datos frecuentes
- **TTL de 5 minutos** — datos en caché no más de 5 min antes de refrescar
- **Descarga incremental** — primera carga descarga 60 días; posteriores solo traen registros desde el último `created_at`
- **Thread Locking anti-stampede** — un solo hilo recarga la caché; los demás esperan

**Objetivo:** reducir queries pesadas a PostgreSQL, proteger la BD y mejorar tiempos de respuesta del dashboard.

***

## 🔒 Seguridad implementada

### Activa

- `X-API-Key` en `POST /ingest` — solo el ESP32 autorizado puede insertar datos
- Sanitización XSS en frontend (escapado de variables dinámicas en `innerHTML`)
- RLS en Supabase
- Red Docker aislada (`nexus_net`)
- Thread Locks anti-stampede en caché
- Fallback automático Postgres → Supabase
- `/robots.txt` para proteger rutas de API de indexación web

### Pendiente

- JWT Authentication para endpoints de lectura
- Cloudflare Access como capa de red antes del servidor
- Dominio personalizado con Named Tunnel permanente

***

## 📁 Infraestructura completa

```text
NEXUS/
├── .github/                     # Workflows y configuración de GitHub
├── api/
│   ├── routers/                 # Rutas de la API (analytics, data, ingest, system)
│   ├── services/                # Servicios de caché y base de datos
│   └── main.py                  # Punto de entrada de FastAPI
├── fetch/
│   ├── database/                # Clientes de BD (Postgres, Supabase)
│   ├── load_history.py
│   ├── load_history_supabase.py
│   ├── notifier.py              # Gestión de alertas (Telegram y DB)
│   ├── reconciliation.py        # Jobs de reconciliación (PUSH/PULL)
│   ├── recover.py               # Scripts de recuperación
│   ├── sync.py                  # Job principal de sincronización (ThingSpeak)
│   └── thingspeak.py            # Cliente de ThingSpeak
├── frontend/
│   ├── analytics.html
│   ├── analytics.js
│   ├── app.js
│   ├── index.html
│   └── style.css
├── docs/
│   ├── architecture/
│   ├── deployment/
│   └── images/
├── docker/
├── backups/
├── .env.example
├── render.yaml
└── requirements.txt
```

***

## 🔧 Mantenimiento

### Actualizar dependencias

```bash
pip install -r requirements.txt --upgrade
```

### Reconstruir entorno virtual

**Windows:**

```powershell
deactivate
rmdir /s /q venv

python -m venv venv
venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

**Linux:**

```bash
deactivate
rm -rf venv

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

***

## 📈 Escalabilidad futura

Planeado:

- Migración completa al servidor doméstico (Debian 12) como hosting principal
- Cloudflare Access + Named Tunnel permanente
- Multi-tenant real con aislamiento por `tenant_id`
- JWT Authentication para todos los endpoints
- Dashboards avanzados con métricas históricas estacionales
- Forecasting ambiental avanzado

***

## 🌿 Ramas Git

| Rama | Uso |
|---|---|
| `main` | Producción (Render) |
| `dev` | Desarrollo activo |

Flujo: trabajar en `dev` → resolver conflictos → merge a `main`.

***

## 👤 Autor

**Robinson Segura Aponte**
[github.com/robinsons1](https://github.com/robinsons1)