const API = "https://nexus-w0yh.onrender.com";

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

    // Actualizar status bar
    const lastDate = data.at(-1).created_at;
    document.getElementById("sb-ultimo").textContent = formatDate(toColombiaTime(lastDate));
    document.getElementById("sb-hace").textContent   = timeAgo(lastDate);
    document.getElementById("sb-desde").textContent  = formatDate(toColombiaTime(data[0].created_at));
    document.getElementById("sb-pagina").textContent = new Date().toLocaleString("es-CO", {timeZone: "America/Bogota"});

    resetCountdown();
}

// ── Filtro ──
async function aplicarFiltro() {
    const inicio = document.getElementById("fecha-inicio").value;
    const fin    = document.getElementById("fecha-fin").value;

    if (!inicio && !fin) {
        renderCharts(allData);
        return;
    }

    try {
        let url = `${API}/data?limit=99999`;
        if (inicio) url += `&start=${inicio}`;
        if (fin)    url += `&end=${fin}T23:59:59`;

        const res  = await fetch(url);
        const json = await res.json();
        const data = json.data.reverse();

        if (data.length === 0) {
            alert("No hay datos en ese rango de fechas.");
            return;
        }
        renderCharts(data);
    } catch (e) {
        console.error("Error filtrando datos:", e);
    }
}

function resetFiltro() {
    document.getElementById("fecha-inicio").value = "";
    document.getElementById("fecha-fin").value = "";
    renderCharts(allData);
}

// ── Carga de datos ──
async function loadData() {
    try {
        const res  = await fetch(`${API}/data?limit=100`);
        const json = await res.json();
        allData = json.data.reverse();
        renderCharts(allData);
    } catch (e) {
        console.error("Error cargando datos:", e);
    }
}

// ── Auto-refresh con visibilidad ──
function startAutoRefresh() {
    if (refreshTimer) return;
    refreshTimer = setInterval(() => {
        const inicio = document.getElementById("fecha-inicio").value;
        const fin    = document.getElementById("fecha-fin").value;
        if (inicio && fin) {
            aplicarFiltro();
        } else {
            loadData();
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
        const m = Math.floor(countdownSeconds / 60);
        const s = String(countdownSeconds % 60).padStart(2, "0");
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
loadData();
startAutoRefresh();
startCountdown();