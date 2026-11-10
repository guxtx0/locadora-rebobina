# Locadora Rebobina · Análise de Locações com Power BI

Projeto de portfólio sobre uma rede fictícia de videolocadoras na Região Metropolitana de Belo Horizonte, com movimento de **janeiro de 2009 a janeiro de 2011**. Ele cobre todo o ciclo de um projeto de dados:
- **Simulação dos dados** em Python;
- **Modelagem estrela** em SQL Server;
- **Painel em Power BI**, entregue como projeto `.pbip` versionável;
- **Relatório em PDF** com as análises.

> **Relatório das análises:** [`docs/Locadora_Rebobina_Analises.pdf`](docs/Locadora_Rebobina_Analises.pdf)

---

## Principais números

| Indicador | Valor |
|---|---|
| Faturamento total | **R$ 549.434,85** |
| Locações | **105.078** |
| Clientes ativos | **3.109** |
| Ticket médio por locação | **R$ 5,23** |
| Receita vinda de multas | **16,0%** (R$ 87.715,75) |
| Devoluções com atraso | **21,3%** |
| Locações com alguma promoção | **54,9%** (R$ 28.766,62 em descontos) |
| Média de locações em véspera de feriado × dia útil | **181,1 × 124,5 por dia (+45,4%)** |
| Previsão de demanda dos lançamentos (teste) | **R² 0,91 · erro médio de 7,7 locações** |
| Ganho com o número ideal de cópias | **R$ 38.413,12** |
| Modelo de abandono de clientes | **AUC 0,773** |

## Perguntas respondidas

- **Bilheteria explica a procura?** Sim. Filmes acima de R$ 1 bi de bilheteria tiveram em média 150,7 locações por título, contra 20,2 dos que fizeram até R$ 100 mi.
- **Qual o melhor dia do calendário?** A véspera de feriado, que supera até o fim de semana.
- **O calendário muda o gênero alugado?** Sim:
  - Animação e Família vão de 6,4% para 8,5% das locações nas férias escolares.
  - Terror vai de 5,6% para 8,1% em outubro.
  - Filmes de Natal, Dia das Mães, Dia dos Pais, Páscoa e futebol (Copa de 2010) têm até o triplo da procura nas suas datas.
- **Quanto pesam multas e promoções?** As multas são 16% da receita, e mais da metade das locações tem algum desconto.
- **Onde estão os melhores clientes?** Nos bairros da zona sul de BH: Gutierrez, Santo Antônio, Prado e Funcionários.

---

## Como abrir o painel

1. Baixe o repositório pelo botão **Code > Download ZIP** ou com `git clone`.
2. Abra **`powerbi/Locadora_Rebobina.pbip`** no Power BI Desktop, na versão de setembro de 2026 ou mais recente.
3. Na primeira abertura, clique em **Página Inicial > Atualizar**. Os dados estão embutidos no próprio projeto, então não é preciso banco de dados nem configuração.

O painel tem 6 páginas, e os filtros de loja, categoria e mês são sincronizados entre elas:

| Página | Conteúdo |
|---|---|
| Visão Geral | faturamento e locações por mês, lojas, categorias, top 10 bairros |
| Filmes e Atores | top 15 filmes, top 10 atores, perfil do título, locações × faixa de bilheteria |
| Clientes e Operação | dia da semana, status das devoluções, top 10 clientes, faixa etária |
| Sazonalidade e Datas | locações por dia, média por tipo de dia, datas comemorativas, gêneros ao longo do ano |
| Estoque e Retenção | taxa de ocupação das cópias, matriz de coorte de retenção, demanda não atendida |
| Previsões e Recomendações | previsto × real, cópias atuais × ideais, fatores de abandono, clientes por faixa de risco |

## Análises avançadas

### DAX

| Análise | Técnica |
|---|---|
| **Taxa de ocupação das cópias** | Cada locação é um intervalo de datas (retirada → devolução) cruzado com o período filtrado. A medida remove o filtro de calendário e soma a sobreposição linha a linha com `SUMX`, sem perder os filtros de filme e loja. |
| **Coorte de retenção** | Tabela desconectada de meses relativos (0 a 24) + `TREATAS` para levar o mês-alvo de cada coorte até o calendário. |
| **Grupo de cálculo "Comparação de Tempo"** | Período atual, mês anterior, mesmo período do ano anterior, acumulado no ano e variação %, aplicáveis a qualquer medida. Usa `SELECTEDMEASURE`, `ISSELECTEDMEASURE` e formato dinâmico. |
| **Rankings Top N dinâmicos** | `RANKX` com `ALLSELECTED`, respeitando os filtros da página. |

### Python (`scripts/analises_python.py`)

| Análise | Método | Resultado |
|---|---|---|
| **Previsão de demanda dos lançamentos** (8 primeiras semanas) | HistGradientBoosting com bilheteria, votos, popularidade, gênero e mês de chegada; validação temporal (treino até abr/10, teste mai–dez/10); comparação com regressão linear | R² 0,91, erro médio de 7,7 locações (contra 9,4 da linear) |
| **Número ideal de cópias** por filme e loja | Para cada cópia extra, compara a receita adicional com o custo líquido (compra − revenda) nos 180 dias de lançamento, usando a demanda observada (locações + tentativas sem cópia) | 1.060 dos 1.095 pares filme × loja com cópias em excesso; ganho potencial de R$ 38,4 mil |
| **Risco de abandono (churn)** | Fotos mensais de cada cliente (recência, frequência, gasto, atrasos, promoções…); rótulo = nenhuma locação nos 90 dias seguintes; validação temporal; importância por permutação | AUC 0,773 (contra 0,744 da logística); os 20% de maior risco concentram 44,6% dos abandonos |

Os resultados viram tabelas do modelo (`previsao_lancamentos`, `otimizacao_copias`, `importancia_churn`, `metricas_modelos` e colunas de risco em `dim_cliente`) e aparecem na página "Previsões e Recomendações".

## Estrutura do repositório

```
powerbi/                  projeto Power BI (.pbip)
  Locadora_Rebobina.pbip
  Locadora_Rebobina.SemanticModel/   modelo em TMDL: tabelas, relacionamentos, 65 medidas DAX e grupo de cálculo
  Locadora_Rebobina.Report/          relatório em PBIR: páginas, visuais, tema e fundos
sql/                      mesma base para SQL Server (criação, cargas e views de BI)
dados/csv/                tabelas do modelo estrela em CSV
docs/                     relatório das análises e roteiro de apresentação em PDF
scripts/                  pipeline em Python que gera tudo a partir da base TMDB 5000
```

## Modelo de dados

O modelo é uma **estrela**:
- **Fatos:** `fato_locacao` (uma linha por filme alugado) e `fato_pagamento` (locações e multas, base do faturamento).
- **Dimensões de filme:** `dim_filme`, `dim_ator` e a ponte `ponte_filme_ator`, que liga filmes e atores numa relação muitos-para-muitos.
- **Demais dimensões:**
  - `dim_cliente`;
  - `dim_loja`;
  - `dim_calendario`, com feriados nacionais, vésperas, férias escolares, datas comemorativas e jogos do Brasil na Copa de 2010.

As medidas DAX ficam organizadas em pastas: Receita, Volume, Catálogo, Operação, Calendário, Rankings, Estoque, Retenção e Modelos (Python).

O modelo também tem:
- `dim_copia` e `fato_demanda_nao_atendida`, para o estoque;
- `meses_relativos`, tabela desconectada da coorte;
- o grupo de cálculo `Comparação de Tempo`;
- as tabelas geradas pelos modelos em Python.

### Onde entra Python, Power Query e DAX

| Tabela | Montada em | O que tem |
|---|---|---|
| `dim_calendario` | Python | feriados, vésperas, férias escolares, datas comemorativas, Copa 2010 |
| `dim_filme`, `dim_ator`, `ponte_filme_ator` | Python | filmes do TMDB com título em português, categoria, perfil e elenco |
| `dim_loja`, `dim_copia`, `dim_cliente` | Python | lojas, cópias, clientes, coorte e risco de abandono (scikit-learn) |
| `fato_locacao`, `fato_pagamento`, `fato_demanda_nao_atendida` | Python | simulação dia a dia das locações, pagamentos e falta de cópia |
| `previsao_lancamentos`, `otimizacao_copias`, `importancia_churn`, `metricas_modelos` | Python | saídas dos modelos |
| `meses_relativos` | Power Query (M) | sequência 0–24 da coorte |
| `Comparação de Tempo` | DAX | grupo de cálculo com 5 itens |
| `_Medidas` | DAX | 65 medidas |

A regra: **Python** faz tudo o que é linha a linha ou depende de modelo; o **Power Query** só carrega os CSVs embutidos; o **DAX** faz tudo o que muda com o filtro. O modelo não tem colunas calculadas.

## Usar no SQL Server (opcional)

1. Rode `sql/01_criar_banco_rebobina.sql` no SSMS.
2. Rode os scripts de carga pelo Prompt de Comando, nesta ordem:

```
sqlcmd -S localhost\SQLEXPRESS -E -f 65001 -i sql\02_carga_cadastros.sql
sqlcmd -S localhost\SQLEXPRESS -E -f 65001 -i sql\03_carga_locacoes.sql
sqlcmd -S localhost\SQLEXPRESS -E -f 65001 -i sql\04_carga_pagamentos.sql
```

3. Rode `sql/05_views_bi.sql`. Ele cria as views `bi.*` e mostra uma conferência dos totais.

Os scripts SQL trazem a base transacional. As tabelas geradas pelos modelos em Python estão no projeto do Power BI e em `dados/csv/`.

## Regerar o projeto do zero

```
pip install -r requirements.txt
python scripts/pipeline.py --tmdb dados/brutos
```

O pipeline precisa dos arquivos `tmdb_5000_movies.csv` e `tmdb_5000_credits.csv` em `dados/brutos/`. O passo a passo para baixá-los está em [`dados/brutos/LEIA-ME.md`](dados/brutos/LEIA-ME.md).

O pipeline faz, em sequência:
1. Simula a locadora.
2. Monta o modelo estrela e roda as análises em Python.
3. Gera o projeto Power BI.
4. Gera os scripts SQL.
5. Exporta os CSVs.

O resultado é sempre o mesmo, porque a simulação usa sementes fixas.

### Títulos em português

O arquivo `scripts/titulos_ptbr.txt` traz o **título em português dos 3.000 filmes** do acervo. Sempre que o filme foi lançado no Brasil, vale o título oficial de distribuição (o mesmo que aparece em sites como AdoroCinema e Cinema10). Para filmes que não chegaram ao circuito brasileiro, a tradução é própria e segue o título original.

Quando dois filmes diferentes têm o mesmo título no Brasil (por exemplo, *O Sobrevivente* para *The Running Man* e *Rescue Dawn*), o ano entra entre parênteses para não misturá-los nos gráficos. O título original e o título em inglês continuam no modelo, ocultos, para consulta.

O script `scripts/buscar_titulos_ptbr.py` é opcional: consulta a API do TMDB e serve para revisar a lista ou incluir filmes novos, caso a base seja ampliada.

## Regras de negócio da simulação

**Procura pelos filmes**
- A procura de cada filme combina bilheteria (50%), votos (35%) e popularidade (15%).
- **Lançamentos:** chegam à locadora de 2 a 3,5 meses depois do cinema, com pico de procura nas primeiras semanas.
- **Clássicos:** mantêm a procura ao longo do tempo.

**Estoque**
- Os 15% de filmes de maior sucesso têm **3 cópias por loja**, os lançamentos têm 2 e o restante do acervo tem 1.
- Quando não há cópia livre, o cliente troca de filme ou desiste.

**Calendário**
- Vésperas de feriado com +45% de movimento.
- Férias escolares e Semana das Crianças com mais Animação e Família.
- Outubro com mais Terror.
- Datas comemorativas com mais saída de filmes temáticos.
- Queda no movimento em dias de jogo do Brasil na Copa de 2010.

**Preços e promoções (R$)**

| Tipo | 2009 | 2010 |
|---|---|---|
| Lançamento | 5,89 | 6,49 |
| Catálogo | 3,79 | 4,39 |
| Clássico | 2,99 | 3,29 |

| Promoção | Desconto |
|---|---|
| Quarta promocional | −25% em catálogo e clássico |
| Combo de 3 filmes | −10% |
| Cartão fidelidade | −7% |

**Multas**
- De R$ 1,89 a R$ 3,19 por dia de atraso, com acordo de 30% de desconto em parte dos casos.

## Limitações

- As locações, os clientes e as lojas são **simulados**. O projeto serve para estudo e portfólio.
- Bilheteria e orçamento foram convertidos para reais pelo câmbio médio de 2010 (R$ 1,76 por US$).
- A classificação indicativa foi estimada a partir do gênero.

## Créditos

- **Dados dos filmes:** [TMDB 5000 Movie Dataset](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata). *This product uses the TMDB API but is not endorsed or certified by TMDB.*
- **Autor:** Gustavo Oliveira · Design instrucional, educação tecnológica e análise de dados.
