"""Funções compartilhadas pelo dashboard: carga de dados, filtros, KPIs,
gráficos e textos de interpretação.

O banco SQLite (database/desemprego.sqlite) e o CSV tratado são gerados pelo
notebook notebooks/analise_desemprego.ipynb.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap
from sqlalchemy import create_engine

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CAMINHO_CSV = BASE_DIR / "dados" / "simulacao_desemprego_brasil.csv"
CAMINHO_TRATADO = BASE_DIR / "dados" / "simulacao_desemprego_brasil_tratado.csv"
CAMINHO_GEOJSON = BASE_DIR / "dados" / "br_uf.geojson"
CAMINHO_BANCO = BASE_DIR / "database" / "desemprego.sqlite"

# ---------------------------------------------------------------------------
# Cores (paleta categórica validada para daltonismo, ordem fixa por entidade)
# ---------------------------------------------------------------------------
ORDEM_REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
CORES_REGIAO = {
    "Norte": "#2a78d6",
    "Nordeste": "#eb6834",
    "Centro-Oeste": "#1baf7a",
    "Sudeste": "#eda100",
    "Sul": "#e87ba4",
}
ORDEM_RISCO = ["Baixo", "Médio", "Alto", "Crítico"]
CORES_RISCO = {
    "Baixo": "#0ca30c",
    "Médio": "#fab219",
    "Alto": "#ec835a",
    "Crítico": "#d03b3b",
}
ORDEM_FAIXAS_RENDA = ["Até R$ 2 mil", "R$ 2 a 3 mil", "R$ 3 a 4 mil", "Acima de R$ 4 mil"]
ORDEM_SETORES = ["Agropecuária", "Comércio", "Construção", "Indústria", "Serviços"]
AZUL = "#2a78d6"
AZUL_ESCURO = "#184f95"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
GRADE = "#e1e0d9"

CMAP_SEQUENCIAL = LinearSegmentedColormap.from_list(
    "azul", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
)
CMAP_DIVERGENTE = LinearSegmentedColormap.from_list(
    "azul_vermelho", ["#1c5cab", "#86b6ef", "#f0efec", "#f19a99", "#b42f2f"]
)
ESCALA_PLOTLY = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]

sns.set_theme(style="whitegrid", font_scale=0.95)
plt.rcParams.update({
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": TINTA_SECUNDARIA,
    "axes.titlecolor": TINTA,
    "axes.titleweight": "bold",
    "axes.titlesize": 12,
    "grid.color": GRADE,
    "xtick.color": TINTA_SECUNDARIA,
    "ytick.color": TINTA_SECUNDARIA,
    "figure.facecolor": "white",
    "axes.facecolor": "#fcfcfb",
})

# ---------------------------------------------------------------------------
# Formatação pt-BR
# ---------------------------------------------------------------------------

def fmt_num(valor, casas=0):
    """Formata número no padrão brasileiro (1.234,5)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(valor, casas=2):
    return f"{fmt_num(valor, casas)}%"


def fmt_moeda(valor, markdown=True):
    """Em textos Markdown o cifrão é escapado para o Streamlit não tratar como fórmula."""
    simbolo = "R\\$" if markdown else "R$"
    return f"{simbolo} {fmt_num(valor, 2)}"


def fmt_milhoes(valor):
    return f"{fmt_num(valor / 1e6, 2)} mi"


def eixo_pct(ax, eixo="y"):
    formatador = mtick.FuncFormatter(lambda v, _: fmt_pct(v, 1))
    (ax.yaxis if eixo == "y" else ax.xaxis).set_major_formatter(formatador)


def eixo_moeda(ax, eixo="x"):
    formatador = mtick.FuncFormatter(lambda v, _: f"R$ {fmt_num(v, 0)}")
    (ax.yaxis if eixo == "y" else ax.xaxis).set_major_formatter(formatador)


# ---------------------------------------------------------------------------
# Carga de dados
# ---------------------------------------------------------------------------

CONSULTA_SQL = """
SELECT
    i.ano, i.trimestre, i.data, i.periodo,
    r.nome   AS regiao,
    u.sigla  AS uf,
    u.nome   AS estado,
    u.codigo_ibge,
    s.nome   AS setor_predominante,
    i.populacao_ativa, i.empregados, i.desempregados,
    i.taxa_desemprego, i.taxa_ocupacao, i.renda_media,
    i.vagas_formais, i.inflacao, i.nivel_risco,
    i.variacao_taxa_anual, i.media_movel_4t,
    i.faixa_renda, i.fase_economica
FROM indicador_trimestral AS i
JOIN uf     AS u ON u.id = i.uf_id
JOIN regiao AS r ON r.id = u.regiao_id
JOIN setor  AS s ON s.id = i.setor_id
ORDER BY i.data, r.nome, u.sigla
"""


@st.cache_data(show_spinner="Carregando dados do banco SQLite...")
def carregar_dados():
    """Lê a base tratada do SQLite via SQLAlchemy (JOIN entre 4 tabelas).

    Se o banco não existir, usa o CSV tratado como alternativa.
    Retorna o DataFrame e a origem usada.
    """
    if CAMINHO_BANCO.exists():
        engine = create_engine(f"sqlite:///{CAMINHO_BANCO}")
        with engine.connect() as conexao:
            df = pd.read_sql(CONSULTA_SQL, conexao)
        origem = "SQLite (SQLAlchemy)"
    else:
        df = pd.read_csv(CAMINHO_TRATADO)
        origem = "CSV tratado"

    df["data"] = pd.to_datetime(df["data"])
    df["regiao"] = pd.Categorical(df["regiao"], ORDEM_REGIOES, ordered=True)
    df["nivel_risco"] = pd.Categorical(df["nivel_risco"], ORDEM_RISCO, ordered=True)
    df["faixa_renda"] = pd.Categorical(df["faixa_renda"], ORDEM_FAIXAS_RENDA, ordered=True)
    return df, origem


@st.cache_data
def carregar_geojson():
    with open(CAMINHO_GEOJSON, encoding="utf-8") as arquivo:
        return json.load(arquivo)


@st.cache_data
def contar_registros_banco():
    """Quantidade de linhas por tabela do modelo relacional."""
    if not CAMINHO_BANCO.exists():
        return pd.DataFrame()
    engine = create_engine(f"sqlite:///{CAMINHO_BANCO}")
    tabelas = ["regiao", "uf", "setor", "indicador_trimestral"]
    with engine.connect() as conexao:
        linhas = [
            (t, pd.read_sql(f"SELECT COUNT(*) AS n FROM {t}", conexao)["n"].iloc[0])
            for t in tabelas
        ]
    return pd.DataFrame(linhas, columns=["tabela", "registros"])


# ---------------------------------------------------------------------------
# Filtros (sidebar)
# ---------------------------------------------------------------------------

def aplicar_filtros_sidebar(df):
    """Monta os 6 filtros obrigatórios na barra lateral e devolve a base filtrada."""
    st.sidebar.header("Filtros")

    anos = sorted(df["ano"].unique())
    ano_ini, ano_fim = st.sidebar.select_slider(
        "Ano", options=anos, value=(anos[0], anos[-1]), key="f_ano"
    )
    trimestres = st.sidebar.multiselect(
        "Trimestre", [1, 2, 3, 4], default=[1, 2, 3, 4],
        format_func=lambda t: f"{t}º trimestre", key="f_trimestre",
    )
    regioes = st.sidebar.multiselect(
        "Região", ORDEM_REGIOES, default=ORDEM_REGIOES, key="f_regiao"
    )
    ufs_disponiveis = sorted(df.loc[df["regiao"].isin(regioes), "uf"].unique())
    # Remove do estado salvo as UFs que saíram por causa do filtro de região
    if "f_uf" in st.session_state:
        st.session_state["f_uf"] = [
            u for u in st.session_state["f_uf"] if u in ufs_disponiveis
        ]
    ufs = st.sidebar.multiselect(
        "Estado", ufs_disponiveis, key="f_uf", placeholder="Todos os estados das regiões",
        help="A lista depende das regiões escolhidas. Deixe vazio para considerar todos.",
    )
    setores = st.sidebar.multiselect(
        "Setor econômico", ORDEM_SETORES, default=ORDEM_SETORES, key="f_setor"
    )
    riscos = st.sidebar.multiselect(
        "Nível de risco", ORDEM_RISCO, default=ORDEM_RISCO, key="f_risco"
    )

    if st.sidebar.button("Limpar filtros", width="stretch"):
        for chave in ["f_ano", "f_trimestre", "f_regiao", "f_uf", "f_setor", "f_risco"]:
            st.session_state.pop(chave, None)
        st.rerun()

    filtro = (
        df["ano"].between(ano_ini, ano_fim)
        & df["trimestre"].isin(trimestres)
        & df["regiao"].isin(regioes)
        & df["uf"].isin(ufs or ufs_disponiveis)
        & df["setor_predominante"].isin(setores)
        & df["nivel_risco"].isin(riscos)
    )
    df_filtrado = df[filtro].copy()
    st.sidebar.caption(f"{len(df_filtrado)} de {len(df)} registros selecionados.")
    return df_filtrado


def obter_base():
    """Base filtrada guardada pelo app.py para as páginas."""
    return st.session_state["df_filtrado"], st.session_state["df_completo"]


def checar_vazio(df):
    if df.empty:
        st.warning("Nenhum registro atende aos filtros escolhidos. Ajuste os filtros na barra lateral.")
        st.stop()


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

def calcular_kpis(df):
    """KPIs do Tema 04, calculados sobre a base filtrada."""
    por_periodo = df.groupby("data")["taxa_desemprego"].mean().sort_index()
    ultimo = df["data"].max()
    ultimo_trim = df[df["data"] == ultimo]
    por_uf = df.groupby("uf")["taxa_desemprego"].mean().sort_values(ascending=False)
    por_regiao = (
        df.groupby("regiao", observed=True)["taxa_desemprego"].mean().sort_values(ascending=False)
    )
    nomes = df.drop_duplicates("uf").set_index("uf")["estado"]

    return {
        "taxa_media": df["taxa_desemprego"].mean(),
        "taxa_ponderada": df["desempregados"].sum() / df["populacao_ativa"].sum() * 100,
        "uf_maior": por_uf.index[0],
        "uf_maior_nome": nomes[por_uf.index[0]],
        "uf_maior_taxa": por_uf.iloc[0],
        "uf_menor": por_uf.index[-1],
        "uf_menor_nome": nomes[por_uf.index[-1]],
        "uf_menor_taxa": por_uf.iloc[-1],
        "regiao_maior": por_regiao.index[0],
        "regiao_maior_taxa": por_regiao.iloc[0],
        "regiao_menor": por_regiao.index[-1],
        "regiao_menor_taxa": por_regiao.iloc[-1],
        "desempregados_ultimo": ultimo_trim["desempregados"].sum(),
        "ultimo_periodo": ultimo_trim["periodo"].iloc[0],
        "desempregados_total": df["desempregados"].sum(),
        "renda_media": df["renda_media"].mean(),
        "taxa_inicio": por_periodo.iloc[0],
        "taxa_fim": por_periodo.iloc[-1],
        "periodo_inicio": df.loc[df["data"] == por_periodo.index[0], "periodo"].iloc[0],
        "periodo_fim": df.loc[df["data"] == por_periodo.index[-1], "periodo"].iloc[0],
        "variacao_pp": por_periodo.iloc[-1] - por_periodo.iloc[0],
        "inclinacao_anual": _inclinacao_anual(df),
    }


def _inclinacao_anual(df):
    """Tendência linear (pontos percentuais por ano) da taxa média trimestral."""
    serie = df.groupby("data")["taxa_desemprego"].mean()
    if len(serie) < 2:
        return 0.0
    anos = (serie.index - serie.index[0]).days / 365.25
    return float(np.polyfit(anos, serie.values, 1)[0])


def mostrar_kpis(df):
    k = calcular_kpis(df)
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Taxa média de desemprego", fmt_pct(k["taxa_media"]),
        help=f"Média simples das taxas. Ponderada pela população ativa: {fmt_pct(k['taxa_ponderada'])}.",
    )
    c2.metric(
        "Estado com maior desemprego", f"{k['uf_maior']} · {fmt_pct(k['uf_maior_taxa'])}",
        help=k["uf_maior_nome"],
    )
    c3.metric(
        "Região mais afetada", k["regiao_maior"], f"{fmt_pct(k['regiao_maior_taxa'])} de média",
        delta_color="off",
    )
    c4, c5, c6 = st.columns(3)
    c4.metric(
        f"Desempregados ({k['ultimo_periodo']})", fmt_milhoes(k["desempregados_ultimo"]),
        help=(
            "Soma do último trimestre filtrado. Somar todos os trimestres conta a "
            f"mesma pessoa várias vezes: {fmt_milhoes(k['desempregados_total'])} no período."
        ),
    )
    c5.metric("Renda média nacional", fmt_moeda(k["renda_media"], markdown=False))
    c6.metric(
        f"Evolução da taxa ({k['periodo_inicio']} a {k['periodo_fim']})",
        fmt_pct(k["taxa_fim"]),
        f"{fmt_num(k['variacao_pp'], 2)} p.p.",
        delta_color="inverse",
        help=f"Tendência linear: {fmt_num(k['inclinacao_anual'], 2)} p.p. por ano.",
    )
    return k


# ---------------------------------------------------------------------------
# Gráficos Matplotlib / Seaborn
# ---------------------------------------------------------------------------

def _figura(largura=10, altura=4.2):
    fig, ax = plt.subplots(figsize=(largura, altura))
    sns.despine(fig=fig)
    return fig, ax


def grafico_linha_temporal(df):
    """Linha temporal: taxa média nacional + média móvel de 4 trimestres."""
    serie = df.groupby("data")["taxa_desemprego"].mean().sort_index()
    fig, ax = _figura()
    ax.plot(serie.index, serie.values, color=AZUL, lw=2, marker="o", ms=4, label="Taxa média trimestral")
    if len(serie) >= 4:
        movel = serie.rolling(4).mean()
        ax.plot(movel.index, movel.values, color=TINTA_SECUNDARIA, lw=2, ls="--", label="Média móvel (4 trimestres)")
    for inicio, fim, rotulo in [("2015-10-01", "2016-12-31", "Crise 2016"), ("2020-01-01", "2021-12-31", "Pandemia")]:
        ini, fi = pd.Timestamp(inicio), pd.Timestamp(fim)
        if serie.index.min() <= fi and serie.index.max() >= ini:
            ax.axvspan(ini, fi, color="#f0efec", zorder=0)
            ax.text(ini + (fi - ini) / 2, ax.get_ylim()[1], rotulo, ha="center", va="top", fontsize=9, color=TINTA_SECUNDARIA)
    ax.set_title("Evolução da taxa média de desemprego")
    ax.set_xlabel("Trimestre")
    ax.set_ylabel("Taxa de desemprego")
    eixo_pct(ax)
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    return fig


def grafico_linha_regioes(df):
    """Uma linha por região (média anual)."""
    tab = df.groupby(["ano", "regiao"], observed=True)["taxa_desemprego"].mean().reset_index()
    fig, ax = _figura()
    sns.lineplot(
        data=tab, x="ano", y="taxa_desemprego", hue="regiao", palette=CORES_REGIAO,
        hue_order=[r for r in ORDEM_REGIOES if r in tab["regiao"].unique()],
        marker="o", lw=2, ax=ax,
    )
    for regiao, grupo in tab.groupby("regiao", observed=True):
        ultimo = grupo.iloc[-1]
        ax.annotate(regiao, (ultimo["ano"], ultimo["taxa_desemprego"]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9, color=TINTA_SECUNDARIA)
    ax.set_title("Taxa média anual de desemprego por região")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Taxa de desemprego")
    ax.set_xticks(sorted(tab["ano"].unique()))
    eixo_pct(ax)
    ax.legend(title="Região", frameon=False, bbox_to_anchor=(1.12, 1), loc="upper left")
    fig.tight_layout()
    return fig


def grafico_barras_estado(df):
    """Barras horizontais por estado, coloridas pela região."""
    tab = (
        df.groupby(["uf", "regiao"], observed=True)["taxa_desemprego"].mean()
        .reset_index().sort_values("taxa_desemprego", ascending=False)
    )
    media = df["taxa_desemprego"].mean()
    fig, ax = _figura(10, max(3.5, 0.32 * len(tab) + 1))
    cores = tab["regiao"].map(CORES_REGIAO)
    ax.barh(tab["uf"], tab["taxa_desemprego"], color=cores, edgecolor="white", linewidth=1)
    ax.invert_yaxis()
    ax.axvline(media, color=TINTA_SECUNDARIA, ls="--", lw=1.2)
    ax.text(media, -0.8, f" média {fmt_pct(media)}", fontsize=9, color=TINTA_SECUNDARIA, va="bottom")
    for y, v in enumerate(tab["taxa_desemprego"]):
        ax.text(v + 0.1, y, fmt_pct(v), va="center", fontsize=8, color=TINTA_SECUNDARIA)
    alcas = [plt.Rectangle((0, 0), 1, 1, color=CORES_REGIAO[r]) for r in ORDEM_REGIOES if r in set(tab["regiao"])]
    ax.legend(alcas, [r for r in ORDEM_REGIOES if r in set(tab["regiao"])], title="Região",
              frameon=False, loc="lower right")
    ax.set_title("Taxa média de desemprego por estado")
    ax.set_xlabel("Taxa de desemprego")
    ax.set_ylabel("")
    eixo_pct(ax, "x")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def grafico_barras_regiao(df):
    tab = df.groupby("regiao", observed=True)["taxa_desemprego"].mean().sort_values(ascending=False)
    fig, ax = _figura(8, 3.8)
    ax.bar(tab.index.astype(str), tab.values, color=[CORES_REGIAO[r] for r in tab.index],
           edgecolor="white", linewidth=2, width=0.6)
    for x, v in enumerate(tab.values):
        ax.text(x, v + 0.15, fmt_pct(v), ha="center", fontsize=10, color=TINTA)
    ax.axhline(df["taxa_desemprego"].mean(), color=TINTA_SECUNDARIA, ls="--", lw=1.2, label="Média geral")
    ax.set_title("Taxa média de desemprego por região")
    ax.set_ylabel("Taxa de desemprego")
    ax.set_xlabel("")
    eixo_pct(ax)
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False)
    fig.tight_layout()
    return fig


def grafico_dispersao_renda(df):
    fig, ax = _figura(9, 4.6)
    sns.scatterplot(
        data=df, x="renda_media", y="taxa_desemprego", hue="regiao", palette=CORES_REGIAO,
        hue_order=[r for r in ORDEM_REGIOES if r in set(df["regiao"])],
        s=40, alpha=0.75, edgecolor="white", linewidth=0.6, ax=ax,
    )
    if len(df) > 2:
        sns.regplot(data=df, x="renda_media", y="taxa_desemprego", scatter=False,
                    color=TINTA, line_kws={"lw": 2, "ls": "--"}, ax=ax)
    r = df["renda_media"].corr(df["taxa_desemprego"]) if len(df) > 2 else float("nan")
    ax.set_title(f"Renda média x taxa de desemprego (r = {fmt_num(r, 2)})")
    ax.set_xlabel("Renda média mensal")
    ax.set_ylabel("Taxa de desemprego")
    eixo_pct(ax)
    eixo_moeda(ax, "x")
    ax.legend(title="Região", frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    return fig


def grafico_inflacao_desemprego(df):
    """Inflação x desemprego: média anual em dois painéis com o mesmo eixo X."""
    tab = df.groupby("ano")[["taxa_desemprego", "inflacao"]].mean()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5.2), sharex=True)
    sns.despine(fig=fig)
    ax1.plot(tab.index, tab["taxa_desemprego"], color=AZUL, lw=2, marker="o")
    ax1.set_ylabel("Desemprego")
    ax1.set_title("Desemprego e inflação: médias anuais")
    eixo_pct(ax1)
    ax2.plot(tab.index, tab["inflacao"], color="#eb6834", lw=2, marker="o")
    ax2.set_ylabel("Inflação")
    ax2.set_xlabel("Ano")
    ax2.set_xticks(tab.index)
    eixo_pct(ax2)
    fig.tight_layout()
    return fig


def grafico_heatmap_trimestral(df):
    tab = df.pivot_table(index="ano", columns="trimestre", values="taxa_desemprego", aggfunc="mean")
    tab.columns = [f"T{c}" for c in tab.columns]
    fig, ax = plt.subplots(figsize=(7, max(3, 0.42 * len(tab) + 1)))
    sns.heatmap(
        tab, annot=True, fmt=".2f", cmap=CMAP_SEQUENCIAL, linewidths=2, linecolor="white",
        cbar_kws={"label": "Taxa média de desemprego (%)"}, ax=ax,
    )
    ax.set_title("Heatmap trimestral da taxa de desemprego")
    ax.set_xlabel("Trimestre")
    ax.set_ylabel("Ano")
    fig.tight_layout()
    return fig


def grafico_heatmap_regiao_ano(df):
    tab = df.pivot_table(index="regiao", columns="ano", values="taxa_desemprego", aggfunc="mean", observed=True)
    fig, ax = plt.subplots(figsize=(10, 3.4))
    sns.heatmap(tab, annot=True, fmt=".1f", cmap=CMAP_SEQUENCIAL, linewidths=2, linecolor="white",
                cbar_kws={"label": "%"}, ax=ax)
    ax.set_title("Taxa média de desemprego por região e ano")
    ax.set_xlabel("Ano")
    ax.set_ylabel("")
    fig.tight_layout()
    return fig


COLUNAS_CORRELACAO = {
    "taxa_desemprego": "Desemprego",
    "renda_media": "Renda média",
    "inflacao": "Inflação",
    "vagas_formais": "Vagas formais",
    "populacao_ativa": "População ativa",
}


def grafico_correlacao(df):
    corr = df[list(COLUNAS_CORRELACAO)].rename(columns=COLUNAS_CORRELACAO).corr()
    mascara = np.triu(np.ones_like(corr, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(6.5, 5))
    sns.heatmap(corr, mask=mascara, annot=True, fmt=".2f", cmap=CMAP_DIVERGENTE, vmin=-1, vmax=1,
                linewidths=2, linecolor="white", cbar_kws={"label": "Correlação de Pearson"}, ax=ax)
    ax.set_title("Matriz de correlação")
    fig.tight_layout()
    return fig


def grafico_sazonalidade_setor(df):
    tab = df.pivot_table(index="setor_predominante", columns="trimestre",
                         values="taxa_desemprego", aggfunc="mean")
    tab.columns = [f"T{c}" for c in tab.columns]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    sns.heatmap(tab, annot=True, fmt=".2f", cmap=CMAP_SEQUENCIAL, linewidths=2, linecolor="white",
                cbar_kws={"label": "%"}, ax=ax)
    ax.set_title("Sazonalidade: taxa média por setor e trimestre")
    ax.set_xlabel("Trimestre")
    ax.set_ylabel("")
    fig.tight_layout()
    return fig


def grafico_boxplot_setor(df):
    ordem = df.groupby("setor_predominante")["taxa_desemprego"].median().sort_values(ascending=False).index
    fig, ax = _figura(9, 4)
    sns.boxplot(data=df, x="setor_predominante", y="taxa_desemprego", order=ordem,
                color="#86b6ef", linecolor=AZUL_ESCURO, width=0.55, ax=ax)
    ax.set_title("Distribuição da taxa de desemprego por setor predominante")
    ax.set_xlabel("")
    ax.set_ylabel("Taxa de desemprego")
    eixo_pct(ax)
    fig.tight_layout()
    return fig


def grafico_risco(df):
    """Quantidade de registros por nível de risco e região."""
    tab = pd.crosstab(df["regiao"], df["nivel_risco"]).reindex(columns=ORDEM_RISCO, fill_value=0)
    tab = tab.loc[tab.sum(axis=1) > 0]
    fig, ax = _figura(9, 3.8)
    base = np.zeros(len(tab))
    for nivel in ORDEM_RISCO:
        ax.barh(tab.index.astype(str), tab[nivel], left=base, color=CORES_RISCO[nivel],
                edgecolor="white", linewidth=2, label=nivel)
        base += tab[nivel].values
    ax.invert_yaxis()
    ax.set_title("Registros por nível de risco em cada região")
    ax.set_xlabel("Quantidade de registros (estado x trimestre)")
    ax.legend(title="Risco", frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def grafico_renda_regiao(df):
    tab = df.groupby(["ano", "regiao"], observed=True)["renda_media"].mean().reset_index()
    fig, ax = _figura()
    sns.lineplot(data=tab, x="ano", y="renda_media", hue="regiao", palette=CORES_REGIAO,
                 hue_order=[r for r in ORDEM_REGIOES if r in set(tab["regiao"])],
                 marker="o", lw=2, ax=ax)
    ax.set_title("Renda média mensal por região")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Renda média")
    ax.set_xticks(sorted(tab["ano"].unique()))
    eixo_moeda(ax, "y")
    ax.legend(title="Região", frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    return fig


def grafico_desigualdade(df):
    """Diferença (p.p.) entre a região com maior e a com menor taxa, por ano."""
    tab = df.groupby(["ano", "regiao"], observed=True)["taxa_desemprego"].mean().unstack()
    gap = tab.max(axis=1) - tab.min(axis=1)
    fig, ax = _figura(10, 3.4)
    ax.bar(gap.index, gap.values, color=AZUL, edgecolor="white", linewidth=2, width=0.6)
    for x, v in zip(gap.index, gap.values):
        ax.text(x, v + 0.1, fmt_num(v, 1), ha="center", fontsize=9, color=TINTA_SECUNDARIA)
    ax.set_title("Desigualdade regional: diferença entre a maior e a menor taxa regional")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Pontos percentuais")
    ax.set_xticks(gap.index)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Gráficos interativos Plotly
# ---------------------------------------------------------------------------

LAYOUT_PLOTLY = dict(
    font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=TINTA),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=50, b=10),
    hoverlabel=dict(bgcolor="white"),
)


def mapa_uf(df):
    """Mapa coroplético interativo da taxa média por UF (malha do IBGE)."""
    tab = (
        df.groupby(["uf", "estado", "codigo_ibge", "regiao"], observed=True)
        .agg(taxa=("taxa_desemprego", "mean"), renda=("renda_media", "mean"),
             desempregados=("desempregados", "mean"))
        .reset_index()
    )
    tab["codigo_ibge"] = tab["codigo_ibge"].astype(str)
    fig = px.choropleth(
        tab, geojson=carregar_geojson(), locations="codigo_ibge",
        featureidkey="properties.codarea", color="taxa",
        color_continuous_scale=ESCALA_PLOTLY,
        hover_name="estado",
        hover_data={"codigo_ibge": False, "uf": True, "regiao": True,
                    "taxa": ":.2f", "renda": ":,.2f", "desempregados": ":,.0f"},
        labels={"taxa": "Taxa média (%)", "renda": "Renda média (R$)", "uf": "UF",
                "regiao": "Região", "desempregados": "Desempregados (média)"},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_traces(marker_line_color="white", marker_line_width=1)
    fig.update_layout(**LAYOUT_PLOTLY, height=520,
                      title="Taxa média de desemprego por estado (estados sem dados ficam em branco)")
    return fig


def linha_interativa_uf(df, ufs):
    tab = df[df["uf"].isin(ufs)].groupby(["data", "periodo", "uf"])["taxa_desemprego"].mean().reset_index()
    fig = px.line(tab, x="data", y="taxa_desemprego", color="uf", markers=True,
                  hover_data={"periodo": True, "data": False},
                  labels={"data": "Trimestre", "taxa_desemprego": "Taxa (%)", "uf": "UF", "periodo": "Período"},
                  color_discrete_sequence=list(CORES_REGIAO.values()))
    fig.update_traces(line_width=2)
    fig.update_layout(**LAYOUT_PLOTLY, height=420, title="Comparação trimestral entre estados",
                      hovermode="x unified", yaxis_ticksuffix="%")
    return fig


def dispersao_interativa(df, eixo_x):
    rotulos = {"renda_media": "Renda média (R$)", "inflacao": "Inflação (%)",
               "vagas_formais": "Vagas formais", "taxa_desemprego": "Taxa de desemprego (%)",
               "regiao": "Região"}
    fig = px.scatter(
        df, x=eixo_x, y="taxa_desemprego", color="regiao", color_discrete_map=CORES_REGIAO,
        category_orders={"regiao": ORDEM_REGIOES}, hover_name="estado",
        hover_data={"periodo": True, "setor_predominante": True, "nivel_risco": True},
        labels=rotulos, opacity=0.8,
    )
    fig.update_traces(marker=dict(size=9, line=dict(color="white", width=1)))
    fig.update_layout(**LAYOUT_PLOTLY, height=460, title=f"{rotulos[eixo_x]} x taxa de desemprego")
    return fig


# ---------------------------------------------------------------------------
# Textos de interpretação (calculados a partir dos dados filtrados)
# ---------------------------------------------------------------------------

def texto_temporal(df):
    anual = df.groupby("ano")["taxa_desemprego"].mean()
    if len(anual) < 2:
        return "Selecione mais de um ano para avaliar a tendência temporal."
    pico, vale = anual.idxmax(), anual.idxmin()
    k = calcular_kpis(df)
    direcao = "queda" if k["inclinacao_anual"] < 0 else "alta"
    return (
        f"A taxa média anual foi mais alta em **{pico}** ({fmt_pct(anual[pico])}) e mais baixa em "
        f"**{vale}** ({fmt_pct(anual[vale])}). Entre {k['periodo_inicio']} e {k['periodo_fim']} a taxa "
        f"variou **{fmt_num(k['variacao_pp'], 2)} p.p.**, com tendência linear de {direcao} de "
        f"{fmt_num(abs(k['inclinacao_anual']), 2)} p.p. por ano. Os picos coincidem com os períodos "
        "de crise (recessão de 2015 e 2016 e pandemia em 2020 e 2021), seguidos de recuperação."
    )


def texto_crises(df):
    anual = df.groupby("ano")["taxa_desemprego"].mean()
    if len(anual) < 3:
        return ""
    media = anual.mean()
    crise = anual[anual > media + 0.5 * anual.std()]
    recuperacao = ""
    if not crise.empty and crise.index.max() < anual.index.max():
        pico = crise.idxmax()
        fim = anual.index.max()
        recuperacao = (
            f" Depois do pico de {pico}, a taxa recuou {fmt_num(anual[pico] - anual[fim], 2)} p.p. "
            f"até {fim}, sinal de recuperação do mercado de trabalho."
        )
    anos = ", ".join(str(a) for a in crise.index) or "nenhum"
    return (
        f"Anos acima da média do período ({fmt_pct(media)}) em mais de meio desvio padrão, "
        f"considerados de crise: **{anos}**.{recuperacao}"
    )


def texto_regional(df):
    k = calcular_kpis(df)
    diferenca = k["regiao_maior_taxa"] - k["regiao_menor_taxa"]
    return (
        f"O **{k['regiao_maior']}** concentra a maior taxa média ({fmt_pct(k['regiao_maior_taxa'])}) e "
        f"o **{k['regiao_menor']}** a menor ({fmt_pct(k['regiao_menor_taxa'])}): diferença de "
        f"{fmt_num(diferenca, 2)} p.p. Entre os estados, **{k['uf_maior_nome']}** lidera "
        f"({fmt_pct(k['uf_maior_taxa'])}) e **{k['uf_menor_nome']}** tem a menor taxa "
        f"({fmt_pct(k['uf_menor_taxa'])}). A desigualdade regional é estrutural: o ranking das "
        "regiões quase não muda de um ano para outro."
    )


def _forca(r):
    r = abs(r)
    if r < 0.1:
        return "praticamente nula"
    if r < 0.3:
        return "fraca"
    if r < 0.6:
        return "moderada"
    return "forte"


def texto_correlacao(df, variavel, nome):
    if len(df) < 3:
        return ""
    r = df[variavel].corr(df["taxa_desemprego"])
    if abs(r) < 0.1:
        relacao = "relação praticamente nula"
    else:
        relacao = f"relação {'positiva' if r > 0 else 'negativa'} {_forca(r)}"
    return (
        f"Correlação de Pearson entre {nome} e desemprego: **r = {fmt_num(r, 2)}** "
        f"({relacao}). Nesta base simulada, {nome} sozinha não explica a taxa "
        "de desemprego; a região do estado tem peso muito maior."
    )


def texto_sazonalidade(df):
    tab = df.pivot_table(index="setor_predominante", columns="trimestre",
                         values="taxa_desemprego", aggfunc="mean")
    if tab.shape[1] < 2:
        return "Selecione mais de um trimestre para avaliar sazonalidade."
    amplitude = (tab.max(axis=1) - tab.min(axis=1)).sort_values(ascending=False)
    setor = amplitude.index[0]
    trim = tab.loc[setor].idxmax()
    return (
        f"O setor com maior oscilação entre trimestres é **{setor}** "
        f"({fmt_num(amplitude.iloc[0], 2)} p.p. entre o melhor e o pior trimestre), com pico no "
        f"**{trim}º trimestre**. Nos demais setores a variação é menor, o que indica sazonalidade fraca."
    )


def texto_vulneraveis(df):
    setor = df.groupby("setor_predominante")["taxa_desemprego"].mean().sort_values(ascending=False)
    faixa = df.groupby("faixa_renda", observed=True)["taxa_desemprego"].mean().sort_values(ascending=False)
    criticos = df[df["nivel_risco"] == "Crítico"]
    regioes_criticas = criticos["regiao"].value_counts()
    trecho_critico = ""
    if not criticos.empty:
        regiao = regioes_criticas.index[0]
        trecho_critico = (
            f" Dos {len(criticos)} registros em risco **Crítico**, "
            f"{fmt_num(regioes_criticas.iloc[0] / len(criticos) * 100, 0)}% estão no {regiao}."
        )
    return (
        f"Os grupos mais vulneráveis são os estados do Nordeste e do Norte.{trecho_critico} "
        f"Por setor, **{setor.index[0]}** tem a maior taxa média ({fmt_pct(setor.iloc[0])}), "
        f"mas a diferença para o menor ({setor.index[-1]}, {fmt_pct(setor.iloc[-1])}) é pequena. "
        f"Por faixa de renda, a maior taxa está na faixa **{faixa.index[0].replace('$', chr(92) + '$')}** "
        f"({fmt_pct(faixa.iloc[0])})."
    )
