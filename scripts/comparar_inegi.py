import requests
import pandas as pd
import os
import calendar

def consultar_inegi_oficial():
    # Códigos proporcionados por el usuario
    indicadores = {
        "INPC_General": "910392",
        "Subyacente": "910393",
        "Mercancias": "910394",
        "Servicios": "910395",
        "No_Subyacente": "910396",
        "Agropecuarios": "910397",
        "Energeticos_Tarifas": "910398"
    }

    ids_totales = list(indicadores.values())
    token = "129ac2e3-e8a6-72c7-58c1-acced5a601bd"
    base_url = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{}/es/00/false/BIE-BISE/2.0/{}?type=json"
    
    ids_string = ",".join(ids_totales)
    url = base_url.format(ids_string, token)
    
    lista_total_resultados = []
    print(f"Consultando {len(ids_totales)} indicadores a INEGI...")

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        for serie in data.get('Series', []):
            indicador_id = serie.get('INDICADOR')
            observaciones = serie.get('OBSERVATIONS', [])
            
            for obs in observaciones:
                lista_total_resultados.append({
                    'ID_Indicador': indicador_id,
                    'Fecha_Texto': obs.get('TIME_PERIOD'),
                    'Valor': obs.get('OBS_VALUE')
                })
    except Exception as e:
        print(f"Error en la consulta: {e}")
        return None

    if not lista_total_resultados:
        print("No se obtuvieron datos.")
        return None

    df = pd.DataFrame(lista_total_resultados)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    
    # Mapear IDs a nombres
    id_a_nombre = {v: k for k, v in indicadores.items()}
    df['Concepto'] = df['ID_Indicador'].map(id_a_nombre)
    
    def parsear_fechas_inegi(fecha_texto):
        texto = str(fecha_texto).strip()
        partes = texto.split('/')
        try:
            if len(partes) == 2:
                # Mensual: YYYY/MM
                return pd.to_datetime(texto + '/01')
            elif len(partes) == 3:
                # Quincenal: detect YYYY/MM/QQ or QQ/MM/YYYY
                if len(partes[2]) == 4:
                    q, m, y = int(partes[0]), int(partes[1]), int(partes[2])
                else:
                    y, m, q = int(partes[0]), int(partes[1]), int(partes[2])
                if q == 1: dia = 15
                elif q == 2: dia = calendar.monthrange(y, m)[1]
                else: dia = q
                return pd.to_datetime(f"{y}-{m:02d}-{dia:02d}")
            else:
                return pd.to_datetime(texto, format='%Y')
        except Exception:
            return pd.NaT

    df['Fecha'] = df['Fecha_Texto'].apply(parsear_fechas_inegi)
    
    df_pivot = df.pivot_table(
        index='Fecha', 
        columns='Concepto', 
        values='Valor'
    ).sort_index()

    return df_pivot

if __name__ == "__main__":
    df_oficial = consultar_inegi_oficial()
    if df_oficial is not None:
        # Solo necesitamos datos desde 2023 por ejemplo, o todo el historico
        df_oficial = df_oficial[df_oficial.index >= '2023-01-01']
        df_oficial.to_csv("data/intermediate/inegi_oficial_benchmark.csv")
        print("Datos oficiales guardados en data/intermediate/inegi_oficial_benchmark.csv")
        
        # Comparar con niveles.csv
        niveles_path = "data/intermediate/niveles.csv"
        if os.path.exists(niveles_path):
            df_calculado = pd.read_csv(niveles_path)
            df_calculado['Fecha'] = pd.to_datetime(df_calculado['Fecha'])
            df_calculado = df_calculado.set_index('Fecha')
            
            # Hacer el join
            comunes = df_oficial.index.intersection(df_calculado.index)
            
            for col in df_oficial.columns:
                if col in df_calculado.columns:
                    diff = df_calculado.loc[comunes, col] - df_oficial.loc[comunes, col]
                    print(f"\n--- Discrepancias para {col} ---")
                    res = pd.DataFrame({
                        'Oficial': df_oficial.loc[comunes, col],
                        'Calculado': df_calculado.loc[comunes, col],
                        'Diferencia': diff
                    })
                    print(res.tail(24))  # Mostrar los últimos 24 meses
