"""Funções compartilhadas pelo dashboard: carga de dados, filtros, KPIs,
gráficos e textos de interpretação.

O banco SQLite (database/desemprego.sqlite) e o CSV tratado são gerados pelo
notebook notebooks/analise_desemprego.ipynb. O visual (tema escuro, CSS,
template do Plotly e componentes) fica em visual.py.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st
from plotly.subplots import make_subplots
from sqlalchemy import create_engine

import visual as v

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CAMINHO_CSV = BASE_DIR / "dados" / "simulacao_desemprego_brasil.csv"
CAMINHO_TRATADO = BASE_DIR / "dados" / "simulacao_desemprego_brasil_tratado.csv"
CAMINHO_GEOJSON = BASE_DIR / "dados" / "br_uf.geojson"
CAMINHO_BANCO = BASE_DIR / "database" / "desemprego.sqlite"

# ---------------------------------------------------------------------------
# Categorias e cores (as cores vêm de visual.py, ordem fixa por entidade)
# ---------------------------------------------------------------------------
ORDEM_REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
ORDEM_RISCO = ["Baixo", "Médio", "Alto", "Crítico"]
ORDEM_FAIXAS_RENDA = ["Até R$ 2 mil", "R$ 2 a 3 mil", "R$ 3 a 4 mil", "Acima de R$ 4 mil"]
ORDEM_SETORES = ["Agropecuária", "Comércio", "Construção", "Indústria", "Serviços"]
CORES_REGIAO = v.CORES_REGIAO
CORES_RISCO = v.CORES_RISCO
CMAP_SEQUENCIAL = v.CMAP_SEQUENCIAL
CRISES = [("2015-10-01", "2016-12-31", "Crise 2016"), ("2020-01-01", "2021-12-31", "Pandemia")]

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


def anotacoes(tab, casas=2):
    """Valores dos heatmaps no formato brasileiro (vírgula decimal)."""
    return tab.map(lambda v: "" if pd.isna(v) else fmt_num(v, casas)).values


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
    st.sidebar.markdown("#### Filtros")

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
    st.sidebar.caption(f"{len(df_filtrado)} de {len(df)} registros selecionados")
    return df_filtrado


def obter_base():
    """Base filtrada guardada pelo app.py para as páginas."""
    return st.session_state["df_filtrado"], st.session_state["df_completo"]


def checar_vazio(df):
    if df.empty:
        st.warning("Nenhum registro atende aos filtros escolhidos. Ajuste os filtros na barra lateral "
                   "ou use Limpar filtros.")
        st.stop()



# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

def calcular_kpis(df):
    """KPIs do Tema 04 (e a mediana, como curiosidade) calculados sobre a base filtrada."""
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
        "mediana": df["taxa_desemprego"].median(),
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
    """Seis cartões com os KPIs obrigatórios; a mediana aparece como curiosidade no primeiro."""
    k = calcular_kpis(df)
    melhorou = k["variacao_pp"] < 0
    seta = (f'<span class="{"pos" if melhorou else "neg"}">{"▼" if melhorou else "▲"} '
            f'{fmt_num(abs(k["variacao_pp"]), 2)} p.p.</span>')
    v.cartoes_kpi([
        dict(rotulo="Taxa média de desemprego", valor=k["taxa_media"], sufixo="%",
             apoio=f"Mediana <b>{fmt_pct(k['mediana'])}</b> (curiosidade)"),
        dict(rotulo="Estado com maior desemprego", prefixo=k["uf_maior"], valor=k["uf_maior_taxa"], sufixo="%",
             apoio=f"{k['uf_maior_nome']}"),
        dict(rotulo="Região mais afetada", texto=k["regiao_maior"],
             apoio=f"<b>{fmt_pct(k['regiao_maior_taxa'])}</b> de taxa média"),
        dict(rotulo="Total de desempregados", valor=k["desempregados_total"] / 1e6, sufixo="mi",
             apoio=f"<b>{fmt_milhoes(k['desempregados_ultimo'])}</b> em {k['ultimo_periodo']}"),
        dict(rotulo="Renda média nacional", prefixo="R$", valor=k["renda_media"], apoio="Média salarial mensal"),
        dict(rotulo="Evolução da taxa", valor=k["taxa_fim"], sufixo="%",
             apoio=f"{seta} desde {k['periodo_inicio']}"),
    ])
    return k


def _regiao_de(df, uf):
    return str(df.loc[df["uf"] == uf, "regiao"].iloc[0])


# ---------------------------------------------------------------------------
# Gráficos interativos Plotly (animações, hover e transições)
# ---------------------------------------------------------------------------

def _regioes_presentes(df):
    return [r for r in ORDEM_REGIOES if r in set(df["regiao"].astype(str))]


def linha_temporal(df, estatistica="Média"):
    """Linha temporal da taxa (média ou mediana) com média móvel, crises e range slider."""
    agregacao = "median" if estatistica == "Mediana" else "mean"
    serie = (df.groupby(["data", "periodo"])["taxa_desemprego"].agg(agregacao)
             .reset_index().sort_values("data"))
    serie["movel"] = serie["taxa_desemprego"].rolling(4).mean()
    fig = go.Figure()
    for inicio, fim, rotulo in CRISES:
        ini, fi = pd.Timestamp(inicio), pd.Timestamp(fim)
        if serie["data"].min() <= fi and serie["data"].max() >= ini:
            fig.add_vrect(x0=ini, x1=fi, fillcolor="rgba(255,255,255,0.045)", line_width=0, layer="below",
                          annotation_text=rotulo, annotation_position="top left",
                          annotation_font=dict(color=v.TEXTO_3, size=11))
    fig.add_trace(go.Scatter(
        x=serie["data"], y=serie["taxa_desemprego"], name=f"{estatistica} trimestral", mode="lines+markers",
        line=dict(color=v.AZUL, width=3, shape="spline", smoothing=0.5),
        marker=dict(size=7, color=v.AZUL, line=dict(color=v.FUNDO, width=1.5)),
        customdata=serie["periodo"], hovertemplate="%{customdata}: <b>%{y:.2f}%</b><extra></extra>",
    ))
    if len(serie) >= 4:
        fig.add_trace(go.Scatter(
            x=serie["data"], y=serie["movel"], name="Média móvel (4 trimestres)", mode="lines",
            line=dict(color=v.TEXTO_2, width=2, dash="dot"),
            hovertemplate="Média móvel: %{y:.2f}%<extra></extra>",
        ))
    referencia = df["taxa_desemprego"].agg(agregacao)
    fig.add_hline(y=referencia, line=dict(color=v.TEXTO_3, width=1, dash="dash"),
                  annotation_text=f"{estatistica} do período: {fmt_pct(referencia)}",
                  annotation_position="bottom right", annotation_font=dict(color=v.TEXTO_2, size=12))
    fig.update_layout(
        title=f"Evolução da {estatistica.lower()} da taxa de desemprego",
        hovermode="x unified", legend=dict(orientation="h"),
        yaxis=dict(ticksuffix="%", title=None),
        xaxis=dict(title=None, rangeslider=dict(visible=True, thickness=0.07, bgcolor=v.CARTAO, bordercolor=v.BORDA)),
    )
    return v.finalizar(fig, 470)


def barras_regiao(df, animar=False):
    """Barras por região (comparação nacional), com opção de animação ano a ano."""
    regioes = _regioes_presentes(df)
    if animar:
        tab = (df.groupby(["ano", "regiao"], observed=True)["taxa_desemprego"].mean().reset_index())
        tab["regiao"] = tab["regiao"].astype(str)
        fig = px.bar(tab, x="regiao", y="taxa_desemprego", color="regiao", animation_frame="ano",
                     color_discrete_map=CORES_REGIAO, category_orders={"regiao": regioes},
                     range_y=[0, tab["taxa_desemprego"].max() * 1.18], text="taxa_desemprego",
                     labels={"regiao": "Região", "taxa_desemprego": "Taxa média (%)", "ano": "Ano"})
        fig.update_traces(texttemplate="%{y:.2f}%", textposition="outside", cliponaxis=False,
                          marker_line_width=0, hovertemplate="%{x}: <b>%{y:.2f}%</b><extra></extra>")
        for quadro in fig.frames:
            for trace in quadro.data:
                trace.update(texttemplate="%{y:.2f}%", textposition="outside")
        fig.update_layout(title="Taxa média por região, ano a ano (aperte ▶)", showlegend=False,
                          yaxis=dict(ticksuffix="%", title=None), xaxis=dict(title=None))
        return v.finalizar(fig, 470)

    tab = df.groupby("regiao", observed=True)["taxa_desemprego"].mean().sort_values(ascending=False)
    fig = go.Figure(go.Bar(
        x=tab.index.astype(str), y=tab.values, marker=dict(color=[CORES_REGIAO[r] for r in tab.index],
                                                           cornerradius=8),
        text=tab.values, texttemplate="<b>%{y:.2f}%</b>", textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: <b>%{y:.2f}%</b><extra></extra>",
    ))
    media = df["taxa_desemprego"].mean()
    fig.add_hline(y=media, line=dict(color=v.TEXTO_2, dash="dash", width=1.2),
                  annotation_text=f"Média nacional {fmt_pct(media)}", annotation_font=dict(color=v.TEXTO_2))
    fig.update_layout(title="Taxa média de desemprego por região", showlegend=False,
                      yaxis=dict(ticksuffix="%", title=None, range=[0, tab.max() * 1.18]), xaxis=dict(title=None))
    return v.finalizar(fig, 420)


def ranking_estados(df, animar=False):
    """Barras por estado. Animado: corrida de barras que se reordena a cada ano."""
    if animar:
        tab = df.groupby(["ano", "uf", "estado", "regiao"], observed=True)["taxa_desemprego"].mean().reset_index()
        tab["regiao"] = tab["regiao"].astype(str)
        tab["posicao"] = tab.groupby("ano")["taxa_desemprego"].rank(ascending=False, method="first")
        n = tab["uf"].nunique()
        fig = px.bar(tab, x="taxa_desemprego", y="posicao", color="regiao", orientation="h",
                     animation_frame="ano", animation_group="uf", text="uf", hover_name="estado",
                     color_discrete_map=CORES_REGIAO, category_orders={"regiao": _regioes_presentes(df)},
                     range_x=[0, tab["taxa_desemprego"].max() * 1.12],
                     labels={"taxa_desemprego": "Taxa média (%)", "posicao": "Posição", "regiao": "Região", "ano": "Ano"})
        fig.update_traces(texttemplate="<b>%{text}</b>  %{x:.1f}%", textposition="inside", insidetextanchor="start",
                          textfont=dict(color="white", size=12), marker_line_width=0,
                          hovertemplate="<b>%{hovertext}</b><br>Taxa: %{x:.2f}%<br>Posição: %{y}º<extra></extra>")
        for quadro in fig.frames:
            for trace in quadro.data:
                trace.update(texttemplate="<b>%{text}</b>  %{x:.1f}%", textposition="inside", insidetextanchor="start")
        fig.update_layout(title="Corrida do ranking estadual (aperte ▶)",
                          yaxis=dict(autorange="reversed", showticklabels=False, title=None, range=[n + 0.5, 0.5]),
                          xaxis=dict(ticksuffix="%", title=None), legend=dict(orientation="h"),
                          bargap=0.15)
        return v.finalizar(fig, max(460, 30 * n + 170))

    tab = (df.groupby(["uf", "estado", "regiao"], observed=True)["taxa_desemprego"].mean()
           .reset_index().sort_values("taxa_desemprego"))
    tab["regiao"] = tab["regiao"].astype(str)
    fig = go.Figure()
    for regiao in _regioes_presentes(df):
        parte = tab[tab["regiao"] == regiao]
        fig.add_trace(go.Bar(
            x=parte["taxa_desemprego"], y=parte["uf"], orientation="h", name=regiao,
            marker=dict(color=CORES_REGIAO[regiao], cornerradius=6), customdata=parte[["estado", "uf"]],
            text=parte["taxa_desemprego"], texttemplate="%{x:.2f}%", textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{customdata[0]}</b><br>Taxa média: %{x:.2f}%<extra></extra>",
        ))
    media = df["taxa_desemprego"].mean()
    fig.add_vline(x=media, line=dict(color=v.TEXTO_2, dash="dash", width=1.2),
                  annotation_text=f"média {fmt_pct(media)}", annotation_font=dict(color=v.TEXTO_2))
    fig.update_layout(title="Taxa média de desemprego por estado (clique numa barra para detalhar)",
                      barmode="overlay", bargap=0.25,
                      yaxis=dict(categoryorder="array", categoryarray=tab["uf"].tolist(), title=None),
                      xaxis=dict(ticksuffix="%", title=None, range=[0, tab["taxa_desemprego"].max() * 1.12]),
                      legend=dict(orientation="h"))
    return v.finalizar(fig, max(420, 26 * len(tab) + 140))


def mapa_uf(df, animar=False):
    """Mapa coroplético da taxa média por estado; animado ano a ano ou clicável."""
    escala = ["#1c3358", "#1c5cab", "#3987e5", "#86b6ef", "#e3efff"]
    if animar:
        tab = (df.groupby(["ano", "uf", "estado", "codigo_ibge"], observed=True)["taxa_desemprego"].mean()
               .reset_index())
    else:
        tab = (df.groupby(["uf", "estado", "codigo_ibge", "regiao"], observed=True)
               .agg(taxa_desemprego=("taxa_desemprego", "mean"), renda_media=("renda_media", "mean"))
               .reset_index())
    tab["codigo_ibge"] = tab["codigo_ibge"].astype(str)
    faixa = [df.groupby(["ano", "uf"])["taxa_desemprego"].mean().min(),
             df.groupby(["ano", "uf"])["taxa_desemprego"].mean().max()] if animar else None
    fig = px.choropleth(
        tab, geojson=carregar_geojson(), locations="codigo_ibge", featureidkey="properties.codarea",
        color="taxa_desemprego", color_continuous_scale=escala, range_color=faixa,
        animation_frame="ano" if animar else None, hover_name="estado", custom_data=["uf"],
        labels={"taxa_desemprego": "Taxa (%)", "ano": "Ano"},
    )
    fig.update_traces(marker_line_color=v.FUNDO, marker_line_width=1.2,
                      hovertemplate="<b>%{hovertext}</b><br>Taxa média: %{z:.2f}%<extra></extra>")
    if animar:
        for quadro in fig.frames:
            for trace in quadro.data:
                trace.update(hovertemplate="<b>%{hovertext}</b><br>Taxa média: %{z:.2f}%<extra></extra>")
    fig.update_geos(visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator",
                    lataxis_range=[-34.5, 6], lonaxis_range=[-75, -33], center=dict(lat=-14, lon=-53))
    fig.update_layout(
        title="Taxa média de desemprego por estado" + (" ano a ano (aperte ▶)" if animar else " (clique num estado)"),
        coloraxis_colorbar=dict(title="Taxa", ticksuffix="%", thickness=14, len=0.75),
        margin=dict(l=0, r=0, t=56, b=0), clickmode="event+select",
    )
    return v.finalizar(fig, 560)


def dispersao(df, eixo_x="renda_media", animar=False):
    """Dispersão de uma variável econômica contra a taxa (bolha = população ativa)."""
    rotulos = {"renda_media": "Renda média (R$)", "inflacao": "Inflação (%)", "vagas_formais": "Vagas formais",
               "taxa_desemprego": "Taxa de desemprego (%)", "regiao": "Região", "populacao_ativa": "População ativa",
               "ano": "Ano"}
    base = df.copy()
    base["regiao"] = base["regiao"].astype(str)
    regioes = _regioes_presentes(df)
    margem_x = (base[eixo_x].max() - base[eixo_x].min()) * 0.05
    fig = px.scatter(
        base, x=eixo_x, y="taxa_desemprego", color="regiao", symbol="regiao", size="populacao_ativa",
        size_max=18 if animar else 11, color_discrete_map=CORES_REGIAO, symbol_map=v.SIMBOLOS_REGIAO,
        category_orders={"regiao": regioes}, hover_name="estado",
        hover_data={"periodo": True, "setor_predominante": True, "populacao_ativa": ":,.0f", "regiao": False},
        animation_frame="ano" if animar else None, animation_group="uf" if animar else None,
        range_x=[base[eixo_x].min() - margem_x, base[eixo_x].max() + margem_x],
        range_y=[0, base["taxa_desemprego"].max() * 1.08], labels=rotulos, opacity=0.85 if animar else 0.7,
    )
    fig.update_traces(marker=dict(line=dict(color=v.FUNDO, width=1)))
    r = base[eixo_x].corr(base["taxa_desemprego"]) if len(base) > 2 else float("nan")
    if not animar and len(base) > 2:
        a, b = np.polyfit(base[eixo_x], base["taxa_desemprego"], 1)
        xs = np.linspace(base[eixo_x].min(), base[eixo_x].max(), 50)
        fig.add_trace(go.Scatter(x=xs, y=a * xs + b, mode="lines", name="Tendência linear",
                                 line=dict(color=v.TEXTO, width=2, dash="dash"), hoverinfo="skip"))
    fig.update_layout(
        title=f"{rotulos[eixo_x]} x taxa de desemprego (r = {fmt_num(r, 2)})" + (" · aperte ▶" if animar else ""),
        yaxis=dict(ticksuffix="%"), legend=dict(orientation="h"),
    )
    if eixo_x == "renda_media":
        fig.update_xaxes(tickprefix="R$ ")
    return v.finalizar(fig, 520)


def linhas_regiao(df):
    tab = df.groupby(["ano", "regiao"], observed=True)["taxa_desemprego"].mean().reset_index()
    tab["regiao"] = tab["regiao"].astype(str)
    fig = go.Figure()
    for regiao in _regioes_presentes(df):
        parte = tab[tab["regiao"] == regiao]
        fig.add_trace(go.Scatter(
            x=parte["ano"], y=parte["taxa_desemprego"], name=regiao, mode="lines+markers",
            line=dict(color=CORES_REGIAO[regiao], width=3, shape="spline", smoothing=0.5),
            marker=dict(size=7, symbol=v.SIMBOLOS_REGIAO[regiao], line=dict(color=v.FUNDO, width=1)),
            hovertemplate=f"{regiao}: <b>%{{y:.2f}}%</b><extra></extra>",
        ))
        fig.add_annotation(x=parte["ano"].iloc[-1], y=parte["taxa_desemprego"].iloc[-1], text=f"<b>{regiao}</b>",
                           xanchor="left", xshift=10, showarrow=False, font=dict(color=CORES_REGIAO[regiao], size=12))
    fig.update_layout(title="Taxa média anual por região", hovermode="x unified",
                      yaxis=dict(ticksuffix="%", title=None), xaxis=dict(dtick=1, title=None),
                      legend=dict(orientation="h"), margin=dict(r=110))
    return v.finalizar(fig, 450)


def linha_estados(df, ufs):
    tab = df[df["uf"].isin(ufs)].groupby(["data", "periodo", "uf"])["taxa_desemprego"].mean().reset_index()
    paleta = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"]
    fig = px.line(tab, x="data", y="taxa_desemprego", color="uf", markers=True, line_shape="spline",
                  custom_data=["periodo"], color_discrete_sequence=paleta,
                  labels={"data": "Trimestre", "taxa_desemprego": "Taxa (%)", "uf": "UF"})
    fig.update_traces(line_width=2.6, marker_size=6,
                      hovertemplate="%{fullData.name}: <b>%{y:.2f}%</b><extra></extra>")
    fig.update_layout(title="Comparação trimestral entre estados", hovermode="x unified",
                      yaxis=dict(ticksuffix="%", title=None), xaxis=dict(title=None),
                      legend=dict(orientation="h"))
    return v.finalizar(fig, 440)


def inflacao_desemprego(df):
    """Dois painéis com o mesmo eixo de tempo (sem eixo duplo)."""
    tab = df.groupby("ano")[["taxa_desemprego", "inflacao"]].mean()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=("Desemprego (média anual)", "Inflação (média anual)"))
    fig.add_trace(go.Scatter(x=tab.index, y=tab["taxa_desemprego"], name="Desemprego", mode="lines+markers",
                             line=dict(color=v.AZUL, width=3, shape="spline", smoothing=0.5), marker=dict(size=8),
                             hovertemplate="Desemprego: <b>%{y:.2f}%</b><extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=tab.index, y=tab["inflacao"], name="Inflação", mode="lines+markers",
                             line=dict(color=v.LARANJA, width=3, shape="spline", smoothing=0.5), marker=dict(size=8),
                             hovertemplate="Inflação: <b>%{y:.2f}%</b><extra></extra>"), row=2, col=1)
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(dtick=1)
    fig.update_annotations(font=dict(color=v.TEXTO_2, size=13))
    fig.update_layout(hovermode="x unified", showlegend=False, margin=dict(t=40))
    return v.finalizar(fig, 500)


def renda_regiao(df):
    tab = df.groupby(["ano", "regiao"], observed=True)["renda_media"].mean().reset_index()
    tab["regiao"] = tab["regiao"].astype(str)
    fig = px.line(tab, x="ano", y="renda_media", color="regiao", markers=True, line_shape="spline",
                  color_discrete_map=CORES_REGIAO, category_orders={"regiao": _regioes_presentes(df)},
                  labels={"ano": "Ano", "renda_media": "Renda média (R$)", "regiao": "Região"})
    fig.update_traces(line_width=2.6, hovertemplate="%{fullData.name}: <b>R$ %{y:,.2f}</b><extra></extra>")
    fig.update_layout(title="Renda média mensal por região", hovermode="x unified",
                      yaxis=dict(tickprefix="R$ ", title=None), xaxis=dict(dtick=1, title=None),
                      legend=dict(orientation="h"))
    return v.finalizar(fig, 430)


def risco_regiao(df):
    tab = pd.crosstab(df["regiao"], df["nivel_risco"]).reindex(columns=ORDEM_RISCO, fill_value=0)
    tab = tab.loc[tab.sum(axis=1) > 0]
    fig = go.Figure()
    for nivel in ORDEM_RISCO:
        fig.add_trace(go.Bar(
            y=tab.index.astype(str), x=tab[nivel], name=nivel, orientation="h",
            marker=dict(color=CORES_RISCO[nivel], line=dict(color=v.FUNDO, width=2)),
            text=tab[nivel].where(tab[nivel] > 0), texttemplate="%{x}", textposition="inside",
            textfont=dict(color="#0b0b0b"),
            hovertemplate=f"%{{y}} · {nivel}: <b>%{{x}}</b> registros<extra></extra>",
        ))
    fig.update_layout(title="Registros por nível de risco em cada região", barmode="stack",
                      yaxis=dict(autorange="reversed", title=None), xaxis=dict(title="Registros (estado x trimestre)"),
                      legend=dict(orientation="h"))
    return v.finalizar(fig, 380)


def detalhe_estado(df, uf):
    """Série do estado escolhido comparada com a média dos demais estados filtrados."""
    estado = df[df["uf"] == uf].groupby(["data", "periodo"])["taxa_desemprego"].mean().reset_index()
    resto = df[df["uf"] != uf].groupby("data")["taxa_desemprego"].mean()
    regiao = _regiao_de(df, uf)
    fig = go.Figure()
    if not resto.empty:
        fig.add_trace(go.Scatter(x=resto.index, y=resto.values, name="Média dos outros estados", mode="lines",
                                 line=dict(color=v.TEXTO_3, width=2, dash="dot"),
                                 hovertemplate="Outros: %{y:.2f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=estado["data"], y=estado["taxa_desemprego"], name=uf, mode="lines+markers",
                             line=dict(color=CORES_REGIAO[regiao], width=3, shape="spline", smoothing=0.5),
                             fill="tonexty" if not resto.empty else None, fillcolor="rgba(57,135,229,0.06)",
                             customdata=estado["periodo"],
                             hovertemplate="%{customdata}: <b>%{y:.2f}%</b><extra></extra>"))
    fig.update_layout(hovermode="x unified", yaxis=dict(ticksuffix="%", title=None), xaxis=dict(title=None),
                      legend=dict(orientation="h"), margin=dict(t=30))
    return v.finalizar(fig, 330)


# ---------------------------------------------------------------------------
# Gráficos estatísticos Matplotlib / Seaborn (tema escuro de visual.py)
# ---------------------------------------------------------------------------

def _heatmap(tab, casas, titulo, rotulo_barra, largura=8, altura=None, xlabel="", ylabel=""):
    altura = altura or max(3.2, 0.48 * len(tab) + 1.4)
    fig, ax = plt.subplots(figsize=(largura, altura))
    sns.heatmap(tab, annot=anotacoes(tab, casas), fmt="", cmap=CMAP_SEQUENCIAL, linewidths=2.5,
                linecolor=v.CARTAO, annot_kws={"fontsize": 10.5, "fontweight": "bold"},
                cbar_kws={"label": rotulo_barra, "shrink": 0.85}, ax=ax)
    ax.set_title(titulo, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(length=0)
    ax.collections[0].colorbar.outline.set_visible(False)
    fig.tight_layout()
    return fig


def grafico_heatmap_trimestral(df):
    tab = df.pivot_table(index="ano", columns="trimestre", values="taxa_desemprego", aggfunc="mean")
    tab.columns = [f"T{c}" for c in tab.columns]
    return _heatmap(tab, 2, "", "Taxa média (%)", largura=7.5,
                    xlabel="Trimestre", ylabel="Ano")


def grafico_heatmap_regiao_ano(df):
    tab = df.pivot_table(index="regiao", columns="ano", values="taxa_desemprego", aggfunc="mean", observed=True)
    return _heatmap(tab, 1, "Taxa média por região e ano (%)", "%", largura=12, altura=3.6)


def grafico_sazonalidade_setor(df):
    tab = df.pivot_table(index="setor_predominante", columns="trimestre", values="taxa_desemprego", aggfunc="mean")
    tab.columns = [f"T{c}" for c in tab.columns]
    return _heatmap(tab, 2, "Taxa média por setor e trimestre (%)", "%", largura=7.5,
                    altura=4.2, xlabel="Trimestre")


COLUNAS_CORRELACAO = {
    "taxa_desemprego": "Desemprego", "renda_media": "Renda média", "inflacao": "Inflação",
    "vagas_formais": "Vagas formais", "populacao_ativa": "População ativa",
}


def grafico_correlacao(df):
    corr = df[list(COLUNAS_CORRELACAO)].rename(columns=COLUNAS_CORRELACAO).corr()
    mascara = np.triu(np.ones_like(corr, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(7, 5.4))
    sns.heatmap(corr, mask=mascara, annot=anotacoes(corr, 2), fmt="", cmap=v.CMAP_DIVERGENTE, vmin=-1, vmax=1,
                linewidths=2.5, linecolor=v.CARTAO, annot_kws={"fontsize": 11, "fontweight": "bold"},
                cbar_kws={"label": "Correlação de Pearson", "shrink": 0.85}, ax=ax)
    ax.set_title("Matriz de correlação", loc="left")
    ax.tick_params(length=0)
    ax.collections[0].colorbar.outline.set_visible(False)
    fig.tight_layout()
    return fig


def grafico_boxplot_setor(df):
    ordem = df.groupby("setor_predominante")["taxa_desemprego"].median().sort_values(ascending=False).index
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    sns.boxplot(data=df, x="setor_predominante", y="taxa_desemprego", order=ordem, width=0.55,
                color="#1c4b8a", linecolor=v.AZUL_CLARO, linewidth=1.4,
                flierprops=dict(marker="o", markerfacecolor=v.LARANJA, markeredgecolor=v.LARANJA, markersize=4), ax=ax)
    sns.stripplot(data=df, x="setor_predominante", y="taxa_desemprego", order=ordem, color=v.AZUL_CLARO,
                  alpha=0.18, size=2.5, jitter=0.22, ax=ax)
    ax.set_title("Distribuição da taxa por setor predominante", loc="left")
    ax.set_xlabel("")
    ax.set_ylabel("Taxa de desemprego")
    eixo_pct(ax)
    sns.despine(fig=fig, left=True, bottom=True)
    fig.tight_layout()
    return fig


def grafico_desigualdade(df):
    """Diferença (p.p.) entre a região com maior e a com menor taxa, por ano."""
    tab = df.groupby(["ano", "regiao"], observed=True)["taxa_desemprego"].mean().unstack()
    gap = tab.max(axis=1) - tab.min(axis=1)
    fig, ax = plt.subplots(figsize=(12, 3.6))
    barras = ax.bar(gap.index, gap.values, color=v.AZUL, width=0.62, zorder=3)
    destaque = gap.idxmax()
    barras[list(gap.index).index(destaque)].set_color(v.LARANJA)
    for x, valor in zip(gap.index, gap.values):
        ax.text(x, valor + 0.12, fmt_num(valor, 1), ha="center", fontsize=10.5, color=v.TEXTO, fontweight="bold")
    ax.set_title("Desigualdade regional: maior menos menor taxa regional (p.p.)", loc="left")
    ax.set_xticks(gap.index)
    ax.set_ylim(0, gap.max() * 1.22)
    ax.grid(axis="x", visible=False)
    sns.despine(fig=fig, left=True, bottom=True)
    fig.tight_layout()
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
