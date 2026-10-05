# Evolução do Desemprego no Brasil (2015 a 2024)

Projeto da **Avaliação G1** da disciplina **Linguagem de Programação: Análise e Visualização de Dados com Python**.
**Tema 04: Evolução do Desemprego no Brasil.**
**Autor:** Marcell Sidaco de Moraes

| Entrega | Link |
|---|---|
| Repositório GitHub | https://github.com/{{GITHUB_USER}}/projeto-g1 |
| Página do projeto (GitHub Pages) | https://{{GITHUB_USER}}.github.io/projeto-g1/ |
| Dashboard (Streamlit Community Cloud) | {{STREAMLIT_URL}} |
| Notebook de análise | [`notebooks/analise_desemprego.ipynb`](notebooks/analise_desemprego.ipynb) |
| Código do dashboard | [`app.py`](app.py), [`utils.py`](utils.py), [`pages/`](pages) |
| Base de dados | [`dados/simulacao_desemprego_brasil.csv`](dados/simulacao_desemprego_brasil.csv) |

---

## 1. Descrição do projeto

O projeto investiga o comportamento do desemprego no Brasil entre 2015 e 2024: tendências, regiões mais
afetadas, comparação entre estados, períodos de crise e de recuperação econômica. Cobre todo o pipeline de
dados, da leitura do CSV bruto até a publicação de um dashboard interativo.

### Fluxo do projeto

```
dados/simulacao_desemprego_brasil.csv          (dados brutos)
    ↓ limpeza, validação e engenharia de atributos (pandas, notebook)
dados/simulacao_desemprego_brasil_tratado.csv  (dados tratados)
    ↓ persistência com modelo relacional (SQLAlchemy ORM)
database/desemprego.sqlite                     (banco SQLite)
    ↓ consulta SQL com JOIN (SQLAlchemy + pandas)
app.py + pages/                                (dashboard Streamlit multipágina)
    ↓ deploy
Streamlit Community Cloud + GitHub Pages       (publicação online)
```

---

## 2. Problema e perguntas orientadoras

1. Quais regiões apresentam maior desemprego?
2. Quais estados apresentam menores taxas?
3. Existem períodos de crise econômica mais evidentes?
4. O desemprego aumentou ou diminuiu ao longo do tempo?
5. Existem diferenças relevantes entre regiões?
6. Há sazonalidade em determinados setores?
7. Quais grupos parecem mais vulneráveis?

---

## 3. Base de dados

Arquivo `simulacao_desemprego_brasil.csv`, do repositório
[Dados-Simulados-G2](https://github.com/AlexandreLouzada/Dados-Simulados-G2): 800 linhas (20 estados x 40
trimestres) e 14 colunas (`ano`, `trimestre`, `data`, `regiao`, `uf`, `populacao_ativa`, `empregados`,
`desempregados`, `taxa_desemprego`, `renda_media`, `setor_predominante`, `vagas_formais`, `inflacao`,
`nivel_risco`).

**Tratamento aplicado:** checagem de nulos e duplicados, chave única estado + trimestre, conversão de tipos,
padronização de textos, validação `empregados + desempregados = populacao_ativa`, taxa recalculada, faixas
válidas e outliers (IQR).

**Atributos criados:** `estado` e `codigo_ibge` (API de localidades do IBGE), `periodo`, `taxa_ocupacao`,
`variacao_taxa_anual`, `media_movel_4t`, `faixa_renda` e `fase_economica`.

---

## 4. Tecnologias utilizadas

| Tecnologia | Função |
|---|---|
| Python | Linguagem principal |
| Pandas | Leitura, limpeza, agregações e tabelas dinâmicas |
| NumPy | Tendência linear e cálculos numéricos |
| Matplotlib | Gráficos estáticos |
| Seaborn | Gráficos estatísticos (heatmaps, boxplots, regressão) |
| Plotly | Mapa coroplético e gráficos interativos |
| SQLAlchemy | ORM, modelagem relacional e consultas SQL |
| SQLite | Persistência dos dados |
| Requests | Consumo das APIs públicas do IBGE (estados e malha geográfica) |
| Streamlit | Dashboard interativo multipágina |
| Git, GitHub e GitHub Pages | Versionamento e publicação |

---

## 5. Estrutura do projeto

```text
projeto-g1/
│
├── app.py                 # entrada do dashboard: filtros, navegação e página inicial
├── utils.py               # carga do banco, filtros, KPIs, gráficos e textos
├── pages/                 # páginas do dashboard multipágina
│   ├── 1_Visao_Geral.py
│   ├── 2_Evolucao_Temporal.py
│   ├── 3_Regioes_e_Estados.py
│   ├── 4_Analise_Economica.py
│   └── 5_Dados_e_Conclusao.py
├── requirements.txt
├── README.md
├── index.html             # página do projeto (GitHub Pages)
├── dados/
│   ├── simulacao_desemprego_brasil.csv
│   ├── simulacao_desemprego_brasil_tratado.csv
│   └── br_uf.geojson
├── database/
│   └── desemprego.sqlite
├── notebooks/
│   └── analise_desemprego.ipynb
└── imagens/               # gráficos exportados pelo notebook e prints do dashboard
```

### Modelo relacional

```
regiao (1) ──< (N) uf (1) ──< (N) indicador_trimestral (N) >── (1) setor
```

---

## 6. KPIs

| KPI | Valor (base completa) | Descrição |
|---|---|---|
| Taxa média de desemprego | 9,90% | Média geral das taxas |
| Estado com maior desemprego | Ceará (13,65%) | Ranking estadual |
| Região mais afetada | Nordeste (13,28%) | Comparação regional |
| Total de desempregados | 5,37 milhões | Soma do último trimestre (2024-T4) |
| Renda média nacional | R$ 2.790,65 | Média salarial |
| Evolução da taxa | 10,36% para 8,48% (-1,88 p.p.) | Tendência temporal (2015-T1 a 2024-T4) |

No dashboard todos os KPIs são recalculados de acordo com os filtros.

---

## 7. Dashboard

Páginas: **Início** (título, problema, perguntas e KPIs), **Visão geral**, **Evolução temporal**,
**Regiões e estados**, **Análise econômica** e **Dados e conclusão**.

Filtros na barra lateral (valem para todas as páginas): **ano, trimestre, região, estado, setor econômico e
nível de risco**.

Visualizações: linha temporal com média móvel, linhas por região, barras por estado, barras por região,
dispersão renda x desemprego, heatmap trimestral, heatmap região x ano, desigualdade regional, inflação x
desemprego, matriz de correlação, sazonalidade por setor, boxplot por setor, nível de risco por região, mapa
coroplético interativo, comparação interativa entre estados e tabela dinâmica configurável.

Cada gráfico tem interpretação textual calculada com os dados filtrados, e a última página traz as respostas
às perguntas orientadoras e a conclusão executiva.

### Funcionalidades atendidas

**Intermediárias:** filtros múltiplos, KPIs dinâmicos, gráficos interativos, análise temporal, tratamento
avançado de dados, integração entre tabelas, dashboard organizado em seções, visualizações comparativas e
análise geográfica.

**Avançadas:** persistência em banco (SQLAlchemy + SQLite), modelagem relacional (SQLAlchemy), dashboard
multipágina (Streamlit), mapa interativo (Plotly), séries temporais (média móvel, variação anual, tendência)
e correlação estatística (Pandas/NumPy).

---

## 8. Principais conclusões

* **Tendência de queda com duas crises:** picos em 2016 (recessão) e em 2020 e 2021 (pandemia), seguidos de
  recuperação; 2024 tem a menor média anual da série (8,43%).
* **Desigualdade regional estrutural:** o Nordeste tem taxa cerca de duas vezes maior que a do Sul, e a ordem
  das regiões é a mesma nos dez anos.
* **Estados críticos concentrados:** Bahia, Ceará e Paraíba lideram em trimestres de risco Crítico; Paraná,
  Santa Catarina e Rio Grande do Sul têm as menores taxas.
* **Variáveis econômicas explicam pouco nesta base:** renda, inflação, vagas formais e setor têm correlação
  próxima de zero com o desemprego.
* **Recomendação:** políticas de emprego com foco regional, priorizando Nordeste e Norte.

---

## 9. Como executar localmente

```bash
git clone https://github.com/{{GITHUB_USER}}/projeto-g1.git
cd projeto-g1
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Para refazer o tratamento, o banco e as imagens, execute o notebook (precisa também de `jupyter`):

```bash
pip install jupyter
jupyter nbconvert --to notebook --execute --inplace notebooks/analise_desemprego.ipynb
```

---

## 10. Autor

**Marcell Sidaco de Moraes** · marcell.moraes@soulasalle.com.br
