"""
Registro central de fontes. Cada fato exibido ao usuário aponta para um id aqui.

Regra do projeto: nenhum número é inventado. Todo valor sorteado vem de um
dataset público (OWID/Maddison/ONU/WHO) ou de uma estimativa acadêmica citada.
O campo `confidence` é exibido ao usuário para que ele saiba quando o dado é
medição direta vs. estimativa histórica grosseira.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    publisher: str
    url: str
    license: str = ""
    note: str = ""


SOURCES: dict[str, Source] = {
    "owid_life_expectancy": Source(
        id="owid_life_expectancy",
        title="Life Expectancy at birth",
        publisher="Our World in Data (com base em UN WPP, HMD e Gapminder/Riley)",
        url="https://ourworldindata.org/life-expectancy",
        license="CC BY 4.0",
        note="Mundo desde 1770; países desde 1950 (alguns antes).",
    ),
    "owid_life_expectancy_sex": Source(
        id="owid_life_expectancy_sex",
        title="Life expectancy by sex",
        publisher="Our World in Data (UN World Population Prospects)",
        url="https://ourworldindata.org/grapher/life-expectancy-of-women-vs-life-expectancy-of-men",
        license="CC BY 4.0",
        note="Diferencial de expectativa de vida por sexo, 1950+.",
    ),
    "owid_child_mortality": Source(
        id="owid_child_mortality",
        title="Child mortality rate (share dying before age 5)",
        publisher="Our World in Data (UN IGME e Gapminder)",
        url="https://ourworldindata.org/child-mortality",
        license="CC BY 4.0",
        note="Mundo desde 1800.",
    ),
    "owid_calories": Source(
        id="owid_calories",
        title="Daily per-capita caloric supply",
        publisher="Our World in Data (FAO)",
        url="https://ourworldindata.org/food-supply",
        license="CC BY 4.0",
        note="Suprimento de calorias por pessoa/dia, 1961+.",
    ),
    "maddison_gdp": Source(
        id="maddison_gdp",
        title="GDP per capita (Maddison Project Database 2023)",
        publisher="Bolt & van Zanden / Maddison Project, University of Groningen",
        url="https://www.rug.nl/ggdc/historicaldevelopment/maddison/",
        license="CC BY 4.0",
        note="Renda real por pessoa (US$ internacionais de 2011). Algumas regiões desde o ano 1.",
    ),
    "owid_sex_ratio": Source(
        id="owid_sex_ratio",
        title="Sex ratio at birth",
        publisher="Our World in Data (UN World Population Prospects)",
        url="https://ourworldindata.org/gender-ratio",
        license="CC BY 4.0",
        note="Meninos por 100 meninas ao nascer, 1950+.",
    ),
    "owid_maternal_mortality": Source(
        id="owid_maternal_mortality",
        title="Maternal mortality ratio",
        publisher="Our World in Data (WHO, UNICEF, UNFPA, World Bank)",
        url="https://ourworldindata.org/maternal-mortality",
        license="CC BY 4.0",
        note="Mortes maternas por 100.000 nascidos vivos, 1985+ (séries históricas para alguns países).",
    ),
    "siler_model": Source(
        id="siler_model",
        title="Siler competing-hazards mortality model",
        publisher="Siler, W. (1979), Ecology 60(4); Gage & Dyke (1986)",
        url="https://doi.org/10.2307/1936612",
        license="",
        note="Modelo demográfico padrão usado para gerar a distribuição de idade-de-morte "
        "a partir da expectativa de vida e da mortalidade infantil reais.",
    ),
    "omran_transition": Source(
        id="omran_transition",
        title="The Epidemiologic Transition",
        publisher="Omran, A. R. (1971), Milbank Memorial Fund Quarterly 49(4)",
        url="https://doi.org/10.2307/3349375",
        license="",
        note="Base teórica para a mudança do perfil de causas de morte (infecção/fome -> "
        "doenças crônicas) conforme o desenvolvimento.",
    ),
    "gbd_causes": Source(
        id="gbd_causes",
        title="Global Burden of Disease — causes of death",
        publisher="Institute for Health Metrics and Evaluation (IHME)",
        url="https://www.healthdata.org/research-analysis/gbd",
        license="",
        note="Distribuição moderna de causas de morte por idade.",
    ),
    "historical_estimates": Source(
        id="historical_estimates",
        title="Estimativas de demografia histórica (Antiguidade e período pré-1800)",
        publisher="Várias (Maddison; Clark 2007; Fogel 2004; Scheidel; Riley 2005)",
        url="https://ourworldindata.org/economic-growth",
        license="",
        note="Para épocas sem medição direta, usamos estimativas acadêmicas. "
        "Confiança baixa — ordens de grandeza, não precisão.",
    ),
}


def cite(source_id: str) -> dict:
    s = SOURCES[source_id]
    return {
        "id": s.id,
        "title": s.title,
        "publisher": s.publisher,
        "url": s.url,
        "license": s.license,
        "note": s.note,
    }
