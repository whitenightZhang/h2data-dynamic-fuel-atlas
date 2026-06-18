const DATA_ROOT = "./data/";
const YEARS = [2030, 2035, 2050];

const state = {
  metadata: null,
  world: null,
  product: "hydrogen",
  year: 2035,
  rows: [],
  filteredRows: [],
  selectedRow: null,
  selectedIndex: -1,
  region: "all",
  biasMode: "percent",
  logScale: false,
};

const els = {
  productTabs: document.getElementById("productTabs"),
  yearValue: document.getElementById("yearValue"),
  prevYear: document.getElementById("prevYear"),
  nextYear: document.getElementById("nextYear"),
  regionSelect: document.getElementById("regionSelect"),
  logScale: document.getElementById("logScale"),
  biasMode: document.getElementById("biasMode"),
  costMap: document.getElementById("costMap"),
  biasMap: document.getElementById("biasMap"),
  costStatus: document.getElementById("costStatus"),
  biasStatus: document.getElementById("biasStatus"),
  costSubtitle: document.getElementById("costSubtitle"),
  biasSubtitle: document.getElementById("biasSubtitle"),
  costLegend: document.getElementById("costLegend"),
  biasLegend: document.getElementById("biasLegend"),
  selectedTitle: document.getElementById("selectedTitle"),
  selectedMeta: document.getElementById("selectedMeta"),
  metricStrip: document.getElementById("metricStrip"),
  selectLowest: document.getElementById("selectLowest"),
};

const colors = {
  costLow: [253, 246, 216],
  costMid: [216, 154, 59],
  costHigh: [127, 59, 8],
  biasNeg: [184, 95, 74],
  biasZero: [247, 250, 250],
  biasPos: [14, 103, 172],
  selected: "#101820",
};

function schema() {
  return state.product === "hydrogen"
    ? state.metadata.schemas.hydrogen
    : state.metadata.schemas.product;
}

function idx(name) {
  return schema().indexOf(name);
}

function productMeta() {
  return state.metadata.products[state.product];
}

function finite(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function formatNumber(value, digits = 2) {
  if (!finite(value)) return "n/a";
  const abs = Math.abs(value);
  const maxDigits = abs >= 100 ? 0 : abs >= 10 ? 1 : digits;
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: maxDigits,
  }).format(value);
}

function formatCoord(value, pos, neg) {
  if (!finite(value)) return "";
  return `${Math.abs(value).toFixed(2)}° ${value >= 0 ? pos : neg}`;
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function mix(c1, c2, t) {
  const r = Math.round(lerp(c1[0], c2[0], t));
  const g = Math.round(lerp(c1[1], c2[1], t));
  const b = Math.round(lerp(c1[2], c2[2], t));
  return `rgb(${r},${g},${b})`;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function getExtent(rows, valueIndex) {
  let min = Infinity;
  let max = -Infinity;
  for (const row of rows) {
    const v = row[valueIndex];
    if (finite(v)) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
  if (min === max) return [min - 1, max + 1];
  return [min, max];
}

function getPercentile(rows, valueIndex, p) {
  const values = rows.map((row) => row[valueIndex]).filter(finite).sort((a, b) => a - b);
  if (!values.length) return 1;
  const rank = clamp(Math.floor((values.length - 1) * p), 0, values.length - 1);
  return values[rank];
}

function getPositivePercentile(rows, valueIndex, p) {
  const values = rows
    .map((row) => row[valueIndex])
    .filter((value) => finite(value) && value > 0)
    .sort((a, b) => a - b);
  if (!values.length) return 1;
  const rank = clamp(Math.floor((values.length - 1) * p), 0, values.length - 1);
  return values[rank];
}

function niceScaleMax(value) {
  if (!finite(value) || value <= 0) return 1;
  if (value <= 1) return 1;
  if (value <= 2) return 2;
  if (value <= 5) return 5;
  if (value <= 10) return 10;
  if (value <= 1000) return Math.ceil(value / 10) * 10;
  return Math.ceil(value / 100) * 100;
}

function formatLegendNumber(value) {
  if (!finite(value)) return "0";
  if (Math.abs(value) >= 1) return String(Math.round(value));
  return value.toFixed(1).replace(/\.0$/, "");
}

function legendLabels(maxValue, unit) {
  const maxLabel = formatLegendNumber(maxValue);
  const suffix = unit === "%" ? "%" : ` ${unit}`;
  if (maxValue <= 5) return ["0", `${maxLabel}${suffix}`];
  return ["0", formatLegendNumber(maxValue / 2), `${maxLabel}${suffix}`];
}

function costColor(value, maxValue) {
  if (!finite(value)) return "rgba(170,180,184,0.22)";
  const raw = state.logScale ? Math.log1p(value) / Math.log1p(maxValue) : value / maxValue;
  const t = clamp(raw, 0, 1);
  if (t < 0.55) return mix(colors.costLow, colors.costMid, t / 0.55);
  return mix(colors.costMid, colors.costHigh, (t - 0.55) / 0.45);
}

function biasColor(value, maxValue) {
  if (!finite(value)) return "rgba(170,180,184,0.22)";
  const denom = maxValue <= 0 ? 1 : maxValue;
  return mix(colors.biasZero, colors.biasPos, clamp(Math.max(0, value) / denom, 0, 1));
}

function projection(width, height) {
  const padX = 18;
  const padY = 20;
  const mapWidth = width - padX * 2;
  const mapHeight = height - padY * 2;
  return {
    project(lat, lon) {
      return [
        padX + ((lon + 180) / 360) * mapWidth,
        padY + ((90 - lat) / 180) * mapHeight,
      ];
    },
    unproject(x, y) {
      const lon = ((x - padX) / mapWidth) * 360 - 180;
      const lat = 90 - ((y - padY) / mapHeight) * 180;
      return [lat, lon];
    },
  };
}

function setupCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, width: rect.width, height: rect.height };
}

function decodeArc(topology, arcIndex) {
  const index = arcIndex < 0 ? ~arcIndex : arcIndex;
  const arc = topology.arcs[index] || [];
  const scale = topology.transform.scale;
  const translate = topology.transform.translate;
  let x = 0;
  let y = 0;
  const points = arc.map((point) => {
    x += point[0];
    y += point[1];
    return [x * scale[0] + translate[0], y * scale[1] + translate[1]];
  });
  return arcIndex < 0 ? points.reverse() : points;
}

function drawWorld(ctx, width, height) {
  if (!state.world?.objects?.land) return;
  const proj = projection(width, height);
  const land = state.world.objects.land.geometries?.[0];
  if (!land?.arcs) return;

  ctx.save();
  ctx.beginPath();
  for (const polygon of land.arcs) {
    for (const ring of polygon) {
      let started = false;
      for (const arcIndex of ring) {
        const points = decodeArc(state.world, arcIndex);
        for (const point of points) {
          const [x, y] = proj.project(point[1], point[0]);
          if (!started) {
            ctx.moveTo(x, y);
            started = true;
          } else {
            ctx.lineTo(x, y);
          }
        }
      }
    }
  }
  ctx.fillStyle = "#eef2ef";
  ctx.fill();
  ctx.strokeStyle = "#cfd8d5";
  ctx.lineWidth = 0.7;
  ctx.stroke();
  ctx.restore();
}

function drawGraticule(ctx, width, height) {
  const proj = projection(width, height);
  ctx.save();
  ctx.strokeStyle = "#dbe3e6";
  ctx.lineWidth = 0.7;
  ctx.fillStyle = "#78858c";
  ctx.font = "11px Inter, Arial, sans-serif";

  for (let lon = -120; lon <= 180; lon += 60) {
    const [x1, y1] = proj.project(-70, lon);
    const [x2, y2] = proj.project(85, lon);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.fillText(`${Math.abs(lon)}°${lon < 0 ? "W" : lon > 0 ? "E" : ""}`, x1 - 14, height - 18);
  }

  for (let lat = -60; lat <= 90; lat += 30) {
    const [x1, y] = proj.project(lat, -180);
    const [x2] = proj.project(lat, 180);
    ctx.beginPath();
    ctx.moveTo(x1, y);
    ctx.lineTo(x2, y);
    ctx.stroke();
    ctx.fillText(`${Math.abs(lat)}°${lat < 0 ? "S" : lat > 0 ? "N" : ""}`, 6, y + 4);
  }
  ctx.restore();
}

function drawSelected(ctx, width, height) {
  if (!state.selectedRow) return;
  const proj = projection(width, height);
  const [x, y] = proj.project(state.selectedRow[idx("lat")], state.selectedRow[idx("lon")]);
  ctx.save();
  ctx.lineWidth = 4;
  ctx.strokeStyle = "rgba(255,255,255,0.92)";
  ctx.beginPath();
  ctx.moveTo(x - 13, y);
  ctx.lineTo(x + 13, y);
  ctx.moveTo(x, y - 13);
  ctx.lineTo(x, y + 13);
  ctx.stroke();
  ctx.lineWidth = 2;
  ctx.strokeStyle = colors.selected;
  ctx.beginPath();
  ctx.moveTo(x - 13, y);
  ctx.lineTo(x + 13, y);
  ctx.moveTo(x, y - 13);
  ctx.lineTo(x, y + 13);
  ctx.stroke();
  ctx.restore();
}

function drawMap(canvas, metric) {
  const { ctx, width, height } = setupCanvas(canvas);
  const rows = state.filteredRows;
  const proj = projection(width, height);
  const costIndex = idx("cost_8760");
  const biasIndex = state.biasMode === "percent" ? idx("underestimation_pct") : idx("absolute_underestimate");
  const valueIndex = metric === "cost" ? costIndex : biasIndex;
  const pointSize = state.product === "hydrogen" ? Math.max(1, width / 850) : Math.max(1.45, width / 520);

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcfc";
  ctx.fillRect(0, 0, width, height);
  drawWorld(ctx, width, height);
  drawGraticule(ctx, width, height);

  let scaleMax;
  let maxValue = 1;
  if (metric === "cost") {
    scaleMax = niceScaleMax(getPercentile(rows, costIndex, 0.95));
  } else {
    maxValue = niceScaleMax(getPositivePercentile(rows, biasIndex, 0.95));
  }

  ctx.save();
  ctx.globalAlpha = state.product === "hydrogen" ? 0.72 : 0.86;
  for (const row of rows) {
    const lat = row[idx("lat")];
    const lon = row[idx("lon")];
    const value = row[valueIndex];
    if (!finite(lat) || !finite(lon)) continue;
    const [x, y] = proj.project(lat, lon);
    ctx.fillStyle = metric === "cost" ? costColor(value, scaleMax) : biasColor(value, maxValue);
    if (state.product === "hydrogen") {
      ctx.fillRect(x, y, pointSize, pointSize);
    } else {
      ctx.beginPath();
      ctx.arc(x, y, pointSize, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.restore();
  drawSelected(ctx, width, height);

  if (metric === "cost") {
    renderLegend(els.costLegend, {
      colors: ["#fdf6d8", "#d89a3b", "#7f3b08"],
      labels: legendLabels(scaleMax, productMeta().cost_unit),
    });
  } else {
    renderLegend(els.biasLegend, {
      colors: ["#f7fafa", "#7bb9dc", "#0e67ac"],
      labels: legendLabels(maxValue, state.biasMode === "percent" ? "%" : productMeta().bias_unit),
    });
  }
}

function renderLegend(container, config) {
  container.innerHTML = "";
  const ramp = document.createElement("div");
  ramp.className = "legend-ramp";
  ramp.style.background = `linear-gradient(90deg, ${config.colors.join(", ")})`;
  const labels = document.createElement("div");
  labels.className = "legend-labels";
  labels.innerHTML = config.labels.map((label) => `<span>${label}</span>`).join("");
  container.append(ramp, labels);
}

function showLoading(isLoading) {
  els.costStatus.classList.toggle("visible", isLoading);
  els.biasStatus.classList.toggle("visible", isLoading);
}

async function loadJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`Cannot load ${path}`);
  return response.json();
}

async function init() {
  showLoading(true);
  state.metadata = await loadJson(`${DATA_ROOT}metadata.json`);
  applyUrlState();
  if (state.metadata.world_map) {
    state.world = await loadJson(`${DATA_ROOT}${state.metadata.world_map}`);
  }
  buildProductTabs();
  syncControlState();
  bindEvents();
  await loadCurrentData();
  window.addEventListener("resize", debounce(renderAll, 120));
}

function syncControlState() {
  [...els.productTabs.children].forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.product === state.product);
  });
  [...els.biasMode.children].forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === state.biasMode);
  });
  els.yearValue.textContent = String(state.year);
}

function applyUrlState() {
  const params = new URLSearchParams(window.location.search);
  const product = params.get("product");
  const year = Number(params.get("year"));
  const bias = params.get("bias");
  if (product && state.metadata.products[product]) state.product = product;
  if (YEARS.includes(year)) state.year = year;
  if (bias === "absolute" || bias === "percent") state.biasMode = bias;
}

function buildProductTabs() {
  els.productTabs.innerHTML = "";
  const labels = [
    ["hydrogen", "H2", "Hydrogen"],
    ["ammonia", "NH3", "Ammonia"],
    ["methanol", "MeOH", "Methanol"],
    ["saf", "SAF", "e-SAF"],
  ];
  for (const [key, short, label] of labels) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.product = key;
    button.className = key === state.product ? "active" : "";
    button.innerHTML = `<strong>${short}</strong> ${label}`;
    els.productTabs.appendChild(button);
  }
}

function bindEvents() {
  els.productTabs.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-product]");
    if (!button) return;
    state.product = button.dataset.product;
    state.region = "all";
    [...els.productTabs.children].forEach((btn) => btn.classList.toggle("active", btn === button));
    await loadCurrentData();
  });

  els.prevYear.addEventListener("click", async () => {
    const i = YEARS.indexOf(state.year);
    state.year = YEARS[(i - 1 + YEARS.length) % YEARS.length];
    await loadCurrentData();
  });

  els.nextYear.addEventListener("click", async () => {
    const i = YEARS.indexOf(state.year);
    state.year = YEARS[(i + 1) % YEARS.length];
    await loadCurrentData();
  });

  els.regionSelect.addEventListener("change", () => {
    state.region = els.regionSelect.value;
    applyRegionFilter();
    selectLowestCost();
    renderAll();
  });

  els.logScale.addEventListener("change", () => {
    state.logScale = els.logScale.checked;
    renderAll();
  });

  els.biasMode.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-mode]");
    if (!button) return;
    state.biasMode = button.dataset.mode;
    [...els.biasMode.children].forEach((btn) => btn.classList.toggle("active", btn === button));
    renderAll();
  });

  for (const canvas of [els.costMap, els.biasMap]) {
    canvas.addEventListener("click", (event) => {
      selectNearest(canvas, event);
      renderAll();
    });
  }

  els.selectLowest.addEventListener("click", () => {
    selectLowestCost();
    renderAll();
  });
}

async function loadCurrentData() {
  showLoading(true);
  els.yearValue.textContent = String(state.year);
  const file = state.metadata.products[state.product].files[String(state.year)];
  const payload = await loadJson(`${DATA_ROOT}${file}`);
  state.rows = payload.rows;
  updateSubtitles();
  buildRegionOptions();
  applyRegionFilter();
  selectLowestCost();
  showLoading(false);
  renderAll();
}

function updateSubtitles() {
  const meta = productMeta();
  els.costSubtitle.textContent = `${meta.label}, ${state.year}, ${meta.cost_unit}`;
  els.biasSubtitle.textContent =
    state.biasMode === "percent"
      ? "Underestimation as share of 8760-hour cost"
      : `Absolute underestimation, ${meta.bias_unit}`;
}

function buildRegionOptions() {
  const regionIndex = idx("region");
  const regions = [...new Set(state.rows.map((row) => row[regionIndex]).filter(Boolean))].sort();
  els.regionSelect.innerHTML = `<option value="all">All regions</option>`;
  for (const region of regions) {
    const option = document.createElement("option");
    option.value = region;
    option.textContent = region;
    els.regionSelect.appendChild(option);
  }
  els.regionSelect.value = state.region;
}

function applyRegionFilter() {
  const regionIndex = idx("region");
  state.filteredRows =
    state.region === "all"
      ? state.rows
      : state.rows.filter((row) => row[regionIndex] === state.region);
  if (!state.filteredRows.length) {
    state.filteredRows = state.rows;
    state.region = "all";
    els.regionSelect.value = "all";
  }
}

function selectLowestCost() {
  const costIndex = idx("cost_8760");
  const underIndex = idx("underestimation_pct");
  const regionIndex = idx("region");
  const interpretableRows = state.filteredRows.filter((row) => {
    return (
      finite(row[costIndex]) &&
      finite(row[underIndex]) &&
      row[underIndex] > 0 &&
      row[regionIndex] &&
      row[regionIndex] !== "Unknown"
    );
  });
  const candidates = interpretableRows.length ? interpretableRows : state.filteredRows;
  let best = null;
  let bestIndex = -1;
  for (let i = 0; i < candidates.length; i += 1) {
    const value = candidates[i][costIndex];
    if (!finite(value)) continue;
    if (!best || value < best[costIndex]) {
      best = candidates[i];
      bestIndex = i;
    }
  }
  state.selectedRow = best;
  state.selectedIndex = bestIndex;
}

function selectNearest(canvas, event) {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const proj = projection(rect.width, rect.height);
  let best = null;
  let bestIndex = -1;
  let bestDistance = Infinity;

  for (let i = 0; i < state.filteredRows.length; i += 1) {
    const row = state.filteredRows[i];
    const [px, py] = proj.project(row[idx("lat")], row[idx("lon")]);
    const d = (px - x) ** 2 + (py - y) ** 2;
    if (d < bestDistance) {
      bestDistance = d;
      best = row;
      bestIndex = i;
    }
  }

  state.selectedRow = best;
  state.selectedIndex = bestIndex;
}

function renderAll() {
  updateSubtitles();
  drawMap(els.costMap, "cost");
  drawMap(els.biasMap, "bias");
  renderDetails();
}

function metric(label, value, unit, className = "", note = "") {
  return `
    <div class="metric">
      <div class="metric-label">${label}</div>
      <div class="metric-value ${className}">${value}<span class="metric-unit">${unit}</span></div>
      <div class="metric-note">${note}</div>
    </div>
  `;
}

function renderDetails() {
  const row = state.selectedRow;
  if (!row) {
    els.selectedTitle.textContent = "No grid selected";
    els.selectedMeta.textContent = "Click either map to inspect a node.";
    els.metricStrip.innerHTML = "";
    return;
  }

  const meta = productMeta();
  const lat = row[idx("lat")];
  const lon = row[idx("lon")];
  const region = row[idx("region")];
  els.selectedTitle.textContent = `${formatCoord(lat, "N", "S")}, ${formatCoord(lon, "E", "W")}`;
  els.selectedMeta.textContent = `${meta.label} / ${state.year} / ${region || "unassigned"}`;

  const cost = row[idx("cost_8760")];
  const underAbs = row[idx("absolute_underestimate")];
  const underPct = row[idx("underestimation_pct")];

  els.metricStrip.innerHTML = [
    metric("8760-hour cost", formatNumber(cost), meta.cost_unit, "cost", "Dynamic model output"),
    metric("Underestimation", formatNumber(underAbs), meta.bias_unit, "bias", "8760-hour minus static reference"),
    metric("Underestimation (%)", `${formatNumber(underPct, 1)}%`, "", "bias", "Positive means static benchmark is lower"),
  ].join("");
}

function debounce(fn, wait) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), wait);
  };
}

init().catch((error) => {
  console.error(error);
  showLoading(false);
  els.costStatus.textContent = "Could not load data";
  els.biasStatus.textContent = "Could not load data";
  els.costStatus.classList.add("visible");
  els.biasStatus.classList.add("visible");
});
