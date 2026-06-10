"use strict";
/* Narrativa em português — porte de narrative.py. */

const CAUSE_PHRASE = {
  neonatal: "complicações no parto ou logo após o nascimento",
  infeccao: "uma doença infecciosa",
  fome: "fome e desnutrição",
  parto: "complicações ao dar à luz",
  violencia: "violência — guerra ou homicídio",
  acidente: "um acidente",
  cronica: "uma doença crônica (coração, câncer ou AVC)",
};

const PAISES_PT = {
  "World": "no mundo",
  "China": "na China", "India": "na Índia", "United States": "nos Estados Unidos",
  "Indonesia": "na Indonésia", "Pakistan": "no Paquistão", "Nigeria": "na Nigéria",
  "Brazil": "no Brasil", "Bangladesh": "em Bangladesh", "Russia": "na Rússia",
  "Japan": "no Japão", "Mexico": "no México", "Ethiopia": "na Etiópia",
  "Philippines": "nas Filipinas", "Egypt": "no Egito", "Vietnam": "no Vietnã",
  "Germany": "na Alemanha", "Turkey": "na Turquia", "Iran": "no Irã",
  "France": "na França", "United Kingdom": "no Reino Unido", "Italy": "na Itália",
  "South Africa": "na África do Sul", "Spain": "na Espanha", "Portugal": "em Portugal",
  "Argentina": "na Argentina", "Colombia": "na Colômbia", "Ukraine": "na Ucrânia",
  "Poland": "na Polônia", "Democratic Republic of Congo": "na República Democrática do Congo",
  "Thailand": "na Tailândia", "South Korea": "na Coreia do Sul",
  "Myanmar": "em Mianmar", "Tanzania": "na Tanzânia", "Kenya": "no Quênia",
  "Sudan": "no Sudão", "Iraq": "no Iraque", "Afghanistan": "no Afeganistão",
  "Morocco": "em Marrocos", "Saudi Arabia": "na Arábia Saudita", "Peru": "no Peru",
  "Angola": "em Angola", "Mozambique": "em Moçambique", "Ghana": "em Gana",
  "Greece": "na Grécia", "Netherlands": "nos Países Baixos", "Belgium": "na Bélgica",
  "Sweden": "na Suécia", "Roman Empire": "no Império Romano",
};

const NOME_PT = {
  "China": "China", "India": "Índia", "United States": "Estados Unidos",
  "Indonesia": "Indonésia", "Pakistan": "Paquistão", "Nigeria": "Nigéria",
  "Brazil": "Brasil", "Bangladesh": "Bangladesh", "Russia": "Rússia",
  "Japan": "Japão", "Mexico": "México", "Ethiopia": "Etiópia", "Egypt": "Egito",
  "Vietnam": "Vietnã", "Germany": "Alemanha", "Turkey": "Turquia", "Iran": "Irã",
  "France": "França", "United Kingdom": "Reino Unido", "Italy": "Itália",
  "South Africa": "África do Sul", "Spain": "Espanha", "Portugal": "Portugal",
  "Argentina": "Argentina", "Colombia": "Colômbia", "Ukraine": "Ucrânia",
  "Poland": "Polônia", "Thailand": "Tailândia", "South Korea": "Coreia do Sul",
  "Myanmar": "Mianmar", "Tanzania": "Tanzânia", "Kenya": "Quênia",
  "Sudan": "Sudão", "Iraq": "Iraque", "Afghanistan": "Afeganistão",
  "Morocco": "Marrocos", "Peru": "Peru", "Angola": "Angola", "Greece": "Grécia",
  "Ireland": "Irlanda", "Netherlands": "Países Baixos",
};

const _nomePt = (p) => NOME_PT[p] || p;
const _placeLabel = (p) => PAISES_PT[p] || `em ${p}`;
const _anos = (n) => (n === 1 ? "1 ano" : `${n} anos`);
const _findFact = (result, key) => result.facts.find((f) => f.key === key) || null;

function buildNarrative(result) {
  const sex = result.sex, age = result.age_at_death, year = result.birth_year;
  const place = result.birthplace || result.input.place;
  const sampled = result.birthplace_sampled;
  const causeKey = result.cause.key;

  const mulher = sex === "feminino";
  const artigo = mulher ? "uma" : "um";
  const subst = mulher ? "mulher" : "homem";
  const criancaSubst = mulher ? "menina" : "menino";

  let headline;
  if (age === 0) headline = `Você é ${artigo} ${criancaSubst} que não completa um ano de vida.`;
  else if (age < 13) headline = `Você é ${artigo} ${criancaSubst}. Morre aos ${_anos(age)}.`;
  else headline = `Você é ${artigo} ${subst}. Morre aos ${_anos(age)}.`;

  const story = [];

  // 1. nascimento
  const anoTxt = year >= 0 ? `${year}` : `${Math.abs(year)} a.C.`;
  let localTxt;
  if (sampled && (year < 1800 || !(place in PAISES_PT)))
    localTxt = `na região que hoje chamamos de ${_nomePt(place)}`;
  else localTxt = _placeLabel(place);
  story.push(`Você nasce em ${anoTxt}, ${localTxt}. É ${artigo} ${criancaSubst}.`);

  // 2. arco da vida + causa
  const causa = CAUSE_PHRASE[causeKey] || "causas da época";
  if (age === 0)
    story.push(`Você não sobrevive ao primeiro ano. A causa é ${causa}. ` +
      "Era o destino de uma enorme parcela das crianças durante quase toda a história.");
  else if (age < 5)
    story.push(`Você morre aos ${_anos(age)}, ainda na primeira infância — por ${causa}.`);
  else if (age < 15)
    story.push(`Você chega à infância, mas morre aos ${_anos(age)}, por ${causa}.`);
  else if (age < 45)
    story.push(`Você cresce e chega à vida adulta. Morre cedo, aos ${_anos(age)}, por ${causa}.`);
  else {
    const e0Fact = _findFact(result, "expectativa_vida");
    const e0 = e0Fact ? parseFloat(e0Fact.value) : 40;
    if (age >= e0 + 8)
      story.push(`Você vive até os ${_anos(age)} — uma vida longa para a sua época — e morre por ${causa}.`);
    else story.push(`Você vive até os ${_anos(age)} e morre por ${causa}.`);
  }

  // 3. condições materiais
  const cal = _findFact(result, "calorias"), renda = _findFact(result, "renda");
  const mat = [];
  if (cal) mat.push(`come por volta de ${cal.value} por dia`);
  if (renda) mat.push(`vive com o equivalente a ${renda.value} por ano`);
  if (mat.length) story.push(`No dia a dia, você ${mat.join(" e ")}.`);

  // 4. contraste com o presente
  const today = resolveRaw("life_expectancy", place, 2023);
  if (today) {
    const hoje = today.value, diff = hoje - age;
    if (diff > 3)
      story.push(`Hoje, no mesmo lugar, a expectativa de vida é de cerca de ${hoje.toFixed(0)} anos — ` +
        `${diff.toFixed(0)} a mais do que você viveu.`);
  }

  return { headline, story };
}
