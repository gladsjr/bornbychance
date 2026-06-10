"use strict";
/* Interface: carrega os dados, popula controles e chama o motor no próprio navegador. */

const PRESETS = [
  { label: "Idade da Pedra", from: -10000, to: -8000 },
  { label: "Roma Antiga", from: 1, to: 200 },
  { label: "Idade Média", from: 1000, to: 1400 },
  { label: "Revolução Industrial", from: 1800, to: 1850 },
  { label: "Pós-guerra", from: 1950, to: 1970 },
  { label: "Hoje", from: 2010, to: 2023 },
];

const el = (id) => document.getElementById(id);

function populatePlaces() {
  const sel = el("place");
  sel.innerHTML = "";
  const preferidos = ["World", "Brazil", "France", "Japan", "United States", "Germany", "India", "China"];
  const all = DATA.places;
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
}

function buildPresets() {
  const box = el("presets");
  for (const p of PRESETS) {
    const b = document.createElement("button");
    b.textContent = p.label;
    b.onclick = () => { el("yearFrom").value = p.from; el("yearTo").value = p.to; };
    box.appendChild(b);
  }
}

function badge(conf) {
  const map = { alta: "alta", media: "média", baixa: "baixa" };
  return `<span class="badge ${conf}">${map[conf] || conf}</span>`;
}

function renderResult(data, narrative) {
  const facts = data.facts
    .map((f) => `
      <div class="fact">
        <div class="k">${f.label} ${badge(f.confidence)}</div>
        <div class="v">${f.value}</div>
        <div class="d">${f.detail || ""}</div>
      </div>`)
    .join("");

  const sources = data.sources
    .map((s) => `
      <li>
        <a href="${s.url}" target="_blank" rel="noopener">${s.title}</a> — ${s.publisher}.
        ${s.note ? `<br><span>${s.note}</span>` : ""}
      </li>`)
    .join("");

  const story = narrative.story.map((p) => `<p>${p}</p>`).join("");

  el("result").innerHTML = `
    <div class="headline">${narrative.headline}</div>
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

function doDraw() {
  const btn = el("drawBtn");
  btn.disabled = true;
  try {
    const place = el("place").value || "World";
    const yFrom = parseInt(el("yearFrom").value, 10);
    const yTo = parseInt(el("yearTo").value, 10);
    const result = draw(place, yFrom, yTo);
    const narrative = buildNarrative(result);
    renderResult(result, narrative);
  } catch (e) {
    el("result").innerHTML = `<p style="color:#c98a8a">Erro: ${e.message}</p>`;
    el("result").classList.remove("hidden");
    console.error(e);
  } finally {
    btn.disabled = false;
  }
}

async function init() {
  buildPresets();
  try {
    await loadData();
    populatePlaces();
    const btn = el("drawBtn");
    btn.disabled = false;
    btn.textContent = "🎲 Girar a roleta do nascimento";
    btn.onclick = doDraw;
  } catch (e) {
    el("drawBtn").textContent = "erro ao carregar dados";
    console.error(e);
  }
}

init();
