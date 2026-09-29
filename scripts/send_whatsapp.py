import os
import requests

def send_pdf():
    instance_id = os.getenv("GREEN_API_INSTANCE")
    api_token = os.getenv("GREEN_API_TOKEN")
    chat_id = os.getenv("WHATSAPP_GROUP_ID")
    url = f"https://api.green-api.com/waInstance{instance_id}/sendFileByUpload/{api_token}"

    payload = {'chatId': chat_id, 'caption': 'Reporte de Inflación Actualizado'}
    files = {'file': ('resumen_inflacion.pdf', open('pdf/resumen_inflacion.pdf', 'rb'), 'application/pdf')}

    response = requests.post(url, data=payload, files=files)
    response.raise_for_status()

if __name__ == "__main__":
    send_pdf()