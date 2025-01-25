import os
import json
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

# Configuración de los scopes necesarios para Google Sheets y Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # Permite acceso de lectura y escritura a Google Sheets
    "https://www.googleapis.com/auth/drive"         # Permite acceso de lectura a archivos en Google Drive
]

# Cargar las credenciales desde la variable de entorno (Render Environment Variables)
credentials_info = json.loads(os.getenv("CREDENTIALS_JSON"))
credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)

# Autorizar gspread con las credenciales
gc = gspread.authorize(credentials)

# Configuración del bot
TOKEN = os.getenv("TOKEN")  # Cargar el token del bot desde las variables de entorno
GC_SHEET = "BD de horarios"  # Nombre de la hoja de cálculo de Google Sheets

try:
    # Conectar a Google Sheets
    sheet = gc.open(GC_SHEET)
    bd_hoja = sheet.worksheet("BD")  # Hoja con la base de datos principal
    notas_generales_hoja = sheet.worksheet("Notas Generales")  # Hoja con las notas generales
    notas_hoja = sheet.worksheet("Notas")  # Hoja con las notas específicas
except Exception as e:
    print("Error al conectar con Google Sheets:", e)
    exit(1)

# Función para el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    teclado = [["Consultar horario"]]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "¡Bienvenido al bot de horarios! Selecciona una opción:",
        reply_markup=reply_markup
    )

# Obtener todas las líneas disponibles
def obtener_lineas():
    try:
        lineas = bd_hoja.col_values(1)[1:]  # Leer columna 1 (saltando el encabezado)
        return sorted(set(lineas))  # Retornar líneas únicas y ordenadas
    except Exception as e:
        print("Error al obtener líneas:", e)
        return []

# Obtener servicios por línea
def obtener_servicios(linea):
    try:
        servicios = [row[1] for row in bd_hoja.get_all_values() if row[0] == linea]
        return sorted(set(servicios))
    except Exception as e:
        print("Error al obtener servicios:", e)
        return []

# Filtrar datos de la hoja principal
def filtrar_datos(linea, servicio, dias, temporada):
    try:
        datos = bd_hoja.get_all_records()  # Obtener todos los registros como lista de diccionarios
        filtrados = [d for d in datos if (
            (d["Servicio"] == linea or not linea) and
            (str(d["Código Servicio"]) == servicio or not servicio) and
            (d["Días"] == dias or not dias) and
            (d["Temporada"] == temporada or not temporada)
        )]
        return filtrados
    except Exception as e:
        print("Error al filtrar datos:", e)
        return []

# Obtener descripción de notas generales
def obtener_notas_generales(codigo):
    try:
        notas = notas_generales_hoja.get_all_records()
        return next((n["Descripción"] for n in notas if n["Código General"] == codigo), "")
    except Exception as e:
        print("Error al obtener notas generales:", e)
        return ""

# Obtener descripción de notas específicas
def obtener_notas(codigo):
    try:
        notas = notas_hoja.get_all_records()
        return next((n["Descripción"] for n in notas if n["Código"] == codigo), "")
    except Exception as e:
        print("Error al obtener notas específicas:", e)
        return ""

# Función para consultar horario
async def consultar_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lineas = obtener_lineas()
    if not lineas:
        await update.message.reply_text("No se encontraron líneas disponibles.")
        return

    teclado = [[linea] for linea in lineas]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "¿Qué línea deseas consultar?",
        reply_markup=reply_markup
    )

# Manejar mensajes desconocidos
async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("No entiendo tu mensaje. Por favor, usa los comandos disponibles.")

# Función principal para inicializar el bot
async def main():
    application = Application.builder().token(TOKEN).build()

    # Agregar manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text(["Consultar horario"]), consultar_horario))
    application.add_handler(MessageHandler(filters.ALL, mensaje_desconocido))

    # Iniciar el bot
    await application.start()
    await application.updater.start_polling()
    await application.idle()

if __name__ == "__main__":
    asyncio.run(main())
