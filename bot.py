import os
import json
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

# Configuración de los scopes necesarios para Google Sheets y Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # Acceso a Google Sheets
    "https://www.googleapis.com/auth/drive.readonly"  # Acceso de solo lectura a Drive
]

# Cargar las credenciales desde la variable de entorno en Render
credentials_info = json.loads(os.getenv("CREDENTIALS_JSON"))
credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)

# Autorizar gspread con las credenciales
gc = gspread.authorize(credentials)

# Configuración del bot
TOKEN = os.getenv("TOKEN")  # Cargar el token del bot desde las variables de entorno
GC_SHEET = "BD de horarios"  # Nombre de la hoja de cálculo de Google Sheets

try:
    # Conexión a Google Sheets
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

# Función para obtener todas las líneas disponibles
def obtener_lineas():
    try:
        lineas = bd_hoja.col_values(1)[1:]  # Leer columna 1 (saltando el encabezado)
        return sorted(set(lineas))  # Retornar líneas únicas y ordenadas
    except Exception as e:
        print("Error al obtener líneas:", e)
        return []

# Función para obtener servicios según la línea seleccionada
def obtener_servicios(linea):
    try:
        servicios = [
            row[1] for row in bd_hoja.get_all_values() if row[0] == linea
        ]  # Filtro por la línea
        return sorted(set(servicios))
    except Exception as e:
        print("Error al obtener servicios:", e)
        return []

# Función para filtrar datos según línea, servicio, días y temporada
def filtrar_datos(linea, servicio, dias, temporada):
    try:
        datos = bd_hoja.get_all_records()  # Leer toda la hoja
        filtrados = [
            d for d in datos if (
                (d["Servicio"] == linea or not linea) and
                (str(d["Código Servicio"]) == servicio or not servicio) and
                (d["Días"] == dias or not dias) and
                (d["Temporada"] == temporada or not temporada)
            )
        ]
        return filtrados
    except Exception as e:
        print("Error al filtrar datos:", e)
        return []

# Función para obtener notas generales según el código
def obtener_notas_generales(codigo):
    try:
        notas = notas_generales_hoja.get_all_records()
        return next((n["Descripción"] for n in notas if n["Código General"] == codigo), "")
    except Exception as e:
        print("Error al obtener notas generales:", e)
        return ""

# Función para obtener notas específicas según el código
def obtener_notas(codigo):
    try:
        notas = notas_hoja.get_all_records()
        return next((n["Descripción"] for n in notas if n["Código"] == codigo), "")
    except Exception as e:
        print("Error al obtener notas:", e)
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
    return "ESPERANDO_LINEA"

# Función para manejar línea seleccionada
async def manejar_linea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["linea"] = update.message.text
    servicios = obtener_servicios(context.user_data["linea"])
    if not servicios:
        await update.message.reply_text("No se encontraron servicios para esta línea.")
        return

    teclado = [[servicio] for servicio in servicios]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Selecciona el servicio:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_SERVICIO"

# Función para manejar servicio seleccionado
async def manejar_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["servicio"] = update.message.text
    dias_teclado = [["TD - Todos los días"], ["SDF - Sábados"], ["LAB - Laborables"]]
    reply_markup = ReplyKeyboardMarkup(dias_teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Selecciona los días:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_DIAS"

# Función para manejar días seleccionados
async def manejar_dias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["dias"] = update.message.text
    temporada_teclado = [["IV - Todo el año"], ["V - Verano"], ["I - Invierno"]]
    reply_markup = ReplyKeyboardMarkup(temporada_teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Selecciona la temporada:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_TEMPORADA"

# Función para manejar la temporada seleccionada
async def manejar_temporada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

# Función para manejar mensajes desconocidos
async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("No entiendo tu mensaje. Por favor, usa los comandos disponibles.")

# Función principal para inicializar el bot
async def main():
    application = Application.builder().token(TOKEN).build()

    # Inicializar la aplicación
    await application.initialize()

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
