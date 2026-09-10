import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO INSTITUCIONAL (LIGHT THEME)
# ==============================================================================
st.set_page_config(
    page_title="Monitor de Inflación | Dirección de Estudios Económicos",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de CSS institucional optimizado para Theme Light
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Reducción drástica del espacio superior del header */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1rem !important;
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Contenedores tipo Card para Theme Light */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
    }
    .metric-title {
        color: #64748B;
        font-size: 0.80rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value {
        color: #0F172A;
        font-size: 1.85rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        line-height: 1.2;
    }
    .metric-delta {
        font-size: 0.85rem;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        margin-top: 6px;
    }
    .delta-up { color: #DC2626; }     /* Rojo para presión inflacionaria */
    .delta-down { color: #16A34A; }   /* Verde para descenso */
    .delta-neutral { color: #64748B; }
    
    /* Pestañas institucionales limpias */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        white-space: pre-wrap;
        border-radius: 6px 6px 0 0;
        color: #64748B;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #2596BE !important;
        border-bottom: 2px solid #2596BE !important;
    }
    
    /* Ajuste de dataframes para densidad y números tabulares */
    div[data-testid="stDataFrame"] {
        font-variant-numeric: tabular-nums;
    }
</style>
""", unsafe_allow_html=True)

# Paleta Institucional
COLOR_PRIMARIO = "#2596BE"     # Azul Institucional
COLOR_SECUNDARIO = "#008889"   # Teal / Verde Azulado (Subyacente)
COLOR_TERCIARIO = "#73C6E3"    # Celeste Claro (No Subyacente)
COLOR_TEXTO = "#0F172A"
COLOR_GRID = "#F1F5F9"
COLOR_BORDER = "#E2E8F0"

# ==============================================================================
# CARGA Y DEPURACIÓN RESILIENTE DE DATOS
# ==============================================================================
# Mapeo seguro para meses en español (evita errores de 'locale' en servidores en la nube)
MESES_ABREV = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
MESES_COMPLETOS = {1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'}

def parse_dates_safe(series: pd.Series) -> pd.Series:
    """Parsea fechas forzando la extracción estricta del formato DD/MM/AAAA."""
    # Limpieza: quitar espacios, aislar solo la fecha (ignora timestamps) y unificar separadores
    cleaned = series.astype(str).str.strip().str.split(' ').str[0]
    cleaned = cleaned.str.replace('-', '/')
    
    # 1. Parseo estricto del formato mexicano (Día/Mes/Año)
    parsed = pd.to_datetime(cleaned, format='%d/%m/%Y', errors='coerce')
    
    # 2. Respaldo estricto para formato de base de datos (AAAA/MM/DD) sin ambigüedades
    if parsed.isna().sum() > 0:
        fallback = pd.to_datetime(cleaned, format='%Y/%m/%d', errors='coerce')
        parsed = parsed.combine_first(fallback)
        
    return parsed

@st.cache_data
def load_data():
    # 1. Niveles
    df_niv = pd.read_csv("data/intermediate/niveles.csv")
    df_niv.columns = df_niv.columns.str.strip()
    df_niv['Fecha'] = parse_dates_safe(df_niv['Fecha'])
    df_niv = df_niv.dropna(subset=['Fecha']).sort_values('Fecha').reset_index(drop=True)
    
    df_niv['Periodo'] = df_niv['Fecha'].dt.month.map(MESES_ABREV) + '-' + df_niv['Fecha'].dt.year.astype(str)
    df_niv['Anio_Mes'] = df_niv['Fecha'].dt.strftime('%Y-%m')
    
    # 2. Genéricos
    df_gen = pd.read_csv("data/intermediate/genericos.csv")
    df_gen.columns = df_gen.columns.str.strip()
    df_gen['Fecha'] = parse_dates_safe(df_gen['Fecha'])
    df_gen = df_gen.dropna(subset=['Fecha']).sort_values(['Fecha', 'Concepto']).reset_index(drop=True)
    
    df_gen['Periodo'] = df_gen['Fecha'].dt.month.map(MESES_ABREV) + '-' + df_gen['Fecha'].dt.year.astype(str)
    df_gen['Anio_Mes'] = df_gen['Fecha'].dt.strftime('%Y-%m')
    
    return df_niv, df_gen

try:
    df_niveles, df_genericos = load_data()
except Exception as e:
    st.error(f"Error al leer archivos de datos: {e}. Verifique que 'data/intermediate/niveles.csv' y 'data/intermediate/genericos.csv' existan y tengan registros válidos.")
    st.stop()

if df_niveles.empty:
    st.error("El archivo 'niveles.csv' no contiene registros de fecha válidos.")
    st.stop()

# ==============================================================================
# CONTROLES LATERALES (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.markdown("### **Rango de Análisis**")
    
    # Lista de periodos mensuales disponibles en formato YYYY-MM
    periodos_disponibles = df_niveles['Anio_Mes'].unique().tolist()
    
    # Slider de selección mensual
    p_inicio_default = "2018-01" if "2018-01" in periodos_disponibles else periodos_disponibles[0]
    p_fin_default = periodos_disponibles[-1]
    
    sel_periodos = st.select_slider(
        "Horizonte temporal (Mes/Año):",
        options=periodos_disponibles,
        value=(p_inicio_default, p_fin_default)
    )
    
    p_inicio, p_fin = sel_periodos
    
    st.markdown("---")
    st.markdown("### **Parámetros del Monitor**")
    umbral_banxico = st.checkbox("Mostrar Rango Objetivo Banxico (3% ± 1%)", value=True)
    tipo_variacion = st.radio("Métrica Activa", ["Anual (%)", "Mensual (%)"], index=0)
    var_col_suffix = "Var_Anual" if tipo_variacion == "Anual (%)" else "Var_Mensual"
    inc_col_suffix = "Inc_Anual" if tipo_variacion == "Anual (%)" else "Inc_Mensual"

# Filtrar datasets según los periodos seleccionados
df_niv_filtered = df_niveles[
    (df_niveles['Anio_Mes'] >= p_inicio) & 
    (df_niveles['Anio_Mes'] <= p_fin)
].reset_index(drop=True)

ultimo_registro = df_niveles.iloc[-1]
idx_actual = df_niveles.index[-1]
registro_previo = df_niveles.iloc[idx_actual - 1] if idx_actual >= 1 else ultimo_registro
registro_previo_anio = df_niveles.iloc[idx_actual - 12] if idx_actual >= 12 else ultimo_registro

# ==============================================================================
# ENCABEZADO Y TARJETAS KPI
# ==============================================================================
st.title("Sistema de Seguimiento y Desglose de Inflación (INPC)")
mes_corte = MESES_COMPLETOS[ultimo_registro['Fecha'].month].capitalize()
st.caption(f"Corte analítico: **{mes_corte} de {ultimo_registro['Fecha'].year}** | Cobertura seleccionada: **{p_inicio}** a **{p_fin}**")

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
        <div class="metric-title">INPC General (Anual)</div>
        <div class="metric-value">{v_actual_a:.2f}%</div>
        <div class="metric-delta delta-neutral">
            MoM: <span style="color: {c_a_prev}; font-weight: 700;">{delta_a_prev:+.2f} pp</span> &nbsp;|&nbsp; 
            YoY: <span style="color: {c_a_anio}; font-weight: 700;">{delta_a_anio:+.2f} pp</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with k_a2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Subyacente (Anual)</div>
        <div class="metric-value">{ultimo_registro['Subyacente_Var_Anual']:.2f}%</div>
        <div class="metric-delta" style="color: {COLOR_SECUNDARIO};">Incidencia Anual: {ultimo_registro['Subyacente_Inc_Anual']:.2f} pp</div>
    </div>
    """, unsafe_allow_html=True)

with k_a3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">No Subyacente (Anual)</div>
        <div class="metric-value">{ultimo_registro['No_Subyacente_Var_Anual']:.2f}%</div>
        <div class="metric-delta" style="color: {COLOR_PRIMARIO};">Incidencia Anual: {ultimo_registro['No_Subyacente_Inc_Anual']:.2f} pp</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

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
        <div class="metric-title">INPC General (Mensual)</div>
        <div class="metric-value">{v_actual_m:.2f}%</div>
        <div class="metric-delta delta-neutral">
            MoM: <span style="color: {c_m_prev}; font-weight: 700;">{delta_m_prev:+.2f} pp</span> &nbsp;|&nbsp; 
            YoY: <span style="color: {c_m_anio}; font-weight: 700;">{delta_m_anio:+.2f} pp</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with k_m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Subyacente (Mensual)</div>
        <div class="metric-value">{ultimo_registro['Subyacente_Var_Mensual']:.2f}%</div>
        <div class="metric-delta" style="color: {COLOR_SECUNDARIO};">Incidencia Mensual: {ultimo_registro['Subyacente_Inc_Mensual']:.2f} pp</div>
    </div>
    """, unsafe_allow_html=True)

with k_m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">No Subyacente (Mensual)</div>
        <div class="metric-value">{ultimo_registro['No_Subyacente_Var_Mensual']:.2f}%</div>
        <div class="metric-delta" style="color: {COLOR_PRIMARIO};">Incidencia Mensual: {ultimo_registro['No_Subyacente_Inc_Mensual']:.2f} pp</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Configuración base para gráficos Plotly en Theme Light
def aplicar_layout_light(fig, height=380, title=None):
    fig.update_layout(
        template='plotly_white',
        title=dict(text=title, font=dict(color=COLOR_TEXTO, size=14)) if title else None,
        height=height,
        margin=dict(l=15, r=15, t=35 if title else 20, b=15),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        font=dict(color=COLOR_TEXTO, family="Inter"),
        hovermode="x unified",
        xaxis=dict(
            gridcolor=COLOR_GRID,
            linecolor=COLOR_BORDER,
            tickcolor=COLOR_BORDER,
            hoverformat="%b %Y" # Previene el error 'undefined' al unificar el tooltip
        ),
        yaxis=dict(
            gridcolor=COLOR_GRID,
            linecolor=COLOR_BORDER,
            tickcolor=COLOR_BORDER
        ),
        legend=dict(
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor=COLOR_BORDER,
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig

# ==============================================================================
# PESTAÑAS MULTINIVEL
# ==============================================================================
tab_gen, tab_tipo, tab_comp, tab_subcomp, tab_art = st.tabs([
    "0. Nivel General",
    "1. Subyacente vs. No Subyacente",
    "2. Componentes Sectoriales",
    "3. Subcomponentes",
    "4. Desglose Fino (292 Genéricos)"
])

# ------------------------------------------------------------------------------
# TAB 0: NIVEL GENERAL
# ------------------------------------------------------------------------------
with tab_gen:
    st.markdown("#### Trayectoria del INPC e Incidencias en Variación Total")
    
    # 1. Gráfica principal a todo lo ancho sin etiqueta de texto del rango
    fig_gen = go.Figure()
    
    if umbral_banxico and "Anual" in tipo_variacion:
        fig_gen.add_hrect(
            y0=2.0, y1=4.0, 
            fillcolor="#10B981", opacity=0.10, 
            line_width=0
        )
        fig_gen.add_hline(y=3.0, line_dash="dash", line_color="#10B981", opacity=0.6)

    fig_gen.add_trace(go.Scatter(
        x=df_niv_filtered['Fecha'],
        y=df_niv_filtered[f'INPC_General_{var_col_suffix}'],
        mode='lines+markers',
        name='INPC General',
        line=dict(color=COLOR_PRIMARIO, width=2.5),
        marker=dict(size=4),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    fig_gen.add_trace(go.Scatter(
        x=df_niv_filtered['Fecha'],
        y=df_niv_filtered[f'Subyacente_{var_col_suffix}'],
        mode='lines',
        name='Subyacente',
        line=dict(color=COLOR_SECUNDARIO, width=2),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    fig_gen.add_trace(go.Scatter(
        x=df_niv_filtered['Fecha'],
        y=df_niv_filtered[f'No_Subyacente_{var_col_suffix}'],
        mode='lines',
        name='No Subyacente',
        line=dict(color=COLOR_TERCIARIO, width=2, dash='dot'),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    
    aplicar_layout_light(fig_gen, height=420)
    st.plotly_chart(fig_gen, width="stretch")

    # 2. Cascada de Incidencia Aditiva por Subcomponente (A todo lo ancho)
    st.markdown(f"#### Cascada de Incidencia Aditiva Desglosada ({ultimo_registro['Periodo']})")
    
    x_labels = [
        "Alimentos y Bebidas", "Mercancías No Alim.", "Vivienda", "Educación", "Otros Servicios",
        "Frutas y Verduras", "Pecuarios", "Energéticos", "Tarifas Autorizadas",
        "INPC Total"
    ]
    
    y_values = [
        ultimo_registro[f'Alimentos_Bebidas_Tabaco_{inc_col_suffix}'], ultimo_registro[f'Mercancias_No_Alimenticias_{inc_col_suffix}'],
        ultimo_registro[f'Vivienda_{inc_col_suffix}'], ultimo_registro[f'Educacion_{inc_col_suffix}'], ultimo_registro[f'Otros_Servicios_{inc_col_suffix}'],
        ultimo_registro[f'Frutas_Verduras_{inc_col_suffix}'], ultimo_registro[f'Pecuarios_{inc_col_suffix}'],
        ultimo_registro[f'Energeticos_{inc_col_suffix}'], ultimo_registro[f'Tarifas_Autorizadas_{inc_col_suffix}'],
        0  # Total Final INPC
    ]
    
    measures = ["relative"] * 9 + ["total"]
    
    fig_water = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=x_labels,
        y=y_values,
        textposition="outside",
        text=[f"{v:.2f}" if m == "relative" else f"{ultimo_registro[f'INPC_General_{var_col_suffix}']:.2f}%" for v, m in zip(y_values, measures)],
        connector={"line": {"color": "#94A3B8"}},
        decreasing={"marker": {"color": "#16A34A"}},
        increasing={"marker": {"color": "#DC2626"}},
        totals={"marker": {"color": COLOR_PRIMARIO}},
        hovertemplate='%{x}: %{y:.2f} pp<extra></extra>'
    ))
    
    # Fondos sutiles indicando los componentes padre
    fig_water.add_vrect(x0=-0.5, x1=4.5, fillcolor=COLOR_SECUNDARIO, opacity=0.1, line_width=0, annotation_text=f"SUBYACENTE: {ultimo_registro[f'Subyacente_{inc_col_suffix}']:.2f} pp", annotation_position="top left", annotation_font_color=COLOR_SECUNDARIO)
    fig_water.add_vrect(x0=4.5, x1=8.5, fillcolor="#3B82F6", opacity=0.1, line_width=0, annotation_text=f"NO SUBYACENTE: {ultimo_registro[f'No_Subyacente_{inc_col_suffix}']:.2f} pp", annotation_position="top left", annotation_font_color="#3B82F6")

    aplicar_layout_light(fig_water, height=450)
    st.plotly_chart(fig_water, width="stretch")

    # 3. Gráfica 3: Evolución INPC General + Barras de Incidencias de Subcomponentes
    st.markdown("#### Evolución de Incidencias Históricas por Subcomponente")
    fig_mixed = go.Figure()
    
    subcomps_cols = [
        ('Alimentos_Bebidas_Tabaco', '#008889', 'Alimentos, Bebidas y Tabaco'),
        ('Mercancias_No_Alimenticias', '#20B2AA', 'Mercancías No Alimenticias'),
        ('Vivienda', '#48D1CC', 'Vivienda'),
        ('Educacion', '#40E0D0', 'Educación'),
        ('Otros_Servicios', '#7FFFD4', 'Otros Servicios'),
        ('Frutas_Verduras', '#60A5FA', 'Frutas y Verduras'),
        ('Pecuarios', '#1D4ED8', 'Pecuarios'),
        ('Energeticos', '#A78BFA', 'Energéticos'),
        ('Tarifas_Autorizadas', '#6D28D9', 'Tarifas Autorizadas')
    ]
    
    for col, color, name in subcomps_cols:
        fig_mixed.add_trace(go.Bar(
            x=df_niv_filtered['Fecha'],
            y=df_niv_filtered[f'{col}_{inc_col_suffix}'],
            name=name,
            marker_color=color,
            hovertemplate='%{y:.2f} pp<extra></extra>'
        ))
        
    fig_mixed.add_trace(go.Scatter(
        x=df_niv_filtered['Fecha'],
        y=df_niv_filtered[f'INPC_General_{var_col_suffix}'],
        name='INPC General',
        mode='lines',
        line=dict(color=COLOR_TEXTO, width=2.5),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    
    fig_mixed.update_layout(barmode='relative')
    aplicar_layout_light(fig_mixed, height=450)
    st.plotly_chart(fig_mixed, width="stretch")

    st.markdown("---")
    st.markdown("#### Balance Sintético de Todos los Niveles (Corte Reciente)")
    
    summary_data = [
        {"Concepto": "INPC General", "Var Anual (%)": ultimo_registro['INPC_General_Var_Anual'], "Var Mensual (%)": ultimo_registro['INPC_General_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['INPC_General_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['INPC_General_Inc_Mensual']},
        {"Concepto": "Subyacente", "Var Anual (%)": ultimo_registro['Subyacente_Var_Anual'], "Var Mensual (%)": ultimo_registro['Subyacente_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Subyacente_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Subyacente_Inc_Mensual']},
        {"Concepto": "\u2003Mercancías", "Var Anual (%)": ultimo_registro['Mercancias_Var_Anual'], "Var Mensual (%)": ultimo_registro['Mercancias_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Mercancias_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Mercancias_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Alimentos, Bebidas y Tabaco", "Var Anual (%)": ultimo_registro['Alimentos_Bebidas_Tabaco_Var_Anual'], "Var Mensual (%)": ultimo_registro['Alimentos_Bebidas_Tabaco_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Alimentos_Bebidas_Tabaco_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Alimentos_Bebidas_Tabaco_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Mercancías No Alimenticias", "Var Anual (%)": ultimo_registro['Mercancias_No_Alimenticias_Var_Anual'], "Var Mensual (%)": ultimo_registro['Mercancias_No_Alimenticias_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Mercancias_No_Alimenticias_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Mercancias_No_Alimenticias_Inc_Mensual']},
        {"Concepto": "\u2003Servicios", "Var Anual (%)": ultimo_registro['Servicios_Var_Anual'], "Var Mensual (%)": ultimo_registro['Servicios_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Servicios_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Servicios_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Vivienda", "Var Anual (%)": ultimo_registro['Vivienda_Var_Anual'], "Var Mensual (%)": ultimo_registro['Vivienda_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Vivienda_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Vivienda_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Educación", "Var Anual (%)": ultimo_registro['Educacion_Var_Anual'], "Var Mensual (%)": ultimo_registro['Educacion_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Educacion_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Educacion_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Otros Servicios", "Var Anual (%)": ultimo_registro['Otros_Servicios_Var_Anual'], "Var Mensual (%)": ultimo_registro['Otros_Servicios_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Otros_Servicios_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Otros_Servicios_Inc_Mensual']},
        {"Concepto": "No Subyacente", "Var Anual (%)": ultimo_registro['No_Subyacente_Var_Anual'], "Var Mensual (%)": ultimo_registro['No_Subyacente_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['No_Subyacente_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['No_Subyacente_Inc_Mensual']},
        {"Concepto": "\u2003Agropecuarios", "Var Anual (%)": ultimo_registro['Agropecuarios_Var_Anual'], "Var Mensual (%)": ultimo_registro['Agropecuarios_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Agropecuarios_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Agropecuarios_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Frutas y Verduras", "Var Anual (%)": ultimo_registro['Frutas_Verduras_Var_Anual'], "Var Mensual (%)": ultimo_registro['Frutas_Verduras_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Frutas_Verduras_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Frutas_Verduras_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Pecuarios", "Var Anual (%)": ultimo_registro['Pecuarios_Var_Anual'], "Var Mensual (%)": ultimo_registro['Pecuarios_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Pecuarios_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Pecuarios_Inc_Mensual']},
        {"Concepto": "\u2003Energéticos y Tarifas", "Var Anual (%)": ultimo_registro['Energeticos_Tarifas_Var_Anual'], "Var Mensual (%)": ultimo_registro['Energeticos_Tarifas_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Energeticos_Tarifas_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Energeticos_Tarifas_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Energéticos", "Var Anual (%)": ultimo_registro['Energeticos_Var_Anual'], "Var Mensual (%)": ultimo_registro['Energeticos_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Energeticos_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Energeticos_Inc_Mensual']},
        {"Concepto": "\u2003\u2003Tarifas Autorizadas", "Var Anual (%)": ultimo_registro['Tarifas_Autorizadas_Var_Anual'], "Var Mensual (%)": ultimo_registro['Tarifas_Autorizadas_Var_Mensual'], "Inc Anual (pp)": ultimo_registro['Tarifas_Autorizadas_Inc_Anual'], "Inc Mensual (pp)": ultimo_registro['Tarifas_Autorizadas_Inc_Mensual']},
    ]
    st.dataframe(
        pd.DataFrame(summary_data).style.format({
            "Var Anual (%)": "{:.2f}%", 
            "Var Mensual (%)": "{:.2f}%", 
            "Inc Anual (pp)": "{:.2f}", 
            "Inc Mensual (pp)": "{:.2f}"
        }), 
        width="stretch", 
        hide_index=True
    )

# ------------------------------------------------------------------------------
# TAB 1: TIPO (SUBYACENTE VS NO SUBYACENTE)
# ------------------------------------------------------------------------------
def calc_inc_int(df, child_inc_col, parent_inc_col, parent_var_col):
    """Calcula la incidencia interna proporcional en variaciones (% -> pp interno)."""
    ratio = np.where(df[parent_inc_col] == 0, 0, df[child_inc_col] / df[parent_inc_col])
    return ratio * df[parent_var_col]

with tab_tipo:
    st.markdown("#### Análisis Estructural General: Subyacente frente a No Subyacente")
    
    # Gráfica principal a lo ancho
    fig_inc_tipo = go.Figure()
    fig_inc_tipo.add_trace(go.Bar(
        x=df_niv_filtered['Fecha'],
        y=df_niv_filtered[f'Subyacente_{inc_col_suffix}'],
        name='Inc. Subyacente',
        marker_color=COLOR_SECUNDARIO,
        hovertemplate='%{y:.2f} pp<extra></extra>'
    ))
    fig_inc_tipo.add_trace(go.Bar(
        x=df_niv_filtered['Fecha'],
        y=df_niv_filtered[f'No_Subyacente_{inc_col_suffix}'],
        name='Inc. No Subyacente',
        marker_color=COLOR_TERCIARIO,
        hovertemplate='%{y:.2f} pp<extra></extra>'
    ))
    fig_inc_tipo.add_trace(go.Scatter(
        x=df_niv_filtered['Fecha'],
        y=df_niv_filtered[f'INPC_General_{var_col_suffix}'],
        name='INPC General',
        line=dict(color=COLOR_TEXTO, width=2.5),
        hovertemplate='%{y:.2f}%<extra></extra>'
    ))
    fig_inc_tipo.update_layout(barmode='relative')
    aplicar_layout_light(fig_inc_tipo, height=420, title=f"Contribución a la Variación Total {tipo_variacion} (pp)")
    st.plotly_chart(fig_inc_tipo, width="stretch")

    st.markdown("---")
    
    # Subsecciones
    ts_c1, ts_c2 = st.columns(2)
    
    with ts_c1:
        st.markdown("##### 1. Desempeño Subyacente")
        
        fig_sub_lines = go.Figure()
        fig_sub_lines.add_trace(go.Scatter(
            x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Subyacente_{var_col_suffix}'],
            name='Subyacente (Total)', line=dict(color=COLOR_SECUNDARIO, width=2.5)
        ))
        fig_sub_lines.add_trace(go.Scatter(
            x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Mercancias_{var_col_suffix}'],
            name='Mercancías', line=dict(color="#20B2AA", width=1.5, dash='dash')
        ))
        fig_sub_lines.add_trace(go.Scatter(
            x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Servicios_{var_col_suffix}'],
            name='Servicios', line=dict(color="#48D1CC", width=1.5, dash='dash')
        ))
        aplicar_layout_light(fig_sub_lines, height=320, title="Variación por Componente")
        st.plotly_chart(fig_sub_lines, width="stretch")
        
        # Cálculo Incidencia Interna en Nivel 1 (Mercancias/Servicios respecto a Subyacente)
        inc_int_merc = calc_inc_int(df_niv_filtered, f'Mercancias_{inc_col_suffix}', f'Subyacente_{inc_col_suffix}', f'Subyacente_{var_col_suffix}')
        inc_int_serv = calc_inc_int(df_niv_filtered, f'Servicios_{inc_col_suffix}', f'Subyacente_{inc_col_suffix}', f'Subyacente_{var_col_suffix}')
        
        fig_sub_inc = go.Figure()
        fig_sub_inc.add_trace(go.Bar(
            x=df_niv_filtered['Fecha'], y=inc_int_merc,
            name='Inc. Int. Mercancías', marker_color="#20B2AA"
        ))
        fig_sub_inc.add_trace(go.Bar(
            x=df_niv_filtered['Fecha'], y=inc_int_serv,
            name='Inc. Int. Servicios', marker_color="#48D1CC"
        ))
        fig_sub_inc.add_trace(go.Scatter(
            x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Subyacente_{var_col_suffix}'],
            name='Subyacente (Var)', line=dict(color=COLOR_TEXTO, width=2)
        ))
        fig_sub_inc.update_layout(barmode='relative')
        aplicar_layout_light(fig_sub_inc, height=320, title="Incidencia Interna de Componentes Subyacentes")
        st.plotly_chart(fig_sub_inc, width="stretch")

    with ts_c2:
        st.markdown("##### 2. Desempeño No Subyacente")
        
        fig_nosub_lines = go.Figure()
        fig_nosub_lines.add_trace(go.Scatter(
            x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'No_Subyacente_{var_col_suffix}'],
            name='No Subyacente (Total)', line=dict(color=COLOR_TERCIARIO, width=2.5)
        ))
        fig_nosub_lines.add_trace(go.Scatter(
            x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Agropecuarios_{var_col_suffix}'],
            name='Agropecuarios', line=dict(color="#3B82F6", width=1.5, dash='dash')
        ))
        fig_nosub_lines.add_trace(go.Scatter(
            x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Energeticos_Tarifas_{var_col_suffix}'],
            name='Energéticos y Tarifas', line=dict(color="#8B5CF6", width=1.5, dash='dash')
        ))
        aplicar_layout_light(fig_nosub_lines, height=320, title="Variación por Componente")
        st.plotly_chart(fig_nosub_lines, width="stretch")
        
        # Cálculo Incidencia Interna en Nivel 1 (Agropecuarios/Energéticos respecto a No Subyacente)
        inc_int_agro = calc_inc_int(df_niv_filtered, f'Agropecuarios_{inc_col_suffix}', f'No_Subyacente_{inc_col_suffix}', f'No_Subyacente_{var_col_suffix}')
        inc_int_ener = calc_inc_int(df_niv_filtered, f'Energeticos_Tarifas_{inc_col_suffix}', f'No_Subyacente_{inc_col_suffix}', f'No_Subyacente_{var_col_suffix}')
        
        fig_nosub_inc = go.Figure()
        fig_nosub_inc.add_trace(go.Bar(
            x=df_niv_filtered['Fecha'], y=inc_int_agro,
            name='Inc. Int. Agropecuarios', marker_color="#3B82F6"
        ))
        fig_nosub_inc.add_trace(go.Bar(
            x=df_niv_filtered['Fecha'], y=inc_int_ener,
            name='Inc. Int. Energ. y Tarifas', marker_color="#8B5CF6"
        ))
        fig_nosub_inc.add_trace(go.Scatter(
            x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'No_Subyacente_{var_col_suffix}'],
            name='No Subyacente (Var)', line=dict(color=COLOR_TEXTO, width=2)
        ))
        fig_nosub_inc.update_layout(barmode='relative')
        aplicar_layout_light(fig_nosub_inc, height=320, title="Incidencia Interna de Componentes No Subyacentes")
        st.plotly_chart(fig_nosub_inc, width="stretch")

# ------------------------------------------------------------------------------
# TAB 2: COMPONENTES
# ------------------------------------------------------------------------------
with tab_comp:
    st.markdown("#### Dinámica Sectorial por Componentes")
    
    def render_component_kpi(col_obj, title, comp_name, color):
        v_a = ultimo_registro[f'{comp_name}_Var_Anual']
        v_m = ultimo_registro[f'{comp_name}_Var_Mensual']
        i_a = ultimo_registro[f'{comp_name}_Inc_Anual']
        i_m = ultimo_registro[f'{comp_name}_Inc_Mensual']
        
        d_a_p = v_a - registro_previo[f'{comp_name}_Var_Anual']
        d_a_a = v_a - registro_previo_anio[f'{comp_name}_Var_Anual']
        d_m_p = v_m - registro_previo[f'{comp_name}_Var_Mensual']
        d_m_a = v_m - registro_previo_anio[f'{comp_name}_Var_Mensual']
        
        col_obj.markdown(f"""
        <div class="metric-card" style="border-top: 3px solid {color}; margin-bottom: 12px;">
            <div class="metric-title">{title}</div>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <div style="width: 48%;">
                    <div style="font-size: 0.75rem; color: #64748B;">Anual (Inc)</div>
                    <div class="metric-value" style="font-size: 1.3rem;">{v_a:.2f}% <span style="font-size: 0.8rem; color: {color};">({i_a:.2f} pp)</span></div>
                    <div style="font-size: 0.70rem; color: #64748B; margin-top: 4px;">vs mes prev: {d_a_p:+.2f} pp</div>
                    <div style="font-size: 0.70rem; color: #64748B;">vs año prev: {d_a_a:+.2f} pp</div>
                </div>
                <div style="width: 48%;">
                    <div style="font-size: 0.75rem; color: #64748B;">Mensual (Inc)</div>
                    <div class="metric-value" style="font-size: 1.3rem;">{v_m:.2f}% <span style="font-size: 0.8rem; color: {color};">({i_m:.2f} pp)</span></div>
                    <div style="font-size: 0.70rem; color: #64748B; margin-top: 4px;">vs mes prev: {d_m_p:+.2f} pp</div>
                    <div style="font-size: 0.70rem; color: #64748B;">vs año prev: {d_m_a:+.2f} pp</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- SECCIÓN SUBYACENTE ---
    st.markdown("##### 1. Desglose Subyacente")
    c_s1, c_s2 = st.columns(2)
    render_component_kpi(c_s1, "Mercancías", "Mercancias", "#20B2AA")
    render_component_kpi(c_s2, "Servicios", "Servicios", "#48D1CC")
    
    g_s1, g_s2 = st.columns(2)
    with g_s1:
        # Cálculo Incidencia Interna en Nivel 2 (Subcomponentes respecto a Componentes)
        inc_int_alim = calc_inc_int(df_niv_filtered, f'Alimentos_Bebidas_Tabaco_{inc_col_suffix}', f'Mercancias_{inc_col_suffix}', f'Mercancias_{var_col_suffix}')
        inc_int_mercno = calc_inc_int(df_niv_filtered, f'Mercancias_No_Alimenticias_{inc_col_suffix}', f'Mercancias_{inc_col_suffix}', f'Mercancias_{var_col_suffix}')
        
        fig_merc = go.Figure()
        fig_merc.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_alim, name='Inc. Int. Alim. Beb. y Tab.', marker_color="#008889"))
        fig_merc.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_mercno, name='Inc. Int. Merc. No Alim.', marker_color="#20B2AA"))
        fig_merc.add_trace(go.Scatter(x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Mercancias_{var_col_suffix}'], name='Mercancías (Var)', mode='lines', line=dict(color=COLOR_TEXTO, width=2.5)))
        fig_merc.update_layout(barmode='relative')
        aplicar_layout_light(fig_merc, height=350, title=f"Incidencia Interna Subcomponentes - Mercancías ({tipo_variacion})")
        st.plotly_chart(fig_merc, width="stretch")
    
    with g_s2:
        inc_int_viv = calc_inc_int(df_niv_filtered, f'Vivienda_{inc_col_suffix}', f'Servicios_{inc_col_suffix}', f'Servicios_{var_col_suffix}')
        inc_int_edu = calc_inc_int(df_niv_filtered, f'Educacion_{inc_col_suffix}', f'Servicios_{inc_col_suffix}', f'Servicios_{var_col_suffix}')
        inc_int_otr = calc_inc_int(df_niv_filtered, f'Otros_Servicios_{inc_col_suffix}', f'Servicios_{inc_col_suffix}', f'Servicios_{var_col_suffix}')
        
        fig_serv = go.Figure()
        fig_serv.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_viv, name='Inc. Int. Vivienda', marker_color="#48D1CC"))
        fig_serv.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_edu, name='Inc. Int. Educación', marker_color="#40E0D0"))
        fig_serv.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_otr, name='Inc. Int. Otros Serv.', marker_color="#7FFFD4"))
        fig_serv.add_trace(go.Scatter(x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Servicios_{var_col_suffix}'], name='Servicios (Var)', mode='lines', line=dict(color=COLOR_TEXTO, width=2.5)))
        fig_serv.update_layout(barmode='relative')
        aplicar_layout_light(fig_serv, height=350, title=f"Incidencia Interna Subcomponentes - Servicios ({tipo_variacion})")
        st.plotly_chart(fig_serv, width="stretch")
        
    fig_inc_sub = go.Figure()
    fig_inc_sub.add_trace(go.Scatter(x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Mercancias_{inc_col_suffix}'], mode='lines', name='Inc. Mercancías', line=dict(color="#20B2AA", width=2)))
    fig_inc_sub.add_trace(go.Scatter(x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Servicios_{inc_col_suffix}'], mode='lines', name='Inc. Servicios', line=dict(color="#48D1CC", width=2)))
    aplicar_layout_light(fig_inc_sub, height=300, title=f"Incidencias Componentes Subyacentes ({'Anual' if 'Anual' in tipo_variacion else 'Mensual'})")
    st.plotly_chart(fig_inc_sub, width="stretch")

    st.markdown("---")
    
    # --- SECCIÓN NO SUBYACENTE ---
    st.markdown("##### 2. Desglose No Subyacente")
    c_ns1, c_ns2 = st.columns(2)
    render_component_kpi(c_ns1, "Agropecuarios", "Agropecuarios", "#3B82F6")
    render_component_kpi(c_ns2, "Energéticos y Tarifas", "Energeticos_Tarifas", "#8B5CF6")
    
    g_ns1, g_ns2 = st.columns(2)
    with g_ns1:
        inc_int_frut = calc_inc_int(df_niv_filtered, f'Frutas_Verduras_{inc_col_suffix}', f'Agropecuarios_{inc_col_suffix}', f'Agropecuarios_{var_col_suffix}')
        inc_int_pecu = calc_inc_int(df_niv_filtered, f'Pecuarios_{inc_col_suffix}', f'Agropecuarios_{inc_col_suffix}', f'Agropecuarios_{var_col_suffix}')
        
        fig_agro = go.Figure()
        fig_agro.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_frut, name='Inc. Int. Frut. y Verd.', marker_color="#60A5FA"))
        fig_agro.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_pecu, name='Inc. Int. Pecuarios', marker_color="#1D4ED8"))
        fig_agro.add_trace(go.Scatter(x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Agropecuarios_{var_col_suffix}'], name='Agropecuarios (Var)', mode='lines', line=dict(color=COLOR_TEXTO, width=2.5)))
        fig_agro.update_layout(barmode='relative')
        aplicar_layout_light(fig_agro, height=350, title=f"Incidencia Interna Subcomponentes - Agropecuarios ({tipo_variacion})")
        st.plotly_chart(fig_agro, width="stretch")
    
    with g_ns2:
        inc_int_energ = calc_inc_int(df_niv_filtered, f'Energeticos_{inc_col_suffix}', f'Energeticos_Tarifas_{inc_col_suffix}', f'Energeticos_Tarifas_{var_col_suffix}')
        inc_int_tarif = calc_inc_int(df_niv_filtered, f'Tarifas_Autorizadas_{inc_col_suffix}', f'Energeticos_Tarifas_{inc_col_suffix}', f'Energeticos_Tarifas_{var_col_suffix}')
        
        fig_ener = go.Figure()
        fig_ener.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_energ, name='Inc. Int. Energéticos', marker_color="#A78BFA"))
        fig_ener.add_trace(go.Bar(x=df_niv_filtered['Fecha'], y=inc_int_tarif, name='Inc. Int. Tarifas', marker_color="#6D28D9"))
        fig_ener.add_trace(go.Scatter(x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Energeticos_Tarifas_{var_col_suffix}'], name='Energ. y Tarifas (Var)', mode='lines', line=dict(color=COLOR_TEXTO, width=2.5)))
        fig_ener.update_layout(barmode='relative')
        aplicar_layout_light(fig_ener, height=350, title=f"Incidencia Interna Subcomponentes - Energ. y Tarifas ({tipo_variacion})")
        st.plotly_chart(fig_ener, width="stretch")

    fig_inc_nosub = go.Figure()
    fig_inc_nosub.add_trace(go.Scatter(x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Agropecuarios_{inc_col_suffix}'], mode='lines', name='Inc. Agropecuarios', line=dict(color="#3B82F6", width=2)))
    fig_inc_nosub.add_trace(go.Scatter(x=df_niv_filtered['Fecha'], y=df_niv_filtered[f'Energeticos_Tarifas_{inc_col_suffix}'], mode='lines', name='Inc. Energ. y Tarifas', line=dict(color="#8B5CF6", width=2)))
    aplicar_layout_light(fig_inc_nosub, height=300, title=f"Incidencias Componentes No Subyacentes ({'Anual' if 'Anual' in tipo_variacion else 'Mensual'})")
    st.plotly_chart(fig_inc_nosub, width="stretch")

# ------------------------------------------------------------------------------
# TAB 3: SUBCOMPONENTES
# ------------------------------------------------------------------------------
with tab_subcomp:
        st.markdown("#### Matriz de Presión: 9 Subcomponentes")
        subcomps = [
            'Alimentos_Bebidas_Tabaco', 'Mercancias_No_Alimenticias',
            'Vivienda', 'Educacion', 'Otros_Servicios',
            'Frutas_Verduras', 'Pecuarios', 'Energeticos', 'Tarifas_Autorizadas'
        ]
        subcomps_labels = [
            'Alimentos, Bebidas y Tabaco', 'Mercancías No Alimenticias',
            'Vivienda', 'Educación', 'Otros Servicios',
            'Frutas y Verduras', 'Pecuarios', 'Energéticos', 'Tarifas Autorizadas'
        ]
        
        # Eliminamos registros duplicados por 'Periodo'
        df_heat_temp = df_niv_filtered.drop_duplicates(subset=['Periodo'], keep='last')
        
        df_heat_var = df_heat_temp.set_index('Periodo')[[f"{s}_{var_col_suffix}" for s in subcomps]].T
        df_heat_var.index = subcomps_labels
        cols_heat = df_heat_var.columns[-18:] if df_heat_var.shape[1] >= 18 else df_heat_var.columns
        
        fig_heat_var = px.imshow(
            df_heat_var[cols_heat],
            color_continuous_scale=["#16A34A", "#F8FAFC", "#DC2626"], aspect="auto"
        )
        aplicar_layout_light(fig_heat_var, height=420, title=f"Mapa de Variación {tipo_variacion}")
        st.plotly_chart(fig_heat_var, width="stretch")
        
        df_heat_inc = df_heat_temp.set_index('Periodo')[[f"{s}_{inc_col_suffix}" for s in subcomps]].T
        df_heat_inc.index = subcomps_labels
        
        fig_heat_inc = px.imshow(
            df_heat_inc[cols_heat],
            color_continuous_scale=["#16A34A", "#F8FAFC", "#DC2626"], aspect="auto"
        )
        aplicar_layout_light(fig_heat_inc, height=420, title=f"Mapa de Incidencia ({'Anual' if 'Anual' in tipo_variacion else 'Mensual'})")
        st.plotly_chart(fig_heat_inc, width="stretch")

        st.markdown("---")
        st.markdown("#### Estadísticas Detalladas por Subcomponente")
        
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
                        <div style="font-size: 0.70rem; color: #64748B;">Anual (Inc)</div>
                        <div class="metric-value" style="font-size: 1.15rem; color: {c_va};">{v_a:.2f}% <span style="font-size: 0.75rem; color: #94A3B8;">({i_a:.2f} pp)</span></div>
                        <div style="font-size: 0.65rem; color: #64748B;">vs mes prev: {d_a_p:+.2f} pp</div>
                        <div style="font-size: 0.65rem; color: #64748B;">vs año prev: {d_a_a:+.2f} pp</div>
                    </div>
                    <div style="width: 48%;">
                        <div style="font-size: 0.70rem; color: #64748B;">Mensual (Inc)</div>
                        <div class="metric-value" style="font-size: 1.15rem; color: {c_vm};">{v_m:.2f}% <span style="font-size: 0.75rem; color: #94A3B8;">({i_m:.2f} pp)</span></div>
                        <div style="font-size: 0.65rem; color: #64748B;">vs mes prev: {d_m_p:+.2f} pp</div>
                        <div style="font-size: 0.65rem; color: #64748B;">vs año prev: {d_m_a:+.2f} pp</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 4: DESGLOSE FINO (292 GENÉRICOS)
# ------------------------------------------------------------------------------
with tab_art:
    st.markdown("#### Explorador a Nivel Genérico (Canasta Detallada)")
    
    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        tipos_disp = ["Todos"] + sorted([t for t in df_genericos['Tipo'].dropna().unique()])
        sel_tipo = st.selectbox("Tipo:", tipos_disp)
        
    with col_sel2:
        df_t = df_genericos if sel_tipo == "Todos" else df_genericos[df_genericos['Tipo'] == sel_tipo]
        comps_disp = ["Todos"] + sorted([c for c in df_t['Componente'].dropna().unique()])
        sel_comp = st.selectbox("Componente:", comps_disp)
        
    with col_sel3:
        df_tc = df_t if sel_comp == "Todos" else df_t[df_t['Componente'] == sel_comp]
        subcomps_disp = ["Todos"] + sorted([sc for sc in df_tc['Subcomponente'].dropna().unique()])
        sel_subcomp = st.selectbox("Subcomponente:", subcomps_disp)
        
    df_gen_view = df_tc if sel_subcomp == "Todos" else df_tc[df_tc['Subcomponente'] == sel_subcomp]
    
    # Rankings del corte más reciente disponible en genéricos
    fecha_max_gen = df_gen_view['Fecha'].max()
    df_corte_gen = df_gen_view[df_gen_view['Fecha'] == fecha_max_gen]
    
    st.markdown("##### Ranking de Mayores Cambios y Aportaciones")
    r_opt1, r_opt2 = st.columns(2)
    with r_opt1:
        tipo_ranking = st.radio("Métrica a rankear:", ["Incidencia (pp)", "Variación (%)"], horizontal=True)
    with r_opt2:
        periodo_ranking = st.radio("Periodo del ranking:", ["Anual", "Mensual"], horizontal=True)
        
    col_rank = "Inc_Anual"
    if tipo_ranking == "Incidencia (pp)" and periodo_ranking == "Anual": col_rank = "Inc_Anual"
    elif tipo_ranking == "Incidencia (pp)" and periodo_ranking == "Mensual": col_rank = "Inc_Mensual"
    elif tipo_ranking == "Variación (%)" and periodo_ranking == "Anual": col_rank = "Var_Anual"
    elif tipo_ranking == "Variación (%)" and periodo_ranking == "Mensual": col_rank = "Var_Mensual"
    
    r1, r2 = st.columns(2)
    fecha_max_str = f"{MESES_ABREV[fecha_max_gen.month]}-{fecha_max_gen.year}"
    
    with r1:
        top_alza = df_corte_gen.sort_values(col_rank, ascending=False).head(8)
        fig_alza = px.bar(
            top_alza, x=col_rank, y='Concepto', orientation='h',
            color_discrete_sequence=['#DC2626'], text_auto='.3f'
        )
        fig_alza.update_layout(yaxis={'autorange': 'reversed'})
        aplicar_layout_light(fig_alza, height=310, title=f"Mayores Presiones al Alza ({fecha_max_str})")
        st.plotly_chart(fig_alza, width="stretch")
        
    with r2:
        top_baja = df_corte_gen.sort_values(col_rank, ascending=True).head(8)
        fig_baja = px.bar(
            top_baja, x=col_rank, y='Concepto', orientation='h',
            color_discrete_sequence=['#16A34A'], text_auto='.3f'
        )
        aplicar_layout_light(fig_baja, height=310, title=f"Mayores Contribuciones a la Baja ({fecha_max_str})")
        st.plotly_chart(fig_baja, width="stretch")
        
    st.markdown("---")
    st.markdown("#### Ficha y Evolución Temporal por Genérico")
    
    conceptos = sorted(df_gen_view['Concepto'].dropna().unique().tolist())
    if conceptos:
        concepto_sel = st.selectbox("Seleccionar Genérico:", conceptos)
        df_art = df_genericos[df_genericos['Concepto'] == concepto_sel].sort_values('Fecha')
        
        jerarquia = df_art.iloc[-1]
        st.markdown(f"""
        <div style="background-color: #F8FAFC; padding: 12px; border-radius: 6px; border: 1px solid #E2E8F0; margin-bottom: 16px;">
            <span style="color: #64748B; font-size: 0.85rem;">Estructura de Clasificación:</span><br>
            <strong>Tipo:</strong> {jerarquia['Tipo']} &nbsp; | &nbsp; 
            <strong>Componente:</strong> {jerarquia['Componente']} &nbsp; | &nbsp; 
            <strong>Subcomponente:</strong> {jerarquia['Subcomponente']}
        </div>
        """, unsafe_allow_html=True)
        
        c_k1, c_k2, c_k3, c_k4 = st.columns(4)
        c_k1.metric("Índice Base", f"{jerarquia['Indice']:.2f}")
        c_k2.metric("Var. Anual", f"{jerarquia['Var_Anual']:.2f}%")
        c_k3.metric("Var. Mensual", f"{jerarquia['Var_Mensual']:.2f}%")
        c_k4.metric("Incidencia Anual", f"{jerarquia['Inc_Anual']:.4f} pp")
        
        fig_art_ts = go.Figure()
        fig_art_ts.add_trace(go.Scatter(
            x=df_art['Fecha'], y=df_art['Var_Anual'],
            name='Var. Anual (%)', line=dict(color=COLOR_PRIMARIO, width=2.2)
        ))
        fig_art_ts.add_trace(go.Bar(
            x=df_art['Fecha'], y=df_art['Inc_Anual'],
            name='Incidencia Anual (pp)', marker_color=COLOR_SECUNDARIO, opacity=0.5, yaxis='y2'
        ))
        fig_art_ts.update_layout(
            yaxis=dict(title="Variación Anual (%)"),
            yaxis2=dict(title="Incidencia (pp)", overlaying='y', side='right', showgrid=False)
        )
        aplicar_layout_light(fig_art_ts, height=380, title=f"Serie Histórica e Incidencia: {concepto_sel}")
        st.plotly_chart(fig_art_ts, width="stretch")
        
        with st.expander(f"Ver matriz de datos históricos de {concepto_sel}"):
            st.dataframe(
                df_art[['Fecha', 'Indice', 'Var_Anual', 'Var_Mensual', 'Inc_Anual', 'Inc_Mensual']]
                .sort_values('Fecha', ascending=False)
                .style.format({
                    'Fecha': lambda t: t.strftime('%d/%m/%Y'),
                    'Indice': '{:.2f}',
                    'Var_Anual': '{:.2f}%',
                    'Var_Mensual': '{:.2f}%',
                    'Inc_Anual': '{:.4f}',
                    'Inc_Mensual': '{:.4f}'
                }),
                width="stretch", hide_index=True
            )
    else:
        st.info("No se encontraron genéricos que coincidan con los filtros seleccionados.")