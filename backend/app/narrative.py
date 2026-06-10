"""
Transforma o resultado do sorteio em uma narrativa concreta em portugues:
"Voce e uma mulher de 32 anos. Vai morrer aos 33, de forma violenta."

A ideia e dar concretude — uma vida, nao uma tabela de probabilidades — e
deixar o contraste com o presente emergir por si.
"""
from __future__ import annotations

from .data_loader import get_store

# frase de causa da morte (concordando com a narrativa)
_CAUSE_PHRASE = {
    "neonatal": "complicações no parto ou logo após o nascimento",
    "infeccao": "uma doença infecciosa",
    "fome": "fome e desnutrição",
    "parto": "complicações ao dar à luz",
    "violencia": "violência — guerra ou homicídio",
    "acidente": "um acidente",
    "cronica": "uma doença crônica (coração, câncer ou AVC)",
}


# preposição + nome em português para os países mais prováveis num sorteio mundial
# (a maioria dos nascimentos cai nos mais populosos). Fallback: "em {país}".
_PAISES_PT = {
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
}


# nome do país em português (sem preposição), para a moldura "região que hoje chamamos de X"
_NOME_PT = {
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
}


def _nome_pt(place: str) -> str:
    return _NOME_PT.get(place, place)


def _place_label(place: str) -> str:
    return _PAISES_PT.get(place, f"em {place}")


def _anos(n: int) -> str:
    return "1 ano" if n == 1 else f"{n} anos"


def build_narrative(result: dict) -> dict:
    sex = result["sex"]
    age = result["age_at_death"]
    year = result["birth_year"]
    place = result.get("birthplace", result["input"]["place"])
    sampled = result.get("birthplace_sampled", False)
    cause_key = result["cause"]["key"]

    mulher = sex == "feminino"
    artigo = "uma" if mulher else "um"
    subst = "mulher" if mulher else "homem"
    crianca_subst = "menina" if mulher else "menino"

    # manchete concreta
    if age == 0:
        headline = f"Você é {artigo} {crianca_subst} que não completa um ano de vida."
    elif age < 13:
        headline = f"Você é {artigo} {crianca_subst}. Morre aos {_anos(age)}."
    else:
        headline = f"Você é {artigo} {subst}. Morre aos {_anos(age)}."

    story: list[str] = []

    # 1. nascimento — se o local foi sorteado entre vários, dá-se a descoberta
    ano_txt = f"{year}" if year >= 0 else f"{abs(year)} a.C."
    if sampled and (year < 1800 or place not in _PAISES_PT):
        # moldura "região que hoje chamamos de X" — sempre gramatical e no tom do projeto
        local_txt = f"na região que hoje chamamos de {_nome_pt(place)}"
    else:
        local_txt = _place_label(place)
    story.append(
        f"Você nasce em {ano_txt}, {local_txt}. "
        f"É {artigo} {crianca_subst}."
    )

    # 2. arco da vida + causa
    causa = _CAUSE_PHRASE.get(cause_key, "causas da época")
    if age == 0:
        story.append(
            f"Você não sobrevive ao primeiro ano. A causa é {causa}. "
            "Era o destino de uma enorme parcela das crianças durante quase toda a história."
        )
    elif age < 5:
        story.append(
            f"Você morre aos {_anos(age)}, ainda na primeira infância — por {causa}."
        )
    elif age < 15:
        story.append(
            f"Você chega à infância, mas morre aos {_anos(age)}, por {causa}."
        )
    elif age < 45:
        story.append(
            f"Você cresce e chega à vida adulta. Morre cedo, aos {_anos(age)}, por {causa}."
        )
    else:
        e0_fact = _find(result, "expectativa_vida")
        e0 = float(e0_fact["value"]) if e0_fact else 40.0
        if age >= e0 + 8:
            story.append(
                f"Você vive até os {_anos(age)} — uma vida longa para a sua época — "
                f"e morre por {causa}."
            )
        else:
            story.append(f"Você vive até os {_anos(age)} e morre por {causa}.")

    # 3. condições materiais
    cal = _find(result, "calorias")
    renda = _find(result, "renda")
    mat = []
    if cal:
        mat.append(f"come por volta de {cal['value']} por dia")
    if renda:
        mat.append(f"vive com o equivalente a {renda['value']} por ano")
    if mat:
        frase = " e ".join(mat)
        story.append(f"No dia a dia, você {frase}.")

    # 4. contraste com o presente (deixa a mensagem emergir dos dados)
    contraste = _contrast_today(place, age)
    if contraste:
        story.append(contraste)

    return {"headline": headline, "story": story}


def _find(result: dict, key: str) -> dict | None:
    for f in result["facts"]:
        if f["key"] == key:
            return f
    return None


def _contrast_today(place: str, age: int) -> str | None:
    store = get_store()
    look = store.resolve("life_expectancy", place, 2023)
    if look is None:
        return None
    hoje = look.value
    diff = hoje - age
    if diff <= 3:
        return None
    return (
        f"Hoje, no mesmo lugar, a expectativa de vida é de cerca de {hoje:.0f} anos — "
        f"{diff:.0f} a mais do que você viveu. O presente que reclamamos é, "
        "estatisticamente, um dos melhores momentos para se estar vivo."
    )
