# ⬡ NEXUS — Monitor IoT en Tiempo Real

Plataforma de monitoreo de sensores IoT con visualización de datos en tiempo real,
almacenamiento histórico en la nube y sincronización automática cada 5 minutos.

🌐 **Demo en vivo:** [nexus-w0yh.onrender.com/dashboard](https://nexus-w0yh.onrender.com/dashboard)

---

## 🚀 Estado del proyecto

> **En desarrollo activo** — Versión 0.2.0

---

## ✅ Lo que funciona actualmente

- Lectura de datos desde ThingSpeak via API REST
- Almacenamiento histórico en Firebase Firestore (+14,000 puntos)
- Sincronización incremental automática cada 5 minutos (UptimeRobot + endpoint /sync)
- API REST con FastAPI que expone los datos
- Dashboard web con gráficas interactivas (Plotly.js)
- Visualización de Temperatura, Humedad y Presión
- Ajuste automático de zona horaria Colombia (America/Bogota)
- Dashboard público desplegado en Render.com
- Auto-refresco del dashboard cada 5 minutos si la página está abierta

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
- [x] Frontend servido desde FastAPI (ruta raíz `/`)
- [x] UptimeRobot en `/health` para mantener el servicio activo 24/7
- [x] Sincronización automática cada 5 minutos vía APScheduler
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
- [x] Endpoint `/data/stats` con estadísticas (último, mín, máx, promedio)
- [x] Endpoint `/data/export?format=csv` para exportación directa desde backend
- [x] Endpoint `/sensors` con metadata de sensores (nombre, unidad, canal ThingSpeak)
- [x] Logging estructurado para trazabilidad en Render logs
- [x] Índice en Supabase por `created_at DESC` para optimizar queries
- [ ] Paginación en `/data` con parámetros `?limit=N&offset=N`
- [ ] Reintentos con backoff exponencial en `/sync` si ThingSpeak falla

### Fase 5 — Alertas y notificaciones
- [ ] Notificaciones por correo o Telegram cuando se supera un umbral
- [ ] Historial de alertas en Supabase

### Fase 6 — Escalabilidad y seguridad
- [ ] Migración ThingSpeak → POST directo desde ESP32-S3 a `/ingest`
- [ ] Autenticación por API key en `/ingest`
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

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Sensores / Fuente de datos | ThingSpeak |
| Base de datos | Firebase Firestore |
| Backend API | Python + FastAPI |
| Frontend | HTML + CSS + Plotly.js |
| Sincronización | UptimeRobot + endpoint /sync |
| Automatización | GitHub Actions (ejecución manual) |
| Hosting | Render.com |

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
- Cuenta en Firebase
- Canal en ThingSpeak

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
# Editar .env con tus credenciales
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
