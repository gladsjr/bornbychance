"""
Carrega os datasets reais (CSV em data/raw) e resolve consultas
(metrica, lugar, ano) com uma cadeia de fallback honesta:

    lugar exato -> regiao do lugar -> Mundo -> (caller usa estimativa historica)

Cada resultado vem anotado com a fonte, o ano efetivamente usado e um nivel
de confianca, para que a interface nunca apresente um numero sem procedencia.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

_ISO3 = re.compile(r"^[A-Z]{3}$")  # codigo de pais real (exclui OWID_* dos agregados)

# continentes (valores de owid_region) e aliases de agregados -> regioes a amostrar
_CONTINENTS = {"Africa", "Asia", "Europe", "North America", "Oceania", "South America"}
_REGION_ALIASES = {
    "Americas (UN)": {"North America", "South America"},
    "Americas": {"North America", "South America"},
}

# metrica -> (arquivo, coluna_do_valor, source_id)
METRICS = {
    "life_expectancy": ("life_expectancy.csv", "life_expectancy_0", "owid_life_expectancy"),
    "life_expectancy_female": (
        "life_expectancy_by_sex.csv",
        "life_expectancy__sex_female__age_0__variant_estimates",
        "owid_life_expectancy_sex",
    ),
    "life_expectancy_male": (
        "life_expectancy_by_sex.csv",
        "life_expectancy__sex_male__age_0__variant_estimates",
        "owid_life_expectancy_sex",
    ),
    "child_mortality": ("child_mortality.csv", "child_mortality_rate", "owid_child_mortality"),
    "calories": ("daily_calories.csv", "daily_calories", "owid_calories"),
    "gdp_per_capita": ("gdp_per_capita.csv", "gdp_per_capita", "maddison_gdp"),
    "sex_ratio_birth": (
        "sex_ratio_birth.csv",
        "sex_ratio__sex_all__age_0__variant_estimates",
        "owid_sex_ratio",
    ),
    "maternal_mortality": ("maternal_mortality.csv", "mmr", "owid_maternal_mortality"),
}


@dataclass
class Lookup:
    value: float
    source_id: str
    year_used: int
    entity_used: str
    confidence: str  # "alta" | "media" | "baixa"
    note: str = ""


class DataStore:
    def __init__(self, raw_dir: Path = RAW_DIR) -> None:
        self.raw_dir = raw_dir
        self._series: dict[str, dict[str, np.ndarray]] = {}
        self._source: dict[str, str] = {}
        self._region: dict[str, str] = {}  # entity -> owid_region
        self._entities: set[str] = set()
        self._pop: dict[str, np.ndarray] = {}   # pais -> Nx2 (ano, populacao)
        self._countries: set[str] = set()       # entidades que sao paises reais (ISO3)
        self._load()
        self._load_population()

    def _load(self) -> None:
        for metric, (filename, col, source_id) in METRICS.items():
            path = self.raw_dir / filename
            if not path.exists():
                continue
            df = pd.read_csv(path, usecols=lambda c, _c=col: c in {"entity", "year", _c, "owid_region"})
            df = df.dropna(subset=[col])
            self._source[metric] = source_id
            # guarda series por entidade: dict[entity] -> array Nx2 (year, value) ordenado
            by_entity: dict[str, np.ndarray] = {}
            for entity, grp in df.groupby("entity", sort=False):
                arr = grp[["year", col]].to_numpy(dtype=float)
                arr = arr[arr[:, 0].argsort()]
                by_entity[entity] = arr
            self._series[metric] = by_entity
            self._entities.update(by_entity.keys())
            # mapa entidade -> regiao (de qualquer arquivo que tenha owid_region)
            if "owid_region" in df.columns:
                for entity, region in df[["entity", "owid_region"]].dropna().drop_duplicates(
                    "entity"
                ).itertuples(index=False):
                    self._region.setdefault(str(entity), str(region))

    def _load_population(self) -> None:
        """Carrega populacao historica por pais (so paises reais, fronteiras atuais)."""
        path = self.raw_dir / "population.csv"
        if not path.exists():
            return
        df = pd.read_csv(path, usecols=["entity", "code", "year", "population_historical"])
        df = df.dropna(subset=["population_historical", "code"])
        for (entity, code), grp in df.groupby(["entity", "code"], sort=False):
            if not _ISO3.match(str(code)):
                continue  # pula agregados (OWID_*) e estados historicos
            arr = grp[["year", "population_historical"]].to_numpy(dtype=float)
            arr = arr[arr[:, 0].argsort()]
            self._pop[str(entity)] = arr
            self._countries.add(str(entity))

    def is_country(self, entity: str) -> bool:
        return entity in self._countries

    def _pop_at(self, country: str, year: int) -> float:
        arr = self._pop.get(country)
        if arr is None or len(arr) == 0:
            return 0.0
        years, vals = arr[:, 0], arr[:, 1]
        if year <= years[0]:
            return float(vals[0])
        if year >= years[-1]:
            return float(vals[-1])
        return float(np.interp(year, years, vals))

    def sample_birthplace(
        self, selected: str, year: int, rng: np.random.Generator
    ) -> tuple[str, float, float] | None:
        """
        Sorteia um pais concreto ponderado pela populacao no ano dado.
        Retorna (pais, populacao_do_pais, fracao_da_populacao_do_pool) ou None
        se 'selected' ja for um pais (nao ha o que sortear).
        """
        if self.is_country(selected):
            return None
        # define o conjunto de paises elegiveis
        regions: set[str] | None = None
        if selected in _CONTINENTS:
            regions = {selected}
        elif selected in _REGION_ALIASES:
            regions = _REGION_ALIASES[selected]
        pool = [
            c for c in self._countries
            if regions is None or self._region.get(c) in regions
        ]
        weights = np.array([self._pop_at(c, year) for c in pool], dtype=float)
        mask = weights > 0
        pool = [c for c, m in zip(pool, mask) if m]
        weights = weights[mask]
        if len(pool) == 0 or weights.sum() <= 0:
            return None
        total = float(weights.sum())
        probs = weights / total
        idx = int(rng.choice(len(pool), p=probs))
        return pool[idx], float(weights[idx]), float(weights[idx] / total)

    # ---- API publica -------------------------------------------------------

    def places(self) -> list[str]:
        """Lugares com expectativa de vida disponivel (espinha dorsal do sorteio)."""
        return sorted(self._series.get("life_expectancy", {}).keys())

    def coverage(self, metric: str, entity: str) -> tuple[int, int] | None:
        arr = self._series.get(metric, {}).get(entity)
        if arr is None or len(arr) == 0:
            return None
        return int(arr[0, 0]), int(arr[-1, 0])

    def _nearest_in_series(self, arr: np.ndarray, year: int) -> tuple[float, int, int]:
        """Retorna (valor, ano_usado, distancia_em_anos) por interpolacao/vizinho mais proximo."""
        years = arr[:, 0]
        vals = arr[:, 1]
        if year <= years[0]:
            return float(vals[0]), int(years[0]), int(years[0] - year)
        if year >= years[-1]:
            return float(vals[-1]), int(years[-1]), int(year - years[-1])
        # dentro do intervalo: interpola linearmente
        v = float(np.interp(year, years, vals))
        # ano "usado" = o mais proximo, so para exibicao
        idx = int(np.abs(years - year).argmin())
        return v, int(years[idx]), 0

    def resolve(self, metric: str, entity: str, year: int) -> Lookup | None:
        """
        Tenta entidade -> regiao -> Mundo. Retorna None se nada cobrir o periodo
        (ai o motor recorre a estimativa historica curada).
        """
        source_id = self._source.get(metric, "")
        chain: list[tuple[str, str]] = [(entity, "alta")]
        region = self._region.get(entity)
        if region and region != entity:
            chain.append((region, "media"))
        if "World" not in (entity, region):
            chain.append(("World", "media"))

        series = self._series.get(metric, {})
        for cand, base_conf in chain:
            arr = series.get(cand)
            if arr is None or len(arr) == 0:
                continue
            value, year_used, dist = self._nearest_in_series(arr, year)
            confidence = base_conf
            note = ""
            if dist > 0:
                # extrapolacao para fora da cobertura real
                if dist <= 10:
                    note = f"ano mais proximo com dado: {year_used}"
                elif dist <= 60:
                    confidence = "media" if base_conf == "alta" else "baixa"
                    note = f"extrapolado do dado de {year_used} ({dist} anos de distancia)"
                else:
                    # muito longe: deixa o caller usar estimativa historica
                    continue
            if cand != entity:
                note = (note + "; " if note else "") + f"usando dado de '{cand}'"
            return Lookup(value, source_id, year_used, cand, confidence, note)
        return None


_STORE: DataStore | None = None


def get_store() -> DataStore:
    global _STORE
    if _STORE is None:
        _STORE = DataStore()
    return _STORE
