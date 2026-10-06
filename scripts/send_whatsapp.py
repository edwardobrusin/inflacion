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

    # Extraer los genéricos del periodo más reciente
    fecha_max = df_gen['Fecha'].max()
    df_gen_ultimo = df_gen[df_gen['Fecha'] == fecha_max]
    
    # Ordenar por incidencia anual para obtener el Top 3 al alza y a la baja
    alza = df_gen_ultimo.sort_values('Inc_Anual', ascending=False).head(3)['Concepto'].tolist()
    baja = df_gen_ultimo.sort_values('Inc_Anual', ascending=True).head(3)['Concepto'].tolist()

    # Construir el cuerpo del mensaje en formato WhatsApp (asteriscos para negritas)
    msg = f"Reporte de Inflación ({mes} {anio})\n\n"
    msg += f"- Inflación General: *{ultimo_niv['INPC_General_Var_Anual']:.2f}%* Anual (*{ultimo_niv['INPC_General_Var_Mensual']:.2f}%* Mensual)\n"
    msg += f"- Inflación Subyacente: *{ultimo_niv['Subyacente_Var_Anual']:.2f}%* Anual (*{ultimo_niv['Subyacente_Var_Mensual']:.2f}%* Mensual)\n"
    msg += f"- Inflación No Subyacente: *{ultimo_niv['No_Subyacente_Var_Anual']:.2f}%* Anual (*{ultimo_niv['No_Subyacente_Var_Mensual']:.2f}%* Mensual)\n"
    msg += f"- Genéricos de Mayor Incidencia Anual al *Alza*: {'; '.join(alza)}.\n"
    msg += f"- Genéricos de Mayor Incidencia Anual a la *Baja*: {'; '.join(baja)}."
    
    return msg

def send_pdf():
    instance_id = os.getenv("GREEN_API_INSTANCE")
    api_token = os.getenv("GREEN_API_TOKEN")
    chat_id = os.getenv("WHATSAPP_GROUP_ID")
    url = f"https://api.green-api.com/waInstance{instance_id}/sendFileByUpload/{api_token}"

    caption_personalizado = generar_mensaje()
    payload = {'chatId': chat_id, 'caption': caption_personalizado}
    files = {'file': ('resumen_inflacion.pdf', open('pdf/resumen_inflacion.pdf', 'rb'), 'application/pdf')}

    response = requests.post(url, data=payload, files=files)
    response.raise_for_status()

if __name__ == "__main__":
    send_pdf()