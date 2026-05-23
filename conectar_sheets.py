import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

def conectar():
    creds = None

    # Si ya existe token guardado, usarlo
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # Si no hay token válido, pedir autorización
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credenciales.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return gspread.authorize(creds)

def leer_hoja(cliente, sheet_id, nombre_hoja):
    sheet = cliente.open_by_key(sheet_id).worksheet(nombre_hoja)
    return sheet.get_all_records()

if __name__ == "__main__":
    SHEET_ID = "1j2iRn67xxU6BIs3hu8qnw7qO98mgGWuRsGiBp4tyf5U"
    
    cliente = conectar()
    
    # Test — leer ejercicios_detalle
    datos = leer_hoja(cliente, SHEET_ID, "perfil_usuario")
    print(f"Filas leídas: {len(datos)}")
    if datos:
        print("Primera fila:", datos[0])