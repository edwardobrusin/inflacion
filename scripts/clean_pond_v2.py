import pandas as pd
import numpy as np

def limpiar_ponderadores(file_path):
    # 1. Cargar archivo Excel
    df = pd.read_excel(file_path, sheet_name='Hoja1')
    
    # 2. Asignación directa de nombres a las 18 columnas posicionales
    column_names = [
        'Concepto', 'Ponderador', 'Factor_Encadenamiento',
        'Subyacente_Total', 'Mercancias_Total', 'Alimentos_Bebidas_Tabaco',
        'Mercancias_No_Alimenticias', 'Servicios_Total', 'Educacion',
        'Vivienda', 'Otros_Servicios', 'No_Subyacente_Total',
        'Agropecuarios_Total', 'Frutas_Verduras', 'Pecuarios',
        'Energeticos_Tarifas_Total', 'Energeticos', 'Tarifas_Autorizadas'
    ]
    df.columns = column_names[:len(df.columns)]
    
    # =========================================================================
    # PARTE 1: EXTRACCIÓN DE METADATOS DE LOS AGREGADOS
    # =========================================================================
    col_concepto_str = df['Concepto'].astype(str).str.strip().str.lower()
    
    idx_factores = df[col_concepto_str.str.contains('factor de encadenamiento')].index[0]
    idx_ponderadores = df[col_concepto_str.str.contains('indice general')].index[0]
    
    row_factores = df.iloc[idx_factores]
    row_ponderadores = df.iloc[idx_ponderadores]
    
    agregados_schema = [
        # --- Nivel 0: General ---
        {'Clave': 'INPC_General', 'Nombre': 'Índice General', 'Nivel': 'General', 
         'Tipo': 'General', 'Componente': 'General', 'Subcomponente': 'General',
         'Col_Pond': 'Ponderador', 'Col_Fact': 'Factor_Encadenamiento'},
        
        # --- Nivel 1: Tipo ---
        {'Clave': 'Subyacente', 'Nombre': 'Subyacente', 'Nivel': 'Tipo', 
         'Tipo': 'Subyacente', 'Componente': None, 'Subcomponente': None,
         'Col_Pond': 'Subyacente_Total', 'Col_Fact': 'Subyacente_Total'},
        {'Clave': 'No_Subyacente', 'Nombre': 'No subyacente', 'Nivel': 'Tipo', 
         'Tipo': 'No Subyacente', 'Componente': None, 'Subcomponente': None,
         'Col_Pond': 'No_Subyacente_Total', 'Col_Fact': 'No_Subyacente_Total'},
        
        # --- Nivel 2: Componentes Subyacentes ---
        {'Clave': 'Mercancias', 'Nombre': 'Mercancías', 'Nivel': 'Componente', 
         'Tipo': 'Subyacente', 'Componente': 'Mercancías', 'Subcomponente': None,
         'Col_Pond': 'Mercancias_Total', 'Col_Fact': 'Mercancias_Total'},
        {'Clave': 'Servicios', 'Nombre': 'Servicios', 'Nivel': 'Componente', 
         'Tipo': 'Subyacente', 'Componente': 'Servicios', 'Subcomponente': None,
         'Col_Pond': 'Servicios_Total', 'Col_Fact': 'Servicios_Total'},
        
        # --- Nivel 2: Componentes No Subyacentes ---
        {'Clave': 'Agropecuarios', 'Nombre': 'Agropecuarios', 'Nivel': 'Componente', 
         'Tipo': 'No Subyacente', 'Componente': 'Agropecuarios', 'Subcomponente': None,
         'Col_Pond': 'Agropecuarios_Total', 'Col_Fact': 'Agropecuarios_Total'},
        {'Clave': 'Energeticos_Tarifas', 'Nombre': 'Energéticos y tarifas autorizadas por el gobierno', 
         'Nivel': 'Componente', 'Tipo': 'No Subyacente', 'Componente': 'Energéticos y tarifas', 'Subcomponente': None,
         'Col_Pond': 'Energeticos_Tarifas_Total', 'Col_Fact': 'Energeticos_Tarifas_Total'},
        
        # --- Nivel 3: Subcomponentes de Mercancías ---
        {'Clave': 'Alimentos_Bebidas_Tabaco', 'Nombre': 'Alimentos, bebidas y tabaco', 'Nivel': 'Subcomponente', 
         'Tipo': 'Subyacente', 'Componente': 'Mercancías', 'Subcomponente': 'Alimentos, bebidas y tabaco',
         'Col_Pond': 'Alimentos_Bebidas_Tabaco', 'Col_Fact': 'Alimentos_Bebidas_Tabaco'},
        {'Clave': 'Mercancias_No_Alimenticias', 'Nombre': 'Mercancías no alimenticias', 'Nivel': 'Subcomponente', 
         'Tipo': 'Subyacente', 'Componente': 'Mercancías', 'Subcomponente': 'Mercancías no alimenticias',
         'Col_Pond': 'Mercancias_No_Alimenticias', 'Col_Fact': 'Mercancias_No_Alimenticias'},
        
        # --- Nivel 3: Subcomponentes de Servicios ---
        {'Clave': 'Vivienda', 'Nombre': 'Vivienda', 'Nivel': 'Subcomponente', 
         'Tipo': 'Subyacente', 'Componente': 'Servicios', 'Subcomponente': 'Vivienda',
         'Col_Pond': 'Vivienda', 'Col_Fact': 'Vivienda'},
        {'Clave': 'Educacion', 'Nombre': 'Educación (Colegiaturas)', 'Nivel': 'Subcomponente', 
         'Tipo': 'Subyacente', 'Componente': 'Servicios', 'Subcomponente': 'Educación (Colegiaturas)',
         'Col_Pond': 'Educacion', 'Col_Fact': 'Educacion'},
        {'Clave': 'Otros_Servicios', 'Nombre': 'Otros servicios', 'Nivel': 'Subcomponente', 
         'Tipo': 'Subyacente', 'Componente': 'Servicios', 'Subcomponente': 'Otros servicios',
         'Col_Pond': 'Otros_Servicios', 'Col_Fact': 'Otros_Servicios'},
        
        # --- Nivel 3: Subcomponentes de Agropecuarios ---
        {'Clave': 'Frutas_Verduras', 'Nombre': 'Frutas y verduras', 'Nivel': 'Subcomponente', 
         'Tipo': 'No Subyacente', 'Componente': 'Agropecuarios', 'Subcomponente': 'Frutas y verduras',
         'Col_Pond': 'Frutas_Verduras', 'Col_Fact': 'Frutas_Verduras'},
        {'Clave': 'Pecuarios', 'Nombre': 'Pecuarios', 'Nivel': 'Subcomponente', 
         'Tipo': 'No Subyacente', 'Componente': 'Agropecuarios', 'Subcomponente': 'Pecuarios',
         'Col_Pond': 'Pecuarios', 'Col_Fact': 'Pecuarios'},
        
        # --- Nivel 3: Subcomponentes de Energéticos y Tarifas ---
        {'Clave': 'Energeticos', 'Nombre': 'Energéticos', 'Nivel': 'Subcomponente', 
         'Tipo': 'No Subyacente', 'Componente': 'Energéticos y tarifas', 'Subcomponente': 'Energéticos',
         'Col_Pond': 'Energeticos', 'Col_Fact': 'Energeticos'},
        {'Clave': 'Tarifas_Autorizadas', 'Nombre': 'Tarifas autorizadas por el gobierno', 'Nivel': 'Subcomponente', 
         'Tipo': 'No Subyacente', 'Componente': 'Energéticos y tarifas', 'Subcomponente': 'Tarifas autorizadas por el gobierno',
         'Col_Pond': 'Tarifas_Autorizadas', 'Col_Fact': 'Tarifas_Autorizadas'}
    ]
    
    lista_agregados = []
    for item in agregados_schema:
        lista_agregados.append({
            'Clave': item['Clave'],
            'Nombre': item['Nombre'],
            'Nivel': item['Nivel'],
            'Tipo': item['Tipo'],
            'Componente': item['Componente'],
            'Subcomponente': item['Subcomponente'],
            'Ponderador': float(row_ponderadores[item['Col_Pond']]),
            'Factor_Encadenamiento': float(row_factores[item['Col_Fact']])
        })
    df_agregados = pd.DataFrame(lista_agregados)

    # =========================================================================
    # PARTE 2: EXTRACCIÓN Y CLASIFICACIÓN DE GENÉRICOS
    # =========================================================================
    df_clean = df.iloc[idx_ponderadores + 1:].copy()
    df_clean['is_generic'] = df_clean.apply(lambda row: 'X' in [str(x).strip() for x in row[3:].values], axis=1)
    df_items = df_clean[df_clean['is_generic']].copy()
    
    def extract_classification(row):
        clasificacion = {
            'Tipo': 'Subyacente' if pd.notna(row['Subyacente_Total']) and str(row['Subyacente_Total']).strip() == 'X' else 'No Subyacente',
            'Componente': None,
            'Subcomponente': None
        }
        
        if clasificacion['Tipo'] == 'Subyacente':
            if str(row['Mercancias_Total']).strip() == 'X':
                clasificacion['Componente'] = 'Mercancías'
                clasificacion['Subcomponente'] = 'Alimentos, bebidas y tabaco' if str(row['Alimentos_Bebidas_Tabaco']).strip() == 'X' else 'Mercancías no alimenticias'
            elif str(row['Servicios_Total']).strip() == 'X':
                clasificacion['Componente'] = 'Servicios'
                if str(row['Educacion']).strip() == 'X': clasificacion['Subcomponente'] = 'Educación (Colegiaturas)'
                elif str(row['Vivienda']).strip() == 'X': clasificacion['Subcomponente'] = 'Vivienda'
                elif str(row['Otros_Servicios']).strip() == 'X': clasificacion['Subcomponente'] = 'Otros servicios'
        else:
            if str(row['Agropecuarios_Total']).strip() == 'X':
                clasificacion['Componente'] = 'Agropecuarios'
                clasificacion['Subcomponente'] = 'Frutas y verduras' if str(row['Frutas_Verduras']).strip() == 'X' else 'Pecuarios'
            elif str(row['Energeticos_Tarifas_Total']).strip() == 'X':
                clasificacion['Componente'] = 'Energéticos y tarifas'
                clasificacion['Subcomponente'] = 'Energéticos' if str(row['Energeticos']).strip() == 'X' else 'Tarifas autorizadas por el gobierno'
                
        return pd.Series(clasificacion)

    classifications = df_items.apply(extract_classification, axis=1)
    
    df_genericos = pd.concat([
        df_items[['Concepto', 'Ponderador', 'Factor_Encadenamiento']].astype({
            'Ponderador': float, 
            'Factor_Encadenamiento': float
        }), 
        classifications
    ], axis=1)
    
    df_genericos['Concepto'] = df_genericos['Concepto'].str.strip()
    df_genericos = df_genericos.reset_index(drop=True)
    
    return df_genericos, df_agregados

if __name__ == '__main__':
    df_gen, df_agr = limpiar_ponderadores("data/raw/CCIF.xlsx")
    df_gen.to_csv("data/intermediate/catalogo_inpc.csv", index=False, encoding="utf-8-sig")
    df_agr.to_csv("data/intermediate/catalogo_agregados.csv", index=False, encoding="utf-8-sig")
    print(f"Éxito: {len(df_gen)} genéricos y {len(df_agr)} agregados exportados.")