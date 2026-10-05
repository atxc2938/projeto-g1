"""Página: visão geral com KPIs, evolução e comparação regional."""

import streamlit as st

import utils
import visual as v

df, _ = utils.obter_base()

v.cabecalho("Visão geral", "Indicadores principais e os dois movimentos centrais da base: o tempo e as regiões.")
utils.checar_vazio(df)

k = utils.mostrar_kpis(df)
st.write("")

aba_evolucao, aba_regioes, aba_resumo = st.tabs(["Evolução", "Regiões", "Resumo executivo"])

with aba_evolucao:
    estatistica = st.segmented_control("Estatística", ["Média", "Mediana"], default="Média", key="vg_estat") or "Média"
    v.plotly(utils.linha_temporal(df, estatistica), key="vg_linha")
    v.insight(
        utils.texto_temporal(df)
        + f" A mediana das taxas é **{utils.fmt_pct(k['mediana'])}**, um pouco "
        + ("abaixo" if k["mediana"] < k["taxa_media"] else "acima")
        + f" da média ({utils.fmt_pct(k['taxa_media'])})."
    )

with aba_regioes:
    animar = st.toggle("Animar por ano", key="vg_animar", help="Mostra a taxa de cada região ano a ano, com botão Reproduzir.")
    v.plotly(utils.barras_regiao(df, animar=animar), key="vg_regiao")
    v.insight(utils.texto_regional(df))

with aba_resumo:
    tendencia = "queda" if k["variacao_pp"] < 0 else "alta"
    v.insight(
        f"No recorte selecionado, a taxa média de desemprego é **{utils.fmt_pct(k['taxa_media'])}** e a renda média é "
        f"**{utils.fmt_moeda(k['renda_media'])}**. A taxa terminou o período em **{tendencia}** "
        f"({utils.fmt_num(k['variacao_pp'], 2)} p.p. entre {k['periodo_inicio']} e {k['periodo_fim']}). O "
        f"**{k['regiao_maior']}** é a região mais afetada e **{k['uf_maior_nome']}** o estado com maior taxa média; "
        f"**{k['uf_menor_nome']}** tem a menor. No último trimestre filtrado ({k['ultimo_periodo']}) havia "
        f"**{utils.fmt_milhoes(k['desempregados_ultimo'])}** de desempregados nos estados selecionados.",
        rotulo="Resumo executivo",
    )
