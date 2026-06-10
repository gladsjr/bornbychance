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


def _place_label(place: str) -> str:
    especiais = {
        "World": "no mundo",
        "Brazil": "no Brasil",
        "France": "na França",
        "Japan": "no Japão",
        "United States": "nos Estados Unidos",
        "Roman Empire": "no Império Romano",
    }
    return especiais.get(place, f"em {place}")


def build_narrative(result: dict) -> dict:
    sex = result["sex"]
    age = result["age_at_death"]
    year = result["birth_year"]
    place = result["input"]["place"]
    cause_key = result["cause"]["key"]

    mulher = sex == "feminino"
    artigo = "uma" if mulher else "um"
    subst = "mulher" if mulher else "homem"
    crianca_subst = "menina" if mulher else "menino"

    # manchete concreta
    if age == 0:
        headline = f"Você é {artigo} {crianca_subst} que não completa um ano de vida."
    elif age < 13:
        headline = f"Você é {artigo} {crianca_subst}. Morre aos {age} anos."
    else:
        headline = f"Você é {artigo} {subst}. Morre aos {age} anos."

    story: list[str] = []

    # 1. nascimento
    nasce = "nasce" if year >= 0 else "nasce"
    ano_txt = f"{year}" if year >= 0 else f"{abs(year)} a.C."
    story.append(
        f"Você {nasce} em {ano_txt}, {_place_label(place)}. "
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
            f"Você morre aos {age} anos, ainda na primeira infância — por {causa}."
        )
    elif age < 15:
        story.append(
            f"Você chega à infância, mas morre aos {age} anos, por {causa}."
        )
    elif age < 45:
        story.append(
            f"Você cresce e chega à vida adulta. Morre cedo, aos {age} anos, por {causa}."
        )
    else:
        story.append(
            f"Você vive até os {age} anos — uma vida longa para a sua época — "
            f"e morre por {causa}."
        )

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
