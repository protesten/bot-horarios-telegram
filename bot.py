import os
import json
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

# ============================
# Configuración de Credenciales
# ============================
# Cargar las credenciales desde la variable de entorno 'CREDENTIALS_JSON'
# Estas credenciales permiten la conexión a Google Sheets mediante gspread.
credentials_info = json.loads(os.getenv("CREDENTIALS_JSON"))

# Definir los alcances necesarios para Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Crear el objeto de credenciales usando las credenciales cargadas y los scopes
credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)

# Autorizar gspread con las credenciales configuradas
gc = gspread.authorize(credentials)

# ============================
# Configuración de Google Sheets
# ============================
# Nombre de la hoja de cálculo
GC_SHEET = "BD de horarios"

# Conectar con la hoja de cálculo en Google Sheets
try:
    sheet = gc.open(GC_SHEET)
    bd_hoja = sheet.worksheet("BD")  # Hoja con los datos principales
    notas_generales_hoja = sheet.worksheet("Notas Generales")  # Hoja de notas generales
    notas_hoja = sheet.worksheet("Notas")  # Hoja de notas específicas
except Exception as e:
    print(f"Error al conectar con Google Sheets: {e}")
    raise

# ============================
# Configuración del Bot de Telegram
# ============================
# Cargar el token del bot desde una variable de entorno
TOKEN = os.getenv("TOKEN")

# ============================
# Funciones Auxiliares
# ============================

def obtener_lineas():
    """Obtiene una lista única de todas las líneas disponibles en la hoja 'BD'."""
    lineas = bd_hoja.col_values(1)[1:]  # Obtener valores de la primera columna, omitiendo el encabezado
    return sorted(set(lineas))

def obtener_servicios(linea):
    """Obtiene una lista única de los servicios disponibles para una línea específica."""
    servicios = [row[1] for row in bd_hoja.get_all_values() if row[0] == linea]
    return sorted(set(servicios))

def filtrar_datos(linea, servicio, dias, temporada):
    """Filtra los datos en la hoja 'BD' según los parámetros proporcionados."""
    datos = bd_hoja.get_all_records()
    filtrados = [d for d in datos if (
        (d["Servicio"] == linea or not linea) and
        (str(d["Código Servicio"]) == servicio or not servicio) and
        (d["Días"] == dias or not dias) and
        (d["Temporada"] == temporada or not temporada)
    )]
    return filtrados

def obtener_notas_generales(codigo):
    """Obtiene la descripción de una nota general según su código."""
    notas = notas_generales_hoja.get_all_records()
    return next((n["Descripción"] for n in notas if n["Código General"] == codigo), "")

def obtener_notas(codigo):
    """Obtiene la descripción de una nota específica según su código."""
    notas = notas_hoja.get_all_records()
    return next((n["Descripción"] for n in notas if n["Código"] == codigo), "")

# ============================
# Handlers de Telegram
# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Se ejecuta cuando el usuario inicia el bot con /start."""
    teclado = [["Consultar horario"]]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "¡Bienvenido al bot de horarios! Selecciona una opción:",
        reply_markup=reply_markup
    )

def obtener_menu_lineas():
    """Genera un teclado con las líneas disponibles."""
    lineas = obtener_lineas()
    teclado = [[linea] for linea in lineas]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)

async def consultar_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pregunta al usuario qué línea desea consultar."""
    reply_markup = obtener_menu_lineas()
    await update.message.reply_text(
        "¿Qué línea deseas consultar?",
        reply_markup=reply_markup
    )
    return "ESPERANDO_LINEA"

async def manejar_linea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja la selección de línea por parte del usuario."""
    context.user_data["linea"] = update.message.text
    servicios = obtener_servicios(context.user_data["linea"])
    teclado = [[servicio] for servicio in servicios]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Selecciona el servicio:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_SERVICIO"

async def manejar_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja la selección de servicio por parte del usuario."""
    context.user_data["servicio"] = update.message.text
    dias_teclado = [["TD - Todos los días"], ["SDF - Sábados"], ["LAB - Laborables"]]
    reply_markup = ReplyKeyboardMarkup(dias_teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Selecciona los días:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_DIAS"

async def manejar_dias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja la selección de días por parte del usuario."""
    context.user_data["dias"] = update.message.text
    temporada_teclado = [["IV - Todo el año"], ["V - Verano"], ["I - Invierno"]]
    reply_markup = ReplyKeyboardMarkup(temporada_teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Selecciona la temporada:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_TEMPORADA"

async def manejar_temporada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja la selección de temporada por parte del usuario y muestra los resultados."""
    context.user_data["temporada"] = update.message.text

    linea = context.user_data.get("linea", "")
    servicio = context.user_data.get("servicio", "")
    dias = context.user_data.get("dias", "")
    temporada = context.user_data.get("temporada", "")

    resultados = filtrar_datos(linea, servicio, dias, temporada)
    if not resultados:
        await update.message.reply_text("No se encontraron horarios para tu búsqueda.")
        return

    respuesta = f"Línea: {linea}\nServicio: {servicio}\nDías: {dias}\nTemporada: {temporada}\n-------------\n"
    for r in resultados:
        respuesta += f"* {r['Hora']} - {r['Lugar']}\n"

    nota_general = obtener_notas_generales(resultados[0].get("Notas Generales", ""))
    if nota_general:
        respuesta += f"-------\nNota General: {nota_general}\n"

    for r in resultados:
        notas = r.get("Notas", "").split("-")
        for nota in notas:
            descripcion_nota = obtener_notas(nota.strip())
            if descripcion_nota:
                respuesta += f"Nota: {descripcion_nota}\n"

    await update.message.reply_text(respuesta)
    return "FIN"

async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a cualquier mensaje desconocido."""
    await update.message.reply_text("No entiendo tu mensaje. Por favor, usa los comandos disponibles.")

# ============================
# Main: Configuración del Bot
# ============================
async def main():
    """Función principal que configura el bot y sus handlers."""
    application = Application.builder().token(TOKEN).build()

    # Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text(["Consultar horario"]), consultar_horario))
    application.add_handler(MessageHandler(filters.ALL, mensaje_desconocido))

    # Iniciar el bot
    await application.start()
    await application.updater.start_polling()
    await application.idle()

if __name__ == "__main__":
    asyncio.run(main())
