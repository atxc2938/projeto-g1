"""Página: evolução temporal, heatmap trimestral, crises e recuperação."""

import streamlit as st

import utils
import visual as v

df, _ = utils.obter_base()

v.cabecalho("Evolução temporal", "Como a taxa mudou entre 2015 e 2024, quais foram as crises e como foi a recuperação.")
utils.checar_vazio(df)

v.plotly(utils.linha_temporal(df), key="et_linha")
v.insight(utils.texto_temporal(df))

aba_regiao, aba_heatmap, aba_crises, aba_estados = st.tabs(
    ["Por região", "Heatmap trimestral", "Crises e fases", "Comparar estados"])

with aba_regiao:
    v.plotly(utils.linhas_regiao(df), key="et_regioes")
    v.insight("As cinco regiões sobem e descem juntas nas crises, mas mantêm a mesma posição relativa: as crises "
              "afetam o país inteiro, enquanto a diferença entre regiões é estrutural. Clique na legenda para isolar regiões.")

with aba_heatmap:
    col_grafico, col_texto = st.columns([3, 2], gap="large")
    with col_grafico:
        v.pyplot(utils.grafico_heatmap_trimestral(df))
    with col_texto:
        v.insight("Cada linha é um ano e cada coluna um trimestre. Os tons mais claros de 2016 e de 2020 e 2021 "
                  "marcam as crises; os tons escuros a partir de 2022 mostram a recuperação.")

with aba_crises:
    fases = (
        df.groupby("fase_economica")[["taxa_desemprego", "renda_media", "vagas_formais"]].mean()
        .reindex(["Crise 2015-2016", "Pré-pandemia", "Pandemia", "Recuperação"]).dropna().rename_axis("Fase")
    )
    st.dataframe(
        fases, width="stretch",
        column_config={
            "taxa_desemprego": st.column_config.ProgressColumn(
                "Taxa média", format="%.2f%%", min_value=0, max_value=float(max(15, fases["taxa_desemprego"].max()))),
            "renda_media": st.column_config.NumberColumn("Renda média", format="R$ %.2f"),
            "vagas_formais": st.column_config.NumberColumn("Vagas formais", format="localized"),
        },
    )
    texto = utils.texto_crises(df)
    anual = df.groupby("ano")["taxa_desemprego"].mean()
    if len(anual) > 1:
        variacao = anual.diff().dropna()
        texto += (f" Maior alta anual: **{variacao.idxmax()}** (+{utils.fmt_num(variacao.max(), 2)} p.p.); "
                  f"maior queda anual: **{variacao.idxmin()}** ({utils.fmt_num(variacao.min(), 2)} p.p.).")
    v.insight(texto)

with aba_estados:
    ufs = sorted(df["uf"].unique())
    padrao = [u for u in ["CE", "SP", "PR"] if u in ufs] or ufs[:3]
    escolhidos = st.multiselect("Estados para comparar (até 5)", ufs, default=padrao, max_selections=5, key="et_ufs")
    if escolhidos:
        v.plotly(utils.linha_estados(df, escolhidos), key="et_estados")
