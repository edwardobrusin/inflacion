import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import base64
import os

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO
# ==============================================================================

st.set_page_config(
    page_title="Resumen Inflación | Dirección de Estudios Económicos",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .block-container {
        padding-top: 1.0rem !important;
        padding-bottom: 1.0rem !important;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #0F172A;
    }

    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 5px;
    }

    .metric-title {
        color: #64748B;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }

    .metric-value {
        color: #0F172A;
        font-size: 1.75rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        line-height: 1.2;
    }

    .metric-sub {
        color: #64748B;
        font-size: 0.78rem;
        margin-top: 2px;
    }

    .metric-line {
        color: #334155;
        font-size: 0.82rem;
        margin-top: 7px;
        font-variant-numeric: tabular-nums;
        line-height: 1.35;
    }

    .metric-line strong {
        color: #0F172A;
        font-weight: 700;
    }

    .chart-title {
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 6px;
        font-size: 0.95rem;
    }

    .small-card {
        min-height: 165px;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 8px;
    }

    .stat-box {
        background-color: #F8FAFC;
        border: 1px solid #EEF2F7;
        border-radius: 6px;
        padding: 8px;
    }

    .stat-label {
        color: #64748B;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
    }

    .stat-value {
        font-size: 1.05rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }

    .stat-note {
        color: #64748B;
        font-size: 0.66rem;
        margin-top: 3px;
        font-variant-numeric: tabular-nums;
    }

    div[data-testid="stDataFrame"] {
        font-variant-numeric: tabular-nums;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# PALETA INSTITUCIONAL
# ==============================================================================

COLOR_PRIMARIO = "#2596BE"
COLOR_SECUNDARIO = "#008889"
COLOR_TERCIARIO = "#73C6E3"
COLOR_TEXTO = "#0F172A"
COLOR_GRID = "#F1F5F9"
COLOR_BORDER = "#E2E8F0"

# ==============================================================================
# UTILIDADES DE FECHA Y DATOS
# ==============================================================================

MESES_ABREV = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
}

MESES_COMPLETOS = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}


def parse_dates_safe(series: pd.Series) -> pd.Series:
    """
    Parsea fechas de forma resiliente, priorizando formato DD/MM/AAAA
    y usando AAAA/MM/DD como respaldo.
    """
    cleaned = series.astype(str).str.strip().str.split(" ").str[0]
    cleaned = cleaned.str.replace("-", "/")

    parsed = pd.to_datetime(cleaned, format="%d/%m/%Y", errors="coerce")

    if parsed.isna().sum() > 0:
        fallback = pd.to_datetime(cleaned, format="%Y/%m/%d", errors="coerce")
        parsed = parsed.combine_first(fallback)

    return parsed


@st.cache_data
def load_data():
    # 1. Niveles
    df_niv = pd.read_csv("data/intermediate/niveles.csv")
    df_niv.columns = df_niv.columns.str.strip()
    df_niv["Fecha"] = parse_dates_safe(df_niv["Fecha"])
    df_niv = df_niv.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)
    df_niv["Periodo"] = df_niv["Fecha"].dt.month.map(MESES_ABREV) + "-" + df_niv["Fecha"].dt.year.astype(str)
    df_niv["Anio_Mes"] = df_niv["Fecha"].dt.strftime("%Y-%m")

    # 2. Genéricos
    df_gen = pd.read_csv("data/intermediate/genericos.csv")
    df_gen.columns = df_gen.columns.str.strip()
    df_gen["Fecha"] = parse_dates_safe(df_gen["Fecha"])
    df_gen = df_gen.dropna(subset=["Fecha"]).sort_values(["Fecha", "Concepto"]).reset_index(drop=True)
    df_gen["Periodo"] = df_gen["Fecha"].dt.month.map(MESES_ABREV) + "-" + df_gen["Fecha"].dt.year.astype(str)
    df_gen["Anio_Mes"] = df_gen["Fecha"].dt.strftime("%Y-%m")

    return df_niv, df_gen


try:
    df_niveles, df_genericos = load_data()
except Exception as e:
    st.error(
        f"Error al leer archivos de datos: {e}. "
        "Verifique que 'data/intermediate/niveles.csv' y "
        "'data/intermediate/genericos.csv' existan y tengan registros válidos."
    )
    st.stop()

if df_niveles.empty:
    st.error("El archivo 'niveles.csv' no contiene registros de fecha válidos.")
    st.stop()


def get_num(row, col: str) -> float:
    """Extrae un valor numérico de una fila con tolerancia a faltantes."""
    try:
        value = row[col]
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def color_delta(value: float) -> str:
    """Rojo para presión inflacionaria, verde para descenso."""
    if value > 0:
        return "#DC2626"
    if value < 0:
        return "#16A34A"
    return "#64748B"


# ==============================================================================
# SIDEBAR: SOLO RANGO DE PERIODO
# ==============================================================================

with st.sidebar:
    st.markdown("### Rango de análisis")

    periodos_disponibles = df_niveles["Anio_Mes"].unique().tolist()

    if len(periodos_disponibles) == 0:
        st.error("No hay periodos disponibles en la base de niveles.")
        st.stop()

    if len(periodos_disponibles) == 1:
        p_inicio = periodos_disponibles[0]
        p_fin = periodos_disponibles[0]
        st.info(f"Único periodo disponible: {p_inicio}")
    else:
        # Por defecto: últimos 13 meses.
        default_start = (
            periodos_disponibles[-13]
            if len(periodos_disponibles) >= 13
            else periodos_disponibles[0]
        )
        default_end = periodos_disponibles[-1]

        p_inicio, p_fin = st.select_slider(
            "Horizonte temporal (Mes/Año):",
            options=periodos_disponibles,
            value=(default_start, default_end)
        )

    st.markdown("---")
    st.caption(
        "Por defecto se muestran los últimos 13 meses para incluir el mes más "
        "reciente y su comparable del año previo."
    )

# ==============================================================================
# FILTRO DE DATOS SEGÚN PERIODO SELECCIONADO
# ==============================================================================

df_niv_filtered = df_niveles[
    (df_niveles["Anio_Mes"] >= p_inicio) &
    (df_niveles["Anio_Mes"] <= p_fin)
].reset_index(drop=True)

if df_niv_filtered.empty:
    st.error("El rango seleccionado no contiene datos.")
    st.stop()

ultimo_registro = df_niv_filtered.iloc[-1]
fecha_actual = ultimo_registro["Fecha"]

# Para calcular cambios MoMio y vs mismo mes del año previo,
# se usa la base completa, no solo el rango filtrado.
idx_matches = df_niveles.index[df_niveles["Fecha"] == fecha_actual]

if len(idx_matches) > 0:
    idx_actual = int(idx_matches[0])
else:
    idx_actual = int(df_niveles.index[-1])

registro_previo = (
    df_niveles.iloc[idx_actual - 1]
    if idx_actual >= 1
    else ultimo_registro
)

registro_previo_anio = (
    df_niveles.iloc[idx_actual - 12]
    if idx_actual >= 12
    else ultimo_registro
)

# Métrica fija para el resumen ejecutivo: anual.
VAR_ANUAL = "Var_Anual"
INC_ANUAL = "Inc_Anual"

# ==============================================================================
# FUNCIONES DE FORMATO PARA GRÁFICAS
# ==============================================================================


def aplicar_layout_base(fig, height: int = 340, hovermode: str = "x unified", is_timeseries: bool = False):
    """
    Layout institucional claro para gráficas de línea / barras / waterfall.
    """
    xaxis_dict = dict(
        gridcolor=COLOR_GRID,
        linecolor=COLOR_BORDER,
        tickcolor=COLOR_BORDER
    )
    if is_timeseries and len(fig.data) > 0:
        fechas = pd.to_datetime(pd.Series(fig.data[0].x)).dropna().drop_duplicates().sort_values()
        meses_lower = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
        }
        ticktext = fechas.dt.month.map(meses_lower) + "-" + fechas.dt.strftime("%y")
        xaxis_dict.update(dict(
            tickangle=-90,
            tickmode="array",
            tickvals=fechas,
            ticktext=ticktext
        ))

    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=15, r=15, t=35, b=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_TEXTO, family="Inter"),
        hovermode=hovermode,
        xaxis=xaxis_dict,
        yaxis=dict(
            gridcolor=COLOR_GRID,
            linecolor=COLOR_BORDER,
            tickcolor=COLOR_BORDER
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=COLOR_BORDER,
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        )
    )
    return fig


def aplicar_layout_heatmap(fig, height: int = 430):
    """
    Layout específico para mapas de calor.
    """
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=15, t=25, b=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_TEXTO, family="Inter"),
        coloraxis_showscale=False
    )

    fig.update_xaxes(
        title_text="",
        side="bottom",
        tickangle=-90,
        gridcolor=COLOR_GRID,
        linecolor=COLOR_BORDER,
        tickcolor=COLOR_BORDER
    )

    fig.update_yaxes(
        autorange="reversed",
        gridcolor=COLOR_GRID,
        linecolor=COLOR_BORDER,
        tickcolor=COLOR_BORDER
    )

    return fig


def calc_inc_int(df, child_inc_col: str, parent_inc_col: str, parent_var_col: str):
    """
    Calcula la incidencia interna proporcional:
    (incidencia hijo / incidencia padre) * variación del padre.
    """
    child_inc = (
        df[child_inc_col]
        .fillna(0)
        .astype(float)
        .replace([np.inf, -np.inf], 0)
    )

    parent_inc = (
        df[parent_inc_col]
        .fillna(0)
        .astype(float)
        .replace([np.inf, -np.inf], 0)
    )

    parent_var = (
        df[parent_var_col]
        .fillna(0)
        .astype(float)
        .replace([np.inf, -np.inf], 0)
    )

    ratio = np.divide(
        child_inc.values,
        parent_inc.values,
        out=np.zeros_like(child_inc.values, dtype=float),
        where=parent_inc.values != 0
    )

    return ratio * parent_var.values


# ==============================================================================
# FUNCIONES DE TARJETAS KPI
# ==============================================================================


def remove_html_newlines(html_text: str) -> str:
    """
    Elimina los saltos de línea del HTML para evitar que el renderizador 
    de Markdown de Streamlit inserte etiquetas <p> o <br> que rompan el diseño.
    """
    return html_text.replace("\n", "")


def render_kpi_card(title: str, prefix: str, border_color: str):
    """
    Tarjeta KPI para INPC General, Subyacente y No Subyacente.
    Muestra variación anual como cifra principal, además de variación mensual,
    incidencias y cambios contra mes previo / mismo mes del año previo.
    """
    v_a = get_num(ultimo_registro, f"{prefix}_Var_Anual")
    v_m = get_num(ultimo_registro, f"{prefix}_Var_Mensual")
    i_a = get_num(ultimo_registro, f"{prefix}_Inc_Anual")
    i_m = get_num(ultimo_registro, f"{prefix}_Inc_Mensual")

    d_prev = v_a - get_num(registro_previo, f"{prefix}_Var_Anual")
    d_year = v_a - get_num(registro_previo_anio, f"{prefix}_Var_Anual")

    c_prev = color_delta(d_prev)
    c_year = color_delta(d_year)

    html = f"""
    <div class="metric-card" style="border-top: 3px solid {border_color};">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{v_a:.2f}%</div>
        <div class="metric-sub">Variación anual</div>

        <div class="metric-line">
            Mensual: <strong>{v_m:.2f}%</strong>
            &nbsp;·&nbsp;
            Incidencia mensual: <strong>{i_m:.2f} pp</strong>
        </div>

        <div class="metric-line">
            Incidencia anual: <strong>{i_a:.2f} pp</strong>
        </div>

        <div class="metric-line">
            Variación anual vs. mes previo:
            <strong style="color:{c_prev};">{d_prev:+.2f} pp</strong>
            &nbsp;·&nbsp;
            vs. mismo mes año previo:
            <strong style="color:{c_year};">{d_year:+.2f} pp</strong>
        </div>
    </div>
    """

    st.markdown(remove_html_newlines(html), unsafe_allow_html=True)


def render_subcomponent_card(col_id: str, label: str):
    """
    Tarjeta detallada para cada subcomponente.
    """
    v_a = get_num(ultimo_registro, f"{col_id}_Var_Anual")
    v_m = get_num(ultimo_registro, f"{col_id}_Var_Mensual")
    i_a = get_num(ultimo_registro, f"{col_id}_Inc_Anual")
    i_m = get_num(ultimo_registro, f"{col_id}_Inc_Mensual")

    d_a_p = v_a - get_num(registro_previo, f"{col_id}_Var_Anual")
    d_a_a = v_a - get_num(registro_previo_anio, f"{col_id}_Var_Anual")
    d_m_p = v_m - get_num(registro_previo, f"{col_id}_Var_Mensual")
    d_m_a = v_m - get_num(registro_previo_anio, f"{col_id}_Var_Mensual")

    c_va = color_delta(v_a)
    c_vm = color_delta(v_m)

    html = f"""
    <div class="metric-card small-card">
        <div class="metric-title" style="color:{COLOR_PRIMARIO}; font-size:0.82rem;">
            {label}
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-label">Anual</div>
                <div class="stat-value" style="color:{c_va};">{v_a:.2f}%</div>
                <div class="stat-note">Incidencia: {i_a:.2f} pp</div>
                <div class="stat-note">vs. mes previo: {d_a_p:+.2f} pp</div>
                <div class="stat-note">vs. año previo: {d_a_a:+.2f} pp</div>
            </div>

            <div class="stat-box">
                <div class="stat-label">Mensual</div>
                <div class="stat-value" style="color:{c_vm};">{v_m:.2f}%</div>
                <div class="stat-note">Incidencia: {i_m:.2f} pp</div>
                <div class="stat-note">vs. mes previo: {d_m_p:+.2f} pp</div>
                <div class="stat-note">vs. año previo: {d_m_a:+.2f} pp</div>
            </div>
        </div>
    </div>
    """

    st.markdown(remove_html_newlines(html), unsafe_allow_html=True)


# ==============================================================================
# FUNCIONES DE GRÁFICAS
# ==============================================================================


def fig_trayectoria_inpc(df):
    """
    3.1 Trayectoria del INPC: General, Subyacente y No Subyacente con rango Banxico.
    Sin leyendas internas para evitar desbordes.
    """
    fig = go.Figure()

    fig.add_hrect(
        y0=2.0,
        y1=4.0,
        fillcolor="#10B981",
        opacity=0.10,
        line_width=0
    )

    fig.add_hline(
        y=3.0,
        line_dash="dash",
        line_color="#10B981",
        opacity=0.6
    )

    fig.add_trace(go.Scatter(
        x=df["Fecha"],
        y=df[f"INPC_General_{VAR_ANUAL}"],
        mode="lines+markers",
        name="INPC General",
        line=dict(color="#000000", width=2.5),
        marker=dict(size=4),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=df["Fecha"],
        y=df[f"Subyacente_{VAR_ANUAL}"],
        mode="lines",
        name="Subyacente",
        line=dict(color="#008889", width=2),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=df["Fecha"],
        y=df[f"No_Subyacente_{VAR_ANUAL}"],
        mode="lines",
        name="No Subyacente",
        line=dict(color="#1E40AF", width=2),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    aplicar_layout_base(fig, height=430, is_timeseries=True)
    fig.update_layout(
        showlegend=False,
        margin=dict(l=15, r=15, t=10, b=15)
    )
    return fig


def fig_incidencias_subcomponentes(df):
    """
    3.2 Evolución de Incidencias Históricas por Subcomponente.
    Barras apiladas a ancho completo sin barra lateral de leyendas.
    """
    fig = go.Figure()

    subcomps_cols = [
        ("Alimentos_Bebidas_Tabaco", "#008889", "Alimentos, Bebidas y Tabaco"),
        ("Mercancias_No_Alimenticias", "#20B2AA", "Mercancías No Alimenticias"),
        ("Vivienda", "#48D1CC", "Vivienda"),
        ("Educacion", "#40E0D0", "Educación"),
        ("Otros_Servicios", "#7FFFD4", "Otros Servicios"),
        ("Frutas_Verduras", "#60A5FA", "Frutas y Verduras"),
        ("Pecuarios", "#1D4ED8", "Pecuarios"),
        ("Energeticos", "#A78BFA", "Energéticos"),
        ("Tarifas_Autorizadas", "#6D28D9", "Tarifas Autorizadas")
    ]

    for col, color, name in subcomps_cols:
        fig.add_trace(go.Bar(
            x=df["Fecha"],
            y=df[f"{col}_{INC_ANUAL}"].fillna(0),
            name=name,
            marker_color=color,
            hovertemplate="%{y:.3f} pp<extra></extra>"
        ))

    fig.add_trace(go.Scatter(
        x=df["Fecha"],
        y=df[f"INPC_General_{VAR_ANUAL}"],
        name="INPC General",
        mode="lines",
        line=dict(color=COLOR_TEXTO, width=2.5),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    aplicar_layout_base(fig, height=350, is_timeseries=True)
    fig.update_layout(
        barmode="relative",
        showlegend=False,
        margin=dict(l=15, r=15, t=10, b=15)
    )
    return fig


def fig_cascada_incidencia(current_row):
    """
    3.3 Cascada de Incidencia Aditiva Desglosada.
    Limpia, con línea divisoria minimalista y sin fondos translúcidos invasivos.
    """
    import textwrap
    x_labels_full = [
        "Alimentos, Bebidas y Tabaco",
        "Mercancías No Alimenticias",
        "Vivienda",
        "Educación",
        "Otros Servicios",
        "Frutas y Verduras",
        "Pecuarios",
        "Energéticos",
        "Tarifas Autorizadas",
        "INPC Total"
    ]
    x_labels = ["<br>".join(textwrap.wrap(l, width=18)) for l in x_labels_full]

    components = [
        "Alimentos_Bebidas_Tabaco",
        "Mercancias_No_Alimenticias",
        "Vivienda",
        "Educacion",
        "Otros_Servicios",
        "Frutas_Verduras",
        "Pecuarios",
        "Energeticos",
        "Tarifas_Autorizadas"
    ]

    y_values = [
        get_num(current_row, f"{comp}_{INC_ANUAL}")
        for comp in components
    ]

    total_value = get_num(current_row, f"INPC_General_{VAR_ANUAL}")
    measures = ["relative"] * 9 + ["total"]
    text_values = [f"{v:.3f}" for v in y_values] + [f"{total_value:.2f}%"]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=x_labels,
        y=y_values,
        textposition="outside",
        text=text_values,
        textfont=dict(size=10, color=COLOR_TEXTO, family="Inter"),
        connector={"line": {"color": "#CBD5E1", "width": 1.5, "dash": "dot"}},
        decreasing={"marker": {"color": "#16A34A"}},
        increasing={"marker": {"color": "#DC2626"}},
        totals={"marker": {"color": COLOR_PRIMARIO}},
        hovertemplate="%{x}: %{y:.3f} pp<extra></extra>",
        cliponaxis=False
    ))

    # Línea vertical divisoria limpia entre Subyacente y No Subyacente
    fig.add_vline(
        x=4.5,
        line_dash="dash",
        line_color="#94A3B8",
        line_width=1.5,
        opacity=0.8
    )

    def _zona(x0, x1, color, pasos=14):
        for k in range(pasos):
            fig.add_shape(
                type="rect", xref="x", yref="paper",
                x0=x0, x1=x1, y0=1 - (k + 1) / pasos, y1=1 - k / pasos,
                fillcolor=color, opacity=0.06 + 0.22 * (1 - k / pasos),
                layer="below", line_width=0
            )

    _zona(-0.5, 4.5, "#008889")
    _zona(4.5, 8.5, "#1E40AF")

    aplicar_layout_base(fig, height=450, hovermode="closest")
    fig.update_layout(
        showlegend=False,
        margin=dict(l=15, r=15, t=15, b=35)
    )
    fig.update_xaxes(
        tickangle=-90,
        tickfont=dict(size=11.5)
    )
    fig.update_yaxes(showgrid=False)
    return fig


def render_grafica_incidencia_interna(
    titulo: str,
    df: pd.DataFrame,
    bars: list,
    parent_inc_col: str,
    parent_var_col: str,
    parent_name: str,
    height: int = 340
):
    """
    Renderiza el título, la leyenda institucional en HTML nativo (flexbox)
    y la gráfica de Plotly limpia, garantizando que nunca se corten ni se sobrepongan.
    """
    items_html = []
    for _, name, color in bars:
        items_html.append(
            f'<div style="display:flex; align-items:center; gap:5px;">'
            f'<span style="width:10px; height:10px; background-color:{color}; border-radius:2px; display:inline-block; flex-shrink:0;"></span>'
            f'<span style="color:#000000; font-size:0.75rem; font-weight:500;">{name} (pp)</span>'
            f'</div>'
        )

    items_html.append(
        f'<div style="display:flex; align-items:center; gap:5px;">'
        f'<span style="width:13px; height:2.5px; background-color:{COLOR_TEXTO}; display:inline-block; flex-shrink:0;"></span>'
        f'<span style="color:#0F172A; font-size:0.75rem; font-weight:500;">{parent_name} (Var. Anual %)</span>'
        f'</div>'
    )

    leyenda_str = "".join(items_html)

    header_html = f"""
    <div style="margin-bottom: 4px;">
        <div class="chart-title" style="margin-bottom: 4px;">{titulo}</div>
        <div style="display:flex; flex-wrap:wrap; align-items:center; gap:6px 12px; min-height:22px; padding-bottom:2px;">
            {leyenda_str}
        </div>
    </div>
    """
    st.markdown(remove_html_newlines(header_html), unsafe_allow_html=True)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Fecha"],
        y=df[parent_var_col],
        name=parent_name,
        mode="lines",
        line=dict(color=COLOR_TEXTO, width=2.4),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    for child_inc_col, name, color in bars:
        y_vals = calc_inc_int(
            df,
            child_inc_col=child_inc_col,
            parent_inc_col=parent_inc_col,
            parent_var_col=parent_var_col
        )
        fig.add_trace(go.Bar(
            x=df["Fecha"],
            y=y_vals,
            name=name,
            marker_color=color,
            text=y_vals,
            texttemplate="%{text:.3f}",
            textposition="auto",
            cliponaxis=False,
            hovertemplate="%{y:.3f} pp<extra></extra>"
        ))

    fig.update_layout(barmode="relative")
    aplicar_layout_base(fig, height=height, is_timeseries=True)

    fig.update_layout(
        showlegend=False,
        margin=dict(l=15, r=15, t=25, b=15)
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False}
    )


def fig_heatmap(df_matrix: pd.DataFrame, height: int = 430, text_format: str = ".2f"):
    """
    Mapa de calor para variación o incidencia.
    Si la matriz incluye la fila 'INPC General', se dibuja como un panel aparte:
    escala de color propia, contorno oscuro y etiqueta en negritas.
    """
    escala_sub = ["#16A34A", "#F8FAFC", "#DC2626"]
    # INPC General: misma paleta que los subcomponentes, pero centrada en la meta de 3%.
    # Verde intenso = 3%; rojo = el valor más alejado de 3% en el periodo seleccionado.
    escala_gen = ["#DC2626", "#F8FAFC", "#16A34A", "#F8FAFC", "#DC2626"]

    def _max_abs(m: pd.DataFrame) -> float:
        vals = m.values.astype(float)
        if vals.size == 0 or np.all(np.isnan(vals)):
            return 1.0
        mx = float(np.nanmax(np.abs(vals)))
        return 1.0 if (pd.isna(mx) or mx == 0) else mx

    def _heat(m: pd.DataFrame, escala, texto: str, size: int, zrange=None):
        mx = _max_abs(m)
        zmin, zmax = zrange if zrange else (-mx, mx)
        return go.Heatmap(
            z=m.values.astype(float),
            x=list(m.columns),
            y=list(m.index),
            colorscale=escala,
            zmin=zmin,
            zmax=zmax,
            showscale=False,
            texttemplate=texto,
            textfont=dict(size=size, family="Inter"),
            hovertemplate=f"%{{y}} | %{{x}}<br>Valor: %{{z:{text_format}}}<extra></extra>"
        )

    if "INPC General" not in df_matrix.index:
        fig = go.Figure(_heat(df_matrix, escala_sub, f"%{{z:{text_format}}}", 11))
        aplicar_layout_heatmap(fig, height=height)
        return fig

    df_gen = df_matrix.loc[["INPC General"]]
    df_sub = df_matrix.drop(index="INPC General")

    dist_max = float(np.nanmax(np.abs(df_gen.values.astype(float) - 3.0)))
    if pd.isna(dist_max) or dist_max == 0:
        dist_max = 1.0

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[1.25, float(len(df_sub))]
    )
    fig.add_trace(_heat(df_gen, escala_gen, f"<b>%{{z:{text_format}}}</b>", 12, zrange=(3.0 - dist_max, 3.0 + dist_max)), row=1, col=1)
    fig.add_trace(_heat(df_sub, escala_sub, f"%{{z:{text_format}}}", 11), row=2, col=1)

    aplicar_layout_heatmap(fig, height=height + 46)
    fig.update_layout(margin=dict(l=10, r=15, t=34, b=15))

    fig.update_yaxes(
        tickvals=["INPC General"],
        ticktext=["<b>INPC GENERAL</b>"],
        row=1, col=1
    )

    fig.add_shape(
        type="rect", xref="x domain", yref="y domain",
        x0=0, x1=1, y0=0, y1=1,
        line=dict(color=COLOR_TEXTO, width=2.5),
        fillcolor="rgba(0,0,0,0)"
    )
    fig.add_annotation(
        text="Escala de color independiente con referencia en el rango de 3±1% del Banco de México",
        xref="x domain", yref="y domain",
        x=1, y=1, xanchor="right", yanchor="bottom",
        showarrow=False,
        font=dict(size=10, color="#64748B")
    )

    return fig


def fig_ranking_genericos(
    df_corte: pd.DataFrame,
    col_rank: str,
    ascending: bool,
    color: str,
    text_format: str = ".2f",
    height: int = 340
):
    """
    Ranking horizontal de genéricos por incidencia o variación.
    Con margen dinámico del 25% y espaciado para que las etiquetas no queden pegadas.
    """
    if df_corte.empty or col_rank not in df_corte.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Sin datos disponibles",
            showarrow=False
        )
        aplicar_layout_base(fig, height=height, hovermode="closest")
        return fig

    top = (
        df_corte
        .dropna(subset=[col_rank, "Concepto"])
        .sort_values(col_rank, ascending=ascending)
        .head(10)
        .copy()
    )

    if top.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Sin datos disponibles",
            showarrow=False
        )
        aplicar_layout_base(fig, height=height, hovermode="closest")
        return fig

    import textwrap
    top["Concepto_Wrap"] = top["Concepto"].apply(lambda x: "<br>".join(textwrap.wrap(x, width=30)))

    # Espacio seguro entre la punta de la barra y el número
    plantilla_texto = f"&nbsp;%{{x:{text_format}}}" if not ascending else f"%{{x:{text_format}}}&nbsp;"

    fig = px.bar(
        top,
        x=col_rank,
        y="Concepto_Wrap",
        orientation="h",
        color_discrete_sequence=[color],
        text=col_rank
    )

    fig.update_traces(
        texttemplate=plantilla_texto,
        textposition="outside",
        textfont=dict(size=10.5, family="Inter", color="#334155"),
        hovertemplate="%{y}<br>%{x}<extra></extra>",
        cliponaxis=False
    )

    aplicar_layout_base(fig, height=height, hovermode="closest")

    val_min = top[col_rank].min()
    val_max = top[col_rank].max()

    # Rango holgado: anclado a cero para que las barras positivas tengan 25% de aire a la derecha
    # y las negativas tengan 25% de aire a la izquierda
    if not ascending:  # Al alza (positivo)
        x_rango = [0, val_max * 1.25 if val_max > 0 else 1.0]
    else:  # A la baja (negativo)
        x_rango = [val_min * 1.25 if val_min < 0 else -1.0, 0]

    fig.update_layout(
        margin=dict(l=0, r=50, t=15, b=15),
        showlegend=False,
        yaxis=dict(
            title="",
            autorange="reversed",
            tickfont=dict(size=11),
            gridcolor=COLOR_GRID,
            linecolor=COLOR_BORDER,
            tickcolor=COLOR_BORDER
        ),
        xaxis=dict(
            title="",
            range=x_rango,
            gridcolor=COLOR_GRID,
            linecolor=COLOR_BORDER,
            tickcolor=COLOR_BORDER
        )
    )

    return fig


# ==============================================================================
# ENCABEZADO PRINCIPAL
# ==============================================================================

mes_largo = MESES_COMPLETOS[ultimo_registro["Fecha"].month]
anio_corte = ultimo_registro["Fecha"].year
periodo_largo = f"{mes_largo} {anio_corte}"

# ==============================================================================
# BOTÓN FLOTANTE DE DESCARGA
# ==============================================================================

ruta_pdf = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "resumen_inflacion.pdf"
)

if os.path.exists(ruta_pdf):
    with open(ruta_pdf, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")

    svg_icon = '''
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" style="width: 24px; height: 24px;">
  <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
</svg>
'''

    html_boton = f"""
<style>
    .floating-download-btn {{
        position: fixed;
        bottom: 50px;
        right: 20px;
        background-color: #2596BE;
        color: white !important;
        border-radius: 50%;
        width: 56px;
        height: 56px;
        display: flex;
        justify-content: center;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
        text-decoration: none;
    }}

    .floating-download-btn:hover {{
        background-color: #1E7A9B;
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }}
</style>

<a href="data:application/pdf;base64,{base64_pdf}"
   download="Resumen_Inflacion.pdf"
   class="floating-download-btn"
   title="Descargar PDF">
    {svg_icon}
</a>
"""

    st.markdown(html_boton, unsafe_allow_html=True)

else:
    st.markdown(
        """
<style>
.floating-warning {
    position: fixed;
    bottom: 50px;
    right: 20px;
    background-color: #64748B;
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 0.8rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    z-index: 9999;
}
</style>

<div class="floating-warning">Actualizando PDF...</div>
""",
        unsafe_allow_html=True,
    )

st.title(f"Resumen Inflación ({mes_largo.capitalize()} {anio_corte})")

# ==============================================================================
# 2. TARJETAS RESUMEN: GENERAL, SUBYACENTE Y NO SUBYACENTE
# ==============================================================================

st.markdown("""
<style>
.metric-delta {
    font-size: 0.85rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    margin-top: 6px;
}
.delta-up { color: #DC2626; }
.delta-down { color: #16A34A; }
.delta-neutral { color: #64748B; }
</style>
""", unsafe_allow_html=True)

# Fila 1: Indicadores Anuales
k_a1, k_a2, k_a3 = st.columns(3)

with k_a1:
    v_actual_a = ultimo_registro['INPC_General_Var_Anual']
    delta_a_prev = v_actual_a - registro_previo['INPC_General_Var_Anual']
    delta_a_anio = v_actual_a - registro_previo_anio['INPC_General_Var_Anual']
    c_a_prev = '#DC2626' if delta_a_prev > 0 else '#16A34A' if delta_a_prev < 0 else '#64748B'
    c_a_anio = '#DC2626' if delta_a_anio > 0 else '#16A34A' if delta_a_anio < 0 else '#64748B'
    st.markdown(f"""
<div class="metric-card">
    <div class="metric-title">General (Anual)</div>
    <div class="metric-value">{v_actual_a:.2f}%</div>
    <div class="metric-delta delta-neutral">
        MoM: <span style="color: {c_a_prev}; font-weight: 700;">{delta_a_prev:+.2f} pp</span> &nbsp;|&nbsp; 
        YoY: <span style="color: {c_a_anio}; font-weight: 700;">{delta_a_anio:+.2f} pp</span>
    </div>
</div>
""", unsafe_allow_html=True)

    subyacente_comps = ["Alimentos_Bebidas_Tabaco", "Mercancias_No_Alimenticias", "Vivienda", "Educacion", "Otros_Servicios"]
    nosubyacente_comps = ["Frutas_Verduras", "Pecuarios", "Energeticos", "Tarifas_Autorizadas"]
    inc_sub_exact = sum(get_num(ultimo_registro, f"{c}_{INC_ANUAL}") for c in subyacente_comps)
    inc_nosub_exact = sum(get_num(ultimo_registro, f"{c}_{INC_ANUAL}") for c in nosubyacente_comps)

with k_a2:
    st.markdown(f"""
<div class="metric-card">
    <div class="metric-title">Subyacente (Anual)</div>
    <div class="metric-value">{ultimo_registro['Subyacente_Var_Anual']:.2f}%</div>
    <div class="metric-delta" style="color: {COLOR_SECUNDARIO};">Incidencia Anual: {inc_sub_exact:.3f} pp</div>
</div>
""", unsafe_allow_html=True)

with k_a3:
    st.markdown(f"""
<div class="metric-card">
    <div class="metric-title">No Subyacente (Anual)</div>
    <div class="metric-value">{ultimo_registro['No_Subyacente_Var_Anual']:.2f}%</div>
    <div class="metric-delta" style="color: #1E40AF;">Incidencia Anual: {inc_nosub_exact:.3f} pp</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# Fila 2: Indicadores Mensuales
k_m1, k_m2, k_m3 = st.columns(3)

with k_m1:
    v_actual_m = ultimo_registro['INPC_General_Var_Mensual']
    delta_m_prev = v_actual_m - registro_previo['INPC_General_Var_Mensual']
    delta_m_anio = v_actual_m - registro_previo_anio['INPC_General_Var_Mensual']
    c_m_prev = '#DC2626' if delta_m_prev > 0 else '#16A34A' if delta_m_prev < 0 else '#64748B'
    c_m_anio = '#DC2626' if delta_m_anio > 0 else '#16A34A' if delta_m_anio < 0 else '#64748B'
    st.markdown(f"""
<div class="metric-card">
    <div class="metric-title">General (Mensual)</div>
    <div class="metric-value">{v_actual_m:.2f}%</div>
    <div class="metric-delta delta-neutral">
        MoM: <span style="color: {c_m_prev}; font-weight: 700;">{delta_m_prev:+.2f} pp</span> &nbsp;|&nbsp; 
        YoY: <span style="color: {c_m_anio}; font-weight: 700;">{delta_m_anio:+.2f} pp</span>
    </div>
</div>
""", unsafe_allow_html=True)

    inc_sub_exact_m = sum(get_num(ultimo_registro, f"{c}_Inc_Mensual") for c in subyacente_comps)
    inc_nosub_exact_m = sum(get_num(ultimo_registro, f"{c}_Inc_Mensual") for c in nosubyacente_comps)

with k_m2:
    st.markdown(f"""
<div class="metric-card">
    <div class="metric-title">Subyacente (Mensual)</div>
    <div class="metric-value">{ultimo_registro['Subyacente_Var_Mensual']:.2f}%</div>
    <div class="metric-delta" style="color: {COLOR_SECUNDARIO};">Incidencia Mensual: {inc_sub_exact_m:.3f} pp</div>
</div>
""", unsafe_allow_html=True)

with k_m3:
    st.markdown(f"""
<div class="metric-card">
    <div class="metric-title">No Subyacente (Mensual)</div>
    <div class="metric-value">{ultimo_registro['No_Subyacente_Var_Mensual']:.2f}%</div>
    <div class="metric-delta" style="color: #1E40AF;">Incidencia Mensual: {inc_nosub_exact_m:.3f} pp</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 3.1 Y 3.3: TRAYECTORIA Y CASCADA DE INCIDENCIA
# ==============================================================================

col_31, col_32 = st.columns(2)

with col_31:
    header_31 = f"""
    <div style="margin-bottom: 4px;">
        <div class="chart-title" style="margin-bottom: 4px;">Indice Nacional de Precios al Consumidor (Variación Anual en Por Ciento)</div>
        <div style="display:flex; flex-wrap:wrap; align-items:center; gap:6px 12px; min-height:22px; padding-bottom:2px;">
            <div style="display:flex; align-items:center; gap:5px;">
                <span style="width:13px; height:2.5px; background-color:#000000; display:inline-block;"></span>
                <span style="color:#000000; font-size:0.75rem; font-weight:500;">INPC General</span>
            </div>
            <div style="display:flex; align-items:center; gap:5px;">
                <span style="width:13px; height:2.5px; background-color:#008889; display:inline-block;"></span>
                <span style="color:#000000; font-size:0.75rem; font-weight:500;">Subyacente</span>
            </div>
            <div style="display:flex; align-items:center; gap:5px;">
                <span style="width:13px; height:2.5px; background-color:#1E40AF; display:inline-block;"></span>
                <span style="color:#000000; font-size:0.75rem; font-weight:500;">No Subyacente</span>
            </div>
        </div>
    </div>
    """
    st.markdown(remove_html_newlines(header_31), unsafe_allow_html=True)

    fig_31 = fig_trayectoria_inpc(df_niv_filtered)
    st.plotly_chart(
        fig_31,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with col_32:
    # Cálculo exacto de acumulados para los badges ejecutivos de la cascada
    sub_comps_list = ["Alimentos_Bebidas_Tabaco", "Mercancias_No_Alimenticias", "Vivienda", "Educacion", "Otros_Servicios"]
    nosub_comps_list = ["Frutas_Verduras", "Pecuarios", "Energeticos", "Tarifas_Autorizadas"]
    inc_sub_val = sum(get_num(ultimo_registro, f"{c}_{INC_ANUAL}") for c in sub_comps_list)
    inc_nosub_val = sum(get_num(ultimo_registro, f"{c}_{INC_ANUAL}") for c in nosub_comps_list)

    header_33 = f"""
    <div style="margin-bottom: 4px;">
        <div class="chart-title" style="margin-bottom: 4px;">Incidencia por Subcomponente en Puntos Porcentuales ({periodo_largo})</div>
        <div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; min-height:22px; padding-bottom:2px;">
            <div style="display:inline-flex; align-items:center; gap:5px; background-color:#F0FDFA; border:1px solid #99F6E4; padding:2px 8px; border-radius:4px;">
                <span style="width:7px; height:7px; background-color:{COLOR_SECUNDARIO}; border-radius:50%; display:inline-block;"></span>
                <span style="color:#115E59; font-size:0.74rem; font-weight:600;">Subyacente: <strong>{inc_sub_val:+.3f} pp</strong></span>
            </div>
            <div style="display:inline-flex; align-items:center; gap:5px; background-color:#EFF6FF; border:1px solid #BFDBFE; padding:2px 8px; border-radius:4px;">
                <span style="width:7px; height:7px; background-color:#3B82F6; border-radius:50%; display:inline-block;"></span>
                <span style="color:#1E40AF; font-size:0.74rem; font-weight:600;">No Subyacente: <strong>{inc_nosub_val:+.3f} pp</strong></span>
            </div>
            <div style="display:flex; align-items:center; gap:4px; margin-left:auto; font-size:0.72rem; color:#64748B;">
                <span style="width:8px; height:8px; background-color:#DC2626; border-radius:2px; display:inline-block;"></span> Aumento (+)
                <span style="width:8px; height:8px; background-color:#16A34A; border-radius:2px; display:inline-block; margin-left:4px;"></span> Disminución (-)
            </div>
        </div>
    </div>
    """
    st.markdown(remove_html_newlines(header_33), unsafe_allow_html=True)

    fig_33 = fig_cascada_incidencia(ultimo_registro)
    st.plotly_chart(
        fig_33,
        use_container_width=True,
        config={"displayModeBar": False}
    )

# ==============================================================================
# 3.2: EVOLUCIÓN DE INCIDENCIAS HISTÓRICAS POR SUBCOMPONENTE
# ==============================================================================

st.markdown('<div class="chart-title" style="margin-bottom: 4px;">Incidencias Históricas por Subcomponente</div>', unsafe_allow_html=True)

col_chart_32, col_leg_32 = st.columns([3, 1])

with col_chart_32:
    fig_32 = fig_incidencias_subcomponentes(df_niv_filtered)
    st.plotly_chart(
        fig_32,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with col_leg_32:
    header_32 = f"""
    <div style="font-size:0.77rem; padding-top:50px; padding-left:6px; font-family:'Inter', sans-serif;">
        <!-- INPC General arriba y como primer elemento -->
        <div style="display:inline-flex; align-items:center; gap:7px; background-color:#F8FAFC; border:1px solid #E2E8F0; padding:4px 10px; border-radius:5px; margin-bottom:12px; white-space:nowrap;">
            <span style="width:16px; height:2.5px; background-color:{COLOR_TEXTO}; display:inline-block; border-radius:1px;"></span>
            <span style="color:#0F172A; font-weight:700; font-size:0.78rem;">INPC General (Var. Anual %)</span>
        </div>
        
        <!-- Bloques Subyacente y No Subyacente en columnas con ancho suficiente -->
        <div style="display:flex; flex-direction:row; gap:18px; white-space:nowrap;">
            <div style="display:flex; flex-direction:column; gap:6px;">
                <span style="color:#008889; text-transform:uppercase; font-size:0.72rem; font-weight:700; letter-spacing:0.04em; margin-bottom:2px;">Subyacente</span>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#008889; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Alimentos, Bebidas y Tabaco</div>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#20B2AA; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Mercancías No Alimentarias</div>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#48D1CC; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Vivienda</div>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#40E0D0; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Educación</div>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#7FFFD4; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Otros Servicios</div>
            </div>
            <div style="display:flex; flex-direction:column; gap:6px;">
                <span style="color:#1E40AF; text-transform:uppercase; font-size:0.72rem; font-weight:700; letter-spacing:0.04em; margin-bottom:2px;">No Subyacente</span>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#60A5FA; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Frutas y Verduras</div>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#1D4ED8; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Pecuarios</div>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#A78BFA; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Energéticos</div>
                <div style="display:flex; align-items:center; gap:5px;"><span style="width:8px; height:8px; background-color:#6D28D9; border-radius:2px; display:inline-block; flex-shrink:0;"></span> Tarifas Autorizadas</div>
            </div>
        </div>
    </div>
    """
    st.markdown(remove_html_newlines(header_32), unsafe_allow_html=True)

# ==============================================================================
# 3.4 Y 3.5: INCIDENCIA INTERNA DE COMPONENTES
# ==============================================================================

col_34, col_35 = st.columns(2)

with col_34:
    render_grafica_incidencia_interna(
        titulo="Incidencia Interna de Componentes Subyacentes",
        df=df_niv_filtered,
        bars=[
            (f"Mercancias_{INC_ANUAL}", "Mercancías", "#20B2AA"),
            (f"Servicios_{INC_ANUAL}", "Servicios", "#48D1CC")
        ],
        parent_inc_col=f"Subyacente_{INC_ANUAL}",
        parent_var_col=f"Subyacente_{VAR_ANUAL}",
        parent_name="Subyacente"
    )

with col_35:
    render_grafica_incidencia_interna(
        titulo="Incidencia Interna de Componentes No Subyacentes",
        df=df_niv_filtered,
        bars=[
            (f"Agropecuarios_{INC_ANUAL}", "Agropecuarios", "#3B82F6"),
            (f"Energeticos_Tarifas_{INC_ANUAL}", "Energéticos y Tarifas", "#8B5CF6")
        ],
        parent_inc_col=f"No_Subyacente_{INC_ANUAL}",
        parent_var_col=f"No_Subyacente_{VAR_ANUAL}",
        parent_name="No Subyacente"
    )

# ==============================================================================
# 3.6 Y 3.7: INCIDENCIA INTERNA SUBCOMPONENTES - MERCANCÍAS / SERVICIOS
# ==============================================================================

col_36, col_37 = st.columns(2)

with col_36:
    render_grafica_incidencia_interna(
        titulo="Incidencia Interna de Subcomponentes (Mercancías)",
        df=df_niv_filtered,
        bars=[
            (f"Alimentos_Bebidas_Tabaco_{INC_ANUAL}", "Alimentos, Bebidas y Tabaco", "#008889"),
            (f"Mercancias_No_Alimenticias_{INC_ANUAL}", "Mercancías No Alimenticias", "#20B2AA")
        ],
        parent_inc_col=f"Mercancias_{INC_ANUAL}",
        parent_var_col=f"Mercancias_{VAR_ANUAL}",
        parent_name="Mercancías"
    )

with col_37:
    render_grafica_incidencia_interna(
        titulo="Incidencia Interna de Subcomponentes (Servicios)",
        df=df_niv_filtered,
        bars=[
            (f"Vivienda_{INC_ANUAL}", "Vivienda", "#48D1CC"),
            (f"Educacion_{INC_ANUAL}", "Educación", "#40E0D0"),
            (f"Otros_Servicios_{INC_ANUAL}", "Otros Servicios", "#7FFFD4")
        ],
        parent_inc_col=f"Servicios_{INC_ANUAL}",
        parent_var_col=f"Servicios_{VAR_ANUAL}",
        parent_name="Servicios"
    )

# ==============================================================================
# 3.8 Y 3.9: INCIDENCIA INTERNA SUBCOMPONENTES - AGROPECUARIOS / ENERGÉTICOS
# ==============================================================================

col_38, col_39 = st.columns(2)

with col_38:
    render_grafica_incidencia_interna(
        titulo="Incidencia Interna de Subcomponentes (Agropecuarios)",
        df=df_niv_filtered,
        bars=[
            (f"Frutas_Verduras_{INC_ANUAL}", "Frutas y Verduras", "#60A5FA"),
            (f"Pecuarios_{INC_ANUAL}", "Pecuarios", "#1D4ED8")
        ],
        parent_inc_col=f"Agropecuarios_{INC_ANUAL}",
        parent_var_col=f"Agropecuarios_{VAR_ANUAL}",
        parent_name="Agropecuarios"
    )

with col_39:
    render_grafica_incidencia_interna(
        titulo="Incidencia Interna de Subcomponentes (Energéticos y Tarifas Autorizadas)",
        df=df_niv_filtered,
        bars=[
            (f"Energeticos_{INC_ANUAL}", "Energéticos", "#A78BFA"),
            (f"Tarifas_Autorizadas_{INC_ANUAL}", "Tarifas Autorizadas", "#6D28D9")
        ],
        parent_inc_col=f"Energeticos_Tarifas_{INC_ANUAL}",
        parent_var_col=f"Energeticos_Tarifas_{VAR_ANUAL}",
        parent_name="Energéticos y Tarifas Autorizadas"
    )

# ==============================================================================
# PREPARACIÓN DE SUBCOMPONENTES PARA HEATMAPS Y TARJETAS
# ==============================================================================

subcomps = [
    "Alimentos_Bebidas_Tabaco",
    "Mercancias_No_Alimenticias",
    "Vivienda",
    "Educacion",
    "Otros_Servicios",
    "Frutas_Verduras",
    "Pecuarios",
    "Energeticos",
    "Tarifas_Autorizadas"
]

subcomps_labels = [
    "Alimentos, Bebidas y Tabaco",
    "Mercancías No Alimenticias",
    "Vivienda",
    "Educación",
    "Otros Servicios",
    "Frutas y Verduras",
    "Pecuarios",
    "Energéticos",
    "Tarifas Autorizadas"
]

df_heat_temp = (
    df_niv_filtered
    .drop_duplicates(subset=["Periodo"], keep="last")
    .sort_values("Fecha")
    .copy()
)

meses_lower = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
}
df_heat_temp["Periodo_Heatmap"] = df_heat_temp["Fecha"].dt.month.map(meses_lower) + "-" + df_heat_temp["Fecha"].dt.strftime("%y")

# ==============================================================================
# 3.10: MAPA DE VARIACIÓN ANUAL (%)
# ==============================================================================

st.markdown(
    "<div class='chart-title'>Mapa de Variación Anual (%)</div>",
    unsafe_allow_html=True
)

existing_var = [
    (comp, label)
    for comp, label in zip(subcomps, subcomps_labels)
    if f"{comp}_{VAR_ANUAL}" in df_heat_temp.columns
]

if existing_var:
    cols_var = [f"{comp}_{VAR_ANUAL}" for comp, _ in existing_var]
    labels_var = [label for _, label in existing_var]

    df_heat_var = df_heat_temp.set_index("Periodo_Heatmap")[cols_var].T
    df_heat_var.index = labels_var
    df_heat_var.loc["INPC General"] = df_heat_temp[f"INPC_General_{VAR_ANUAL}"].values

    fig_310 = fig_heatmap(df_heat_var, height=430)

    st.plotly_chart(
        fig_310,
        use_container_width=True,
        config={"displayModeBar": False}
    )
else:
    st.info("No hay columnas suficientes para construir el mapa de variación anual.")

# ==============================================================================
# 3.11: MAPA DE INCIDENCIA ANUAL
# ==============================================================================

st.markdown(
    "<div class='chart-title'>Mapa de Incidencia Anual (pp)</div>",
    unsafe_allow_html=True
)

existing_inc = [
    (comp, label)
    for comp, label in zip(subcomps, subcomps_labels)
    if f"{comp}_{INC_ANUAL}" in df_heat_temp.columns
]

if existing_inc:
    cols_inc = [f"{comp}_{INC_ANUAL}" for comp, _ in existing_inc]
    labels_inc = [label for _, label in existing_inc]

    df_heat_inc = df_heat_temp.set_index("Periodo_Heatmap")[cols_inc].T
    df_heat_inc.index = labels_inc
    df_heat_inc.loc["INPC General"] = df_heat_temp[cols_inc].fillna(0).sum(axis=1).values

    fig_311 = fig_heatmap(df_heat_inc, height=430, text_format=".3f")

    st.plotly_chart(
        fig_311,
        use_container_width=True,
        config={"displayModeBar": False}
    )
else:
    st.info("No hay columnas suficientes para construir el mapa de incidencia anual.")

# ==============================================================================
# 3.12: ESTADÍSTICAS DETALLADAS POR SUBCOMPONENTE
# ==============================================================================

st.markdown(
    """
    <div style="margin-bottom: 16px;">
        <div class='chart-title' style='font-size:1.05rem; margin-top:8px; margin-bottom:4px;'>
            Estadísticas Detalladas por Subcomponente
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <div style="display:flex; align-items:center; gap:6px;">
                <span style="width:12px; height:12px; background-color:#008889; border-radius:3px; display:inline-block;"></span>
                <span style="font-size:0.85rem; font-weight:600; color:#334155;">Subyacente</span>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
                <span style="width:12px; height:12px; background-color:#1E40AF; border-radius:3px; display:inline-block;"></span>
                <span style="font-size:0.85rem; font-weight:600; color:#334155;">No Subyacente</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

grid_cols = st.columns(3)

subyacente_comps_set = {"Alimentos_Bebidas_Tabaco", "Mercancias_No_Alimenticias", "Vivienda", "Educacion", "Otros_Servicios"}

for i, (col_id, label) in enumerate(zip(subcomps, subcomps_labels)):
    col_obj = grid_cols[i % 3]

    v_a = ultimo_registro[f'{col_id}_Var_Anual']
    v_m = ultimo_registro[f'{col_id}_Var_Mensual']
    i_a = ultimo_registro[f'{col_id}_Inc_Anual']
    i_m = ultimo_registro[f'{col_id}_Inc_Mensual']

    d_a_p = v_a - registro_previo[f'{col_id}_Var_Anual']
    d_a_a = v_a - registro_previo_anio[f'{col_id}_Var_Anual']
    d_m_p = v_m - registro_previo[f'{col_id}_Var_Mensual']
    d_m_a = v_m - registro_previo_anio[f'{col_id}_Var_Mensual']

    c_va = '#DC2626' if v_a > 0 else '#16A34A' if v_a < 0 else '#64748B'
    c_vm = '#DC2626' if v_m > 0 else '#16A34A' if v_m < 0 else '#64748B'

    card_color = "#008889" if col_id in subyacente_comps_set else "#1E40AF"

    col_obj.markdown(f"""
    <div class="metric-card" style="margin-bottom: 16px; border: 2px solid {card_color}80;">
        <div class="metric-title" style="color: {card_color}; font-size: 0.85rem;">{label}</div>
        <div style="display: flex; justify-content: space-between; margin-top: 8px;">
            <div style="width: 48%;">
                <div style="font-size: 0.90rem; color: #64748B;">Anual (Inc)</div>
                <div class="metric-value" style="font-size: 1.30rem; color: {c_va};">{v_a:.2f}% <span style="font-size: 0.85rem; color: #94A3B8;">({i_a:.3f} pp)</span></div>
                <div style="font-size: 0.80rem; color: #64748B;">MoM: {d_a_p:+.2f} pp</div>
                <div style="font-size: 0.80rem; color: #64748B;">YoY: {d_a_a:+.2f} pp</div>
            </div>
            <div style="width: 48%;">
                <div style="font-size: 0.90rem; color: #64748B;">Mensual (Inc)</div>
                <div class="metric-value" style="font-size: 1.30rem; color: {c_vm};">{v_m:.2f}% <span style="font-size: 0.85rem; color: #94A3B8;">({i_m:.3f} pp)</span></div>
                <div style="font-size: 0.80rem; color: #64748B;">MoM: {d_m_p:+.2f} pp</div>
                <div style="font-size: 0.80rem; color: #64748B;">YoY: {d_m_a:+.2f} pp</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# PREPARACIÓN DE GENÉRICOS PARA RANKINGS
# ==============================================================================

df_gen_rango = df_genericos[
    (df_genericos["Anio_Mes"] >= p_inicio) &
    (df_genericos["Anio_Mes"] <= p_fin)
].copy()

if df_gen_rango.empty:
    df_gen_rango = df_genericos.copy()

if not df_gen_rango.empty:
    fecha_max_gen = df_gen_rango["Fecha"].max()

    if pd.notna(fecha_max_gen):
        df_corte_gen = df_gen_rango[df_gen_rango["Fecha"] == fecha_max_gen].copy()
        fecha_max_str = f"{MESES_COMPLETOS[fecha_max_gen.month]} {fecha_max_gen.year}"
    else:
        df_corte_gen = pd.DataFrame()
        fecha_max_str = periodo_largo
else:
    df_corte_gen = pd.DataFrame()
    fecha_max_str = periodo_largo

# ==============================================================================
# 3.13 Y 3.14: MAYORES PRESIONES AL ALZA
# ==============================================================================

r1, r2 = st.columns(2)

with r1:
    st.markdown(
        f"<div class='chart-title'>Genéricos de Mayor Incidencia Anual al Alza ({fecha_max_str})</div>",
        unsafe_allow_html=True
    )

    fig_313 = fig_ranking_genericos(
        df_corte=df_corte_gen,
        col_rank="Inc_Anual",
        ascending=False,
        color="#DC2626",
        text_format=".3f",
        height=340
    )

    st.plotly_chart(
        fig_313,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with r2:
    st.markdown(
        f"<div class='chart-title'>Genéricos de Mayor Variación Anual al Alza ({fecha_max_str})</div>",
        unsafe_allow_html=True
    )

    fig_314 = fig_ranking_genericos(
        df_corte=df_corte_gen,
        col_rank="Var_Anual",
        ascending=False,
        color="#DC2626",
        text_format=".2f",
        height=340
    )

    st.plotly_chart(
        fig_314,
        use_container_width=True,
        config={"displayModeBar": False}
    )

# ==============================================================================
# 3.15 Y 3.16: MAYORES CONTRIBUCIONES A LA BAJA
# ==============================================================================

r3, r4 = st.columns(2)

with r3:
    st.markdown(
        f"<div class='chart-title'>Genéricos de Mayor Incidencia Anual a la Baja ({fecha_max_str})</div>",
        unsafe_allow_html=True
    )

    fig_315 = fig_ranking_genericos(
        df_corte=df_corte_gen,
        col_rank="Inc_Anual",
        ascending=True,
        color="#16A34A",
        text_format=".3f",
        height=340
    )

    st.plotly_chart(
        fig_315,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with r4:
    st.markdown(
        f"<div class='chart-title'>Genéricos de Mayor Variación Anual a la Baja ({fecha_max_str})</div>",
        unsafe_allow_html=True
    )

    fig_316 = fig_ranking_genericos(
        df_corte=df_corte_gen,
        col_rank="Var_Anual",
        ascending=True,
        color="#16A34A",
        text_format=".2f",
        height=340
    )

    st.plotly_chart(
        fig_316,
        use_container_width=True,
        config={"displayModeBar": False}
    )