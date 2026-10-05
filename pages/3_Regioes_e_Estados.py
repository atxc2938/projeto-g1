"""Página: comparação regional, ranking de estados e mapa interativo."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import utils

df, _ = utils.obter_base()

st.title("Regiões e estados")
st.markdown("Comparação regional, ranking estadual, estados críticos e desigualdade entre regiões.")
utils.checar_vazio(df)

st.subheader("Mapa interativo da taxa média por estado")
st.plotly_chart(utils.mapa_uf(df), width="stretch")
st.caption("Mapa Plotly com a malha oficial do IBGE. Passe o mouse para ver taxa, renda e desempregados.")

col1, col2 = st.columns(2)
with col1:
    fig = utils.grafico_barras_regiao(df)
    st.pyplot(fig)
    plt.close(fig)
with col2:
    fig = utils.grafico_risco(df)
    st.pyplot(fig)
    plt.close(fig)
st.markdown(utils.texto_regional(df))

st.divider()
st.subheader("Comparação entre estados")
fig = utils.grafico_barras_estado(df)
st.pyplot(fig)
plt.close(fig)

st.subheader("Ranking de estados críticos")
ranking = (
    df.groupby(["uf", "estado", "regiao"], observed=True)
    .agg(
        taxa_media=("taxa_desemprego", "mean"),
        taxa_maxima=("taxa_desemprego", "max"),
        trimestres_criticos=("nivel_risco", lambda s: int((s == "Crítico").sum())),
        trimestres=("nivel_risco", "size"),
        renda_media=("renda_media", "mean"),
    )
    .reset_index()
    .sort_values(["trimestres_criticos", "taxa_media"], ascending=False)
)
ranking["pct_critico"] = ranking["trimestres_criticos"] / ranking["trimestres"] * 100
ranking.insert(0, "posição", range(1, len(ranking) + 1))
st.dataframe(
    ranking,
    hide_index=True,
    width="stretch",
    column_config={
        "uf": "UF", "estado": "Estado", "regiao": "Região",
        "taxa_media": st.column_config.NumberColumn("Taxa média (%)", format="%.2f"),
        "taxa_maxima": st.column_config.NumberColumn("Taxa máxima (%)", format="%.2f"),
        "trimestres_criticos": "Trimestres críticos",
        "trimestres": "Trimestres",
        "pct_critico": st.column_config.ProgressColumn("% crítico", format="%.0f%%", min_value=0, max_value=100),
        "renda_media": st.column_config.NumberColumn("Renda média (R$)", format="%.2f"),
    },
)
criticos = ranking[ranking["trimestres_criticos"] > 0]
if not criticos.empty:
    topo = criticos.iloc[0]
    st.markdown(
        f"**{topo['estado']}** passou {topo['trimestres_criticos']} de {topo['trimestres']} trimestres em risco "
        f"Crítico (taxa acima de 14%). {len(criticos)} estados tiveram ao menos um trimestre crítico, "
        f"{(criticos['regiao'] == 'Nordeste').sum()} deles no Nordeste."
    )
else:
    st.markdown("Nenhum estado selecionado teve trimestre em risco Crítico.")

st.divider()
st.subheader("Desigualdade regional")
if df["regiao"].nunique() > 1:
    fig = utils.grafico_heatmap_regiao_ano(df)
    st.pyplot(fig)
    plt.close(fig)
    fig = utils.grafico_desigualdade(df)
    st.pyplot(fig)
    plt.close(fig)
    tab = df.groupby(["ano", "regiao"], observed=True)["taxa_desemprego"].mean().unstack()
    gap = tab.max(axis=1) - tab.min(axis=1)
    ordem_fixa = tab.rank(axis=1).nunique().max() == 1
    st.markdown(
        f"A diferença entre a região com maior e a com menor taxa variou de "
        f"{utils.fmt_num(gap.min(), 1)} a {utils.fmt_num(gap.max(), 1)} p.p. (média de "
        f"{utils.fmt_num(gap.mean(), 1)} p.p.). "
        + ("A ordem das regiões foi a mesma em todos os anos." if ordem_fixa else
           "A ordem entre as regiões mudou em alguns anos.")
    )
else:
    st.info("Selecione mais de uma região para ver a desigualdade regional.")
