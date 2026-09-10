import os
import pandas as pd
import numpy as np

def generar_niveles_y_genericos(
    catalogo_gen_path="data/intermediate/catalogo_inpc.csv",
    catalogo_agr_path="data/intermediate/catalogo_agregados.csv",
    historico_path="data/intermediate/ccif_historico.csv"
):
    # 0. Asegurar ruta del archivo histórico (con o sin tilde)
    if not os.path.exists(historico_path):
        alt_path = "data/raw/ccif_historico.csv"
        if os.path.exists(alt_path):
            historico_path = alt_path
        else:
            raise FileNotFoundError(f"No se encontró el archivo histórico en '{historico_path}' ni en '{alt_path}'.")

    # Asegurar que exista la carpeta de salida
    os.makedirs("data/intermediate", exist_ok=True)

    print("1/5. Cargando catálogos e histórico...")
    df_gen = pd.read_csv(catalogo_gen_path)
    df_agr = pd.read_csv(catalogo_agr_path)
    df_hist = pd.read_csv(historico_path)
    
    # Estandarizar formatos
    df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha'])
    df_hist['Concepto'] = df_hist['Concepto'].astype(str).str.strip()
    df_gen['Concepto'] = df_gen['Concepto'].astype(str).str.strip()

    print("2/5. Vinculando histórico con metadatos y calculando base de transición...")
    # Unir histórico con catálogo de genéricos
    merged = pd.merge(df_hist, df_gen, on='Concepto', how='inner')
    
    # Base transición Julio 2024 = 100: I_base24 = I_t / f_j
    merged['Indice_Base24'] = merged['Indice'] / merged['Factor_Encadenamiento']
    merged['Pond_x_Base24'] = merged['Ponderador'] * merged['Indice_Base24']

    # =========================================================================
    # PARTE A: GENERACIÓN DE NIVELES.CSV Y AGREGADOS
    # =========================================================================
    print("3/5. Calculando los 16 niveles agregados (Laspeyres encadenado)...")
    fechas = sorted(merged['Fecha'].unique())
    registros_niveles = []

    for fecha, sub_df in merged.groupby('Fecha'):
        fila = {'Fecha': fecha}
        
        for _, agr in df_agr.iterrows():
            clave = agr['Clave']
            nivel = agr['Nivel']
            f_h = agr['Factor_Encadenamiento']
            
            if nivel == 'General':
                subset = sub_df
            elif nivel == 'Tipo':
                subset = sub_df[sub_df['Tipo'] == agr['Tipo']]
            elif nivel == 'Componente':
                subset = sub_df[sub_df['Componente'] == agr['Componente']]
            elif nivel == 'Subcomponente':
                subset = sub_df[sub_df['Subcomponente'] == agr['Subcomponente']]
            
            indice_agregado = f_h * (subset['Pond_x_Base24'].sum() / subset['Ponderador'].sum())
            fila[clave] = indice_agregado
            
        registros_niveles.append(fila)

    df_niveles = pd.DataFrame(registros_niveles).sort_values('Fecha').reset_index(drop=True)

    print("4/5. Calculando variaciones e incidencias de agregados...")
    f_gen = df_agr.loc[df_agr['Clave'] == 'INPC_General', 'Factor_Encadenamiento'].values[0]
    
    # Preparar base 24 general para el cálculo de incidencias
    df_niveles['INPC_Gen_B24'] = df_niveles['INPC_General'] / f_gen
    df_niveles['INPC_Gen_B24_lag1'] = df_niveles['INPC_Gen_B24'].shift(1)
    df_niveles['INPC_Gen_B24_lag12'] = df_niveles['INPC_Gen_B24'].shift(12)

    orden_columnas_niveles = ['Fecha']
    claves_ordenadas = [
        'INPC_General', 'Subyacente', 'Mercancias', 'Alimentos_Bebidas_Tabaco',
        'Mercancias_No_Alimenticias', 'Servicios', 'Vivienda', 'Educacion',
        'Otros_Servicios', 'No_Subyacente', 'Agropecuarios', 'Frutas_Verduras',
        'Pecuarios', 'Energeticos_Tarifas', 'Energeticos', 'Tarifas_Autorizadas'
    ]

    for col in claves_ordenadas:
        w_k = df_agr.loc[df_agr['Clave'] == col, 'Ponderador'].values[0]
        f_k = df_agr.loc[df_agr['Clave'] == col, 'Factor_Encadenamiento'].values[0]
        
        # Variaciones
        df_niveles[f'{col}_Var_Anual'] = df_niveles[col].pct_change(12) * 100
        df_niveles[f'{col}_Var_Mensual'] = df_niveles[col].pct_change(1) * 100
        
        # Incidencias
        idx_base24 = df_niveles[col] / f_k
        df_niveles[f'{col}_Inc_Anual'] = (idx_base24 - idx_base24.shift(12)) / df_niveles['INPC_Gen_B24_lag12'] * w_k
        df_niveles[f'{col}_Inc_Mensual'] = (idx_base24 - idx_base24.shift(1)) / df_niveles['INPC_Gen_B24_lag1'] * w_k

        orden_columnas_niveles.extend([
            col, f'{col}_Var_Anual', f'{col}_Var_Mensual', f'{col}_Inc_Anual', f'{col}_Inc_Mensual'
        ])

    # Guardar un df con lags para usar en genéricos antes de filtrar columnas
    lags_gen = df_niveles[['Fecha', 'INPC_Gen_B24_lag1', 'INPC_Gen_B24_lag12']].copy()
    
    df_niveles = df_niveles[orden_columnas_niveles]
    niveles_out = "data/intermediate/niveles.csv"
    df_niveles.to_csv(niveles_out, index=False, encoding="utf-8-sig")
    print(f" -> Guardado: {niveles_out} ({len(df_niveles):,} fechas)")

    # =========================================================================
    # PARTE B: GENERACIÓN DE GENERICOS.CSV
    # =========================================================================
    print("5/5. Calculando variaciones e incidencias para genericos.csv...")
    merged = merged.sort_values(['Concepto', 'Fecha']).reset_index(drop=True)
    
    # Variaciones
    merged['Var_Anual'] = merged.groupby('Concepto')['Indice'].pct_change(12) * 100
    merged['Var_Mensual'] = merged.groupby('Concepto')['Indice'].pct_change(1) * 100
    
    # Lags para incidencias
    merged['Indice_Base24_lag1'] = merged.groupby('Concepto')['Indice_Base24'].shift(1)
    merged['Indice_Base24_lag12'] = merged.groupby('Concepto')['Indice_Base24'].shift(12)
    
    # Unir lags del índice general
    merged = pd.merge(merged, lags_gen, on='Fecha', how='left')
    
    # Incidencias
    merged['Inc_Anual'] = (merged['Indice_Base24'] - merged['Indice_Base24_lag12']) / merged['INPC_Gen_B24_lag12'] * merged['Ponderador']
    merged['Inc_Mensual'] = (merged['Indice_Base24'] - merged['Indice_Base24_lag1']) / merged['INPC_Gen_B24_lag1'] * merged['Ponderador']
    
    # Reestructuración de columnas
    merged = merged.drop(columns=['Indice', 'Ponderador', 'Factor_Encadenamiento'])
    merged = merged.rename(columns={'Indice_Base24': 'Indice'})
    
    cols_gen_orden = [
        'Fecha', 'Concepto', 'Tipo', 'Componente', 'Subcomponente',
        'Indice', 'Var_Anual', 'Var_Mensual', 'Inc_Anual', 'Inc_Mensual'
    ]
    
    df_genericos = merged[cols_gen_orden].sort_values(
        ['Tipo', 'Componente', 'Subcomponente', 'Concepto', 'Fecha']
    ).reset_index(drop=True)
    
    genericos_out = "data/intermediate/genericos.csv"
    df_genericos.to_csv(genericos_out, index=False, encoding="utf-8-sig")
    print(f" -> Guardado: {genericos_out} ({len(df_genericos):,} filas)")

    print("\nProceso terminado con éxito.")
    return df_niveles, df_genericos


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================
if __name__ == '__main__':
    df_niveles, df_genericos = generar_niveles_y_genericos()