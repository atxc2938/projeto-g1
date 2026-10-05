"""Página: evolução temporal, heatmap trimestral, crises e recuperação."""

import matplotlib.pyplot as plt
import streamlit as st

import utils

df, _ = utils.obter_base()

st.title("Evolução temporal")
st.markdown(
    "Como a taxa de desemprego mudou entre 2015 e 2024, quais foram os períodos de crise e como "
    "foi a recuperação."
)
utils.checar_vazio(df)

st.subheader("Linha temporal da taxa média")
fig = utils.grafico_linha_temporal(df)
st.pyplot(fig)
plt.close(fig)
st.markdown(utils.texto_temporal(df))

st.subheader("Evolução por região")
fig = utils.grafico_linha_regioes(df)
st.pyplot(fig)
plt.close(fig)
st.markdown(
    "As cinco regiões sobem e descem juntas nas crises, mas mantêm a mesma posição relativa: "
    "as crises afetam o país inteiro, enquanto a diferença entre regiões é estrutural."
)

st.divider()
col1, col2 = st.columns(2)
with col1:
    st.subheader("Heatmap trimestral")
    fig = utils.grafico_heatmap_trimestral(df)
    st.pyplot(fig)
    plt.close(fig)
with col2:
    st.subheader("Períodos de crise e recuperação")
    anual = df.groupby("ano")["taxa_desemprego"].mean()
    fases = (
        df.groupby("fase_economica")[["taxa_desemprego", "renda_media", "vagas_formais"]].mean()
        .reindex(["Crise 2015-2016", "Pré-pandemia", "Pandemia", "Recuperação"]).dropna()
        .rename(columns={"taxa_desemprego": "Taxa média (%)", "renda_media": "Renda média (R$)",
                         "vagas_formais": "Vagas formais (média)"})
    )
    st.dataframe(fases.style.format(precision=2, thousands=".", decimal=","), width="stretch")
    st.markdown(utils.texto_crises(df))
    if len(anual) > 1:
        variacao = anual.diff().dropna()
        st.markdown(
            f"Maior alta anual: **{variacao.idxmax()}** (+{utils.fmt_num(variacao.max(), 2)} p.p.). "
            f"Maior queda anual: **{variacao.idxmin()}** ({utils.fmt_num(variacao.min(), 2)} p.p.)."
        )

st.markdown(
    "O heatmap mostra cada ano em uma linha: as faixas mais escuras de 2016 e de 2020 e 2021 marcam as crises, "
    "e os tons claros a partir de 2022 mostram a recuperação."
)

st.divider()
st.subheader("Comparação interativa entre estados")
ufs = sorted(df["uf"].unique())
padrao = [u for u in ["CE", "SP", "PR"] if u in ufs] or ufs[:3]
escolhidos = st.multiselect("Estados para comparar (até 5)", ufs, default=padrao, max_selections=5)
if escolhidos:
    st.plotly_chart(utils.linha_interativa_uf(df, escolhidos), width="stretch")
    st.caption("Passe o mouse sobre as linhas para ver os valores de cada trimestre.")
