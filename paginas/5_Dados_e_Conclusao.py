"""Página: tabela dinâmica, dados filtrados, respostas e conclusão executiva."""

import streamlit as st

import utils
import visual as v

df, _ = utils.obter_base()

v.cabecalho("Dados e conclusão", "Tabela dinâmica, dados filtrados, respostas às perguntas orientadoras e conclusão executiva.")
utils.checar_vazio(df)

aba_pivo, aba_dados, aba_respostas, aba_conclusao = st.tabs(
    ["Tabela dinâmica", "Dados filtrados", "Respostas às perguntas", "Conclusão executiva"])

with aba_pivo:
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
    linhas = col1.selectbox("Linhas", list(dimensoes), format_func=dimensoes.get, index=0, key="dc_linhas")
    opcoes_colunas = [d for d in dimensoes if d != linhas]
    colunas = col2.selectbox("Colunas", opcoes_colunas, format_func=dimensoes.get,
                             index=opcoes_colunas.index("ano"), key="dc_colunas")
    metrica = col3.selectbox("Métrica", list(metricas), format_func=metricas.get, key="dc_metrica")
    agregacao = col4.selectbox("Agregação", ["mean", "median", "sum", "max", "min"], key="dc_agregacao",
                               format_func={"mean": "Média", "median": "Mediana", "sum": "Soma",
                                            "max": "Máximo", "min": "Mínimo"}.get)
    pivo = df.pivot_table(index=linhas, columns=colunas, values=metrica, aggfunc=agregacao, observed=True)
    casas = 0 if metrica in ("desempregados", "vagas_formais") else 2
    st.dataframe(
        pivo.style.format(precision=casas, thousands=".", decimal=",")
        .background_gradient(cmap=utils.CMAP_SEQUENCIAL, axis=None, text_color_threshold=0.45),
        width="stretch",
    )
    st.caption("Cores do menor (escuro) ao maior (claro) valor da tabela.")

with aba_dados:
    colunas_exibir = [
        "periodo", "regiao", "uf", "estado", "setor_predominante", "populacao_ativa", "desempregados",
        "taxa_desemprego", "renda_media", "vagas_formais", "inflacao", "nivel_risco", "fase_economica",
    ]
    st.dataframe(
        df[colunas_exibir], hide_index=True, width="stretch", height=420,
        column_config={
            "periodo": "Período", "regiao": "Região", "uf": "UF", "estado": "Estado",
            "setor_predominante": "Setor", "nivel_risco": "Risco", "fase_economica": "Fase econômica",
            "populacao_ativa": st.column_config.NumberColumn("População ativa", format="localized"),
            "desempregados": st.column_config.NumberColumn("Desempregados", format="localized"),
            "vagas_formais": st.column_config.NumberColumn("Vagas formais", format="localized"),
            "taxa_desemprego": st.column_config.NumberColumn("Taxa (%)", format="%.2f"),
            "renda_media": st.column_config.NumberColumn("Renda média", format="R$ %.2f"),
            "inflacao": st.column_config.NumberColumn("Inflação (%)", format="%.2f"),
        },
    )
    st.download_button("Baixar dados filtrados (CSV)", df[colunas_exibir].to_csv(index=False).encode("utf-8"),
                       file_name="desemprego_filtrado.csv", mime="text/csv", icon=":material/download:")

k = utils.calcular_kpis(df)
with aba_respostas:
    estados_menores = df.groupby("estado")["taxa_desemprego"].mean().nsmallest(3)
    respostas = [
        ("1. Quais regiões apresentam maior desemprego?",
         f"{k['regiao_maior']} ({utils.fmt_pct(k['regiao_maior_taxa'])} de taxa média). " + utils.texto_regional(df)),
        ("2. Quais estados apresentam menores taxas?",
         ", ".join(f"{e} ({utils.fmt_pct(t)})" for e, t in estados_menores.items()) + "."),
        ("3. Existem períodos de crise econômica mais evidentes?",
         utils.texto_crises(df) or "Selecione mais anos para identificar crises."),
        ("4. O desemprego aumentou ou diminuiu ao longo do tempo?", utils.texto_temporal(df)),
        ("5. Existem diferenças relevantes entre regiões?",
         f"Sim: {utils.fmt_num(k['regiao_maior_taxa'] - k['regiao_menor_taxa'], 2)} p.p. separam {k['regiao_maior']} e "
         f"{k['regiao_menor']}, e a ordem entre regiões se mantém ao longo dos anos."),
        ("6. Há sazonalidade em determinados setores?", utils.texto_sazonalidade(df)),
        ("7. Quais grupos parecem mais vulneráveis?", utils.texto_vulneraveis(df)),
    ]
    for i, (pergunta, resposta) in enumerate(respostas):
        with st.expander(pergunta, expanded=i == 0):
            st.markdown(resposta)

with aba_conclusao:
    st.html(
        '<div class="interp"><span class="r">Conclusão executiva</span><div><ol class="lista-limpa">'
        f'<li><strong>Tendência de queda com duas crises.</strong> A taxa média passou de {utils.fmt_pct(k["taxa_inicio"])} '
        f'({k["periodo_inicio"]}) para {utils.fmt_pct(k["taxa_fim"])} ({k["periodo_fim"]}). Os picos de 2016 (recessão) e de '
        '2020 e 2021 (pandemia) foram seguidos de recuperação, e 2024 fechou com a menor média anual da série.</li>'
        '<li><strong>A desigualdade regional é o problema central.</strong> O Nordeste tem taxa cerca de duas vezes maior '
        'que a do Sul, e a ordem entre as regiões não muda em nenhum ano.</li>'
        '<li><strong>Estados críticos estão concentrados.</strong> Bahia, Ceará e Paraíba lideram em trimestres de risco '
        'Crítico; Paraná, Santa Catarina e Rio Grande do Sul têm as menores taxas.</li>'
        '<li><strong>Variáveis econômicas pouco explicam a taxa nesta base.</strong> Renda, inflação, vagas formais e setor '
        'predominante têm correlação próxima de zero com o desemprego.</li>'
        '<li><strong>Recomendação:</strong> políticas de emprego com foco regional, priorizando Nordeste e Norte, e '
        'monitoramento trimestral para agir cedo em novos períodos de crise.</li>'
        '</ol></div></div>'
    )
    st.caption("Conclusão baseada na base completa; os números do primeiro item acompanham os filtros ativos.")
