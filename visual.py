"""Identidade visual do dashboard: tema escuro sóbrio, tipografia, movimento suave,
template do Plotly, estilo do Matplotlib/Seaborn e componentes HTML simples
(cabeçalho de página, cartões de KPI e bloco de interpretação).
"""

import html
import json
import re
import uuid

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
import seaborn as sns
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap

# ---------------------------------------------------------------------------
# Tokens de cor
# ---------------------------------------------------------------------------
FUNDO = "#111827"
CARTAO = "#1a2233"
CARTAO_2 = "#1f293b"
BORDA = "#2a3447"
GRADE = "#222c3d"
TEXTO = "#e5e7eb"
TEXTO_2 = "#9ca3af"
TEXTO_3 = "#8b94a5"
AZUL = "#3987e5"
AZUL_CLARO = "#86b6ef"
LARANJA = "#d95926"
POSITIVO = "#34c759"
NEGATIVO = "#f87171"

# Paleta das regiões validada para daltonismo no fundo escuro (ordem fixa por entidade)
CORES_REGIAO = {
    "Norte": "#3987e5",
    "Nordeste": "#d95926",
    "Centro-Oeste": "#199e70",
    "Sudeste": "#c98500",
    "Sul": "#d55181",
}
SIMBOLOS_REGIAO = {
    "Norte": "circle", "Nordeste": "diamond", "Centro-Oeste": "square",
    "Sudeste": "triangle-up", "Sul": "cross",
}
CORES_RISCO = {"Baixo": "#0ca30c", "Médio": "#fab219", "Alto": "#ec835a", "Crítico": "#d03b3b"}

RAMPA_SEQUENCIAL = ["#172238", "#1c4b8a", "#2f73cc", "#6da7ec", "#cde2fb"]
RAMPA_DIVERGENTE = ["#3987e5", "#24426e", "#2a3140", "#6e2c2c", "#e66767"]
CMAP_SEQUENCIAL = LinearSegmentedColormap.from_list("seq_escuro", RAMPA_SEQUENCIAL)
CMAP_DIVERGENTE = LinearSegmentedColormap.from_list("div_escuro", RAMPA_DIVERGENTE)

FONTE_TITULO = "'Lexend', 'Source Sans 3', system-ui, sans-serif"
FONTE_TEXTO = "'Source Sans 3', 'Source Sans Pro', system-ui, sans-serif"
# O Plotly mede os rótulos antes de a fonte web carregar; fonte de sistema evita cortes
FONTE_GRAFICO = "system-ui, -apple-system, 'Segoe UI', Roboto, 'DejaVu Sans', sans-serif"

METADADOS = "Linguagens de Programação · Prof. Alexandre Neves Louzada · Aluno: Marcell Sidaco de Moraes"

# ---------------------------------------------------------------------------
# Plotly
# ---------------------------------------------------------------------------
_eixo = dict(
    gridcolor=GRADE, linecolor=BORDA, zeroline=False, ticks="", automargin=True,
    tickfont=dict(color=TEXTO_2, size=12), title=dict(font=dict(color=TEXTO_2, size=13)),
)
pio.templates["desemprego_escuro"] = go.layout.Template(
    layout=dict(
        font=dict(family=FONTE_GRAFICO, color=TEXTO, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=list(CORES_REGIAO.values()),
        separators=",.",
        xaxis=_eixo,
        yaxis=_eixo,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXTO_2, size=12), orientation="h",
                    x=0, xanchor="left", y=1.02, yanchor="bottom", title=dict(text="")),
        hoverlabel=dict(bgcolor=CARTAO_2, bordercolor=BORDA, font=dict(color=TEXTO, family=FONTE_GRAFICO, size=13)),
        margin=dict(l=64, r=24, t=36, b=48),
        coloraxis=dict(colorbar=dict(outlinewidth=0, thickness=12, tickfont=dict(color=TEXTO_2),
                                     title=dict(font=dict(color=TEXTO_2)))),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
)
pio.templates.default = "desemprego_escuro"

PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"],
    "locale": "pt-BR",
}


def finalizar(fig, altura=440):
    """Altura, transição suave e controles de animação discretos."""
    fig.update_layout(height=altura, title=None, transition=dict(duration=350, easing="cubic-in-out"))
    if fig.layout.updatemenus:
        fig.update_layout(updatemenus=[dict(
            type="buttons", direction="left", showactive=False,
            bgcolor=CARTAO_2, bordercolor=BORDA, font=dict(color=TEXTO, size=12),
            pad=dict(r=8, t=46), x=0, xanchor="left", y=0, yanchor="top",
            buttons=[
                dict(label="Reproduzir", method="animate",
                     args=[None, {"frame": {"duration": 900, "redraw": True},
                                  "transition": {"duration": 500, "easing": "cubic-in-out"}, "fromcurrent": True}]),
                dict(label="Pausar", method="animate",
                     args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]),
            ],
        )])
        for slider in fig.layout.sliders:
            slider.update(
                currentvalue=dict(prefix="Ano ", font=dict(color=TEXTO, size=13)),
                font=dict(color=TEXTO_3, size=11), bgcolor=CARTAO_2, bordercolor=BORDA,
                activebgcolor=AZUL, tickcolor=BORDA, pad=dict(t=46, l=190),
                transition=dict(duration=400, easing="cubic-in-out"),
            )
        fig.update_layout(margin=dict(b=110))
    return fig


def plotly(fig, key):
    """Gráfico Plotly com o template próprio (sem o tema padrão do Streamlit)."""
    return st.plotly_chart(fig, width="stretch", theme=None, key=key, config=PLOTLY_CONFIG)


# ---------------------------------------------------------------------------
# Matplotlib / Seaborn
# ---------------------------------------------------------------------------

def estilo_matplotlib():
    sns.set_theme(style="dark", font_scale=1.0)
    plt.rcParams.update({
        "figure.facecolor": CARTAO, "axes.facecolor": CARTAO, "savefig.facecolor": CARTAO,
        "axes.edgecolor": BORDA, "axes.labelcolor": TEXTO_2, "axes.titlecolor": TEXTO,
        "axes.titleweight": "normal", "axes.titlesize": 12.5, "axes.titlepad": 10, "axes.labelsize": 11,
        "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.7,
        "xtick.color": TEXTO_2, "ytick.color": TEXTO_2, "xtick.labelsize": 10.5, "ytick.labelsize": 10.5,
        "text.color": TEXTO, "legend.frameon": False, "legend.labelcolor": TEXTO_2,
        "figure.dpi": 160, "font.family": "sans-serif", "font.sans-serif": ["Source Sans 3", "DejaVu Sans", "Arial"],
    })


def pyplot(fig):
    st.pyplot(fig, width="stretch")
    plt.close(fig)


# ---------------------------------------------------------------------------
# CSS global
# ---------------------------------------------------------------------------
CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@500;600&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root {{
  --fundo: {FUNDO}; --cartao: {CARTAO}; --cartao-2: {CARTAO_2}; --borda: {BORDA};
  --texto: {TEXTO}; --texto-2: {TEXTO_2}; --texto-3: {TEXTO_3}; --azul: {AZUL};
}}
html, body, .stApp {{ font-family: {FONTE_TEXTO}; }}
.stApp {{ font-size: 16px; }}
.stMarkdown p, .stMarkdown li {{ line-height: 1.6; color: var(--texto); }}
h1, h2, h3, h4 {{ font-family: {FONTE_TITULO} !important; font-weight: 600 !important; letter-spacing: -0.01em; }}

[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{
  max-width: 1440px;
  padding: clamp(1.5rem, 2.4vw, 2.75rem) clamp(1.5rem, 3vw, 3.5rem) 4rem;
  container-type: inline-size; container-name: conteudo;
}}
@container conteudo (max-width: 980px) {{
  [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ flex: 1 1 100% !important; min-width: 100% !important; }}
}}

/* Barra lateral */
[data-testid="stSidebar"] {{ background: #0e1420; border-right: 1px solid var(--borda); }}
[data-testid="stSidebar"] [data-tag] {{ background: #243049 !important; border: 1px solid #33415c; color: var(--texto) !important; }}
[data-testid="stSidebar"] [data-tag] button {{ color: var(--texto-2) !important; }}
[data-testid="stSidebarNavLink"] {{ border-radius: 8px; transition: background-color .15s ease; }}

/* Contêineres com borda e abas */
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--borda) !important; background: var(--cartao); border-radius: 12px; }}
[data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--borda); }}
[data-baseweb="tab"] {{ padding: 10px 16px; font-weight: 600; color: var(--texto-2); transition: color .15s ease; }}
[data-baseweb="tab"][aria-selected="true"] {{ color: var(--texto); }}
[data-baseweb="tab-highlight"] {{ background-color: var(--azul) !important; }}
[data-baseweb="tab-panel"] {{ padding-top: 1.1rem; }}

/* Movimento: só opacidade, curto */
@keyframes surgir {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"],
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlockBorderWrapper"],
[data-baseweb="tab-panel"] {{ animation: surgir .22s ease-out both; }}

/* Cabeçalho de página */
.cab {{ margin: 0 0 1.4rem; padding-bottom: 1rem; border-bottom: 1px solid var(--borda); }}
.cab h1 {{ margin: 0; font-size: clamp(1.75rem, 2.1vw, 2.15rem); color: var(--texto); line-height: 1.2; padding: 0; }}
.cab p {{ margin: .35rem 0 0; color: var(--texto-2); font-size: 1.02rem; max-width: 900px; }}
.cab .meta {{ margin-top: .6rem; color: var(--texto-3); font-size: .86rem; letter-spacing: .01em; }}

.secao {{ margin: 1.8rem 0 .7rem; }}
.secao h3 {{ margin: 0; font-size: 1.15rem; color: var(--texto); padding: 0; }}
.secao p {{ margin: .25rem 0 0; color: var(--texto-2); font-size: .95rem; }}

/* Cartões de KPI */
.kpis {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
@container conteudo (min-width: 1180px) {{ .kpis.seis {{ grid-template-columns: repeat(6, 1fr); }} }}
@container conteudo (min-width: 700px) and (max-width: 1179px) {{ .kpis.seis {{ grid-template-columns: repeat(3, 1fr); }} }}
.kpi {{ background: var(--cartao); border: 1px solid var(--borda); border-radius: 12px; padding: 16px 18px;
  transition: border-color .15s ease; container-type: inline-size; }}
.kpi:hover {{ border-color: #3b4a63; }}
.kpi .rot {{ color: var(--texto-2); font-size: .78rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }}
.kpi .val {{ font-family: {FONTE_TEXTO}; font-size: clamp(1.45rem, 14cqi, 2.1rem); font-weight: 700; color: var(--texto);
  margin: 6px 0 4px; white-space: nowrap; font-variant-numeric: tabular-nums; line-height: 1.15; }}
.kpi .val .suf {{ font-size: .62em; font-weight: 600; color: var(--texto-2); margin-left: 2px; }}
.kpi .val .pre {{ font-size: .62em; font-weight: 600; color: var(--texto-2); margin-right: 4px; }}
.kpi .apoio {{ color: var(--texto-3); font-size: .86rem; line-height: 1.4; }}
.kpi .apoio b {{ color: var(--texto-2); font-weight: 600; }}
.kpi .pos, .kpi .pos .suf {{ color: {POSITIVO}; font-weight: 600; }}
.kpi .neg, .kpi .neg .suf {{ color: {NEGATIVO}; font-weight: 600; }}

/* Interpretação */
.interp {{ border-left: 3px solid var(--azul); background: rgba(57,135,229,.06); border-radius: 0 8px 8px 0;
  padding: 12px 16px; margin: .8rem 0 .4rem; }}
.interp .r {{ display: block; color: #6aa6f2; font-size: .74rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; margin-bottom: 4px; }}
.interp div {{ color: var(--texto); font-size: .98rem; line-height: 1.6; }}
.interp strong {{ color: #fff; font-weight: 600; }}

.lista-limpa {{ margin: 0; padding-left: 1.2rem; color: var(--texto); line-height: 1.75; }}
.lista-limpa li::marker {{ color: var(--texto-3); }}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
"""


def aplicar_estilo():
    """Injeta o CSS global e configura o Matplotlib (uma vez por execução, no app.py)."""
    st.html(f"<style>{CSS}</style>")
    estilo_matplotlib()


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------

def _md(texto):
    """Converte o Markdown simples dos textos (negrito e cifrão escapado) para HTML."""
    texto = html.escape(texto.replace("\\$", "$"), quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)


def cabecalho(titulo, descricao, metadados=True):
    meta = f'<div class="meta">{html.escape(METADADOS)}</div>' if metadados else ""
    st.html(f'<div class="cab"><h1>{html.escape(titulo)}</h1><p>{_md(descricao)}</p>{meta}</div>')


def secao(titulo, descricao=""):
    desc = f"<p>{_md(descricao)}</p>" if descricao else ""
    st.html(f'<div class="secao"><h3>{html.escape(titulo)}</h3>{desc}</div>')


def insight(texto, rotulo="Interpretação"):
    if texto:
        st.html(f'<div class="interp"><span class="r">{html.escape(rotulo)}</span><div>{_md(texto)}</div></div>')


def _fmt(valor, casas):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def cartoes_kpi(cartoes):
    """Cartões de KPI com contagem suave até o valor.

    Cada cartão: rotulo, valor (número) ou texto, casas, prefixo, sufixo, apoio (HTML curto).
    """
    id_grade = "k" + uuid.uuid4().hex[:10]
    partes = []
    for c in cartoes:
        if c.get("texto") is not None:
            corpo = html.escape(str(c["texto"]))
        else:
            casas = c.get("casas", 2)
            pre = f'<span class="pre">{html.escape(c["prefixo"])}</span>' if c.get("prefixo") else ""
            suf = f'<span class="suf">{html.escape(c["sufixo"])}</span>' if c.get("sufixo") else ""
            sinal = "+" if c.get("sinal") and c["valor"] > 0 else ""
            tom = f' class="{c["tom"]}"' if c.get("tom") else ""
            corpo = (f'<span{tom}>{pre}<span class="contador" data-alvo="{c["valor"]:.{casas}f}" data-casas="{casas}"'
                     f'{" data-sinal=1" if c.get("sinal") else ""}>{sinal}{_fmt(c["valor"], casas)}</span>{suf}</span>')
        partes.append(f'<div class="kpi"><div class="rot">{html.escape(c["rotulo"])}</div>'
                      f'<div class="val">{corpo}</div><div class="apoio">{c.get("apoio", "")}</div></div>')
    script = """
<script>
(function () {
  const grade = document.getElementById(%s);
  if (!grade || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  grade.querySelectorAll('.contador').forEach(function (el) {
    const alvo = parseFloat(el.dataset.alvo), casas = parseInt(el.dataset.casas, 10);
    const fmt = new Intl.NumberFormat('pt-BR', {minimumFractionDigits: casas, maximumFractionDigits: casas,
                                                 signDisplay: el.dataset.sinal ? 'exceptZero' : 'auto'});
    const inicio = performance.now(), dur = 700;
    function passo(t) {
      const p = Math.min(1, (t - inicio) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt.format(alvo * e);
      if (p < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  });
})();
</script>""" % json.dumps(id_grade)
    classe = "kpis seis" if len(cartoes) == 6 else "kpis"
    st.html(f'<div class="{classe}" id="{id_grade}">{"".join(partes)}</div>{script}', unsafe_allow_javascript=True)
