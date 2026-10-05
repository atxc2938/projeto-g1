"""Página: visão geral com KPIs e resumo executivo."""

import matplotlib.pyplot as plt
import streamlit as st

import utils

df, _ = utils.obter_base()

st.title("Visão geral")
st.markdown("KPIs do Tema 04 calculados sobre os registros selecionados nos filtros.")
utils.checar_vazio(df)

k = utils.mostrar_kpis(df)

st.divider()
col1, col2 = st.columns([3, 2])
with col1:
    fig = utils.grafico_linha_temporal(df)
    st.pyplot(fig)
    plt.close(fig)
    st.markdown(utils.texto_temporal(df))
with col2:
    fig = utils.grafico_barras_regiao(df)
    st.pyplot(fig)
    plt.close(fig)
    st.markdown(utils.texto_regional(df))

st.divider()
st.subheader("Resumo executivo")
tendencia = "queda" if k["variacao_pp"] < 0 else "alta"
st.info(
    f"No recorte selecionado, a taxa média de desemprego é **{utils.fmt_pct(k['taxa_media'])}** e a renda "
    f"média é **{utils.fmt_moeda(k['renda_media'])}**. A taxa terminou o período em "
    f"**{tendencia}** ({utils.fmt_num(k['variacao_pp'], 2)} p.p. entre {k['periodo_inicio']} e "
    f"{k['periodo_fim']}). O **{k['regiao_maior']}** é a região mais afetada e "
    f"**{k['uf_maior_nome']}** o estado com maior taxa média; **{k['uf_menor_nome']}** tem a menor. "
    f"No último trimestre filtrado ({k['ultimo_periodo']}) havia "
    f"**{utils.fmt_milhoes(k['desempregados_ultimo'])}** de desempregados nos estados selecionados."
)
