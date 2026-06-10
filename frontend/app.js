"use strict";

const API = "/api";

const PRESETS = [
  { label: "Idade da Pedra", from: -10000, to: -8000 },
  { label: "Roma Antiga", from: 1, to: 200 },
  { label: "Idade Média", from: 1000, to: 1400 },
  { label: "Revolução Industrial", from: 1800, to: 1850 },
  { label: "Pós-guerra", from: 1950, to: 1970 },
  { label: "Hoje", from: 2010, to: 2023 },
];

const el = (id) => document.getElementById(id);

async function loadPlaces() {
  const sel = el("place");
  try {
    const res = await fetch(`${API}/places`);
    const data = await res.json();
    const preferidos = ["World", "Brazil", "France", "Japan", "United States", "Germany", "India", "China"];
    const all = data.places;
    // coloca os preferidos no topo
    const top = preferidos.filter((p) => all.includes(p));
    const rest = all.filter((p) => !top.includes(p));
    for (const p of [...top, "──────────", ...rest]) {
      const opt = document.createElement("option");
      opt.value = p === "──────────" ? "" : p;
      opt.textContent = p;
      if (p === "──────────") opt.disabled = true;
      sel.appendChild(opt);
    }
    sel.value = "World";
  } catch (e) {
    sel.innerHTML = '<option>Erro ao carregar lugares</option>';
  }
}

function buildPresets() {
  const box = el("presets");
  for (const p of PRESETS) {
    const b = document.createElement("button");
    b.textContent = p.label;
    b.onclick = () => {
      el("yearFrom").value = p.from;
      el("yearTo").value = p.to;
    };
    box.appendChild(b);
  }
}

function badge(conf) {
  const map = { alta: "alta", media: "média", baixa: "baixa" };
  return `<span class="badge ${conf}">${map[conf] || conf}</span>`;
}

function renderResult(data) {
  const n = data.narrative;
  const facts = data.facts
    .map(
      (f) => `
      <div class="fact">
        <div class="k">${f.label} ${badge(f.confidence)}</div>
        <div class="v">${f.value}</div>
        <div class="d">${f.detail || ""}</div>
      </div>`
    )
    .join("");

  const sources = data.sources
    .map(
      (s) => `
      <li>
        <a href="${s.url}" target="_blank" rel="noopener">${s.title}</a> — ${s.publisher}.
        ${s.note ? `<br><span>${s.note}</span>` : ""}
      </li>`
    )
    .join("");

  const story = n.story.map((p) => `<p>${p}</p>`).join("");

  el("result").innerHTML = `
    <div class="headline">${n.headline}</div>
    <div class="story">${story}</div>
    <div class="facts">${facts}</div>
    <p class="legend">Confiança do dado: ${badge("alta")} medição direta &nbsp;
      ${badge("media")} extrapolado/modelado &nbsp; ${badge("baixa")} estimativa histórica</p>
    <div class="sources">
      <h3>Fontes</h3>
      <ul>${sources}</ul>
    </div>
    <button class="again" id="againBtn">🎲 Girar de novo</button>
  `;
  el("result").classList.remove("hidden");
  el("againBtn").onclick = doDraw;
  el("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function doDraw() {
  const btn = el("drawBtn");
  btn.disabled = true;
  try {
    const body = {
      place: el("place").value || "World",
      year_from: parseInt(el("yearFrom").value, 10),
      year_to: parseInt(el("yearTo").value, 10),
    };
    const res = await fetch(`${API}/draw`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    renderResult(data);
  } catch (e) {
    el("result").innerHTML = `<p style="color:#c98a8a">Erro: ${e.message}</p>`;
    el("result").classList.remove("hidden");
  } finally {
    btn.disabled = false;
  }
}

el("drawBtn").onclick = doDraw;
buildPresets();
loadPlaces();
