"""
Baixa os datasets públicos reais usados pelo Born by Chance.

Todas as fontes são públicas e citáveis. Cada dataset é salvo em
backend/data/raw/ e a procedência fica registrada em backend/app/sources.py.

Uso:
    python scripts/download_data.py
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "backend" / "data" / "raw"

# Endpoint de CSV "full" do grapher da Our World in Data.
# Documentação: cada gráfico do OWID expõe um CSV em /grapher/<slug>.csv
OWID = "https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true"

# slug do OWID -> nome do arquivo local
DATASETS = {
    "life-expectancy": "life_expectancy.csv",
    "life-expectancy-of-women-vs-life-expectancy-of-men": "life_expectancy_by_sex.csv",
    "child-mortality": "child_mortality.csv",
    "daily-per-capita-caloric-supply": "daily_calories.csv",
    "gdp-per-capita-maddison": "gdp_per_capita.csv",
    "sex-ratio-at-birth": "sex_ratio_birth.csv",
    "share-of-deaths-by-cause": "deaths_by_cause.csv",
    "maternal-mortality": "maternal_mortality.csv",
    "population": "population.csv",
}


def download(slug: str, filename: str) -> bool:
    url = OWID.format(slug=slug)
    dest = RAW_DIR / filename
    req = urllib.request.Request(url, headers={"User-Agent": "born-by-chance/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        n_lines = data.count(b"\n")
        print(f"  OK  {filename:34s} ({n_lines:>7,} linhas)  <- {slug}")
        return True
    except Exception as exc:  # noqa: BLE001 - queremos continuar mesmo se 1 falhar
        print(f"  ERRO {filename:34s} :: {exc}")
        return False


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / ".gitkeep").touch()
    print(f"Baixando datasets para {RAW_DIR}\n")
    ok = 0
    for slug, filename in DATASETS.items():
        ok += download(slug, filename)
    print(f"\n{ok}/{len(DATASETS)} datasets baixados.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
