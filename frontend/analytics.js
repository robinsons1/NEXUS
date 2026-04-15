const API = "";

// ─── TEMA ─────────────────────────────────────────────────────────────────
const themeToggle = document.getElementById("themeToggle");
let isLight = localStorage.getItem("nexus-theme") === "light";
if (isLight) document.body.classList.add("light");
themeToggle.textContent = isLight ? "☀️" : "🌙";
themeToggle.addEventListener("click", () => {
    isLight = !isLight;
    document.body.classList.toggle("light", isLight);
    themeToggle.textContent = isLight ? "☀️" : "🌙";
    localStorage.setItem("nexus-theme", isLight ? "light" : "dark");
    cache = {};
    renderAll();
});

// ─── HELPERS ──────────────────────────────────────────────────────────────
function getTheme() {
    return isLight
        ? { bg: "#ffffff", paper: "#f8fafc", grid: "#e2e8f0", text: "#0f172a", muted: "#475569" }
        : { bg: "#1e293b", paper: "#1e293b", grid: "#334155", text: "#e0eaf5", muted: "#94a3b8" };
}

function baseLayout(title, xaxis = {}, yaxis = {}) {
    const t = getTheme();
    return {
        title: { text: title, font: { color: t.muted, size: 13 }, x: 0 },
        paper_bgcolor: t.paper,
        plot_bgcolor:  t.bg,
        font: { color: t.text, family: "Segoe UI, sans-serif" },
        margin: { l: 55, r: 24, t: 40, b: 55 },
        xaxis: { gridcolor: t.grid, zerolinecolor: t.grid, ...xaxis },
        yaxis: { gridcolor: t.grid, zerolinecolor: t.grid, ...yaxis },
        legend: { font: { color: t.muted }, bgcolor: "rgba(0,0,0,0)" },
        hoverlabel: { bgcolor: t.paper, bordercolor: t.grid, font: { color: t.text } },
    };
}

function spinner(id) {
    const el = document.getElementById(id);
    if (el) {
        // Le decimos a Plotly que limpie su gráfica de forma segura primero
        try { Plotly.purge(id); } catch(e) {} 
        
        // Ahora sí ponemos la ruedita de carga
        el.innerHTML = '<div class="loading-spinner"></div>';
    }
}
function errMsg(id, msg) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-dim);font-size:0.85rem;">⚠️ ${msg}</div>`;
}

function clearSpinner(id) {
    const el = document.getElementById(id);
    const spin = el ? el.querySelector('.loading-spinner') : null;
    if (spin) spin.remove(); // Solo borra la ruedita, deja la gráfica intacta
}

// ─── CACHE ────────────────────────────────────────────────────────────────
let cache = {};
async function fetchJSON(url) {
    if (cache[url]) return cache[url];
    const r = await fetch(API + url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    cache[url] = await r.json();
    return cache[url];
}

// ─── RENDER ALL ───────────────────────────────────────────────────────────
function renderAll() {
    renderHeatmap();
    renderWeekly();
    renderCorrelation();
    renderCycles();
    renderForecast();
    renderAnomalies();
}

// ─── 1. HEATMAP POR HORA ──────────────────────────────────────────────────
async function renderHeatmap() {
    spinner("chart-heatmap");
    try {
        const days = document.getElementById("heatmap-days").value;
        const d = await fetchJSON(`/data/heatmap?days=${days}`);
        const rows = d.data;
        const hours = rows.map(r => `${String(r.hour).padStart(2,"0")}:00`);
        const temps = rows.map(r => r.temperature);
        const t = getTheme();

        // 👇 NUEVO: Calcular mínimo y máximo ignorando nulos
        const validTemps = temps.filter(v => v !== null);
        const minT = validTemps.length > 0 ? Math.min(...validTemps) : 0;
        const maxT = validTemps.length > 0 ? Math.max(...validTemps) : 30;

        clearSpinner("chart-heatmap");

        Plotly.react("chart-heatmap", [{
            x: hours, y: temps, type: "bar",
            marker: {
                color: temps,
                colorscale: [[0,"#818cf8"],[0.5,"#f87171"],[1,"#fbbf24"]],
                showscale: true,
                colorbar: { title: "°C", thickness: 12, tickfont: { color: t.muted, size: 10 } }
            },
            hovertemplate: "<b>%{x}</b><br>Temp promedio: %{y:.1f} °C<extra></extra>",
        }], {
            ...baseLayout("Temperatura promedio por hora del día",
                { title: "Hora (COT)", tickangle: -45 },
                // 👇 NUEVO: Aplicar el recorte (zoom) al eje Y
                { title: "Temp (°C)", range: [minT - 0.5, maxT + 0.5] } 
            ),
            showlegend: false
        }, { responsive: true, displayModeBar: false });

        document.getElementById("heatmap-info").textContent =
            `Basado en ${rows.length} horas · últimos ${days} días`;
    } catch(e) { errMsg("chart-heatmap", "Error cargando heatmap"); }
}
// ─── 2. TENDENCIA SEMANAL ─────────────────────────────────────────────────
async function renderWeekly() {
    spinner("chart-weekly");
    try {
        const days = document.getElementById("weekly-days").value;
        const d = await fetchJSON(`/data/weekly?days=${days}`);
        const rows = d.data;
        const names = rows.map(r => r.day_name);
        const t = getTheme();

        clearSpinner("chart-weekly");

        Plotly.react("chart-weekly", [
            {
                x: names, y: rows.map(r => r.temperature),
                name: "Temperatura (°C)", type: "scatter", mode: "lines+markers",
                line: { color: "#f87171", width: 2 }, marker: { color: "#f87171", size: 7 },
                hovertemplate: "<b>%{x}</b><br>Temp: %{y:.1f} °C<extra></extra>",
            },
            {
                x: names, y: rows.map(r => r.humidity),
                name: "Humedad (%)", type: "scatter", mode: "lines+markers",
                line: { color: "#34d399", width: 2 }, marker: { color: "#34d399", size: 7 },
                yaxis: "y2",
                hovertemplate: "<b>%{x}</b><br>Humedad: %{y:.1f}%<extra></extra>",
            },
        ], {
            ...baseLayout(`Comportamiento promedio semanal · últimos ${days} días`),
            yaxis:  { ...baseLayout("").yaxis, title: "Temperatura (°C)" },
            yaxis2: { title: "Humedad (%)", overlaying: "y", side: "right",
                      gridcolor: t.grid, zerolinecolor: t.grid, tickfont: { color: t.muted } },
        }, { responsive: true, displayModeBar: false });
    } catch(e) { errMsg("chart-weekly", "Error cargando tendencia semanal"); }
}

// ─── 3. CORRELACIÓN TEMP / HUMEDAD ────────────────────────────────────────
async function renderCorrelation() {
    spinner("chart-correlation");
    try {
        const d = await fetchJSON(`/data?limit=2000`);
        const rows = d.data.filter(r => r.field1 != null && r.field2 != null);
        const temps = rows.map(r => parseFloat(r.field1));
        const hums  = rows.map(r => parseFloat(r.field2));
        const n = temps.length;
        const mT = temps.reduce((a,b)=>a+b,0)/n;
        const mH = hums.reduce((a,b)=>a+b,0)/n;
        const num  = temps.reduce((s,t,i)=>s+(t-mT)*(hums[i]-mH),0);
        const denT = Math.sqrt(temps.reduce((s,t)=>s+(t-mT)**2,0));
        const denH = Math.sqrt(hums.reduce((s,h)=>s+(h-mH)**2,0));
        const r = (denT*denH)>0 ? (num/(denT*denH)).toFixed(3) : "N/A";

        clearSpinner("chart-correlation");

        Plotly.react("chart-correlation", [{
            x: temps, y: hums, mode: "markers", type: "scatter",
            marker: {
                color: temps,
                colorscale: [[0,"#818cf8"],[0.5,"#38bdf8"],[1,"#f87171"]],
                size: 4, opacity: 0.55, showscale: true,
                colorbar: { title: "°C", thickness: 12 }
            },
            hovertemplate: "Temp: %{x:.1f}°C<br>Humedad: %{y:.1f}%<extra></extra>",
        }], {
            ...baseLayout(`Correlación Temperatura / Humedad · r = ${r}`,
                { title: "Temperatura (°C)" },
                { title: "Humedad (%)" }
            ),
            showlegend: false
        }, { responsive: true, displayModeBar: false });

        document.getElementById("correlation-r").textContent =
            `Pearson r = ${r} · ${n.toLocaleString()} puntos`;
    } catch(e) { errMsg("chart-correlation", "Error cargando correlación"); }
}

// ─── 4. CICLOS DIARIOS 3 SENSORES ────────────────────────────────────────
async function renderCycles() {
    spinner("chart-cycles");
    try {
        const d = await fetchJSON(`/data/heatmap?days=30`);
        const rows = d.data;
        const hours = rows.map(r => `${String(r.hour).padStart(2,"0")}:00`);
        const t = getTheme();

        clearSpinner("chart-cycles");

        Plotly.react("chart-cycles", [
            {
                x: hours, y: rows.map(r => r.temperature),
                name: "Temperatura (°C)", mode: "lines+markers",
                line: { color: "#f87171", width: 2 }, marker: { color: "#f87171", size: 5 },
                hovertemplate: "<b>%{x}</b><br>Temp: %{y:.1f} °C<extra></extra>",
            },
            {
                x: hours, y: rows.map(r => r.humidity),
                name: "Humedad (%)", mode: "lines+markers",
                line: { color: "#34d399", width: 2, dash: "dot" }, marker: { color: "#34d399", size: 5 },
                yaxis: "y2",
                hovertemplate: "<b>%{x}</b><br>Humedad: %{y:.1f}%<extra></extra>",
            },
            {
                x: hours, y: rows.map(r => r.pressure),
                name: "Presión (hPa)", mode: "lines+markers",
                line: { color: "#818cf8", width: 2, dash: "dash" }, marker: { color: "#818cf8", size: 5 },
                yaxis: "y3",
                hovertemplate: "<b>%{x}</b><br>Presión: %{y:.1f} hPa<extra></extra>",
            },
        ], {
            ...baseLayout("Ciclos diarios promedio — 3 sensores × hora (30 días)"),
            yaxis:  { gridcolor: t.grid, zerolinecolor: t.grid, title: "Temp (°C)", titlefont: { color: "#f87171" } },
            yaxis2: { title: "Humedad (%)", overlaying: "y", side: "right", showgrid: false,
                      titlefont: { color: "#34d399" }, tickfont: { color: t.muted }, zerolinecolor: t.grid },
            yaxis3: { title: "Presión (hPa)", overlaying: "y", side: "right",
                      anchor: "free", position: 0.95, showgrid: false,
                      titlefont: { color: "#818cf8" }, tickfont: { color: t.muted }, zerolinecolor: t.grid },
        }, { responsive: true, displayModeBar: false });
    } catch(e) { errMsg("chart-cycles", "Error cargando ciclos diarios"); }
}

// ─── 5. FORECAST ──────────────────────────────────────────────────────────
async function renderForecast() {
    spinner("chart-forecast");
    try {
        const d = await fetchJSON(`/data?limit=288`);
        const rows = d.data.filter(r => r.field1 != null).reverse();
        const times = rows.map(r => new Date(r.created_at).toLocaleString("es-CO",
            { timeZone: "America/Bogota", hour: "2-digit", minute: "2-digit" }));
        const temps = rows.map(r => parseFloat(r.field1));

        // Media móvil 12 puntos (~1h)
        const W = 12;
        const rolling = temps.map((_,i) => {
            if (i < W-1) return null;
            const s = temps.slice(i-W+1, i+1);
            return parseFloat((s.reduce((a,b)=>a+b,0)/W).toFixed(2));
        });

        // Tendencia lineal sobre últimos 12 puntos del rolling
        const valid = rolling.filter(v=>v!==null);
        const recent = valid.slice(-12);
        const slope  = (recent[recent.length-1] - recent[0]) / (recent.length-1);

        // Forecast 12 pasos (~1h)
        const lastTime = new Date(rows[rows.length-1]?.created_at);
        const fTemps = [], fTimes = [];
        for (let i=1; i<=12; i++) {
            fTemps.push(parseFloat((valid[valid.length-1] + slope*i).toFixed(2)));
            const ft = new Date(lastTime.getTime() + i*5*60*1000);
            fTimes.push(ft.toLocaleString("es-CO",
                { timeZone: "America/Bogota", hour: "2-digit", minute: "2-digit" }));
        }
        const pivot = times[times.length-1];
        const pivotV = valid[valid.length-1];

        clearSpinner("chart-forecast");

        Plotly.react("chart-forecast", [
            {
                x: times, y: temps, name: "Temperatura real",
                mode: "lines", line: { color: "#f87171", width: 1.5 }, opacity: 0.55,
                hovertemplate: "%{x}<br>%{y:.1f} °C<extra></extra>",
            },
            {
                x: times.filter((_,i)=>rolling[i]!==null),
                y: rolling.filter(v=>v!==null),
                name: "Media móvil 1h", mode: "lines",
                line: { color: "#38bdf8", width: 2.5 },
                hovertemplate: "%{x}<br>%{y:.1f} °C<extra></extra>",
            },
            {
                x: [pivot,...fTimes], y: [pivotV,...fTemps],
                name: "Forecast 1h", mode: "lines+markers",
                line: { color: "#facc15", width: 2, dash: "dot" },
                marker: { color: "#facc15", size: 5 },
                hovertemplate: "%{x}<br>Forecast: %{y:.1f} °C<extra></extra>",
            },
        ], {
            ...baseLayout("Temperatura últimas 24h + Forecast 1h",
                { title: "Hora (COT)", tickangle: -45, nticks:12 },
                { title: "°C" }
            )
        }, { responsive: true, displayModeBar: false });

        const dir = slope > 0.01 ? "↗ subiendo" : slope < -0.01 ? "↘ bajando" : "→ estable";
        document.getElementById("forecast-info").textContent =
            `Tendencia: ${dir} · Estimado en 1h: ${fTemps[fTemps.length-1]} °C`;
    } catch(e) { errMsg("chart-forecast", "Error calculando forecast"); }
}

// ─── 6. ANOMALÍAS ─────────────────────────────────────────────────────────
async function renderAnomalies() {
    try {
        const days  = document.getElementById("anomaly-days").value;
        const sigma = document.getElementById("anomaly-sigma").value;
        const d = await fetchJSON(`/data/anomalies?days=${days}&sigma=${sigma}`);

        const container = document.getElementById("anomalies-list");
        const badge     = document.getElementById("anomaly-count");
        badge.textContent = d.total;
        badge.style.background = d.total > 0 ? "#f87171" : "#34d399";

        if (d.total === 0) {
            container.innerHTML = `<div style="text-align:center;padding:32px;color:var(--text-dim);">
                <span style="font-size:2rem;display:block;margin-bottom:8px">✅</span>
                Sin anomalías en los últimos ${days} días con umbral ${sigma}σ
            </div>`;
            return;
        }

        const ICONS  = { temperature:"🌡️", humidity:"💧", pressure:"🔵" };
        const COLORS = { temperature:"#f87171", humidity:"#34d399", pressure:"#818cf8" };

        container.innerHTML = d.data.slice(0,50).map(a => {
            const dt = new Date(a.created_at).toLocaleString("es-CO",
                { timeZone:"America/Bogota", dateStyle:"short", timeStyle:"short" });
            return `<div class="alert-item">
                <div class="alert-icon" style="background:${COLORS[a.sensor]}20;color:${COLORS[a.sensor]};border:1px solid ${COLORS[a.sensor]}40">
                    ${ICONS[a.sensor]}
                </div>
                <div class="alert-content">
                    <div class="alert-message">${a.sensor} = ${a.value} &nbsp;·&nbsp; ${a.deviation}σ de la media</div>
                    <div class="alert-meta">
                        <span class="alert-time">${dt}</span>
                        <span class="alert-value">media ${a.mean} ± ${a.std}</span>
                    </div>
                </div>
            </div>`;
        }).join("");
    } catch(e) {
        document.getElementById("anomalies-list").innerHTML =
            `<div style="color:var(--text-dim);padding:20px;text-align:center;">⚠️ Error cargando anomalías</div>`;
    }
}

// ─── CONTROLES ────────────────────────────────────────────────────────────
document.getElementById("heatmap-days").addEventListener("change",  () => { cache={}; renderHeatmap(); });
document.getElementById("weekly-days").addEventListener("change",   () => { cache={}; renderWeekly(); });
document.getElementById("anomaly-days").addEventListener("change",  () => { cache={}; renderAnomalies(); });
document.getElementById("anomaly-sigma").addEventListener("change", () => { cache={}; renderAnomalies(); });

// ─── INIT ─────────────────────────────────────────────────────────────────
renderAll();
