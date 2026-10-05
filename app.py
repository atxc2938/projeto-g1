"""Dashboard: Evolução do Desemprego no Brasil (2015 a 2024).

Avaliação G1, Tema 04. Autor: Marcell Sidaco de Moraes.
Execução local: streamlit run app.py
"""

import streamlit as st

import utils

st.set_page_config(
    page_title="Desemprego no Brasil | Dashboard",
    page_icon="📉",
    layout="wide",
)


def pagina_inicial():
    df, df_completo = utils.obter_base()

    st.title("Evolução do Desemprego no Brasil (2015 a 2024)")
    st.caption("Avaliação G1 · Tema 04 · Linguagem de Programação: Análise e Visualização de Dados com Python")

    st.markdown(
        """
        ### Descrição do problema
        O desemprego é um dos principais indicadores socioeconômicos de um país: afeta a renda das famílias,
        o consumo, o desenvolvimento regional e o crescimento econômico. Este dashboard investiga a evolução
        das taxas de desemprego no Brasil entre 2015 e 2024 para **identificar tendências, regiões mais
        afetadas, estados críticos, períodos de crise e de recuperação econômica**.

        A base é um conjunto de dados **simulado** com 800 registros (20 estados x 40 trimestres), tratado no
        notebook do projeto e armazenado em um banco **SQLite** modelado com **SQLAlchemy**.
        """
    )

    col_esq, col_dir = st.columns([3, 2])
    with col_esq:
        st.markdown(
            """
            ### Perguntas orientadoras
            1. Quais regiões apresentam maior desemprego?
            2. Quais estados apresentam menores taxas?
            3. Existem períodos de crise econômica mais evidentes?
            4. O desemprego aumentou ou diminuiu ao longo do tempo?
            5. Existem diferenças relevantes entre regiões?
            6. Há sazonalidade em determinados setores?
            7. Quais grupos parecem mais vulneráveis?

            As respostas, calculadas com os filtros ativos, estão na página **Dados e conclusão**.
            """
        )
    with col_dir:
        st.markdown("### Como navegar")
        st.markdown(
            """
            * **Visão geral:** KPIs e resumo executivo.
            * **Evolução temporal:** linha do tempo, heatmap trimestral, crises e recuperação.
            * **Regiões e estados:** comparação regional, ranking estadual e mapa interativo.
            * **Análise econômica:** renda, inflação, correlação, setores e grupos vulneráveis.
            * **Dados e conclusão:** tabela dinâmica, dados filtrados e conclusão executiva.

            Use os **filtros da barra lateral**: eles valem para todas as páginas.
            """
        )

    st.divider()
    utils.checar_vazio(df)
    st.subheader("Indicadores com os filtros atuais")
    utils.mostrar_kpis(df)

    st.divider()
    st.markdown("### Fonte e tecnologias")
    st.markdown(
        f"""
        * Base: `simulacao_desemprego_brasil.csv` do repositório
          [Dados-Simulados-G2](https://github.com/AlexandreLouzada/Dados-Simulados-G2).
        * Dados lidos de: **{st.session_state['origem_dados']}**, consulta com JOIN entre as tabelas
          `indicador_trimestral`, `uf`, `regiao` e `setor`.
        * Tecnologias: Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, SQLAlchemy, SQLite e Streamlit.
        """
    )
    registros = utils.contar_registros_banco()
    if not registros.empty:
        with st.expander("Modelo relacional do banco SQLite"):
            st.markdown(
                "`regiao` (1) ── (N) `uf` (1) ── (N) `indicador_trimestral` (N) ── (1) `setor`"
            )
            st.dataframe(registros, hide_index=True, width="content")


# Dados e filtros compartilhados por todas as páginas
df_completo, origem = utils.carregar_dados()
st.session_state["df_completo"] = df_completo
st.session_state["origem_dados"] = origem
st.session_state["df_filtrado"] = utils.aplicar_filtros_sidebar(df_completo)

st.sidebar.divider()
st.sidebar.caption("Autor: Marcell Sidaco de Moraes")

paginas = st.navigation([
    st.Page(pagina_inicial, title="Início", icon="🏠", default=True),
    st.Page("pages/1_Visao_Geral.py", url_path="visao-geral", title="Visão geral", icon="📊"),
    st.Page("pages/2_Evolucao_Temporal.py", url_path="evolucao-temporal", title="Evolução temporal", icon="📈"),
    st.Page("pages/3_Regioes_e_Estados.py", url_path="regioes-e-estados", title="Regiões e estados", icon="🗺️"),
    st.Page("pages/4_Analise_Economica.py", url_path="analise-economica", title="Análise econômica", icon="💰"),
    st.Page("pages/5_Dados_e_Conclusao.py", url_path="dados-e-conclusao", title="Dados e conclusão", icon="📋"),
])
paginas.run()
