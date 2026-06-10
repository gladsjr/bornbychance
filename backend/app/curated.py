"""
Estimativas de demografia historica para periodos sem medicao direta
(antes de ~1770 para a maioria das metricas).

NAO sao numeros inventados: sao estimativas academicas de demografia historica,
deliberadamente tratadas como ordens de grandeza (confianca "baixa") e sempre
acompanhadas da fonte. Referencias principais:
  - Riley, J. C. (2005) "Estimates of Regional and Global Life Expectancy, 1800-2001"
  - Volk & Atkinson (2013) meta-analise de mortalidade infantil pre-moderna (~46% antes da vida adulta)
  - Fogel, R. (2004) "The Escape from Hunger and Premature Death" (ingestao calorica pre-industrial)
  - Maddison Project Database 2023 (renda per capita historica)
  - Scheidel, W.; Clark, G. (2007) "A Farewell to Alms"
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Estimate:
    value: float
    confidence: str  # quase sempre "baixa" aqui
    note: str
    source_id: str = "historical_estimates"


def _piecewise(year: int, points: list[tuple[int, float]]) -> float:
    """Interpola linearmente entre pontos-ancora (anos crescentes)."""
    if year <= points[0][0]:
        return points[0][1]
    if year >= points[-1][0]:
        return points[-1][1]
    for (y0, v0), (y1, v1) in zip(points, points[1:]):
        if y0 <= year <= y1:
            t = (year - y0) / (y1 - y0)
            return v0 + t * (v1 - v0)
    return points[-1][1]


# Expectativa de vida ao nascer (global, pre-1770). Riley (2005) e Galor;
# essencialmente estavel em ~24-33 anos durante quase toda a historia.
_LIFE_EXP = [
    (-10000, 31.0),  # cacadores-coletores (estimativa muito incerta)
    (-3000, 26.0),   # primeiras civilizacoes agricolas
    (1, 25.0),       # Imperio Romano / Antiguidade classica
    (1000, 27.0),    # alta Idade Media
    (1500, 30.0),    # inicio da era moderna
    (1700, 34.0),    # vespera da transicao demografica
    (1770, 29.0),    # encontra a serie real do OWID (Mundo ~28.5 em 1770)
]

# Mortalidade infantil: % que morre antes dos 5 anos. Volk & Atkinson (2013).
_CHILD_MORT = [
    (-10000, 48.0),
    (1, 47.0),
    (1500, 46.0),
    (1700, 44.0),
    (1770, 43.0),
]

# Calorias/dia por pessoa. Fogel (2004): pre-industrial ~1800-2200, fome recorrente.
_CALORIES = [
    (-10000, 2000.0),
    (1, 1900.0),
    (1500, 1950.0),
    (1700, 2050.0),
    (1960, 2200.0),  # encontra a serie da FAO (que comeca em 1961)
]

# Renda per capita (US$ int. 2011). Piso de subsistencia de Maddison ~ 600-1100.
_GDP = [
    (1, 900.0),
    (1000, 850.0),
    (1500, 1000.0),
    (1700, 1100.0),
    (1820, 1127.0),  # Mundo em 1820 segundo Maddison
]

# Razao mortalidade materna (mortes por 100.000 nascidos vivos), pre-moderna.
# Estimativas historicas (Inglaterra pre-1800 ~ 1000-1500). Confianca baixa.
_MMR = [
    (1, 1300.0),
    (1700, 1200.0),
    (1800, 900.0),
    (1900, 500.0),
]


_TABLES = {
    "life_expectancy": (_LIFE_EXP, "expectativa de vida pre-1770 (estimativa de demografia historica)"),
    "life_expectancy_female": (_LIFE_EXP, "expectativa de vida pre-1770 (estimativa)"),
    "life_expectancy_male": (_LIFE_EXP, "expectativa de vida pre-1770 (estimativa)"),
    "child_mortality": (_CHILD_MORT, "mortalidade infantil pre-1800 (Volk & Atkinson 2013)"),
    "calories": (_CALORIES, "ingestao calorica pre-industrial (Fogel 2004)"),
    "gdp_per_capita": (_GDP, "renda per capita historica (Maddison Project)"),
    "maternal_mortality": (_MMR, "mortalidade materna historica (estimativa)"),
}


def estimate(metric: str, year: int) -> Estimate | None:
    table = _TABLES.get(metric)
    if table is None:
        return None
    points, note = table
    return Estimate(value=_piecewise(year, points), confidence="baixa", note=note)
