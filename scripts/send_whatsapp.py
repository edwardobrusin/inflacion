import os
import requests
import pandas as pd

def generar_mensaje():
    df_niv = pd.read_csv('data/intermediate/niveles.csv')
    df_gen = pd.read_csv('data/intermediate/genericos.csv')

    # Extraer el registro de niveles más reciente
    ultimo_niv = df_niv.iloc[-1]
    
    # Parseo robusto de fecha
    fecha_str = str(ultimo_niv['Fecha']).strip().split(" ")[0].replace("-", "/")
    try:
        fecha = pd.to_datetime(fecha_str, format="%d/%m/%Y")
    except ValueError:
        fecha = pd.to_datetime(fecha_str, format="%Y/%m/%d")

    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes = meses[fecha.month - 1]
    anio = fecha.year

    # Calcular YTD
    dec_prev_year = f"{anio-1}-12-01"
    # Puede ser que el formato en el CSV sea YYYY-MM-DD
    prev_niv_df = df_niv[df_niv['Fecha'] == dec_prev_year]
    
    if not prev_niv_df.empty:
        prev_niv = prev_niv_df.iloc[0]
        ytd_general = (ultimo_niv['INPC_General'] / prev_niv['INPC_General'] - 1) * 100
        ytd_sub = (ultimo_niv['Subyacente'] / prev_niv['Subyacente'] - 1) * 100
        ytd_nosub = (ultimo_niv['No_Subyacente'] / prev_niv['No_Subyacente'] - 1) * 100
    else:
        # Fallback if december prev year not found
        ytd_general = ytd_sub = ytd_nosub = 0.0

    # Extraer los genéricos del periodo más reciente
    fecha_max = df_gen['Fecha'].max()
    df_gen_ultimo = df_gen[df_gen['Fecha'] == fecha_max]
    
    # Ordenar por incidencia anual para obtener el Top 3 al alza y a la baja
    top_alza = df_gen_ultimo.sort_values('Inc_Anual', ascending=False).head(3)
    alza_str_list = [f"{row['Concepto']} ({row['Inc_Anual']:.3f})" for _, row in top_alza.iterrows()]
    
    top_baja = df_gen_ultimo.sort_values('Inc_Anual', ascending=True).head(3)
    baja_str_list = [f"{row['Concepto']} ({row['Inc_Anual']:.3f})" for _, row in top_baja.iterrows()]

    msg = f"Reporte de Inflación ({mes} {anio})\n"
    msg += f"- General: {ultimo_niv['INPC_General_Var_Anual']:.2f}% YoY | {ultimo_niv['INPC_General_Var_Mensual']:.2f}% MoM | {ytd_general:.2f}% YTD\n"
    msg += f"- Subyacente: {ultimo_niv['Subyacente_Var_Anual']:.2f}% YoY | {ultimo_niv['Subyacente_Var_Mensual']:.2f}% MoM | {ytd_sub:.2f}% YTD\n"
    msg += f"- No Subyacente: {ultimo_niv['No_Subyacente_Var_Anual']:.2f}% YoY | {ultimo_niv['No_Subyacente_Var_Mensual']:.2f}% MoM | {ytd_nosub:.2f}% YTD\n"
    msg += f"- Mayor Incidencia Anual al Alza: {'; '.join(alza_str_list)}.\n"
    msg += f"- Mayor Incidencia Anual a la Baja: {'; '.join(baja_str_list)}."
    
    return msg

def send_pdf():
    instance_id = os.getenv("GREEN_API_INSTANCE")
    api_token = os.getenv("GREEN_API_TOKEN")
    chat_id = os.getenv("WHATSAPP_GROUP_ID")
    url = f"https://api.green-api.com/waInstance{instance_id}/sendFileByUpload/{api_token}"

    caption_personalizado = generar_mensaje()
    
    # Determinar nombre del archivo PDF a partir del CSV
    df_niv = pd.read_csv('data/intermediate/niveles.csv')
    ultimo_niv = df_niv.iloc[-1]
    fecha_str = str(ultimo_niv['Fecha']).strip().split(" ")[0].replace("-", "/")
    try:
        fecha = pd.to_datetime(fecha_str, format="%d/%m/%Y")
    except ValueError:
        fecha = pd.to_datetime(fecha_str, format="%Y/%m/%d")

    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes = meses[fecha.month - 1]
    anio = fecha.year
    nombre_archivo = f"Inflación_{mes}_{anio}.pdf"

    payload = {
        'chatId': chat_id, 
        'caption': caption_personalizado,
        'fileName': nombre_archivo
    }
    # Usamos un nombre ASCII en 'files' para evitar que requests corrompa los acentos en el multipart/form-data
    files = {'file': ('reporte.pdf', open(f'pdf/{nombre_archivo}', 'rb'), 'application/pdf')}

    response = requests.post(url, data=payload, files=files)
    response.raise_for_status()

if __name__ == "__main__":
    send_pdf()