"""Página: mapa interativo, comparação regional, ranking de estados e desigualdade."""

import streamlit as st

import utils
import visual as v

df, _ = utils.obter_base()

v.cabecalho("Regiões e estados", "Mapa, comparação regional, ranking estadual e desigualdade entre regiões.")
utils.checar_vazio(df)

ufs = sorted(df["uf"].unique())
nomes = df.drop_duplicates("uf").set_index("uf")["estado"]

aba_mapa, aba_regional, aba_ranking, aba_desigualdade = st.tabs(
    ["Mapa", "Comparação regional", "Ranking de estados", "Desigualdade"])

with aba_mapa:
    col_mapa, col_detalhe = st.columns([3, 2], gap="large")
    with col_mapa:
        animar_mapa = st.toggle("Animar por ano", key="re_animar_mapa")
        evento = st.plotly_chart(
            utils.mapa_uf(df, animar=animar_mapa), width="stretch", theme=None, key="re_mapa",
            config=v.PLOTLY_CONFIG, on_select="ignore" if animar_mapa else "rerun", selection_mode="points",
        )
        st.caption("Clique em um estado para ver o detalhe. Estados fora da base simulada aparecem vazios.")
    clicado = None
    if evento and not animar_mapa:
        pontos = evento.get("selection", {}).get("points", [])
        if pontos and pontos[0].get("customdata"):
            clicado = pontos[0]["customdata"][0]
    if clicado in ufs:
        st.session_state["re_uf"] = clicado
    if st.session_state.get("re_uf") not in ufs:
        st.session_state["re_uf"] = utils.calcular_kpis(df)["uf_maior"]
    with col_detalhe:
        uf = st.selectbox("Estado em destaque", ufs, key="re_uf", format_func=lambda u: f"{nomes[u]} ({u})")
        do_estado = df[df["uf"] == uf]
        ranking = df.groupby("uf")["taxa_desemprego"].mean().rank(ascending=False, method="min")
        v.cartoes_kpi([
            dict(rotulo="Taxa média", valor=do_estado["taxa_desemprego"].mean(), sufixo="%",
                 apoio=f"{int(ranking[uf])}º de {len(ranking)} no ranking"),
            dict(rotulo="Trimestres críticos", valor=int((do_estado["nivel_risco"] == "Crítico").sum()), casas=0,
                 apoio=f"de {len(do_estado)} trimestres"),
            dict(rotulo="Renda média", prefixo="R$", valor=do_estado["renda_media"].mean(),
                 apoio=str(do_estado["regiao"].iloc[0])),
        ])
        v.plotly(utils.detalhe_estado(df, uf), key="re_detalhe")

with aba_regional:
    col1, col2 = st.columns(2, gap="large")
    with col1:
        v.plotly(utils.barras_regiao(df), key="re_regiao")
    with col2:
        v.plotly(utils.risco_regiao(df), key="re_risco")
    v.insight(utils.texto_regional(df))

with aba_ranking:
    animar_ranking = st.toggle("Animar por ano", key="re_animar_ranking",
                               help="Corrida do ranking: as barras se reordenam a cada ano.")
    v.plotly(utils.ranking_estados(df, animar=animar_ranking), key="re_ranking")
    tabela = (
        df.groupby(["uf", "estado", "regiao"], observed=True)
        .agg(taxa_media=("taxa_desemprego", "mean"), taxa_maxima=("taxa_desemprego", "max"),
             trimestres_criticos=("nivel_risco", lambda s: int((s == "Crítico").sum())),
             trimestres=("nivel_risco", "size"), renda_media=("renda_media", "mean"))
        .reset_index().sort_values(["trimestres_criticos", "taxa_media"], ascending=False)
    )
    tabela["pct_critico"] = tabela["trimestres_criticos"] / tabela["trimestres"] * 100
    tabela.insert(0, "posicao", range(1, len(tabela) + 1))
    v.secao("Ranking de estados críticos", "Ordenado pelo número de trimestres com taxa acima de 14% (risco Crítico).")
    st.dataframe(
        tabela, hide_index=True, width="stretch",
        column_config={
            "posicao": st.column_config.NumberColumn("#", width="small"),
            "uf": "UF", "estado": "Estado", "regiao": "Região",
            "taxa_media": st.column_config.NumberColumn("Taxa média", format="%.2f%%"),
            "taxa_maxima": st.column_config.NumberColumn("Taxa máxima", format="%.2f%%"),
            "trimestres_criticos": "Trimestres críticos", "trimestres": "Trimestres",
            "pct_critico": st.column_config.ProgressColumn("% crítico", format="%.0f%%", min_value=0, max_value=100),
            "renda_media": st.column_config.NumberColumn("Renda média", format="R$ %.2f"),
        },
    )
    com_critico = tabela[tabela["trimestres_criticos"] > 0]
    if not com_critico.empty:
        topo = com_critico.iloc[0]
        v.insight(f"**{topo['estado']}** passou {topo['trimestres_criticos']} de {topo['trimestres']} trimestres em "
                  f"risco Crítico. {len(com_critico)} estados tiveram ao menos um trimestre crítico, "
                  f"{(com_critico['regiao'] == 'Nordeste').sum()} deles no Nordeste.")
    else:
        v.insight("Nenhum estado selecionado teve trimestre em risco Crítico.")

with aba_desigualdade:
    if df["regiao"].nunique() > 1:
        v.pyplot(utils.grafico_heatmap_regiao_ano(df))
        v.pyplot(utils.grafico_desigualdade(df))
        tab = df.groupby(["ano", "regiao"], observed=True)["taxa_desemprego"].mean().unstack()
        gap = tab.max(axis=1) - tab.min(axis=1)
        ordem_fixa = tab.rank(axis=1).nunique().max() == 1
        v.insight(
            f"A diferença entre a região com maior e a com menor taxa variou de {utils.fmt_num(gap.min(), 1)} a "
            f"{utils.fmt_num(gap.max(), 1)} p.p. (média de {utils.fmt_num(gap.mean(), 1)} p.p.). "
            + ("A ordem das regiões foi a mesma em todos os anos." if ordem_fixa else
               "A ordem entre as regiões mudou em alguns anos."))
    else:
        v.insight("Selecione mais de uma região para ver a desigualdade regional.")
