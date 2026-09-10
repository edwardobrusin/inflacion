import os
import numpy as np
import pandas as pd

# 1. Carga de insumos
path_parquet = 'data/intermediate/ccif_historico.parquet'
path_catalogo = 'data/intermediate/catalogo_inpc.csv'

if not os.path.exists(path_parquet):
    raise FileNotFoundError(f"No se encontró el archivo histórico en '{path_parquet}'.")
if not os.path.exists(path_catalogo):
    raise FileNotFoundError(f"No se encontró el catálogo en '{path_catalogo}'.")

print("Cargando ccif_historico.parquet y catalogo_inpc.csv...")
df_hist = pd.read_parquet(path_parquet)
df_cat = pd.read_csv(path_catalogo)

# Asegurar formato de fecha datetime y normalizar al nivel mensual
df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha']).dt.to_period('M').dt.to_timestamp()

# Normalización robusta de Concepto para evitar diferencias invisibles
def normalizar_concepto(s):
    return (
        s.astype('string')
        .str.replace('\u00A0', ' ', regex=False)  # espacio no separable
        .str.replace(r'\s+', ' ', regex=True)    # espacios, tabs, saltos, etc.
        .str.strip()
    )

df_hist['Concepto'] = normalizar_concepto(df_hist['Concepto'])
df_cat['Concepto'] = normalizar_concepto(df_cat['Concepto'])

# Auditoría de conceptos antes del merge
conceptos_hist = set(df_hist['Concepto'].dropna().unique())
conceptos_cat = set(df_cat['Concepto'].dropna().unique())

solo_hist = conceptos_hist - conceptos_cat
solo_cat = conceptos_cat - conceptos_hist

print(f"\nConceptos únicos en histórico: {len(conceptos_hist)}")
print(f"Conceptos únicos en catálogo:  {len(conceptos_cat)}")

if solo_hist:
    print("\nConceptos presentes SOLO en histórico:")
    for x in sorted(solo_hist):
        print(repr(x))

if solo_cat:
    print("\nConceptos presentes SOLO en catálogo:")
    for x in sorted(solo_cat):
        print(repr(x))

# 2. Conexión (Merge)
df_merged = df_hist.merge(
    df_cat,
    on='Concepto',
    how='inner',
    validate='many_to_one'
)

if df_merged.empty:
    raise SystemExit(
        "El cruce entre el histórico y el catálogo resultó vacío. "
        "Revisa los Conceptos."
    )

print(
    f"Base combinada: {len(df_merged):,} registros "
    f"cubriendo {df_merged['Concepto'].nunique()} productos genéricos."
)

if df_merged['Concepto'].nunique() != len(conceptos_cat):
    faltantes = conceptos_cat - set(df_merged['Concepto'].unique())
    print("\nADVERTENCIA: conceptos del catálogo que no llegaron al merge:")
    for x in sorted(faltantes):
        print(repr(x))

if df_merged['Concepto'].nunique() != 292:
    raise SystemExit(
        f"ERROR: se esperaban 292 genéricos después del merge, "
        f"pero se obtuvieron {df_merged['Concepto'].nunique()}."
    )

# Orden cronológico estricto por producto
df_merged = df_merged.sort_values(
    by=['Concepto', 'Fecha']
).reset_index(drop=True)

# Cada genérico debe tener exactamente una observación por mes
duplicados = df_merged[
    df_merged.duplicated(
        subset=['Concepto', 'Fecha'],
        keep=False
    )
]

if not duplicados.empty:
    print("\nERROR: existen múltiples observaciones para el mismo Concepto-Fecha:")
    print(
        duplicados[
            ['Concepto', 'Fecha', 'Indice']
        ].sort_values(['Concepto', 'Fecha']).to_string(index=False)
    )
    raise SystemExit(
        "Corrige los duplicados Concepto-Fecha antes de continuar."
    )

# 3. Lags e Inflaciones a Nivel Producto Genérico
# Los rezagos se obtienen por fecha calendario, no por posición de fila.

lag_base = df_merged[['Concepto', 'Fecha', 'Indice']].copy()

# Mes anterior
lag1 = lag_base.rename(
    columns={
        'Fecha': 'Fecha_Lag1',
        'Indice': 'Indice_Lag1'
    }
)

lag1['Fecha'] = lag1['Fecha_Lag1'] + pd.DateOffset(months=1)
lag1 = lag1[['Concepto', 'Fecha', 'Indice_Lag1']]

# Mismo mes del año anterior
lag12 = lag_base.rename(
    columns={
        'Fecha': 'Fecha_Lag12',
        'Indice': 'Indice_Lag12'
    }
)

lag12['Fecha'] = lag12['Fecha_Lag12'] + pd.DateOffset(months=12)
lag12 = lag12[['Concepto', 'Fecha', 'Indice_Lag12']]

# Incorporar rezagos
df_merged = df_merged.merge(
    lag1,
    on=['Concepto', 'Fecha'],
    how='left',
    validate='one_to_one'
)

df_merged = df_merged.merge(
    lag12,
    on=['Concepto', 'Fecha'],
    how='left',
    validate='one_to_one'
)

df_merged['Inflacion_Mensual'] = (
    df_merged['Indice'] / df_merged['Indice_Lag1'] - 1
) * 100

df_merged['Inflacion_Anual'] = (
    df_merged['Indice'] / df_merged['Indice_Lag12'] - 1
) * 100

# Auditoría de cobertura temporal por genérico
cobertura = (
    df_merged
    .groupby('Concepto')['Fecha']
    .agg(['min', 'max', 'count'])
)

cobertura['meses_esperados'] = (
    (cobertura['max'].dt.year - cobertura['min'].dt.year) * 12
    + (cobertura['max'].dt.month - cobertura['min'].dt.month)
    + 1
)

faltantes_temporales = cobertura[
    cobertura['count'] != cobertura['meses_esperados']
]

if not faltantes_temporales.empty:
    print("\nADVERTENCIA: existen genéricos con meses faltantes:")
    print(faltantes_temporales.to_string())

# 4. Cálculo del Índice General del INPC (Base de ponderación)
# Se calcula dinámicamente como la media ponderada del total de la canasta
def weighted_avg(g):
    return (g['Ponderador'] * g['Indice']).sum() / g['Ponderador'].sum()

gen_idx = df_merged.groupby('Fecha').apply(
    weighted_avg,
    include_groups=False
).rename('Indice_General').reset_index()

gen_idx = gen_idx.sort_values('Fecha').reset_index(drop=True)

# Rezago mensual por fecha
gen_lag1 = gen_idx[['Fecha', 'Indice_General']].copy()
gen_lag1['Fecha'] = gen_lag1['Fecha'] + pd.DateOffset(months=1)
gen_lag1 = gen_lag1.rename(
    columns={'Indice_General': 'Indice_Gen_Lag1'}
)

# Rezago anual por fecha
gen_lag12 = gen_idx[['Fecha', 'Indice_General']].copy()
gen_lag12['Fecha'] = gen_lag12['Fecha'] + pd.DateOffset(months=12)
gen_lag12 = gen_lag12.rename(
    columns={'Indice_General': 'Indice_Gen_Lag12'}
)

gen_idx = gen_idx.merge(
    gen_lag1[['Fecha', 'Indice_Gen_Lag1']],
    on='Fecha',
    how='left',
    validate='one_to_one'
)

gen_idx = gen_idx.merge(
    gen_lag12[['Fecha', 'Indice_Gen_Lag12']],
    on='Fecha',
    how='left',
    validate='one_to_one'
)

gen_idx['Inflacion_Mensual'] = (
    gen_idx['Indice_General'] / gen_idx['Indice_Gen_Lag1'] - 1
) * 100

gen_idx['Inflacion_Anual'] = (
    gen_idx['Indice_General'] / gen_idx['Indice_Gen_Lag12'] - 1
) * 100

gen_idx['Incidencia_Mensual'] = gen_idx['Inflacion_Mensual']
gen_idx['Incidencia_Anual'] = gen_idx['Inflacion_Anual']
gen_idx['Nivel'] = 'General'
gen_idx['Agrupador'] = 'INPC General'
gen_idx['Incidencia_Mensual'] = gen_idx['Inflacion_Mensual']
gen_idx['Incidencia_Anual'] = gen_idx['Inflacion_Anual']
gen_idx['Nivel'] = 'General'
gen_idx['Agrupador'] = 'INPC General'
gen_idx['Ponderador'] = (
    df_merged[['Concepto', 'Ponderador']]
    .drop_duplicates()
    ['Ponderador']
    .sum()
)

# 5. Cálculo de Incidencias Individuales (Genéricos)
df_merged = df_merged.merge(
    gen_idx[['Fecha', 'Indice_Gen_Lag1', 'Indice_Gen_Lag12']], 
    on='Fecha', 
    how='left'
)

# Fórmula oficial de incidencia: w_i * (I_t - I_base) / I_gen_base
df_merged['Incidencia_Mensual'] = (
    df_merged['Ponderador'] * (df_merged['Indice'] - df_merged['Indice_Lag1'])
) / df_merged['Indice_Gen_Lag1']

df_merged['Incidencia_Anual'] = (
    df_merged['Ponderador'] * (df_merged['Indice'] - df_merged['Indice_Lag12'])
) / df_merged['Indice_Gen_Lag12']

# 6. Agregaciones por Niveles Jerárquicos (Subcomponente, Componente, Tipo)
def aggregate_by_hierarchy(df_base, level_column, level_name):
    records = []

    for (fecha, agrupador), g in df_base.groupby(
        ['Fecha', level_column],
        dropna=False
    ):
        w_sum = g['Ponderador'].sum()

        if w_sum == 0:
            idx_agg = np.nan
        else:
            idx_agg = (
                (g['Ponderador'] * g['Indice']).sum()
                / w_sum
            )

        inc_m = g['Incidencia_Mensual'].sum(min_count=1)
        inc_a = g['Incidencia_Anual'].sum(min_count=1)

        records.append({
            'Fecha': fecha,
            'Nivel': level_name,
            'Agrupador': agrupador,
            'Ponderador': w_sum,
            'Indice': idx_agg,
            'Incidencia_Mensual': inc_m,
            'Incidencia_Anual': inc_a
        })

    df_lvl = pd.DataFrame(records)

    df_lvl = df_lvl.sort_values(
        ['Agrupador', 'Fecha']
    ).reset_index(drop=True)

    # Rezago mensual por fecha calendario
    lag1 = df_lvl[
        ['Agrupador', 'Fecha', 'Indice']
    ].copy()

    lag1['Fecha'] = lag1['Fecha'] + pd.DateOffset(months=1)
    lag1 = lag1.rename(
        columns={'Indice': 'Indice_Lag1'}
    )

    # Rezago anual por fecha calendario
    lag12 = df_lvl[
        ['Agrupador', 'Fecha', 'Indice']
    ].copy()

    lag12['Fecha'] = lag12['Fecha'] + pd.DateOffset(months=12)
    lag12 = lag12.rename(
        columns={'Indice': 'Indice_Lag12'}
    )

    df_lvl = df_lvl.merge(
        lag1[
            ['Agrupador', 'Fecha', 'Indice_Lag1']
        ],
        on=['Agrupador', 'Fecha'],
        how='left',
        validate='one_to_one'
    )

    df_lvl = df_lvl.merge(
        lag12[
            ['Agrupador', 'Fecha', 'Indice_Lag12']
        ],
        on=['Agrupador', 'Fecha'],
        how='left',
        validate='one_to_one'
    )

    df_lvl['Inflacion_Mensual'] = (
        df_lvl['Indice'] / df_lvl['Indice_Lag1'] - 1
    ) * 100

    df_lvl['Inflacion_Anual'] = (
        df_lvl['Indice'] / df_lvl['Indice_Lag12'] - 1
    ) * 100

    return df_lvl

print("Calculando agregaciones por Subcomponente, Componente y Tipo...")
df_subcomp = aggregate_by_hierarchy(df_merged, 'Subcomponente', 'Subcomponente')
df_comp = aggregate_by_hierarchy(df_merged, 'Componente', 'Componente')
df_tipo = aggregate_by_hierarchy(df_merged, 'Tipo', 'Tipo')

# Estructura del nivel Genérico
df_gen_items = df_merged.copy()
df_gen_items['Nivel'] = 'Generico'
df_gen_items['Agrupador'] = df_gen_items['Concepto']

cols_std = [
    'Fecha', 'Nivel', 'Agrupador', 'Ponderador', 'Indice',
    'Inflacion_Mensual', 'Inflacion_Anual', 'Incidencia_Mensual', 'Incidencia_Anual'
]

df_general_clean = gen_idx.rename(columns={'Indice_General': 'Indice'})[cols_std]
df_items_clean = df_gen_items[cols_std]

# 7. Consolidación de la Base Maestra Tidy
df_master_tidy = pd.concat([
    df_general_clean,
    df_tipo[cols_std],
    df_comp[cols_std],
    df_subcomp[cols_std],
    df_items_clean
], ignore_index=True)

# 8. Auditoría de consistencia y aditividad en el último periodo

ultima_fecha = df_master_tidy['Fecha'].max()
t_audit = df_master_tidy[
    df_master_tidy['Fecha'] == ultima_fecha
].copy()

general = t_audit[
    t_audit['Nivel'] == 'General'
]

if general.empty:
    raise SystemExit(
        "ERROR: no se encontró el registro General en el último periodo."
    )

inf_m_gen = general['Inflacion_Mensual'].iloc[0]
inf_a_gen = general['Inflacion_Anual'].iloc[0]

print("\n" + "=" * 70)
print(
    f"AUDITORÍA DE CONSISTENCIA — "
    f"{ultima_fecha.strftime('%Y-%m')}"
)
print("=" * 70)

print(
    f"Inflación General Mensual: {inf_m_gen:.6f}%"
)
print(
    f"Inflación General Anual:   {inf_a_gen:.6f}%"
)

print(
    f"\nGenéricos utilizados: "
    f"{t_audit[t_audit['Nivel'] == 'Generico']['Agrupador'].nunique()}"
)

# Revisar aditividad de incidencias
for lvl in ['Tipo', 'Componente', 'Subcomponente', 'Generico']:

    nivel = t_audit[t_audit['Nivel'] == lvl]

    sum_m = nivel['Incidencia_Mensual'].sum(
        min_count=1
    )

    sum_a = nivel['Incidencia_Anual'].sum(
        min_count=1
    )

    diff_m = sum_m - inf_m_gen
    diff_a = sum_a - inf_a_gen

    print(
        f"\nNivel [{lvl:<13}]"
    )
    print(
        f"  Incidencia mensual = {sum_m:.6f} p.p."
    )
    print(
        f"  Diferencia mensual = {diff_m:.10f} p.p."
    )
    print(
        f"  Incidencia anual   = {sum_a:.6f} p.p."
    )
    print(
        f"  Diferencia anual   = {diff_a:.10f} p.p."
    )

# Auditoría específica de genéricos
gen_audit = df_merged[
    df_merged['Fecha'] == ultima_fecha
]

print("\n--- AUDITORÍA DE GENÉRICOS ---")

print(
    f"Genéricos en histórico/canasta: "
    f"{len(conceptos_hist)}"
)

print(
    f"Genéricos en catálogo: "
    f"{len(conceptos_cat)}"
)

print(
    f"Genéricos después del merge: "
    f"{df_merged['Concepto'].nunique()}"
)

# Verificar ponderadores
peso_total = (
    gen_audit[
        ['Concepto', 'Ponderador']
    ]
    .drop_duplicates()
    ['Ponderador']
    .sum()
)

print(
    f"Suma de ponderadores de genéricos: "
    f"{peso_total:.10f}"
)

# Genéricos sin inflación mensual/anual
sin_lag_m = gen_audit[
    gen_audit['Indice_Lag1'].isna()
]['Concepto'].nunique()

sin_lag_a = gen_audit[
    gen_audit['Indice_Lag12'].isna()
]['Concepto'].nunique()

print(
    f"Genéricos sin dato para inflación mensual: "
    f"{sin_lag_m}"
)

print(
    f"Genéricos sin dato para inflación anual: "
    f"{sin_lag_a}"
)

# 9. Top 5 Productos con Mayor y Menor Incidencia Mensual
top_positivas = df_merged[df_merged['Fecha'] == ultima_fecha].nlargest(5, 'Incidencia_Mensual')[['Concepto', 'Ponderador', 'Inflacion_Mensual', 'Incidencia_Mensual']]
top_negativas = df_merged[df_merged['Fecha'] == ultima_fecha].nsmallest(5, 'Incidencia_Mensual')[['Concepto', 'Ponderador', 'Inflacion_Mensual', 'Incidencia_Mensual']]

print("\n--- MAYOR INCIDENCIA AL ALZA (Mensual) ---")
print(top_positivas.to_string(index=False))

print("\n--- MAYOR INCIDENCIA A LA BAJA (Mensual) ---")
print(top_negativas.to_string(index=False))

# 10. Almacenamiento de Resultados
os.makedirs('data/intermediate', exist_ok=True)

# Guardar base detallada a nivel genérico con todas sus clasificaciones
path_detallado = 'data/intermediate/genericos.csv'
cols_detalladas = [
    'Fecha', 'ID_API', 'Concepto', 'Tipo', 'Componente', 'Subcomponente',
    'Ponderador', 'Indice', 'Inflacion_Mensual', 'Inflacion_Anual',
    'Incidencia_Mensual', 'Incidencia_Anual'
]
df_merged[cols_detalladas].to_csv(path_detallado, index=False)

# Guardar base maestra jerárquica unificada (todos los niveles)
path_master = 'data/intermediate/niveles.csv'
df_master_tidy.to_csv(path_master, index=False)

print(f"\nBases generadas exitosamente:")
print(f" 1. Detalle de genéricos: '{path_detallado}'")
print(f" 2. Base jerárquica multinivel: '{path_master}'")