import pandas as pd
import numpy as np

def limpiar_ponderadores(file_path):
    # Cargar y mapear columnas clave basándose en sus índices
    df = pd.read_excel(file_path, sheet_name='Hoja1')
    
    col_mapping = {
        df.columns[0]: 'Concepto', df.columns[1]: 'Ponderador', df.columns[2]: 'Factor_Encadenamiento',
        df.columns[3]: 'Subyacente_Total', df.columns[4]: 'Mercancias_Total', df.columns[5]: 'Alimentos_Bebidas_Tabaco',
        df.columns[6]: 'Mercancias_No_Alimenticias', df.columns[7]: 'Servicios_Total', df.columns[8]: 'Educacion',
        df.columns[9]: 'Vivienda', df.columns[10]: 'Otros_Servicios', df.columns[11]: 'No_Subyacente_Total',
        df.columns[12]: 'Agropecuarios_Total', df.columns[13]: 'Frutas_Verduras', df.columns[14]: 'Pecuarios',
        df.columns[15]: 'Energeticos_Tarifas_Total', df.columns[16]: 'Energeticos', df.columns[17]: 'Tarifas_Autorizadas'
    }
    df = df.rename(columns=col_mapping)
    
    # Descartar metadatos (primeras filas)
    df_clean = df.iloc[4:].copy()
    
    # Filtrar solo productos genéricos (los que contienen la marca 'X' en alguna columna de clasificación)
    df_clean['is_generic'] = df_clean.apply(lambda row: 'X' in row[3:].values, axis=1)
    df_items = df_clean[df_clean['is_generic']].copy()
    
    # Función de ruteo para aplanar jerarquías
    def extract_classification(row):
        clasificacion = {
            'Tipo': 'Subyacente' if pd.notna(row['Subyacente_Total']) and row['Subyacente_Total'] == 'X' else 'No Subyacente',
            'Componente': None,
            'Subcomponente': None
        }
        
        if clasificacion['Tipo'] == 'Subyacente':
            if row['Mercancias_Total'] == 'X':
                clasificacion['Componente'] = 'Mercancías'
                clasificacion['Subcomponente'] = 'Alimentos, bebidas y tabaco' if row['Alimentos_Bebidas_Tabaco'] == 'X' else 'Mercancías no alimenticias'
            elif row['Servicios_Total'] == 'X':
                clasificacion['Componente'] = 'Servicios'
                if row['Educacion'] == 'X': clasificacion['Subcomponente'] = 'Educación (Colegiaturas)'
                elif row['Vivienda'] == 'X': clasificacion['Subcomponente'] = 'Vivienda'
                elif row['Otros_Servicios'] == 'X': clasificacion['Subcomponente'] = 'Otros servicios'
        else:
            if row['Agropecuarios_Total'] == 'X':
                clasificacion['Componente'] = 'Agropecuarios'
                clasificacion['Subcomponente'] = 'Frutas y verduras' if row['Frutas_Verduras'] == 'X' else 'Pecuarios'
            elif row['Energeticos_Tarifas_Total'] == 'X':
                clasificacion['Componente'] = 'Energéticos y tarifas'
                clasificacion['Subcomponente'] = 'Energéticos' if row['Energeticos'] == 'X' else 'Tarifas autorizadas por el gobierno'
                
        return pd.Series(clasificacion)

    classifications = df_items.apply(extract_classification, axis=1)
    df_final = pd.concat([df_items[['Concepto', 'Ponderador', 'Factor_Encadenamiento']], classifications], axis=1)
    
    df_final['Concepto'] = df_final['Concepto'].str.strip()
    return df_final.reset_index(drop=True)

# Ejecución y guardado relacional
df_relacional = limpiar_ponderadores("data/raw/CCIF.xlsx")
df_relacional.to_csv("data/intermediate/catalogo_inpc.csv", index=False, encoding="utf-8-sig")