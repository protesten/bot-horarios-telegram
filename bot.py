import asyncio  # Para manejar programación asincrónica
import os  # Para acceder a las variables de entorno
import json  # Para procesar datos en formato JSON
from telegram import Update, ReplyKeyboardMarkup  # Herramientas de la API de Telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes  # Manejadores de eventos para Telegram
import gspread  # Para interactuar con Google Sheets
from google.oauth2.service_account import Credentials  # Para autenticar con Google Sheets usando una cuenta de servicio

# **Cargar las credenciales desde la variable de entorno**
# El archivo de credenciales se almacena como una variable de entorno en Render
credentials_info = json.loads(os.getenv("CREDENTIALS_JSON"))  # Carga las credenciales en formato JSON desde la variable de entorno
credentials = Credentials.from_service_account_info(credentials_info)  # Crea un objeto de credenciales para Google Sheets
gc = gspread.authorize(credentials)  # Autoriza gspread con las credenciales

# **Configuración del bot**
TOKEN = os.getenv("TOKEN")  # Obtiene el token del bot de Telegram desde la variable de entorno
GC_SHEET = "BD de horarios"  # Nombre de la hoja de cálculo en Google Sheets

# **Conexión a Google Sheets**
sheet = gc.open(GC_SHEET)  # Abre la hoja de cálculo de Google Sheets por su nombre
bd_hoja = sheet.worksheet("BD")  # Accede a la hoja "BD" dentro del archivo de Google Sheets
notas_generales_hoja = sheet.worksheet("Notas Generales")  # Accede a la hoja "Notas Generales"
notas_hoja = sheet.worksheet("Notas")  # Accede a la hoja "Notas"

# **Comando /start**
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Crear un teclado con opciones para el usuario
    teclado = [["Consultar horario"]]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    # Enviar un mensaje de bienvenida con el teclado incluido
    await update.message.reply_text(
        "¡Bienvenido al bot de horarios! Selecciona una opción:",
        reply_markup=reply_markup
    )

# **Obtener las líneas disponibles**
def obtener_lineas():
    lineas = bd_hoja.col_values(1)[1:]  # Obtiene todos los valores de la primera columna (excepto el encabezado)
    return sorted(set(lineas))  # Devuelve las líneas únicas en orden

# **Obtener los servicios disponibles para una línea específica**
def obtener_servicios(linea):
    servicios = [row[1] for row in bd_hoja.get_all_values() if row[0] == linea]  # Busca los servicios de la línea
    return sorted(set(servicios))  # Devuelve los servicios únicos en orden

# **Filtrar los datos según los criterios del usuario**
def filtrar_datos(linea, servicio, dias, temporada):
    datos = bd_hoja.get_all_records()  # Obtiene todos los registros de la hoja en formato de diccionario
    # Filtra los registros según los parámetros dados
    filtrados = [d for d in datos if (
        (str(d["Servicio"]) == linea or not linea) and  # Si no se especifica línea, toma todas
        (str(d["Código Servicio"]) == servicio or not servicio) and  # Si no se especifica servicio, toma todos
        (d["Días"] == dias or not dias) and  # Si no se especifican días, toma todos
        (d["Temporada"] == temporada or not temporada)  # Si no se especifica temporada, toma todas
    )]
    return filtrados  # Devuelve los registros filtrados

# **Obtener notas generales según su código**
def obtener_notas_generales(codigo):
    notas = notas_generales_hoja.get_all_records()  # Obtiene todas las notas generales
    # Devuelve la descripción correspondiente al código
    return next((n["Descripción"] for n in notas if n["Código General"] == codigo), "")

# **Obtener notas específicas según su código**
def obtener_notas(codigo):
    notas = notas_hoja.get_all_records()  # Obtiene todas las notas específicas
    # Devuelve la descripción correspondiente al código
    return next((n["Descripción"] for n in notas if n["Código"] == codigo), "")

# **Manejar la consulta de horarios**
async def consultar_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lineas = obtener_lineas()  # Obtiene todas las líneas disponibles
    teclado = [[linea] for linea in lineas]  # Crea un teclado con las líneas
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    # Solicita al usuario que seleccione una línea
    await update.message.reply_text(
        "¿Qué línea deseas consultar?",
        reply_markup=reply_markup
    )
    return "ESPERANDO_LINEA"

# **Manejar la selección de una línea**
async def manejar_linea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["linea"] = update.message.text  # Guarda la línea seleccionada en los datos del usuario
    servicios = obtener_servicios(context.user_data["linea"])  # Obtiene los servicios de esa línea
    teclado = [[servicio] for servicio in servicios]  # Crea un teclado con los servicios
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    # Solicita al usuario que seleccione un servicio
    await update.message.reply_text(
        "Selecciona el servicio:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_SERVICIO"

# **Manejar la selección de un servicio**
async def manejar_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["servicio"] = update.message.text  # Guarda el servicio seleccionado
    dias_teclado = [["TD - Todos los días"], ["SDF - Sábados"], ["LAB - Laborables"]]
    reply_markup = ReplyKeyboardMarkup(dias_teclado, resize_keyboard=True, one_time_keyboard=True)
    # Solicita al usuario que seleccione los días
    await update.message.reply_text(
        "Selecciona los días:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_DIAS"

# **Manejar la selección de días**
async def manejar_dias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["dias"] = update.message.text  # Guarda los días seleccionados
    temporada_teclado = [["IV - Todo el año"], ["V - Verano"], ["I - Invierno"]]
    reply_markup = ReplyKeyboardMarkup(temporada_teclado, resize_keyboard=True, one_time_keyboard=True)
    # Solicita al usuario que seleccione la temporada
    await update.message.reply_text(
        "Selecciona la temporada:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_TEMPORADA"

# **Manejar la selección de temporada y mostrar resultados**
async def manejar_temporada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["temporada"] = update.message.text  # Guarda la temporada seleccionada

    # Recupera los criterios del usuario
    linea = context.user_data.get("linea", "")
    servicio = context.user_data.get("servicio", "")
    dias = context.user_data.get("dias", "")
    temporada = context.user_data.get("temporada", "")

    # Filtra los datos según los criterios
    resultados = filtrar_datos(linea, servicio, dias, temporada)
    if not resultados:
        await update.message.reply_text("No se encontraron horarios para tu búsqueda.")
        return

    # Construye la respuesta para el usuario
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

# **Manejar mensajes desconocidos**
async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("No entiendo tu mensaje. Por favor, usa los comandos disponibles.")

# **Función principal**
async def main():
    # Crea una aplicación para el bot con el token
    application = Application.builder().token(TOKEN).build()

    # Agrega manejadores para los comandos y mensajes
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text(["Consultar horario"]), consultar_horario))
    application.add_handler(MessageHandler(filters.ALL, mensaje_desconocido))

    # Inicia el bot
    await application.run_polling()

# **Punto de entrada**
if __name__ == "__main__":
    asyncio.run(main())
