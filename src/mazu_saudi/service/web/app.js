const state = { config: null, forecast: null, lead: 1, region: "arabian_peninsula", layer: "probability" };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function getJSON(path) {
  const response = await fetch(path);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed: ${response.status}`);
  return payload;
}

function formatUtc(value) {
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: "UTC", hour12: false }).format(new Date(value)) + " UTC";
}

async function initialize() {
  state.config = await getJSON("/api/v1/config");
  const select = $("#region-select");
  state.config.regions.forEach((region) => {
    const option = document.createElement("option"); option.value = region.id;
    option.textContent = `${region.label_zh} / ${region.label}`; select.appendChild(option);
  });
  $("#forecast-origin").textContent = formatUtc(state.config.forecast_origin);
  select.addEventListener("change", () => { state.region = select.value; loadForecast(); });
  $$("[data-lead]").forEach((button) => button.addEventListener("click", () => {
    state.lead = Number(button.dataset.lead); $$("[data-lead]").forEach((item) => item.classList.toggle("active", item === button)); loadForecast();
  }));
  $$("[data-layer]").forEach((button) => button.addEventListener("click", () => {
    state.layer = button.dataset.layer; $$("[data-layer]").forEach((item) => item.classList.toggle("active", item === button)); drawMap();
  }));
  $("#refresh-button").addEventListener("click", loadForecast);
  window.addEventListener("resize", drawMap);
  const events = await getJSON("/api/v1/events"); renderEvents(events);
  await loadForecast();
}

async function loadForecast() {
  $("#loading").classList.add("visible");
  try {
    state.forecast = await getJSON(`/api/v1/forecast?region=${encodeURIComponent(state.region)}&lead_hours=${state.lead}`);
    renderForecast();
  } catch (error) {
    $("#forecast-status").textContent = "ERROR"; $("#forecast-status").classList.add("abstain");
  } finally { $("#loading").classList.remove("visible"); }
}

function renderForecast() {
  const data = state.forecast, summary = data.summary;
  $("#map-title").textContent = `${data.region.label_zh} · 极端降水发生概率`;
  $("#valid-time").textContent = formatUtc(data.valid_time);
  $("#map-north").textContent = `${data.region.bbox[2]}°N`; $("#map-south").textContent = `${data.region.bbox[0]}°N`;
  $("#max-probability").textContent = `${Math.round(summary.max_probability * 100)}%`;
  $("#mean-probability").textContent = `${Math.round(summary.mean_probability * 100)}%`;
  $("#p50-rain").textContent = summary.p50_rainfall_mm.toFixed(1); $("#p90-rain").textContent = summary.p90_rainfall_mm.toFixed(1);
  $("#uncertainty-value").textContent = summary.uncertainty.toFixed(2);
  $("#coverage-value").textContent = `${Math.round(summary.selective_coverage * 100)}%`;
  $("#confidence-ring").style.setProperty("--coverage", `${summary.selective_coverage * 100}%`);
  const status = $("#forecast-status"); status.textContent = summary.status === "abstain" ? "REVIEW" : "FORECAST"; status.classList.toggle("abstain", summary.status === "abstain");
  $("#model-version").textContent = data.model.version; $("#data-version").textContent = data.data_version;
  renderRouting(data.routing); renderSources(data.sources); drawMap();
}

function renderRouting(routes) {
  $("#routing-bars").innerHTML = routes.map((route) => `<div class="route"><div class="route-head"><span>${route.label}</span><span>${Math.round(route.weight * 100)}%</span></div><div class="route-track"><i style="width:${route.weight * 100}%"></i></div></div>`).join("");
}

function renderSources(sources) {
  $("#source-list").innerHTML = sources.map((source) => `<div class="source-row"><i class="source-dot ${source.status}"></i><div class="source-main"><strong>${source.label}</strong><small>${source.source}</small></div><div class="source-state"><strong>${source.status.replaceAll("_", " ")}</strong><small>${source.freshness_minutes == null ? "STATIC / EVAL" : `${source.freshness_minutes} MIN AGO`}</small></div></div>`).join("");
}

function renderEvents(events) {
  $("#event-list").innerHTML = events.map((event) => `<div class="event-row"><span class="event-time">${event.time}</span><span class="event-node"><i></i></span><span class="event-copy"><strong>${event.title}</strong><small>${event.detail}</small></span></div>`).join("");
}

function colorFor(value, layer) {
  if (layer === "uncertainty") {
    const t = Math.max(0, Math.min(1, value / .5)); return `rgba(${Math.round(81 + 174*t)},${Math.round(175 - 47*t)},${Math.round(176 - 65*t)},${.18 + .7*t})`;
  }
  const stops = [[8,28,22],[37,101,75],[91,191,130],[215,245,111],[255,177,92]];
  const scaled = Math.max(0, Math.min(.999, value)) * (stops.length - 1), index = Math.floor(scaled), t = scaled - index;
  const a = stops[index], b = stops[Math.min(index + 1, stops.length - 1)];
  return `rgb(${a.map((item, i) => Math.round(item + (b[i]-item)*t)).join(",")})`;
}

function drawMap() {
  if (!state.forecast) return;
  const canvas = $("#forecast-map"), rect = canvas.getBoundingClientRect(), ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(rect.width * ratio); canvas.height = Math.round(rect.height * ratio);
  const context = canvas.getContext("2d"); context.scale(ratio, ratio);
  const rows = 18, columns = 24, cellWidth = rect.width / columns, cellHeight = rect.height / rows;
  context.fillStyle = "#071510"; context.fillRect(0, 0, rect.width, rect.height);
  state.forecast.cells.forEach((cell) => { context.fillStyle = colorFor(cell[state.layer], state.layer); context.fillRect(cell.column * cellWidth, cell.row * cellHeight, cellWidth + .5, cellHeight + .5); });
  context.globalCompositeOperation = "screen"; context.fillStyle = "rgba(215,245,111,.055)";
  context.beginPath(); context.ellipse(rect.width*.44, rect.height*.56, rect.width*.34, rect.height*.28, -.25, 0, Math.PI*2); context.fill(); context.globalCompositeOperation = "source-over";
  canvas.onmousemove = (event) => showTooltip(event, rect, rows, columns); canvas.onmouseleave = () => $("#map-tooltip").hidden = true;
}

function showTooltip(event, rect, rows, columns) {
  const column = Math.min(columns - 1, Math.floor(event.offsetX / (rect.width / columns))), row = Math.min(rows - 1, Math.floor(event.offsetY / (rect.height / rows)));
  const cell = state.forecast.cells.find((item) => item.row === row && item.column === column); if (!cell) return;
  const tooltip = $("#map-tooltip"); tooltip.hidden = false; tooltip.style.left = `${Math.min(event.offsetX + 12, rect.width - 150)}px`; tooltip.style.top = `${Math.min(event.offsetY + 12, rect.height - 74)}px`;
  tooltip.innerHTML = `${cell.latitude.toFixed(2)}°N / ${cell.longitude.toFixed(2)}°E<br>概率&nbsp; ${Math.round(cell.probability*100)}%<br>不确定性&nbsp; ${cell.uncertainty.toFixed(2)}`;
}

initialize().catch(() => { $("#forecast-status").textContent = "OFFLINE"; });
