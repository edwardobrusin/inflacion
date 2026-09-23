import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
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
    3.1 Trayectoria del INPC e Incidencias en Variación Total.
    Líneas: General, Subyacente y No Subyacente, con rango objetivo Banxico.
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
        line=dict(color=COLOR_PRIMARIO, width=2.5),
        marker=dict(size=4),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=df["Fecha"],
        y=df[f"Subyacente_{VAR_ANUAL}"],
        mode="lines",
        name="Subyacente",
        line=dict(color=COLOR_SECUNDARIO, width=2),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=df["Fecha"],
        y=df[f"No_Subyacente_{VAR_ANUAL}"],
        mode="lines",
        name="No Subyacente",
        line=dict(color=COLOR_TERCIARIO, width=2, dash="dot"),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    aplicar_layout_base(fig, height=430, is_timeseries=True)
    return fig


def fig_incidencias_subcomponentes(df):
    """
    3.2 Evolución de Incidencias Históricas por Subcomponente.
    Barras apiladas relativas + línea del INPC General.
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

    aplicar_layout_base(fig, height=340, is_timeseries=True)
    fig.update_layout(
        barmode="relative",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=COLOR_BORDER,
            borderwidth=1
        )
    )
    return fig


def fig_cascada_incidencia(current_row):
    """
    3.3 Cascada de Incidencia Aditiva Desglosada.
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
    x_labels = ["<br>".join(textwrap.wrap(l, width=14)) for l in x_labels_full]

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
        connector={"line": {"color": "#94A3B8"}},
        decreasing={"marker": {"color": "#16A34A"}},
        increasing={"marker": {"color": "#DC2626"}},
        totals={"marker": {"color": COLOR_PRIMARIO}},
        hovertemplate="%{x}: %{y:.3f} pp<extra></extra>"
    ))

    inc_sub = sum(get_num(current_row, f"{comp}_{INC_ANUAL}") for comp in components[:5])
    inc_nosub = sum(get_num(current_row, f"{comp}_{INC_ANUAL}") for comp in components[5:])

    fig.add_vrect(
        x0=-0.5,
        x1=4.5,
        fillcolor=COLOR_SECUNDARIO,
        opacity=0.10,
        line_width=0,
        annotation_text=f"SUBYACENTE: {inc_sub:.3f} pp",
        annotation_position="top left",
        annotation_font_color=COLOR_SECUNDARIO
    )

    fig.add_vrect(
        x0=4.5,
        x1=8.5,
        fillcolor="#3B82F6",
        opacity=0.10,
        line_width=0,
        annotation_text=f"NO SUBYACENTE: {inc_nosub:.3f} pp",
        annotation_position="top left",
        annotation_font_color="#3B82F6"
    )

    fig.add_vline(
        x=4.5,
        line_dash="dash",
        line_color="#475569",
        line_width=1.5,
        opacity=0.7
    )

    aplicar_layout_base(fig, height=430, hovermode="closest")
    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickangle=-90)
    return fig


def fig_incidencia_interna(
    df,
    bars,
    parent_inc_col: str,
    parent_var_col: str,
    parent_name: str,
    height: int = 340
):
    """
    Gráfica de incidencia interna:
    barras para hijos + línea para variación del padre.
    """
    fig = go.Figure()

    try:
        line_max = df[parent_var_col].max()
        line_min = df[parent_var_col].min()

        pos_sum = np.zeros(len(df))
        neg_sum = np.zeros(len(df))

        for child_inc_col, _, _ in bars:
            y_tmp = calc_inc_int(df, child_inc_col, parent_inc_col, parent_var_col)
            pos_sum += np.where(y_tmp > 0, y_tmp, 0)
            neg_sum += np.where(y_tmp < 0, y_tmp, 0)

        y_max = float(max(line_max, np.nanmax(pos_sum)))
        y_min = float(min(line_min, np.nanmin(neg_sum)))

        rango = y_max - y_min if y_max != y_min else 1.0
        y_max_pad = y_max + (rango * 0.35)
        y_min_pad = y_min - (rango * 0.05)
    except Exception:
        y_max_pad, y_min_pad = None, None

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
            name=f"{name}&nbsp;&nbsp;&nbsp;",
            marker_color=color,
            hovertemplate="%{y:.3f} pp<extra></extra>"
        ))

    fig.add_trace(go.Scatter(
        x=df["Fecha"],
        y=df[parent_var_col],
        name=f"{parent_name}&nbsp;&nbsp;&nbsp;",
        mode="lines",
        line=dict(color=COLOR_TEXTO, width=2.4),
        hovertemplate="%{y:.2f}%<extra></extra>"
    ))

    fig.update_layout(barmode="relative")

    aplicar_layout_base(fig, height=height, is_timeseries=True)

    layout_updates = dict(
        legend=dict(
            orientation="h",
            yanchor="top",
            y=0.98,
            xanchor="center",
            x=0.5
        )
    )

    if y_max_pad is not None and y_min_pad is not None:
        layout_updates["yaxis_range"] = [y_min_pad, y_max_pad]

    fig.update_layout(**layout_updates)

    return fig


def fig_heatmap(df_matrix: pd.DataFrame, height: int = 430, text_format: str = ".2f"):
    """
    Mapa de calor para variación o incidencia.
    """
    fig = px.imshow(
        df_matrix,
        color_continuous_scale=["#16A34A", "#F8FAFC", "#DC2626"],
        aspect="auto",
        text_auto=text_format
    )

    fig.update_traces(
        hovertemplate=f"%{{y}} | %{{x}}<br>Valor: %{{z:{text_format}}}<extra></extra>"
    )

    aplicar_layout_heatmap(fig, height=height)

    # Centrar la escala en cero si hay valores positivos y negativos.
    values = df_matrix.values.astype(float)

    if values.size > 0 and not np.all(np.isnan(values)):
        max_abs = float(np.nanmax(np.abs(values)))
        if pd.isna(max_abs) or max_abs == 0:
            max_abs = 1.0
    else:
        max_abs = 1.0

    fig.update_coloraxes(
        cmin=-max_abs,
        cmax=max_abs
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

    fig = px.bar(
        top,
        x=col_rank,
        y="Concepto_Wrap",
        orientation="h",
        color_discrete_sequence=[color],
        text=col_rank
    )

    fig.update_traces(
        texttemplate=f"%{{x:{text_format}}}",
        textposition="outside",
        hovertemplate="%{y}<br>%{x}<extra></extra>",
        cliponaxis=False
    )

    aplicar_layout_base(fig, height=height, hovermode="closest")

    x_min, x_max = top[col_rank].min(), top[col_rank].max()
    x_span = x_max - x_min if x_max != x_min else 1
    pad = x_span * 0.22

    fig.update_layout(
        margin=dict(l=0, r=30, t=20, b=15),
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
            range=[x_min - pad, x_max + pad],
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
    <div class="metric-delta" style="color: {COLOR_PRIMARIO};">Incidencia Anual: {inc_nosub_exact:.3f} pp</div>
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
    <div class="metric-delta" style="color: {COLOR_PRIMARIO};">Incidencia Mensual: {inc_nosub_exact_m:.3f} pp</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 3.1 Y 3.3: TRAYECTORIA Y CASCADA DE INCIDENCIA
# ==============================================================================

col_31, col_32 = st.columns(2)

with col_31:
    st.markdown(
        "<div class='chart-title'>Indice Nacional de Precios al Consumidor (Variación Anual en Por Ciento)</div>",
        unsafe_allow_html=True
    )
    fig_31 = fig_trayectoria_inpc(df_niv_filtered)
    st.plotly_chart(
        fig_31,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with col_32:
    st.markdown(
        f"<div class='chart-title'>Incidencia por Subcomponente en Puntos Porcentuales ({periodo_largo})</div>",
        unsafe_allow_html=True
    )
    fig_33 = fig_cascada_incidencia(ultimo_registro)
    st.plotly_chart(
        fig_33,
        use_container_width=True,
        config={"displayModeBar": False}
    )

# ==============================================================================
# 3.2: EVOLUCIÓN DE INCIDENCIAS HISTÓRICAS POR SUBCOMPONENTE
# ==============================================================================

st.markdown(
    "<div class='chart-title'>Incidencias Históricas por Subcomponente</div>",
    unsafe_allow_html=True
)

fig_32 = fig_incidencias_subcomponentes(df_niv_filtered)

st.plotly_chart(
    fig_32,
    use_container_width=True,
    config={"displayModeBar": False}
)

# ==============================================================================
# 3.4 Y 3.5: INCIDENCIA INTERNA DE COMPONENTES
# ==============================================================================

col_34, col_35 = st.columns(2)

with col_34:
    st.markdown(
        "<div class='chart-title'>Incidencia Interna de Componentes Subyacentes</div>",
        unsafe_allow_html=True
    )

    fig_34 = fig_incidencia_interna(
        df=df_niv_filtered,
        bars=[
            (f"Mercancias_{INC_ANUAL}", "Mercancías", "#20B2AA"),
            (f"Servicios_{INC_ANUAL}", "Servicios", "#48D1CC")
        ],
        parent_inc_col=f"Subyacente_{INC_ANUAL}",
        parent_var_col=f"Subyacente_{VAR_ANUAL}",
        parent_name="Subyacente"
    )

    st.plotly_chart(
        fig_34,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with col_35:
    st.markdown(
        "<div class='chart-title'>Incidencia Interna de Componentes No Subyacentes</div>",
        unsafe_allow_html=True
    )

    fig_35 = fig_incidencia_interna(
        df=df_niv_filtered,
        bars=[
            (f"Agropecuarios_{INC_ANUAL}", "Agropecuarios", "#3B82F6"),
            (f"Energeticos_Tarifas_{INC_ANUAL}", "Energéticos y Tarifas", "#8B5CF6")
        ],
        parent_inc_col=f"No_Subyacente_{INC_ANUAL}",
        parent_var_col=f"No_Subyacente_{VAR_ANUAL}",
        parent_name="No Subyacente"
    )

    st.plotly_chart(
        fig_35,
        use_container_width=True,
        config={"displayModeBar": False}
    )

# ==============================================================================
# 3.6 Y 3.7: INCIDENCIA INTERNA SUBCOMPONENTES - MERCANCÍAS / SERVICIOS
# ==============================================================================

col_36, col_37 = st.columns(2)

with col_36:
    st.markdown(
        "<div class='chart-title'>Incidencia Interna de Subcomponentes (Mercancías)</div>",
        unsafe_allow_html=True
    )

    fig_36 = fig_incidencia_interna(
        df=df_niv_filtered,
        bars=[
            (
                f"Alimentos_Bebidas_Tabaco_{INC_ANUAL}",
                "Alimentos, Bebidas y Tabaco",
                "#008889"
            ),
            (
                f"Mercancias_No_Alimenticias_{INC_ANUAL}",
                "Mercancías No Alimenticias",
                "#20B2AA"
            )
        ],
        parent_inc_col=f"Mercancias_{INC_ANUAL}",
        parent_var_col=f"Mercancias_{VAR_ANUAL}",
        parent_name="Mercancías"
    )

    st.plotly_chart(
        fig_36,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with col_37:
    st.markdown(
        "<div class='chart-title'>Incidencia Interna de Subcomponentes (Servicios)</div>",
        unsafe_allow_html=True
    )

    fig_37 = fig_incidencia_interna(
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

    st.plotly_chart(
        fig_37,
        use_container_width=True,
        config={"displayModeBar": False}
    )

# ==============================================================================
# 3.8 Y 3.9: INCIDENCIA INTERNA SUBCOMPONENTES - AGROPECUARIOS / ENERGÉTICOS
# ==============================================================================

col_38, col_39 = st.columns(2)

with col_38:
    st.markdown(
        "<div class='chart-title'>Incidencia Interna de Subcomponentes (Agropecuarios)</div>",
        unsafe_allow_html=True
    )

    fig_38 = fig_incidencia_interna(
        df=df_niv_filtered,
        bars=[
            (f"Frutas_Verduras_{INC_ANUAL}", "Frutas y Verduras", "#60A5FA"),
            (f"Pecuarios_{INC_ANUAL}", "Pecuarios", "#1D4ED8")
        ],
        parent_inc_col=f"Agropecuarios_{INC_ANUAL}",
        parent_var_col=f"Agropecuarios_{VAR_ANUAL}",
        parent_name="Agropecuarios"
    )

    st.plotly_chart(
        fig_38,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with col_39:
    st.markdown(
        "<div class='chart-title'>Incidencia Interna de Subcomponentes (Energéticos y Tarifas Autorizadas)</div>",
        unsafe_allow_html=True
    )

    fig_39 = fig_incidencia_interna(
        df=df_niv_filtered,
        bars=[
            (f"Energeticos_{INC_ANUAL}", "Energéticos", "#A78BFA"),
            (f"Tarifas_Autorizadas_{INC_ANUAL}", "Tarifas Autorizadas", "#6D28D9")
        ],
        parent_inc_col=f"Energeticos_Tarifas_{INC_ANUAL}",
        parent_var_col=f"Energeticos_Tarifas_{VAR_ANUAL}",
        parent_name="Energéticos y Tarifas Autorizadas"
    )

    st.plotly_chart(
        fig_39,
        use_container_width=True,
        config={"displayModeBar": False}
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
    "<div class='chart-title' style='font-size:1.05rem; margin-top:8px;'>"
    "Estadísticas Detalladas por Subcomponente"
    "</div>",
    unsafe_allow_html=True
)

grid_cols = st.columns(3)

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

    col_obj.markdown(f"""
    <div class="metric-card" style="margin-bottom: 16px;">
        <div class="metric-title" style="color: {COLOR_PRIMARIO}; font-size: 0.85rem;">{label}</div>
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
        f"<div class='chart-title'>Genéricos de Mayor Incidencia al Alza ({fecha_max_str})</div>",
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
        f"<div class='chart-title'>Genéricos de Mayor Variación al Alza ({fecha_max_str})</div>",
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
        f"<div class='chart-title'>Genéricos de Mayor Incidencia a la Baja ({fecha_max_str})</div>",
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
        f"<div class='chart-title'>Genéricos de Mayor Variación a la Baja ({fecha_max_str})</div>",
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