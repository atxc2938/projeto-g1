"""Página: renda, inflação, correlação, setores e grupos vulneráveis."""

import streamlit as st

import utils
import visual as v

df, _ = utils.obter_base()

v.cabecalho("Análise econômica", "Relação do desemprego com renda, inflação e vagas formais; setores e grupos vulneráveis.")
utils.checar_vazio(df)

aba_renda, aba_inflacao, aba_correlacao, aba_setores = st.tabs(
    ["Renda", "Inflação", "Correlação", "Setores e grupos vulneráveis"])

with aba_renda:
    animar = st.toggle("Animar por ano", key="ae_animar", help="Cada ponto é um estado em um trimestre; o tamanho indica a população ativa.")
    v.plotly(utils.dispersao(df, "renda_media", animar=animar), key="ae_disp_renda")
    v.insight(utils.texto_correlacao(df, "renda_media", "a renda média"))
    v.secao("Renda média por região")
    v.plotly(utils.renda_regiao(df), key="ae_renda_regiao")
    renda = df.groupby("regiao", observed=True)["renda_media"].mean().sort_values(ascending=False)
    v.insight(f"A renda média foi maior no **{renda.index[0]}** ({utils.fmt_moeda(renda.iloc[0])}) e menor no "
              f"**{renda.index[-1]}** ({utils.fmt_moeda(renda.iloc[-1])}). A diferença de renda entre regiões é "
              "pequena perto da diferença de desemprego.")

with aba_inflacao:
    v.plotly(utils.inflacao_desemprego(df), key="ae_inflacao")
    texto = utils.texto_correlacao(df, "inflacao", "a inflação")
    anual = df.groupby("ano")[["inflacao", "taxa_desemprego"]].mean()
    if len(anual) > 2:
        r_anual = anual["inflacao"].corr(anual["taxa_desemprego"])
        texto += (f" Com médias anuais, a correlação é **r = {utils.fmt_num(r_anual, 2)}**; um valor negativo lembra "
                  "a curva de Phillips, mas com poucos anos o resultado é frágil.")
    v.insight(texto)

with aba_correlacao:
    col1, col2 = st.columns([4, 5], gap="large")
    with col1:
        v.pyplot(utils.grafico_correlacao(df))
    with col2:
        variavel = st.selectbox(
            "Variável comparada com a taxa de desemprego", ["renda_media", "inflacao", "vagas_formais"],
            format_func={"renda_media": "Renda média", "inflacao": "Inflação", "vagas_formais": "Vagas formais"}.get,
            key="ae_variavel",
        )
        v.plotly(utils.dispersao(df, variavel), key="ae_disp_var")
    v.insight("Todas as correlações de Pearson com o desemprego ficam próximas de zero. Nesta base simulada, renda, "
              "inflação e vagas formais variam quase de forma independente da taxa; o fator que mais separa os "
              "estados é a região.")

with aba_setores:
    col1, col2 = st.columns(2, gap="large")
    with col1:
        v.pyplot(utils.grafico_sazonalidade_setor(df))
    with col2:
        v.pyplot(utils.grafico_boxplot_setor(df))
    v.insight(utils.texto_sazonalidade(df))
    v.secao("Grupos vulneráveis")
    tabela = df.groupby("faixa_renda", observed=True)["taxa_desemprego"].agg(["mean", "count"])
    col1, col2 = st.columns([2, 3], gap="large")
    with col1:
        st.dataframe(
            tabela, width="stretch",
            column_config={
                "mean": st.column_config.ProgressColumn("Taxa média", format="%.2f%%", min_value=0,
                                                        max_value=float(max(12, tabela["mean"].max()))),
                "count": st.column_config.NumberColumn("Registros"),
            },
        )
    with col2:
        v.insight(utils.texto_vulneraveis(df))
