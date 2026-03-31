const API = "https://nexus-w0yh.onrender.com";
//const API = "http://127.0.0.1:8000";

let allData = [];
let refreshTimer = null;
let countdownTimer = null;
let countdownSeconds = 5 * 60;

const REFRESH_MS = 5 * 60 * 1000;

const toColombiaTime = (utcStr) => new Date(utcStr);

const formatDate = (d) => d.toLocaleString("es-CO", {
    timeZone: "America/Bogota",
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit"
});

const timeAgo = (dateStr) => {
    const diff = Math.floor((new Date() - new Date(dateStr)) / 1000);
    if (diff < 60) return `hace ${diff} seg`;
    if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
    return `hace ${Math.floor(diff / 3600)} h`;
};

const chartLayout = () => ({
    paper_bgcolor: "#1e293b",
    plot_bgcolor: "#1e293b",
    font: { color: "#94a3b8" },
    height: 220,
    margin: { t: 10, b: 40, l: 50, r: 20 },
    xaxis: { gridcolor: "#334155", type: "date", tickformat: "%d/%m %H:%M" },
    yaxis: { gridcolor: "#334155", autorange: true, rangemode: "normal" }
});

function renderCharts(data) {
    const times = data.map(d => new Date(d.created_at));
    const temp  = data.map(d => parseFloat(d.field1));
    const hum   = data.map(d => parseFloat(d.field2));
    const pres  = data.map(d => parseFloat(d.field3));

    document.getElementById("val-temp").textContent = temp.at(-1)?.toFixed(1) ?? "--";
    document.getElementById("val-hum").textContent  = hum.at(-1)?.toFixed(1)  ?? "--";
    document.getElementById("val-pres").textContent = pres.at(-1)?.toFixed(1) ?? "--";

    const trace = (y, color) => [{
        x: times, y,
        type: "scatter", mode: "lines",
        line: { color, width: 2 },
        fill: "none"
    }];

    Plotly.newPlot("chart-temp", trace(temp, "#f87171"), chartLayout(), {responsive: true});
    Plotly.newPlot("chart-hum",  trace(hum,  "#34d399"), chartLayout(), {responsive: true});
    Plotly.newPlot("chart-pres", trace(pres, "#818cf8"), chartLayout(), {responsive: true});

    const lastDate = data.at(-1).created_at;
    document.getElementById("sb-ultimo").textContent = formatDate(toColombiaTime(lastDate));
    document.getElementById("sb-hace").textContent   = timeAgo(lastDate);
    document.getElementById("sb-desde").textContent  = formatDate(toColombiaTime(data[0].created_at));
    document.getElementById("sb-pagina").textContent = new Date().toLocaleString("es-CO", {timeZone: "America/Bogota"});

    renderCombined(times, temp, hum, pres);
    checkAlerts();
    resetCountdown();
}

// ── Hace el fetch y aplica ──
async function updateStats(params = "") {
    try {
        const res   = await fetch(`${API}/data/stats${params}`);
        const stats = await res.json();
        applyStats(stats);
    } catch (e) {
        console.error("Error cargando stats:", e);
    }
}

function applyStats(s) {
    const fields = [
        { key: "temperature", id: "temp" },
        { key: "humidity",    id: "hum"  },
        { key: "pressure",    id: "pres" },
    ];

    fields.forEach(({ key, id }) => {
        const d = s[key];
        if (!d) return;
        document.getElementById(`stat-${id}-last`).textContent = d.last;
        document.getElementById(`stat-${id}-min`).textContent  = d.min;
        document.getElementById(`stat-${id}-max`).textContent  = d.max;
        document.getElementById(`stat-${id}-avg`).textContent  = d.avg;
    });
}

// ── Filtro ──                              // ← CAMBIO: async + updateStats
async function aplicarFiltro() {
    const inicio = document.getElementById("fecha-inicio").value;
    const fin    = document.getElementById("fecha-fin").value;

    if (!inicio && !fin) {
        renderCharts(allData);
        await updateStats(`?limit=100`);
        return;
    }

    const startParam = inicio || null;
    const endParam   = fin ? `${fin}T23:59:59` : null;

    try {
        // ── Construir URL de datos ──
        let dataUrl = `${API}/data?limit=99999`;
        if (startParam) dataUrl += `&start=${startParam}`;
        if (endParam)   dataUrl += `&end=${endParam}`;

        // ── Construir params de stats ──
        let statsUrl = `${API}/data/stats?`;
        if (startParam) statsUrl += `start=${startParam}&`;
        if (endParam)   statsUrl += `end=${endParam}`;

        // ── Fetch en paralelo ──
        const [dataRes, statsRes] = await Promise.all([
            fetch(dataUrl),
            fetch(statsUrl)
        ]);

        const json  = await dataRes.json();
        const stats = await statsRes.json();

        const data = json.data.reverse();

        if (data.length === 0) {
            alert("No hay datos en ese rango de fechas.");
            return;
        }

        // ── Primero renderizar, luego aplicar stats ──
        renderCharts(data);
        applyStats(stats);          // ← función separada, no hace fetch

    } catch (e) {
        console.error("Error filtrando datos:", e);
    }
}

function resetFiltro() {
    document.getElementById("fecha-inicio").value = "";
    document.getElementById("fecha-fin").value    = "";
    renderCharts(allData);
    updateStats(`?limit=100`);                       // ← stats para últimas 100
}

async function loadData() {
    try {
        const res  = await fetch(`${API}/data?limit=100`);
        const json = await res.json();
        allData = json.data.reverse();
        renderCharts(allData);
        await updateStats(`?limit=100`);
    } catch (e) {
        console.error("Error cargando datos:", e);
    }
}

async function loadAlerts() {
    try {
        const response = await fetch(`${API}/alerts?limit=10`);
        const alerts = await response.json();
        
        const container = document.getElementById('alerts-container');
        if (!container) {
            console.log('No se encontró #alerts-container');
            return;
        }
        
        let html = '';
        alerts.slice(0, 10).forEach(alert => {
            const time = new Date(alert.created_at).toLocaleString('es-CO');
            html += `
                <div class="alert-item">
                    <strong>${time}</strong>
                    <span>${alert.message.replace(/<[^>]*>/g, '')}</span>
                </div>
            `;
        });
        
        container.innerHTML = html || '<p>No hay alertas recientes</p>';
    } catch (error) {
        console.error('Error cargando alertas:', error);
        document.getElementById('alerts-container').innerHTML = '<p>Error cargando alertas</p>';
    }
}

// ── Auto-refresh ──
function startAutoRefresh() {
    if (refreshTimer) return;
    refreshTimer = setInterval(() => {
        const inicio = document.getElementById("fecha-inicio").value;
        const fin    = document.getElementById("fecha-fin").value;
        resetCountdown();
        if (inicio && fin) {
            aplicarFiltro();
        } else {
            loadData();
            loadAlerts();  // ← AÑADIR ESTA LÍNEA
        }
    }, REFRESH_MS);
    console.log("[Nexus] Auto-refresh iniciado ✅");
}

function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
        console.log("[Nexus] Auto-refresh pausado ⏸️");
    }
}

// ── Countdown ──
function resetCountdown() {
    countdownSeconds = REFRESH_MS / 1000;
}

function startCountdown() {
    if (countdownTimer) return;
    countdownTimer = setInterval(() => {
        countdownSeconds = Math.max(0, countdownSeconds - 1);
        const m  = Math.floor(countdownSeconds / 60);
        const s  = String(countdownSeconds % 60).padStart(2, "0");
        const el = document.getElementById("sb-countdown");
        if (el) el.textContent = `${m}:${s}`;
    }, 1000);
}

function stopCountdown() {
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
}

function rollingAvg(arr, window = 10) {
    return arr.map((_, i) => {
        const start  = Math.max(0, i - window + 1);
        const slice  = arr.slice(start, i + 1);
        const sum    = slice.reduce((a, b) => a + b, 0);
        return Math.round((sum / slice.length) * 100) / 100;
    });
}

function renderCombined(times, temp, hum, pres) {
    const avgTemp = rollingAvg(temp, 10);
    const avgHum  = rollingAvg(hum,  10);
    const avgPres = rollingAvg(pres, 10);

    const traces = [
        // ── Datos crudos (tenues) ──
        {
            x: times, y: temp,
            name: "Temp", type: "scatter", mode: "lines",
            line: { color: "#f87171", width: 1, dash: "dot" },
            opacity: 0.4,
            yaxis: "y1", showlegend: false
        },
        {
            x: times, y: hum,
            name: "Humedad", type: "scatter", mode: "lines",
            line: { color: "#34d399", width: 1, dash: "dot" },
            opacity: 0.4,
            yaxis: "y2", showlegend: false
        },
        {
            x: times, y: pres,
            name: "Presión", type: "scatter", mode: "lines",
            line: { color: "#818cf8", width: 1, dash: "dot" },
            opacity: 0.4,
            yaxis: "y3", showlegend: false
        },

        // ── Rolling average (sólidas) ──
        {
            x: times, y: avgTemp,
            name: "Temp avg (°C)", type: "scatter", mode: "lines",
            line: { color: "#f87171", width: 2.5 },
            yaxis: "y1"
        },
        {
            x: times, y: avgHum,
            name: "Hum avg (%)", type: "scatter", mode: "lines",
            line: { color: "#34d399", width: 2.5 },
            yaxis: "y2"
        },
        {
            x: times, y: avgPres,
            name: "Pres avg (hPa)", type: "scatter", mode: "lines",
            line: { color: "#818cf8", width: 2.5 },
            yaxis: "y3"
        }
    ];

    const layout = {
        ...chartLayout(),
        height: 280,
        legend: { orientation: "h", y: -0.28, font: { size: 11 } },

        yaxis: {
            title: "°C",
            titlefont: { size: 10, color: "#f87171" },
            tickfont:  { size: 9,  color: "#f87171" },
            gridcolor: "#2d3f55",
            autorange: true,
            rangemode: "normal"
        },
        yaxis2: {
            overlaying: "y",
            side: "right",
            title: "%",
            titlefont: { size: 10, color: "#34d399" },
            tickfont:  { size: 9,  color: "#34d399" },
            showgrid: false,
            autorange: true,
            rangemode: "normal"
        },
        yaxis3: {
            overlaying: "y",
            side: "right",
            anchor: "free",
            position: 0.85,
            title: "hPa",
            titlefont: { size: 10, color: "#818cf8" },
            tickfont:  { size: 9,  color: "#818cf8" },
            showgrid: false,
            autorange: true,
            rangemode: "normal"
        },

        margin: { t: 10, b: 60, l: 45, r: 60 }
    };

    Plotly.newPlot("chart-combined", traces, layout, { responsive: true });
}

async function descargarCSV() {
    const inicio = document.getElementById("fecha-inicio").value;
    const fin    = document.getElementById("fecha-fin").value;

    // Construir URL apuntando al nuevo endpoint del backend
    let url = `${API}/data/export?format=csv`;

    if (inicio && fin) {
        url += `&start=${inicio}&end=${fin}T23:59:59`;
    } else if (inicio) {
        url += `&start=${inicio}`;
    } else if (fin) {
        url += `&end=${fin}T23:59:59`;
    } else {
        url += `&limit=1000`;
    }

    // Nombre del archivo con rango o fecha actual
    const desde = inicio || "inicio";
    const hasta = fin    || new Date().toISOString().slice(0, 10);
    const filename = `nexus_${desde}_${hasta}.csv`;

    try {
        const res = await fetch(url);

        if (!res.ok) {
            alert("No hay datos para descargar.");
            return;
        }

        const blob = await res.blob();
        const link = document.createElement("a");
        link.href  = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
        URL.revokeObjectURL(link.href);

    } catch (e) {
        console.error("Error descargando CSV:", e);
        alert("Error al generar el CSV.");
    }
}

const DEFAULT_THRESHOLDS = {
    temp: { min: 21,   max: 23   },
    hum:  { min: 48,   max: 70   },
    pres: { min: 750, max: 755 }
};

function loadThresholds() {
    const saved = localStorage.getItem("nexus_thresholds");
    return saved ? JSON.parse(saved) : { ...DEFAULT_THRESHOLDS };
}

function saveThresholds(t) {
    localStorage.setItem("nexus_thresholds", JSON.stringify(t));
}

function fillThresholdInputs(t) {
    document.getElementById("u-temp-min").value = t.temp.min;
    document.getElementById("u-temp-max").value = t.temp.max;
    document.getElementById("u-hum-min").value  = t.hum.min;
    document.getElementById("u-hum-max").value  = t.hum.max;
    document.getElementById("u-pres-min").value = t.pres.min;
    document.getElementById("u-pres-max").value = t.pres.max;
}

function guardarUmbrales() {
    const t = {
        temp: { min: parseFloat(document.getElementById("u-temp-min").value), max: parseFloat(document.getElementById("u-temp-max").value) },
        hum:  { min: parseFloat(document.getElementById("u-hum-min").value),  max: parseFloat(document.getElementById("u-hum-max").value)  },
        pres: { min: parseFloat(document.getElementById("u-pres-min").value), max: parseFloat(document.getElementById("u-pres-max").value) }
    };
    saveThresholds(t);
    checkAlerts(t);
    document.getElementById("umbrales-toggle").textContent = "✅ ▲";
    setTimeout(() => document.getElementById("umbrales-toggle").textContent = "▲", 1500);
}

function resetUmbrales() {
    saveThresholds(DEFAULT_THRESHOLDS);
    fillThresholdInputs(DEFAULT_THRESHOLDS);
    checkAlerts(DEFAULT_THRESHOLDS);
}

function toggleUmbrales() {
    const body   = document.getElementById("umbrales-body");
    const toggle = document.getElementById("umbrales-toggle");
    const isOpen = body.classList.toggle("open");
    toggle.textContent = isOpen ? "▲" : "▼";
}

function checkAlerts(t = loadThresholds()) {
    const sensors = [
        { id: "val-temp", cardClass: "temp-card", val: parseFloat(document.getElementById("val-temp").textContent), limits: t.temp, label: "°C" },
        { id: "val-hum",  cardClass: "hum-card",  val: parseFloat(document.getElementById("val-hum").textContent),  limits: t.hum,  label: "%" },
        { id: "val-pres", cardClass: "pres-card",  val: parseFloat(document.getElementById("val-pres").textContent), limits: t.pres, label: "hPa" }
    ];

    sensors.forEach(({ id, val, limits }) => {
        const cardEl  = document.getElementById(id).closest(".card");
        const badgeEl = cardEl.querySelector(".alert-badge");

        cardEl.classList.remove("warn", "alert");
        if (badgeEl) badgeEl.textContent = "";

        if (isNaN(val)) return;

        if (val < limits.min || val > limits.max) {
            const isWarn = val < limits.min * 0.9 || val > limits.max * 1.1;
            cardEl.classList.add(isWarn ? "alert" : "warn");
            if (badgeEl) badgeEl.textContent = val < limits.min ? "⚠ Por debajo del mínimo" : "⚠ Por encima del máximo";
        }
    });
}

// ── Tema ──
function applyTheme(theme) {
    document.body.classList.toggle("light", theme === "light");
    document.getElementById("theme-toggle").textContent = theme === "light" ? "🌙" : "☀️";

    // Actualizar colores de Plotly según el tema
    const chartBg   = theme === "light" ? "#ffffff" : "#1e293b";
    const gridColor = theme === "light" ? "#e2e8f0" : "#334155";
    const fontColor = theme === "light" ? "#475569" : "#94a3b8";

    ["chart-temp", "chart-hum", "chart-pres", "chart-combined"].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.data) {
            Plotly.relayout(id, {
                paper_bgcolor: chartBg,
                plot_bgcolor:  chartBg,
                "font.color":  fontColor,
                "xaxis.gridcolor": gridColor,
                "yaxis.gridcolor": gridColor,
            });
        }
    });
}

function toggleTheme() {
    const current = localStorage.getItem("nexus_theme") || "dark";
    const next    = current === "dark" ? "light" : "dark";
    localStorage.setItem("nexus_theme", next);
    applyTheme(next);
}

// ── Visibilidad de pestaña ──
document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
        startAutoRefresh();
        startCountdown();
    } else {
        stopAutoRefresh();
        stopCountdown();
    }
});

// ── Inicio ──
applyTheme(localStorage.getItem("nexus_theme") || "dark");
fillThresholdInputs(loadThresholds());
loadData();
loadAlerts();
startAutoRefresh();
startCountdown();