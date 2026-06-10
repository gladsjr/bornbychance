"""
O sorteio. Dado (lugar, faixa de anos), o motor "joga a roleta do nascimento"
UMA vez e devolve uma vida concreta, amostrada de distribuicoes reais.

Cada fato carrega: valor, fonte, ano efetivamente usado e nivel de confianca.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from . import causes, curated, life_tables
from .data_loader import get_store
from .sources import cite


@dataclass
class Fact:
    key: str
    label: str
    value: object
    confidence: str
    source_id: str
    detail: str = ""


@dataclass
class Resolved:
    value: float
    source_id: str
    confidence: str
    detail: str


def _resolve(metric: str, entity: str, year: int, allow_curated: bool = True) -> Resolved | None:
    """Dado real (lugar->regiao->Mundo) e, se preciso, estimativa historica curada."""
    store = get_store()
    look = store.resolve(metric, entity, year)
    if look is not None:
        detail = f"ano {look.year_used}"
        if look.note:
            detail += f" — {look.note}"
        return Resolved(look.value, look.source_id, look.confidence, detail)
    if allow_curated:
        est = curated.estimate(metric, year)
        if est is not None:
            return Resolved(est.value, est.source_id, est.confidence, est.note)
    return None


def draw(entity: str, year_from: int, year_to: int, seed: int | None = None) -> dict:
    if year_to < year_from:
        year_from, year_to = year_to, year_from
    rng = np.random.default_rng(seed)
    birth_year = int(rng.integers(year_from, year_to + 1))

    facts: list[Fact] = []
    used_sources: set[str] = set()
    store = get_store()

    # --- local de nascimento -----------------------------------------------
    # Se o lugar escolhido for um agregado (Mundo, um continente), sorteia um
    # pais concreto ponderado pela populacao da epoca. A vida e entao calculada
    # com os dados reais desse pais.
    birthplace = entity
    birthplace_sampled = False
    bp = store.sample_birthplace(entity, birth_year, rng)
    if bp is not None:
        birthplace, bp_pop, bp_share = bp
        birthplace_sampled = True
        used_sources.add("owid_population")
        facts.append(Fact(
            "local", "Onde você nasceu", birthplace, "alta", "owid_population",
            f"sorteado entre os lugares de '{entity}' por peso populacional em {birth_year}: "
            f"~{bp_pop/1e6:.1f} mi de habitantes, {bp_share*100:.1f}% da população do recorte",
        ))

    effective_entity = birthplace

    def record(metric: str, **kw) -> Resolved | None:
        r = _resolve(metric, effective_entity, birth_year, **kw)
        if r is not None:
            used_sources.add(r.source_id)
        return r

    # --- sexo (razao de sexo ao nascer real) -------------------------------
    sr = record("sex_ratio_birth")
    ratio = sr.value if sr else 105.0  # meninos por 100 meninas
    p_male = ratio / (ratio + 100.0)
    sex = "masculino" if rng.random() < p_male else "feminino"
    facts.append(Fact(
        "sexo", "Sexo ao nascer", "homem" if sex == "masculino" else "mulher",
        sr.confidence if sr else "baixa",
        sr.source_id if sr else "owid_sex_ratio",
        f"razao de sexo ao nascer ~{ratio:.0f} meninos:100 meninas"
        + (f" ({sr.detail})" if sr else ""),
    ))

    # --- expectativa de vida (geral e por sexo) ----------------------------
    e0_overall = record("life_expectancy")
    e0_val = e0_overall.value if e0_overall else 30.0
    # tenta e0 especifico por sexo so com dado real; senao aplica diferencial
    sex_metric = "life_expectancy_female" if sex == "feminino" else "life_expectancy_male"
    sex_look = store.resolve(sex_metric, effective_entity, birth_year)
    if sex_look is not None:
        e0_used = sex_look.value
        e0_conf = sex_look.confidence
        e0_src = sex_look.source_id
        e0_detail = f"ano {sex_look.year_used}" + (f" — {sex_look.note}" if sex_look.note else "")
        used_sources.add(e0_src)
    else:
        gap = float(np.clip((e0_val - 25.0) * 0.12, 1.0, 6.0))
        e0_used = e0_val + (gap / 2 if sex == "feminino" else -gap / 2)
        e0_conf = e0_overall.confidence if e0_overall else "baixa"
        e0_src = e0_overall.source_id if e0_overall else "owid_life_expectancy"
        e0_detail = (e0_overall.detail if e0_overall else "") + f"; diferencial por sexo aplicado (~{gap:.1f} anos)"

    # --- mortalidade infantil (q5) -----------------------------------------
    cm = record("child_mortality")
    q5 = (cm.value / 100.0) if cm else life_tables.default_q5_from_e0(e0_used)

    # --- idade de morte (modelo de Siler sobre e0 e q5 reais) --------------
    table = life_tables.build_life_table(e0_used, q5)
    age_at_death = life_tables.sample_age_at_death(table, rng)
    used_sources.add("siler_model")
    facts.append(Fact(
        "idade_morte", "Idade ao morrer", age_at_death,
        e0_conf, "siler_model",
        f"sorteada da tabua de vida calibrada para expectativa de vida {e0_used:.1f} anos "
        f"e mortalidade infantil {q5*100:.0f}% (modelo de Siler)",
    ))
    facts.append(Fact(
        "expectativa_vida", "Expectativa de vida ao nascer (do seu lugar/epoca)",
        round(e0_used, 1), e0_conf, e0_src, e0_detail,
    ))
    if cm:
        facts.append(Fact(
            "mortalidade_infantil", "Chance de morrer antes dos 5 anos",
            f"{cm.value:.0f}%", cm.confidence, cm.source_id, cm.detail,
        ))

    # --- causa da morte ----------------------------------------------------
    mmr = None
    if sex == "feminino":
        mm = record("maternal_mortality")
        mmr = mm.value if mm else None
        if mm and 15 <= age_at_death < 50:
            used_sources.add(mm.source_id)
    cause = causes.sample_cause(age_at_death, sex, e0_used, mmr, rng)
    used_sources.add("omran_transition")
    if cause["confidence"] == "media":
        used_sources.add("gbd_causes")
    facts.append(Fact(
        "causa_morte", "Causa da morte", cause["label"],
        cause["confidence"], "omran_transition",
        "sorteada do perfil de causas da epoca (transicao epidemiologica)"
        + (f"; mortalidade materna real considerada (RMM {mmr:.0f}/100mil)" if cause["key"] == "parto" else ""),
    ))

    # --- vida material: calorias e renda -----------------------------------
    cal = record("calories")
    if cal:
        facts.append(Fact(
            "calorias", "Calorias disponiveis por dia",
            f"{cal.value:.0f} kcal", cal.confidence, cal.source_id,
            cal.detail + _calorie_comment(cal.value),
        ))
    gdp = record("gdp_per_capita")
    if gdp:
        facts.append(Fact(
            "renda", "Renda media por pessoa (ao ano)",
            f"US$ {gdp.value:,.0f}", gdp.confidence, gdp.source_id,
            gdp.detail + " — em dolares internacionais de 2011 (comparavel entre epocas)",
        ))

    sources = [cite(sid) for sid in sorted(used_sources)]

    return {
        "input": {"place": entity, "year_from": year_from, "year_to": year_to},
        "birth_year": birth_year,
        "birthplace": birthplace,
        "birthplace_sampled": birthplace_sampled,
        "sex": sex,
        "age_at_death": age_at_death,
        "cause": cause,
        "facts": [asdict(f) for f in facts],
        "sources": sources,
        "model_fit": {"e0": round(table.e0_fit, 1), "q5": round(table.q5_fit, 3)},
    }


def _calorie_comment(kcal: float) -> str:
    if kcal < 1900:
        return " — abaixo do necessario; fome cronica provavel"
    if kcal < 2300:
        return " — no limite da subsistencia"
    return ""
