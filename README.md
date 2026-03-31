# ⬡ NEXUS — Monitor IoT en Tiempo Real

Plataforma de monitoreo de sensores IoT con visualización de datos en tiempo real,
almacenamiento histórico en la nube y sincronización automática cada 5 minutos.

🌐 **Demo en vivo:** [nexus-w0yh.onrender.com](https://nexus-w0yh.onrender.com)

---

## 🚀 Estado del proyecto

> **En desarrollo activo** — Versión 0.4.0

---

## ✅ Lo que funciona actualmente

- Lectura de datos desde ThingSpeak via API REST
- Almacenamiento histórico en Supabase (PostgreSQL) — +20,000 puntos
- Sincronización incremental automática cada 5 minutos (APScheduler interno)
- API REST con FastAPI que expone los datos
- Dashboard web con gráficas interactivas (Plotly.js) — Layout: temperatura + humedad/presión
- Visualización de Temperatura, Humedad y Presión
- Barra de estado con último dato, rango visible y cuenta regresiva
- Filtro por rango de fechas con paginación automática
- Ajuste automático de zona horaria Colombia (America/Bogota)
- Dashboard público desplegado en Render.com — accesible desde la raíz /
- Auto-refresco del dashboard cada 5 minutos si la página está abierta
- UptimeRobot en /health para mantener el servidor activo 24/7

---

## 🗺️ Propuesta y roadmap

### Fase 1 — Base ✅
- [x] Conexión con ThingSpeak
- [x] ~~Base de datos en Firestore~~ → migrado a Supabase
- [x] Sincronización automática en la nube
- [x] API con FastAPI
- [x] Dashboard básico con gráficas

### Fase 2 — Deploy y disponibilidad ✅
- [x] Deploy del backend en Render.com
- [x] Frontend servido desde FastAPI (ruta raíz /)
- [x] UptimeRobot en /health para mantener el servicio activo 24/7
- [x] Sincronización automática cada 5 minutos vía APScheduler interno
- [x] URL pública permanente
- [x] Migración de Firestore a Supabase (PostgreSQL)
- [x] Separación de CSS y JS en archivos independientes
- [x] Barra de estado con cuenta regresiva visible
- [x] Layout: temperatura arriba, humedad y presión lado a lado

### Fase 3 — Mejoras de visualización (completada ✅)
- [x] Selector de rango de fechas para filtrar datos históricos
- [x] Indicadores en tiempo real (último valor, mínimo, máximo, promedio) sobre las gráficas
- [x] Gráfica combinada de los 3 sensores con rolling average
- [x] Grid 2x2 con las 4 gráficas
- [x] Descarga de datos en CSV desde el dashboard
- [x] Timestamp visible de la última sincronización
- [x] Alertas visuales cuando un sensor supera umbrales configurables
- [x] Modo oscuro / claro con persistencia en localStorage

### Fase 4 — Mejoras del backend
- [x] Endpoint `GET /data/stats` con estadísticas (último, mín, máx, promedio)
- [ ] Endpoint `GET /data/export?format=csv` para exportación directa desde backend
- [ ] Endpoint `GET /sensors` con metadata de sensores (nombre, unidad, canal ThingSpeak)
- [ ] Paginación en `/data` con parámetros `?limit=N&offset=N`
- [ ] Reintentos con backoff exponencial en `/sync` si ThingSpeak falla
- [ ] Logging estructurado para trazabilidad en Render logs
- [ ] Índice en Supabase por `created_at DESC` para optimizar queries

### Fase 5 — Alertas y notificaciones
- [ ] Notificaciones por correo o Telegram cuando se supera un umbral
- [ ] Historial de alertas en Supabase

### Fase 6 — Escalabilidad y seguridad
- [ ] Migración de ThingSpeak a envío directo desde ESP32-S3 via POST a `/ingest`
- [ ] Autenticación por API key en endpoint `/ingest`
- [ ] Autenticación JWT para endpoints de lectura
- [ ] Soporte para múltiples canales / dispositivos
- [ ] Panel de administración
- [ ] Soporte para otros protocolos (MQTT, Modbus)

### Fase 7 — Análisis de datos históricos
- [ ] Heatmap de temperatura por hora del día (perfil térmico del apartamento)
- [ ] Tendencia semanal — comparar comportamiento por día de la semana
- [ ] Gráfica de correlación temperatura / humedad (dispersión)
- [ ] Promedio acumulado por hora — ciclos diarios de los 3 sensores
- [ ] Detección de anomalías — lecturas fuera del patrón normal
- [ ] Análisis de presión atmosférica como indicador de clima
- [ ] Forecast simple de temperatura para las próximas horas

---

## 🛠️ Stack tecnológico

| Capa                       | Tecnología                       |
| -------------------------- | -------------------------------- |
| Sensores / Fuente de datos | ThingSpeak                       |
| Base de datos              | Supabase (PostgreSQL)            |
| Backend API                | Python + FastAPI                 |
| Frontend                   | HTML + CSS + Plotly.js           |
| Sincronización             | APScheduler (interno en FastAPI) |
| Keep-alive                 | UptimeRobot → /health            |
| Hosting                    | Render.com                       |

---

## 🔌 Endpoints disponibles

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | GET | Estado de la API |
| `/dashboard` | GET | Dashboard web |
| `/data?limit=N` | GET | Últimos N registros |
| `/data/latest` | GET | Último registro |
| `/data/stats` | GET | Estadísticas agregadas *(próximamente)* |
| `/data/export` | GET | Exportar datos en CSV *(próximamente)* |
| `/sensors` | GET | Metadata de sensores *(próximamente)* |
| `/sync` | GET/HEAD | Ejecutar sincronización manual |
| `/health` | GET/HEAD | Health check |
| `/docs` | GET | Documentación Swagger |

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
# Sincronizar datos desde ThingSpeak
python fetch/sync.py

# Iniciar API
uvicorn api.main:app --reload

# Abrir en el navegador
# http://localhost:8000/dashboard
```

---

## 📁 Estructura del proyecto


```
NEXUS/
├── .github/workflows/    # GitHub Actions (sync automático)
├── api/                  # Backend FastAPI
├── database/             # Conexión con Firestore
├── fetch/                # Scripts de ThingSpeak
├── frontend/             # Dashboard web
├── .env.example          # Variables de entorno (plantilla)
├── requirements.txt      # Dependencias Python
└── README.md
```

---

## 👤 Autor

**Robinson Segura Aponte**  
[github.com/robinsons1](https://github.com/robinsons1)
