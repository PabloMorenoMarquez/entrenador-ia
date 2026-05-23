import gspread
from google.oauth2.service_account import Credentials
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

def conectar():
    credenciales_json = os.getenv("GOOGLE_CREDENTIALS")
    credenciales_dict = json.loads(credenciales_json)
    creds = Credentials.from_service_account_info(credenciales_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def leer_hoja(cliente, sheet_id, nombre_hoja):
    sheet = cliente.open_by_key(sheet_id).worksheet(nombre_hoja)
    return sheet.get_all_records()

if __name__ == "__main__":
    SHEET_ID = "1j2iRn67xxU6BIs3hu8qnw7qO98mgGWuRsGiBp4tyf5U"
    cliente = conectar()
    datos = leer_hoja(cliente, SHEET_ID, "perfil_usuario")
    print(f"Filas leídas: {len(datos)}")
    if datos:
        print("Primera fila:", datos[0])