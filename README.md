# Born by Chance — a loteria do nascimento

Você não escolheu quando nem onde nasceu. Quase ninguém na história escolheu.

**Born by Chance** deixa você escolher um lugar e uma faixa de anos, "gira a roleta
do nascimento" **uma vez** e devolve uma vida concreta, sorteada a partir de **dados
reais**: sexo, idade da morte, causa da morte, calorias por dia, renda. Não é uma
tabela de probabilidades — é uma pessoa. Você pode girar de novo e virar outra.

O objetivo é dar concretude ao quanto o momento que vivemos hoje, com todos os seus
problemas, está longe de ser o pior da história — e deixar esse contraste emergir
dos próprios números.

## Regra de ouro: nada é inventado

Todo valor exibido vem de uma fonte pública e citável, ou de uma estimativa de
demografia histórica claramente identificada com seu nível de confiança:

| Dimensão | Cobertura de dado real | Fonte |
|---|---|---|
| Expectativa de vida | Mundo 1770+, países 1950+ | Our World in Data (UN, HMD, Gapminder) |
| Mortalidade infantil (<5) | Mundo 1800+ | Our World in Data (UN IGME) |
| Renda per capita | Ano 1+ (regiões), Mundo 1820+ | Maddison Project Database 2023 |
| Calorias/dia | 1961+ | Our World in Data (FAO) |
| Razão de sexo ao nascer | 1950+ | Our World in Data (UN WPP) |
| Mortalidade materna | 1985+ | Our World in Data (WHO/UNICEF) |

Para épocas anteriores à medição direta, usamos estimativas acadêmicas (Riley 2005;
Volk & Atkinson 2013; Fogel 2004; Maddison), sempre marcadas com confiança **baixa**.

### Como a idade da morte é sorteada

A partir de dois números reais — expectativa de vida ao nascer e mortalidade infantil
— calibramos uma **tábua de vida** pelo modelo de riscos concorrentes de **Siler (1979)**,
padrão em demografia, e sorteamos uma idade de morte da distribuição resultante. Isso
reproduz o padrão histórico real: altíssima mortalidade infantil, mas quem sobrevivia
à infância podia chegar à meia-idade.

A **causa da morte** segue a transição epidemiológica (Omran 1971): interpola entre um
perfil pré-moderno (infecção, fome, violência) e um moderno (doenças crônicas) conforme
o desenvolvimento, condicionada a idade e sexo, com a mortalidade materna real injetada.

## Como rodar

```bash
pip install -r requirements.txt
python scripts/download_data.py        # baixa os datasets reais (~7 arquivos)
python -m uvicorn backend.app.main:app --reload --port 8077
# abra http://127.0.0.1:8077
```

## Estrutura

```
backend/
  app/
    main.py          API FastAPI (/api/places, /api/draw)
    engine.py        o sorteio: junta tudo numa vida
    data_loader.py   carrega os CSV reais com fallback lugar->região->Mundo
    curated.py       estimativas históricas para épocas sem medição direta
    life_tables.py   modelo de Siler: idade da morte a partir de e0 e q5 reais
    causes.py        causa da morte (transição epidemiológica)
    narrative.py     monta a narrativa em português
    sources.py       registro central de fontes citáveis
  data/raw/          CSVs baixados (reproduzíveis via scripts/download_data.py)
frontend/            página única (HTML/CSS/JS), sem framework
scripts/
  download_data.py   baixa os datasets públicos
```

## Status

Protótipo funcional. Próximos passos possíveis: causas de morte por idade com dados
GBD licenciados, perfis regionais de violência/guerra históricos, distribuição de
fertilidade, e um modo "compare duas épocas lado a lado".
