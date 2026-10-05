"""Página: renda, inflação, correlação, setores e grupos vulneráveis."""

import matplotlib.pyplot as plt
import streamlit as st

import utils

df, _ = utils.obter_base()

st.title("Análise econômica")
st.markdown("Relação do desemprego com renda média, inflação e vagas formais; setores e grupos vulneráveis.")
utils.checar_vazio(df)

aba_renda, aba_inflacao, aba_correlacao, aba_setores = st.tabs(
    ["Renda x desemprego", "Inflação x desemprego", "Correlação", "Setores e grupos vulneráveis"]
)

with aba_renda:
    fig = utils.grafico_dispersao_renda(df)
    st.pyplot(fig)
    plt.close(fig)
    st.markdown(utils.texto_correlacao(df, "renda_media", "a renda média"))
    fig = utils.grafico_renda_regiao(df)
    st.pyplot(fig)
    plt.close(fig)
    renda_regiao = df.groupby("regiao", observed=True)["renda_media"].mean().sort_values(ascending=False)
    st.markdown(
        f"A renda média foi maior no **{renda_regiao.index[0]}** ({utils.fmt_moeda(renda_regiao.iloc[0])}) "
        f"e menor no **{renda_regiao.index[-1]}** ({utils.fmt_moeda(renda_regiao.iloc[-1])}). A diferença de "
        "renda entre regiões é pequena perto da diferença de desemprego."
    )

with aba_inflacao:
    fig = utils.grafico_inflacao_desemprego(df)
    st.pyplot(fig)
    plt.close(fig)
    st.markdown(utils.texto_correlacao(df, "inflacao", "a inflação"))
    anual = df.groupby("ano")[["inflacao", "taxa_desemprego"]].mean()
    if len(anual) > 2:
        r_anual = anual["inflacao"].corr(anual["taxa_desemprego"])
        st.markdown(
            f"Com médias anuais, a correlação é **r = {utils.fmt_num(r_anual, 2)}**. Um valor negativo lembra a "
            "curva de Phillips (inflação maior com desemprego menor), mas com poucos anos o resultado é frágil."
        )

with aba_correlacao:
    col1, col2 = st.columns([2, 3])
    with col1:
        fig = utils.grafico_correlacao(df)
        st.pyplot(fig)
        plt.close(fig)
    with col2:
        variavel = st.selectbox(
            "Variável para comparar com a taxa de desemprego",
            ["renda_media", "inflacao", "vagas_formais"],
            format_func={"renda_media": "Renda média", "inflacao": "Inflação",
                         "vagas_formais": "Vagas formais"}.get,
        )
        st.plotly_chart(utils.dispersao_interativa(df, variavel), width="stretch")
    st.markdown(
        "Todas as correlações de Pearson com o desemprego ficam próximas de zero. Nesta base simulada, renda, "
        "inflação e vagas formais variam quase de forma independente da taxa; o fator que mais separa os "
        "estados é a região."
    )

with aba_setores:
    col1, col2 = st.columns(2)
    with col1:
        fig = utils.grafico_sazonalidade_setor(df)
        st.pyplot(fig)
        plt.close(fig)
    with col2:
        fig = utils.grafico_boxplot_setor(df)
        st.pyplot(fig)
        plt.close(fig)
    st.markdown(utils.texto_sazonalidade(df))
    st.markdown("#### Grupos vulneráveis")
    tabela = (
        df.groupby("faixa_renda", observed=True)["taxa_desemprego"].agg(["mean", "count"])
        .rename(columns={"mean": "Taxa média (%)", "count": "Registros"})
    )
    col1, col2 = st.columns([2, 3])
    with col1:
        st.dataframe(tabela.style.format({"Taxa média (%)": "{:.2f}"}), width="stretch")
    with col2:
        st.markdown(utils.texto_vulneraveis(df))
