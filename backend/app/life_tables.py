r"""
Gera a distribuicao de idade-de-morte a partir de dois numeros REAIS:
expectativa de vida ao nascer (e0) e mortalidade infantil (q5).

Usa o modelo de riscos concorrentes de Siler (1979), padrao em demografia:

    mu(x) = a1*exp(-b1*x)  +  a2  +  a3*exp(b3*x)
            \___ infancia __/   \_/   \__ senescencia __/

Os parametros de forma (b1, a2, b3) sao fixados em valores tipicos da
literatura; a1 e a3 sao calibrados numericamente para reproduzir exatamente
o q5 e o e0 observados. Assim a curva inteira de mortalidade decorre de
dados reais, e podemos sortear uma idade de morte concreta.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

# Parametros de forma (fixos). Valores tipicos para populacoes humanas.
B1 = 1.1      # velocidade de queda da mortalidade infantil
A2 = 0.0005   # mortalidade de fundo (acidentes/violencia basal), constante
B3 = 0.085    # ritmo de envelhecimento de Gompertz (~dobra a cada ~8 anos)

_GRID = np.arange(0.0, 120.0, 0.1)  # idades 0..120 em passos de 0.1 ano
_DT = 0.1


def _survival(a1: float, a3: float) -> np.ndarray:
    mu = a1 * np.exp(-B1 * _GRID) + A2 + a3 * np.exp(B3 * _GRID)
    # risco acumulado por integracao cumulativa (trapezio)
    H = np.cumsum(mu) * _DT
    return np.exp(-H)


def _e0_of(S: np.ndarray) -> float:
    return float(np.trapezoid(S, dx=_DT))


def _q5_of(S: np.ndarray) -> float:
    # S no indice correspondente a idade 5
    i5 = int(round(5.0 / _DT))
    return float(1.0 - S[i5])


def _solve_a1_for_q5(q5: float, a3: float) -> float:
    """Bisseccao: q5 cresce monotonicamente com a1."""
    lo, hi = 0.0, 8.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _q5_of(_survival(mid, a3)) < q5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _solve_a3_for_e0(e0: float, a1: float) -> float:
    """Bisseccao: e0 decresce monotonicamente com a3."""
    lo, hi = 1e-7, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _e0_of(_survival(a1, mid)) > e0:
            lo = mid  # precisa mais mortalidade -> aumenta a3
        else:
            hi = mid
    return 0.5 * (lo + hi)


@dataclass
class LifeTable:
    e0_target: float
    q5_target: float
    a1: float
    a3: float
    survival: np.ndarray
    deaths_pdf: np.ndarray  # densidade de mortes por idade (soma 1)
    e0_fit: float
    q5_fit: float


def build_life_table(e0: float, q5: float) -> LifeTable:
    """e0 em anos; q5 em fracao (0..1). Resultado cacheado por (e0,q5) arredondados."""
    # arredonda para 1 casa (e0) e 3 casas (q5): a calibracao e identica e o cache
    # transforma milhares de sorteios em poucas dezenas de solves distintos.
    return _build_cached(round(float(np.clip(e0, 18.0, 90.0)), 1),
                         round(float(np.clip(q5, 0.001, 0.6)), 3))


@lru_cache(maxsize=4096)
def _build_cached(e0: float, q5: float) -> LifeTable:
    a1, a3 = 0.5, 0.0005
    for _ in range(8):
        a1 = _solve_a1_for_q5(q5, a3)
        a3 = _solve_a3_for_e0(e0, a1)
    S = _survival(a1, a3)
    mu = a1 * np.exp(-B1 * _GRID) + A2 + a3 * np.exp(B3 * _GRID)
    deaths = S * mu
    deaths = deaths / deaths.sum()
    return LifeTable(
        e0_target=e0,
        q5_target=q5,
        a1=a1,
        a3=a3,
        survival=S,
        deaths_pdf=deaths,
        e0_fit=_e0_of(S),
        q5_fit=_q5_of(S),
    )


def sample_age_at_death(table: LifeTable, rng: np.random.Generator) -> int:
    """Sorteia uma idade de morte (anos inteiros) da distribuicao da tabua."""
    idx = rng.choice(len(_GRID), p=table.deaths_pdf)
    return int(_GRID[idx])


# default q5 a partir de e0, para quando so temos expectativa de vida.
# Calibrado para bater com a relacao observada (e0 baixo -> q5 alto).
def default_q5_from_e0(e0: float) -> float:
    pts = [(25.0, 0.46), (30.0, 0.40), (40.0, 0.27), (50.0, 0.16),
           (60.0, 0.08), (70.0, 0.03), (80.0, 0.008)]
    if e0 <= pts[0][0]:
        return pts[0][1]
    if e0 >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= e0 <= x1:
            t = (e0 - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return 0.1
