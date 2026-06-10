"use strict";
/*
 * Born by Chance — motor do sorteio, 100% no navegador.
 * Porte fiel da lógica que antes ficava no backend Python. Lê docs/data.json
 * (gerado por scripts/build_static.py a partir dos dados reais) e devolve uma
 * vida concreta sorteada. Nenhum número é inventado: tudo vem dos dados ou de
 * estimativas históricas citadas.
 */

let DATA = null;
let COUNTRY_SET = null;

const CONTINENTS = new Set(["Africa", "Asia", "Europe", "North America", "Oceania", "South America"]);
const REGION_ALIASES = {
  "Americas (UN)": new Set(["North America", "South America"]),
  "Americas": new Set(["North America", "South America"]),
};

async function loadData() {
  DATA = await fetch("data.json").then((r) => r.json());
  COUNTRY_SET = new Set(DATA.countries);
  return DATA;
}

// ---- utilidades de série ----------------------------------------------------

function _interpPairs(arr, year) {
  // arr: [[ano, valor], ...] ordenado. Retorna [valor, anoUsado, distancia].
  const n = arr.length;
  if (year <= arr[0][0]) return [arr[0][1], arr[0][0], arr[0][0] - year];
  if (year >= arr[n - 1][0]) return [arr[n - 1][1], arr[n - 1][0], year - arr[n - 1][0]];
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (arr[mid][0] <= year) lo = mid; else hi = mid;
  }
  const [y0, v0] = arr[lo], [y1, v1] = arr[hi];
  const t = (year - y0) / (y1 - y0);
  const v = v0 + t * (v1 - v0);
  const yearUsed = year - y0 <= y1 - year ? y0 : y1;
  return [v, yearUsed, 0];
}

// resolve uma métrica: lugar -> região -> Mundo, com regras de extrapolação.
function resolveRaw(metric, entity, year) {
  const series = DATA.metrics[metric] || {};
  const sourceId = DATA.metricSources[metric] || "";
  const region = DATA.regionOf[entity];
  const chain = [[entity, "alta"]];
  if (region && region !== entity) chain.push([region, "media"]);
  if (entity !== "World" && region !== "World") chain.push(["World", "media"]);

  for (const [cand, baseConf] of chain) {
    const arr = series[cand];
    if (!arr || arr.length === 0) continue;
    const [value, yearUsed, dist] = _interpPairs(arr, year);
    let confidence = baseConf, note = "";
    if (dist > 0) {
      if (dist <= 10) note = `ano mais próximo com dado: ${yearUsed}`;
      else if (dist <= 60) {
        confidence = baseConf === "alta" ? "media" : "baixa";
        note = `extrapolado do dado de ${yearUsed} (${dist} anos de distância)`;
      } else continue;
    }
    if (cand !== entity) note = (note ? note + "; " : "") + `usando dado de '${cand}'`;
    return { value, sourceId, confidence, yearUsed, entityUsed: cand, note };
  }
  return null;
}

function curatedEstimate(metric, year) {
  const t = DATA.curated[metric];
  if (!t) return null;
  const pts = t.points;
  let v;
  if (year <= pts[0][0]) v = pts[0][1];
  else if (year >= pts[pts.length - 1][0]) v = pts[pts.length - 1][1];
  else {
    v = pts[pts.length - 1][1];
    for (let i = 0; i < pts.length - 1; i++) {
      const [y0, v0] = pts[i], [y1, v1] = pts[i + 1];
      if (y0 <= year && year <= y1) { v = v0 + ((year - y0) / (y1 - y0)) * (v1 - v0); break; }
    }
  }
  return { value: v, sourceId: "historical_estimates", confidence: "baixa", detail: t.note };
}

// resolve com fallback para estimativa histórica; devolve {value, sourceId, confidence, detail}
function resolve(metric, entity, year, allowCurated = true) {
  const look = resolveRaw(metric, entity, year);
  if (look) {
    let detail = `ano ${look.yearUsed}`;
    if (look.note) detail += ` — ${look.note}`;
    return { value: look.value, sourceId: look.sourceId, confidence: look.confidence, detail };
  }
  if (allowCurated) return curatedEstimate(metric, year);
  return null;
}

// ---- local de nascimento ----------------------------------------------------

function _popAt(country, year) {
  const arr = DATA.population[country];
  if (!arr || arr.length === 0) return 0;
  const n = arr.length;
  if (year <= arr[0][0]) return arr[0][1];
  if (year >= arr[n - 1][0]) return arr[n - 1][1];
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (arr[mid][0] <= year) lo = mid; else hi = mid;
  }
  const [y0, v0] = arr[lo], [y1, v1] = arr[hi];
  return v0 + ((year - y0) / (y1 - y0)) * (v1 - v0);
}

function isCountry(entity) { return COUNTRY_SET.has(entity); }

function sampleBirthplace(selected, year) {
  if (isCountry(selected)) return null;
  let regions = null;
  if (CONTINENTS.has(selected)) regions = new Set([selected]);
  else if (REGION_ALIASES[selected]) regions = REGION_ALIASES[selected];

  const pool = [], weights = [];
  let total = 0;
  for (const c of DATA.countries) {
    if (regions && !regions.has(DATA.regionOf[c])) continue;
    const w = _popAt(c, year);
    if (w > 0) { pool.push(c); weights.push(w); total += w; }
  }
  if (pool.length === 0 || total <= 0) return null;
  let u = Math.random() * total, acc = 0, idx = pool.length - 1;
  for (let i = 0; i < pool.length; i++) { acc += weights[i]; if (u <= acc) { idx = i; break; } }
  return { country: pool[idx], pop: weights[idx], share: weights[idx] / total };
}

// ---- tábua de vida: modelo de Siler -----------------------------------------

const B1 = 1.1, A2 = 0.0005, B3 = 0.085, STEP = 0.2;
const GRID = (() => { const g = []; for (let x = 0; x < 120; x += STEP) g.push(x); return g; })();
const N = GRID.length, IDX5 = Math.round(5 / STEP);
const _ltCache = new Map();

function _computeS(a1, a3) {
  const S = new Float64Array(N);
  let H = 0;
  for (let i = 0; i < N; i++) {
    const x = GRID[i];
    const mu = a1 * Math.exp(-B1 * x) + A2 + a3 * Math.exp(B3 * x);
    H += mu * STEP;
    S[i] = Math.exp(-H);
  }
  return S;
}

function _e0of(S) {
  let s = 0;
  for (let i = 0; i < N; i++) s += S[i];
  return STEP * (s - 0.5 * S[0] - 0.5 * S[N - 1]);
}
function _q5of(S) { return 1 - S[IDX5]; }

function _solveA1(q5, a3) {
  let lo = 0, hi = 8;
  for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; if (_q5of(_computeS(m, a3)) < q5) lo = m; else hi = m; }
  return (lo + hi) / 2;
}
function _solveA3(e0, a1) {
  let lo = 1e-7, hi = 1;
  for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; if (_e0of(_computeS(a1, m)) > e0) lo = m; else hi = m; }
  return (lo + hi) / 2;
}

function buildLifeTable(e0, q5) {
  e0 = Math.round(Math.min(90, Math.max(18, e0)) * 10) / 10;
  q5 = Math.round(Math.min(0.6, Math.max(0.001, q5)) * 1000) / 1000;
  const key = e0 + "|" + q5;
  if (_ltCache.has(key)) return _ltCache.get(key);

  let a1 = 0.5, a3 = 0.0005;
  for (let i = 0; i < 8; i++) { a1 = _solveA1(q5, a3); a3 = _solveA3(e0, a1); }
  const S = _computeS(a1, a3);
  const deaths = new Float64Array(N);
  let tot = 0;
  for (let i = 0; i < N; i++) {
    const x = GRID[i];
    const mu = a1 * Math.exp(-B1 * x) + A2 + a3 * Math.exp(B3 * x);
    deaths[i] = S[i] * mu; tot += deaths[i];
  }
  for (let i = 0; i < N; i++) deaths[i] /= tot;
  const table = { deaths, e0Fit: _e0of(S), q5Fit: _q5of(S) };
  _ltCache.set(key, table);
  return table;
}

function sampleAge(table) {
  let u = Math.random(), acc = 0;
  for (let i = 0; i < N; i++) { acc += table.deaths[i]; if (u <= acc) return Math.floor(GRID[i]); }
  return Math.floor(GRID[N - 1]);
}

function defaultQ5FromE0(e0) {
  const pts = [[25, 0.46], [30, 0.40], [40, 0.27], [50, 0.16], [60, 0.08], [70, 0.03], [80, 0.008]];
  if (e0 <= pts[0][0]) return pts[0][1];
  if (e0 >= pts[pts.length - 1][0]) return pts[pts.length - 1][1];
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[i + 1];
    if (x0 <= e0 && e0 <= x1) return y0 + ((e0 - x0) / (x1 - x0)) * (y1 - y0);
  }
  return 0.1;
}

// ---- causa da morte ---------------------------------------------------------

function _ageGroup(age) { return age < 5 ? "infante" : age < 15 ? "crianca" : age < 50 ? "jovem" : "idoso"; }
function _modernity(e0) { return Math.min(1, Math.max(0, (e0 - 25) / (80 - 25))); }

function sampleCause(age, sex, e0, mmr) {
  const group = _ageGroup(age), m = _modernity(e0);
  const pre = DATA.causes.pre[group], mod = DATA.causes.mod[group];
  const dist = {};
  for (const k of new Set([...Object.keys(pre), ...Object.keys(mod)]))
    dist[k] = (1 - m) * (pre[k] || 0) + m * (mod[k] || 0);

  if (sex === "feminino" && age >= 15 && age < 50 && mmr) {
    const share = Math.min(0.35, Math.max(0, mmr / 2500));
    if (share > 0) {
      let total = 0; for (const k in dist) total += dist[k];
      for (const k in dist) dist[k] *= 1 - share;
      dist["parto"] = share * total;
    }
  }
  const keys = Object.keys(dist);
  let tot = 0; for (const k of keys) tot += dist[k];
  let u = Math.random() * tot, acc = 0, key = keys[keys.length - 1];
  for (const k of keys) { acc += dist[k]; if (u <= acc) { key = k; break; } }
  return { key, label: DATA.causes.labels[key], confidence: m < 0.3 ? "baixa" : "media" };
}

// ---- o sorteio --------------------------------------------------------------

function randint(a, b) { return Math.floor(Math.random() * (b - a + 1)) + a; }

function draw(entity, yearFrom, yearTo) {
  if (yearTo < yearFrom) [yearFrom, yearTo] = [yearTo, yearFrom];
  const birthYear = randint(yearFrom, yearTo);
  const facts = [], used = new Set();

  // local de nascimento
  let birthplace = entity, birthplaceSampled = false;
  const bp = sampleBirthplace(entity, birthYear);
  if (bp) {
    birthplace = bp.country; birthplaceSampled = true; used.add("owid_population");
    facts.push({
      key: "local", label: "Onde você nasceu", value: birthplace, confidence: "alta",
      source_id: "owid_population",
      detail: `sorteado entre os lugares de '${entity}' por peso populacional em ${birthYear}: ` +
        `~${(bp.pop / 1e6).toFixed(1)} mi de habitantes, ${(bp.share * 100).toFixed(1)}% da população do recorte`,
    });
  }
  const eff = birthplace;
  const record = (metric, allowCurated = true) => {
    const r = resolve(metric, eff, birthYear, allowCurated);
    if (r) used.add(r.sourceId);
    return r;
  };

  // sexo
  const sr = record("sex_ratio_birth");
  const ratio = sr ? sr.value : 105.0;
  const pMale = ratio / (ratio + 100);
  const sex = Math.random() < pMale ? "masculino" : "feminino";
  facts.push({
    key: "sexo", label: "Sexo ao nascer", value: sex === "masculino" ? "homem" : "mulher",
    confidence: sr ? sr.confidence : "baixa", source_id: sr ? sr.sourceId : "owid_sex_ratio",
    detail: `razão de sexo ao nascer ~${ratio.toFixed(0)} meninos:100 meninas` + (sr ? ` (${sr.detail})` : ""),
  });

  // expectativa de vida (geral e por sexo)
  const e0overall = record("life_expectancy");
  const e0val = e0overall ? e0overall.value : 30.0;
  const sexMetric = sex === "feminino" ? "life_expectancy_female" : "life_expectancy_male";
  const sexLook = resolveRaw(sexMetric, eff, birthYear);
  let e0used, e0conf, e0src, e0detail;
  if (sexLook) {
    e0used = sexLook.value; e0conf = sexLook.confidence; e0src = sexLook.sourceId;
    e0detail = `ano ${sexLook.yearUsed}` + (sexLook.note ? ` — ${sexLook.note}` : "");
    used.add(e0src);
  } else {
    const gap = Math.min(6, Math.max(1, (e0val - 25) * 0.12));
    e0used = e0val + (sex === "feminino" ? gap / 2 : -gap / 2);
    e0conf = e0overall ? e0overall.confidence : "baixa";
    e0src = e0overall ? e0overall.sourceId : "owid_life_expectancy";
    e0detail = (e0overall ? e0overall.detail : "") + `; diferencial por sexo aplicado (~${gap.toFixed(1)} anos)`;
  }

  // mortalidade infantil
  const cm = record("child_mortality");
  const q5 = cm ? cm.value / 100 : defaultQ5FromE0(e0used);

  // idade da morte
  const table = buildLifeTable(e0used, q5);
  const ageAtDeath = sampleAge(table);
  used.add("siler_model");
  facts.push({
    key: "idade_morte", label: "Idade ao morrer", value: ageAtDeath, confidence: e0conf,
    source_id: "siler_model",
    detail: `sorteada da tábua de vida calibrada para expectativa de vida ${e0used.toFixed(1)} anos ` +
      `e mortalidade infantil ${(q5 * 100).toFixed(0)}% (modelo de Siler)`,
  });
  facts.push({
    key: "expectativa_vida", label: "Expectativa de vida ao nascer (do seu lugar/época)",
    value: Math.round(e0used * 10) / 10, confidence: e0conf, source_id: e0src, detail: e0detail,
  });
  if (cm) facts.push({
    key: "mortalidade_infantil", label: "Chance de morrer antes dos 5 anos",
    value: `${cm.value.toFixed(0)}%`, confidence: cm.confidence, source_id: cm.sourceId, detail: cm.detail,
  });

  // causa da morte
  let mmr = null;
  if (sex === "feminino") {
    const mm = record("maternal_mortality");
    mmr = mm ? mm.value : null;
    if (mm && ageAtDeath >= 15 && ageAtDeath < 50) used.add(mm.sourceId);
  }
  const cause = sampleCause(ageAtDeath, sex, e0used, mmr);
  used.add("omran_transition");
  if (cause.confidence === "media") used.add("gbd_causes");
  facts.push({
    key: "causa_morte", label: "Causa da morte", value: cause.label, confidence: cause.confidence,
    source_id: "omran_transition",
    detail: "sorteada do perfil de causas da época (transição epidemiológica)" +
      (cause.key === "parto" ? `; mortalidade materna real considerada (RMM ${mmr.toFixed(0)}/100mil)` : ""),
  });

  // vida material
  const cal = record("calories");
  if (cal) facts.push({
    key: "calorias", label: "Calorias disponíveis por dia", value: `${cal.value.toFixed(0)} kcal`,
    confidence: cal.confidence, source_id: cal.sourceId, detail: cal.detail + _calorieComment(cal.value),
  });
  const gdp = record("gdp_per_capita");
  if (gdp) facts.push({
    key: "renda", label: "Renda média por pessoa (ao ano)",
    value: `US$ ${Math.round(gdp.value).toLocaleString("en-US")}`,
    confidence: gdp.confidence, source_id: gdp.sourceId,
    detail: gdp.detail + " — em dólares internacionais de 2011 (comparável entre épocas)",
  });

  const sources = [...used].sort().map((id) => DATA.sources[id]).filter(Boolean);
  return {
    input: { place: entity, year_from: yearFrom, year_to: yearTo },
    birth_year: birthYear, birthplace, birthplace_sampled: birthplaceSampled,
    sex, age_at_death: ageAtDeath, cause, facts, sources,
    model_fit: { e0: Math.round(table.e0Fit * 10) / 10, q5: Math.round(table.q5Fit * 1000) / 1000 },
  };
}

function _calorieComment(kcal) {
  if (kcal < 1900) return " — abaixo do necessário; fome crônica provável";
  if (kcal < 2300) return " — no limite da subsistência";
  return "";
}
