"""
Sorteia a CAUSA da morte, condicionada a idade, sexo e nivel de desenvolvimento.

Metodo: a "transicao epidemiologica" (Omran 1971) descreve como o perfil de
causas muda de infeccao/fome/violencia (sociedades pre-modernas) para doencas
cronicas (sociedades modernas). Definimos dois perfis-ancora por faixa etaria
e interpolamos por um indice de modernidade derivado da expectativa de vida
real. A mortalidade materna usa o dado REAL de razao de mortalidade materna.

Perfis modernos ancorados nas proporcoes do Global Burden of Disease (IHME);
perfis pre-modernos na demografia historica. Confianca: media para epocas com
dado, baixa para o perfil pre-moderno.
"""
from __future__ import annotations

import numpy as np

# rotulos legiveis das causas
CAUSES = {
    "neonatal": "complicacoes no nascimento",
    "infeccao": "doenca infecciosa",
    "fome": "fome / desnutricao",
    "parto": "complicacoes no parto",
    "violencia": "violencia (guerra ou homicidio)",
    "acidente": "acidente",
    "cronica": "doenca cronica (coracao, cancer, AVC)",
}

# Perfis pre-modernos (peso relativo por faixa etaria).
_PRE = {
    "infante": {"neonatal": 25, "infeccao": 55, "fome": 15, "acidente": 5},
    "crianca": {"infeccao": 70, "fome": 12, "violencia": 8, "acidente": 10},
    "jovem":   {"infeccao": 45, "fome": 8, "violencia": 20, "acidente": 12, "cronica": 15},
    "idoso":   {"infeccao": 35, "cronica": 45, "fome": 5, "violencia": 5, "acidente": 10},
}

# Perfis modernos (peso relativo por faixa etaria).
_MOD = {
    "infante": {"neonatal": 55, "infeccao": 25, "acidente": 15, "cronica": 5},
    "crianca": {"acidente": 45, "infeccao": 20, "cronica": 25, "violencia": 10},
    "jovem":   {"acidente": 30, "cronica": 30, "violencia": 20, "infeccao": 20},
    "idoso":   {"cronica": 85, "infeccao": 8, "acidente": 5, "violencia": 2},
}


def _age_group(age: int) -> str:
    if age < 5:
        return "infante"
    if age < 15:
        return "crianca"
    if age < 50:
        return "jovem"
    return "idoso"


def _modernity(e0: float) -> float:
    return float(np.clip((e0 - 25.0) / (80.0 - 25.0), 0.0, 1.0))


def _blend(pre: dict, mod: dict, m: float) -> dict:
    keys = set(pre) | set(mod)
    return {k: (1 - m) * pre.get(k, 0.0) + m * mod.get(k, 0.0) for k in keys}


def sample_cause(
    age: int,
    sex: str,
    e0: float,
    mmr: float | None,
    rng: np.random.Generator,
) -> dict:
    """
    Retorna {key, label, confidence}. mmr = mortes maternas por 100.000 nascidos.
    """
    group = _age_group(age)
    m = _modernity(e0)
    dist = _blend(_PRE[group], _MOD[group], m)

    # injeta mortalidade materna real para mulheres em idade reprodutiva
    if sex == "feminino" and 15 <= age < 50 and mmr:
        maternal_share = float(np.clip(mmr / 2500.0, 0.0, 0.35))
        if maternal_share > 0:
            total = sum(dist.values())
            for k in dist:
                dist[k] *= (1 - maternal_share)
            dist["parto"] = maternal_share * total

    keys = list(dist.keys())
    weights = np.array([dist[k] for k in keys], dtype=float)
    weights /= weights.sum()
    key = str(rng.choice(keys, p=weights))

    confidence = "baixa" if m < 0.3 else "media"
    return {"key": key, "label": CAUSES[key], "confidence": confidence}
