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

O app rodando é **100% estático** (HTML/CSS/JS na pasta `docs/`): não há servidor.
O Python serve apenas para **gerar os dados** (`docs/data.json`) a partir dos datasets
reais. Para regenerar os dados:

```bash
pip install -r requirements.txt
python scripts/download_data.py     # baixa os datasets reais para backend/data/raw/
python scripts/build_static.py      # empacota tudo em docs/data.json (~2,5 MB)
```

Para ver o site localmente, basta servir a pasta `docs/` por HTTP:

```bash
python -m http.server 8000 --directory docs
# abra http://localhost:8000
```

### Publicação (GitHub Pages)

O site é servido da pasta `docs/` na branch `main`. Em
**Settings → Pages → Build and deployment**, escolha *Deploy from a branch*,
branch `main` e pasta `/docs`. O endereço fica em
`https://gladsjr.github.io/bornbychance`.

## Estrutura

```
docs/                  o site estático publicado (GitHub Pages)
  index.html           a página
  style.css            estilo
  engine.js            o sorteio: dados, modelo de Siler, causas, motor
  narrative.js         monta a narrativa em português
  app.js               interface (chama o motor no próprio navegador)
  data.json            todos os dados reais, empacotados (gerado pelo build)
backend/app/           camada de dados em Python (usada para gerar data.json)
  data_loader.py       carrega os CSV reais; fallback lugar->região->Mundo; população
  curated.py           estimativas históricas para épocas sem medição direta
  causes.py            perfis de causa de morte (transição epidemiológica)
  sources.py           registro central de fontes citáveis
  data/raw/            CSVs baixados (reproduzíveis via scripts/download_data.py)
scripts/
  download_data.py     baixa os datasets públicos
  build_static.py      empacota os dados em docs/data.json
```

> O `backend/app/{main,engine,life_tables,narrative}.py` contém a versão original
> em Python (servidor FastAPI), mantida como referência. A versão publicada usa o
> porte em JavaScript em `docs/`.

## Status

Funcional como site estático. Próximos passos possíveis: causas de morte por idade com
dados GBD licenciados, perfis regionais de violência/guerra históricos, distribuição de
fertilidade, e um modo "compare duas épocas lado a lado".
