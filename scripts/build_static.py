"""
Gera docs/data.json: empacota TODOS os dados de que o site estático precisa,
reaproveitando os módulos Python como fonte única de verdade.

O Python deixa de ser servidor e passa a ser apenas o gerador de dados; a lógica
de runtime vive em docs/engine.js. Rode após download_data.py:

    python scripts/download_data.py
    python scripts/build_static.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # raiz do projeto no path

from backend.app import causes, sources
from backend.app import curated as cur
from backend.app.data_loader import METRICS, get_store

DOCS = Path(__file__).resolve().parent.parent / "docs"

# casas decimais por métrica (para reduzir o tamanho do JSON)
ROUND = {
    "life_expectancy": 1, "life_expectancy_female": 1, "life_expectancy_male": 1,
    "child_mortality": 1, "calories": 0, "gdp_per_capita": 0,
    "sex_ratio_birth": 1, "maternal_mortality": 0,
}


def _round(v: float, nd: int):
    return int(round(v)) if nd == 0 else round(float(v), nd)


def _series_to_pairs(arr, nd: int) -> list:
    return [[int(y), _round(v, nd)] for y, v in arr]


def main() -> int:
    store = get_store()
    DOCS.mkdir(parents=True, exist_ok=True)

    # --- séries das métricas (entidade -> [[ano, valor], ...]) -----------
    metrics_out: dict[str, dict] = {}
    for metric in METRICS:
        by_entity = store._series.get(metric, {})
        nd = ROUND.get(metric, 1)
        metrics_out[metric] = {
            ent: _series_to_pairs(arr, nd)
            for ent, arr in by_entity.items()
            if "\n" not in ent
        }

    # --- população por país (para sortear o local de nascimento) ---------
    population = {
        c: _series_to_pairs(arr, 0)
        for c, arr in store._pop.items()
        if "\n" not in c
    }

    # --- estimativas históricas curadas (pontos-âncora + nota) -----------
    curated_out = {}
    for metric, (points, note) in cur._TABLES.items():
        curated_out[metric] = {"points": [[int(y), v] for y, v in points], "note": note}

    # --- perfis de causas de morte ---------------------------------------
    causes_out = {"labels": causes.CAUSES, "pre": causes._PRE, "mod": causes._MOD}

    # --- fontes citáveis --------------------------------------------------
    sources_out = {sid: sources.cite(sid) for sid in sources.SOURCES}

    data = {
        "places": [p for p in store.places() if "\n" not in p],
        "regionOf": {k: v for k, v in store._region.items() if "\n" not in k},
        "countries": sorted(c for c in store._countries if "\n" not in c),
        "metricSources": {m: src for m, (_f, _c, src) in METRICS.items()},
        "metrics": metrics_out,
        "population": population,
        "curated": curated_out,
        "causes": causes_out,
        "sources": sources_out,
    }

    out = DOCS / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = out.stat().st_size / 1e6
    n_points = sum(len(s) for d in metrics_out.values() for s in d.values()) + \
        sum(len(s) for s in population.values())
    print(f"docs/data.json gerado: {size_mb:.2f} MB, {n_points:,} pontos de dados")
    print(f"  lugares: {len(data['places'])}  países: {len(data['countries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
