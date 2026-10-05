"""Dashboard: Evolução do Desemprego no Brasil (2015 a 2024).

Avaliação G1, Tema 04. Disciplina: Linguagens de Programação.
Professor: Alexandre Neves Louzada. Aluno: Marcell Sidaco de Moraes.
Execução local: streamlit run app.py
"""

import streamlit as st

import utils
import visual as v

st.set_page_config(
    page_title="Desemprego no Brasil | Dashboard",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)
v.aplicar_estilo()


def pagina_inicial():
    df, df_completo = utils.obter_base()

    v.cabecalho(
        "Evolução do Desemprego no Brasil",
        "Avaliação G1 · Tema 04 · Análise das taxas de desemprego entre 2015 e 2024.",
    )

    col_texto, col_achados = st.columns([3, 2], gap="large")
    with col_texto:
        v.secao("Descrição do problema")
        st.markdown(
            "O desemprego afeta a renda das famílias, o consumo, o desenvolvimento regional e o crescimento "
            "econômico. Este dashboard investiga a evolução das taxas de desemprego no Brasil entre 2015 e 2024 "
            "para identificar tendências, regiões mais afetadas, estados críticos, períodos de crise e de "
            "recuperação econômica."
        )
        st.markdown(
            "A base é simulada, com 800 registros (20 estados ao longo de 40 trimestres), tratada no notebook "
            "do projeto e armazenada em um banco SQLite modelado com SQLAlchemy. Os filtros da barra lateral "
            "valem para todas as páginas."
        )
        st.page_link("paginas/1_Visao_Geral.py", label="Ir para a visão geral", icon=":material/arrow_forward:")
    with col_achados:
        v.secao("Principais achados")
        k = utils.calcular_kpis(df) if not df.empty else utils.calcular_kpis(df_completo)
        st.html(
            '<ol class="lista-limpa">'
            f'<li>A taxa média caiu de {utils.fmt_pct(k["taxa_inicio"])} para {utils.fmt_pct(k["taxa_fim"])}, '
            'com picos na recessão de 2016 e na pandemia (2020 e 2021).</li>'
            f'<li>O {k["regiao_maior"]} tem a maior taxa média ({utils.fmt_pct(k["regiao_maior_taxa"])}) e o '
            f'{k["regiao_menor"]} a menor ({utils.fmt_pct(k["regiao_menor_taxa"])}); a ordem entre as regiões '
            'se mantém em todos os anos.</li>'
            '<li>Renda, inflação e vagas formais têm correlação próxima de zero com a taxa nesta base.</li>'
            '</ol>'
        )

    v.secao("Perguntas orientadoras")
    perguntas = [
        "Quais regiões apresentam maior desemprego?",
        "Quais estados apresentam menores taxas?",
        "Existem períodos de crise econômica mais evidentes?",
        "O desemprego aumentou ou diminuiu ao longo do tempo?",
        "Existem diferenças relevantes entre regiões?",
        "Há sazonalidade em determinados setores?",
        "Quais grupos parecem mais vulneráveis?",
    ]
    col1, col2 = st.columns(2, gap="large")
    col1.html('<ol class="lista-limpa">' + "".join(f"<li>{p}</li>" for p in perguntas[:4]) + "</ol>")
    col2.html('<ol class="lista-limpa" start="5">' + "".join(f"<li>{p}</li>" for p in perguntas[4:]) + "</ol>")
    st.caption("As respostas, calculadas com os filtros ativos, estão na página Dados e conclusão.")

    with st.expander("Fonte dos dados e tecnologias"):
        st.markdown(
            f"""
            * **Base:** `simulacao_desemprego_brasil.csv`, do repositório
              [Dados-Simulados-G2](https://github.com/AlexandreLouzada/Dados-Simulados-G2).
            * **Leitura:** {st.session_state['origem_dados']}, consulta com JOIN entre `indicador_trimestral`,
              `uf`, `regiao` e `setor`.
            * **Tecnologias:** Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, SQLAlchemy, SQLite e Streamlit.
            * **Modelo relacional:** `regiao` (1) para (N) `uf` (1) para (N) `indicador_trimestral` (N) para (1) `setor`.
            """
        )
        registros = utils.contar_registros_banco()
        if not registros.empty:
            st.dataframe(registros, hide_index=True, width="content")


# Dados e filtros compartilhados por todas as páginas
df_completo, origem = utils.carregar_dados()
st.session_state["df_completo"] = df_completo
st.session_state["origem_dados"] = origem
st.session_state["df_filtrado"] = utils.aplicar_filtros_sidebar(df_completo)

st.sidebar.divider()
st.sidebar.caption("Linguagens de Programação  \nProf. Alexandre Neves Louzada  \nAluno: Marcell Sidaco de Moraes  \n"
                   "Avaliação G1 · Tema 04")

paginas = st.navigation([
    st.Page(pagina_inicial, title="Início", icon=":material/home:", default=True),
    st.Page("paginas/1_Visao_Geral.py", url_path="visao-geral", title="Visão geral", icon=":material/dashboard:"),
    st.Page("paginas/2_Evolucao_Temporal.py", url_path="evolucao-temporal", title="Evolução temporal", icon=":material/show_chart:"),
    st.Page("paginas/3_Regioes_e_Estados.py", url_path="regioes-e-estados", title="Regiões e estados", icon=":material/map:"),
    st.Page("paginas/4_Analise_Economica.py", url_path="analise-economica", title="Análise econômica", icon=":material/payments:"),
    st.Page("paginas/5_Dados_e_Conclusao.py", url_path="dados-e-conclusao", title="Dados e conclusão", icon=":material/table_chart:"),
])
paginas.run()
