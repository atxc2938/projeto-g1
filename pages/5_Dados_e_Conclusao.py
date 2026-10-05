"""Página: tabela dinâmica, dados filtrados, respostas e conclusão executiva."""

import streamlit as st

import utils

df, _ = utils.obter_base()

st.title("Dados e conclusão")
utils.checar_vazio(df)

st.subheader("Tabela dinâmica")
dimensoes = {
    "regiao": "Região", "uf": "UF", "ano": "Ano", "trimestre": "Trimestre",
    "setor_predominante": "Setor", "nivel_risco": "Nível de risco", "fase_economica": "Fase econômica",
    "faixa_renda": "Faixa de renda",
}
metricas = {
    "taxa_desemprego": "Taxa de desemprego (%)", "renda_media": "Renda média (R$)",
    "desempregados": "Desempregados", "vagas_formais": "Vagas formais", "inflacao": "Inflação (%)",
}
col1, col2, col3, col4 = st.columns(4)
linhas = col1.selectbox("Linhas", list(dimensoes), format_func=dimensoes.get, index=0)
opcoes_colunas = [d for d in dimensoes if d != linhas]
colunas = col2.selectbox("Colunas", opcoes_colunas, format_func=dimensoes.get,
                         index=opcoes_colunas.index("ano"))
metrica = col3.selectbox("Métrica", list(metricas), format_func=metricas.get)
agregacao = col4.selectbox("Agregação", ["mean", "sum", "max", "min"],
                           format_func={"mean": "Média", "sum": "Soma", "max": "Máximo", "min": "Mínimo"}.get)

pivo = df.pivot_table(index=linhas, columns=colunas, values=metrica, aggfunc=agregacao, observed=True)
casas = 0 if metrica in ("desempregados", "vagas_formais") else 2
st.dataframe(
    pivo.style.format(precision=casas, thousands=".", decimal=",").background_gradient(
        cmap=utils.CMAP_SEQUENCIAL, axis=None
    ),
    width="stretch",
)
st.caption("Escolha linhas, colunas, métrica e agregação. As cores vão do menor (claro) ao maior (escuro) valor.")

st.subheader("Dados filtrados")
colunas_exibir = [
    "periodo", "regiao", "uf", "estado", "setor_predominante", "populacao_ativa", "desempregados",
    "taxa_desemprego", "renda_media", "vagas_formais", "inflacao", "nivel_risco", "fase_economica",
]
st.dataframe(
    df[colunas_exibir], hide_index=True, width="stretch", height=320,
    column_config={
        "periodo": "Período", "regiao": "Região", "uf": "UF", "estado": "Estado",
        "setor_predominante": "Setor", "nivel_risco": "Risco", "fase_economica": "Fase econômica",
        "populacao_ativa": st.column_config.NumberColumn("População ativa", format="localized"),
        "desempregados": st.column_config.NumberColumn("Desempregados", format="localized"),
        "vagas_formais": st.column_config.NumberColumn("Vagas formais", format="localized"),
        "taxa_desemprego": st.column_config.NumberColumn("Taxa (%)", format="%.2f"),
        "renda_media": st.column_config.NumberColumn("Renda média (R$)", format="%.2f"),
        "inflacao": st.column_config.NumberColumn("Inflação (%)", format="%.2f"),
    },
)
st.download_button(
    "Baixar dados filtrados (CSV)",
    df[colunas_exibir].to_csv(index=False).encode("utf-8"),
    file_name="desemprego_filtrado.csv",
    mime="text/csv",
)

st.divider()
st.subheader("Respostas às perguntas orientadoras")
k = utils.calcular_kpis(df)
anual = df.groupby("ano")["taxa_desemprego"].mean()
estados_menores = df.groupby("estado")["taxa_desemprego"].mean().nsmallest(3)

respostas = {
    "1. Quais regiões apresentam maior desemprego?":
        f"{k['regiao_maior']} ({utils.fmt_pct(k['regiao_maior_taxa'])} de taxa média). "
        + utils.texto_regional(df),
    "2. Quais estados apresentam menores taxas?":
        ", ".join(f"{e} ({utils.fmt_pct(v)})" for e, v in estados_menores.items()) + ".",
    "3. Existem períodos de crise econômica mais evidentes?":
        utils.texto_crises(df) or "Selecione mais anos para identificar crises.",
    "4. O desemprego aumentou ou diminuiu ao longo do tempo?":
        utils.texto_temporal(df),
    "5. Existem diferenças relevantes entre regiões?":
        f"Sim: {utils.fmt_num(k['regiao_maior_taxa'] - k['regiao_menor_taxa'], 2)} p.p. separam "
        f"{k['regiao_maior']} e {k['regiao_menor']}, e a ordem entre regiões se mantém ao longo dos anos.",
    "6. Há sazonalidade em determinados setores?":
        utils.texto_sazonalidade(df),
    "7. Quais grupos parecem mais vulneráveis?":
        utils.texto_vulneraveis(df),
}
for pergunta, resposta in respostas.items():
    with st.expander(pergunta, expanded=False):
        st.markdown(resposta)

st.divider()
st.subheader("Conclusão executiva")
st.success(
    f"""
**1. Tendência de queda com duas crises.** A taxa média passou de {utils.fmt_pct(k['taxa_inicio'])}
({k['periodo_inicio']}) para {utils.fmt_pct(k['taxa_fim'])} ({k['periodo_fim']}). Os picos de 2016 (recessão)
e de 2020 e 2021 (pandemia) foram seguidos de recuperação, e 2024 fechou com a menor média anual da série.

**2. A desigualdade regional é o problema central.** O Nordeste tem taxa cerca de duas vezes maior que a
do Sul, e a ordem entre as regiões não muda em nenhum ano: crises atingem todos, mas não alteram a hierarquia.

**3. Estados críticos estão concentrados.** Bahia, Ceará e Paraíba lideram em trimestres de risco Crítico;
Paraná, Santa Catarina e Rio Grande do Sul têm as menores taxas.

**4. Variáveis econômicas pouco explicam a taxa nesta base.** Renda, inflação, vagas formais e setor
predominante têm correlação próxima de zero com o desemprego.

**Recomendação:** políticas de emprego devem ter **foco regional**, priorizando Nordeste e Norte, com
monitoramento trimestral para agir cedo em novos períodos de crise.
"""
)
st.caption("Conclusão baseada na base completa; os números destacados acompanham os filtros ativos.")
