# ⬡ NEXUS — Monitor IoT en Tiempo Real

Plataforma de monitoreo de sensores IoT con visualización de datos en tiempo real, almacenamiento histórico en la nube y sincronización automática.

---

## 🚀 Estado del proyecto

> **En desarrollo activo** — Versión 0.1.0

---

## ✅ Lo que funciona actualmente

- Lectura de datos desde ThingSpeak via API REST
- Almacenamiento histórico en Firebase Firestore (+14,000 puntos)
- Sincronización incremental automática cada 15 minutos (GitHub Actions)
- API REST con FastAPI que expone los datos
- Dashboard web con gráficas interactivas (Plotly.js)
- Visualización de Temperatura, Humedad y Presión
- Ajuste automático de zona horaria Colombia (UTC-5)

---

## 🗺️ Propuesta y roadmap

### Fase 1 — Base (completada ✅)
- [x] Conexión con ThingSpeak
- [x] Base de datos en Firestore
- [x] Sincronización automática en la nube
- [x] API con FastAPI
- [x] Dashboard básico con gráficas

### Fase 2 — Deploy y disponibilidad (en curso 🔄)
- [ ] Deploy del backend en Render.com
- [ ] Deploy del frontend público
- [ ] UptimeRobot para mantener el servicio activo 24/7
- [ ] URL pública permanente

### Fase 3 — Mejoras de visualización
- [ ] Selector de rango de fechas
- [ ] Descarga de datos en CSV
- [ ] Gráfica combinada de los 3 sensores
- [ ] Indicadores de mínimo, máximo y promedio
- [ ] Modo oscuro / claro

### Fase 4 — Alertas y notificaciones
- [ ] Alertas por umbral (ej: temperatura > 30°C)
- [ ] Notificaciones por correo o WhatsApp
- [ ] Historial de alertas

### Fase 5 — Escalabilidad
- [ ] Soporte para múltiples canales ThingSpeak
- [ ] Autenticación de usuarios
- [ ] Panel de administración
- [ ] Soporte para otros protocolos (MQTT, Modbus)

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Sensores / Fuente de datos | ThingSpeak |
| Base de datos | Firebase Firestore |
| Backend API | Python + FastAPI |
| Frontend | HTML + CSS + Plotly.js |
| Automatización | GitHub Actions |
| Hosting | Render.com |

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
python -m uvicorn api.main:app --reload

# Abrir frontend/index.html en el navegador
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
Ingeniero Mecatrónico — Bogotá, Colombia  
[github.com/robinsons1](https://github.com/robinsons1)
