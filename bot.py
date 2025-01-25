import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import gspread

# Configuración del bot
TOKEN = "TU_TOKEN_DE_TELEGRAM"
GC_SHEET = "BD de horarios"  # Nombre de tu hoja de Google Sheets

# Conexión a Google Sheets
gc = gspread.service_account(filename="credenciales.json")
sheet = gc.open(GC_SHEET)
bd_hoja = sheet.worksheet("BD")
notas_generales_hoja = sheet.worksheet("Notas Generales")
notas_hoja = sheet.worksheet("Notas")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    teclado = [["Consultar horario"]]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "¡Bienvenido al bot de horarios! Selecciona una opción:",
        reply_markup=reply_markup
    )

def obtener_lineas():
    lineas = bd_hoja.col_values(1)[1:]
    return sorted(set(lineas))

def obtener_servicios(linea):
    servicios = [row[1] for row in bd_hoja.get_all_values() if row[0] == linea]
    return sorted(set(servicios))

def filtrar_datos(linea, servicio, dias, temporada):
    datos = bd_hoja.get_all_records()
    filtrados = [d for d in datos if (
        (d["Servicio"] == linea or not linea) and
        (str(d["Código Servicio"]) == servicio or not servicio) and
        (d["Días"] == dias or not dias) and
        (d["Temporada"] == temporada or not temporada)
    )]
    return filtrados

def obtener_notas_generales(codigo):
    notas = notas_generales_hoja.get_all_records()
    return next((n["Descripción"] for n in notas if n["Código General"] == codigo), "")

def obtener_notas(codigo):
    notas = notas_hoja.get_all_records()
    return next((n["Descripción"] for n in notas if n["Código"] == codigo), "")

async def consultar_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lineas = obtener_lineas()
    teclado = [[linea] for linea in lineas]
    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "¿Qué línea deseas consultar?",
        reply_markup=reply_markup
    )
    return "ESPERANDO_LINEA"

async def manejar_linea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    context.user_data["servicio"] = update.message.text
    dias_teclado = [["TD - Todos los días"], ["SDF - Sábados"], ["LAB - Laborables"]]
    reply_markup = ReplyKeyboardMarkup(dias_teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Selecciona los días:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_DIAS"

async def manejar_dias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["dias"] = update.message.text
    temporada_teclado = [["IV - Todo el año"], ["V - Verano"], ["I - Invierno"]]
    reply_markup = ReplyKeyboardMarkup(temporada_teclado, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Selecciona la temporada:",
        reply_markup=reply_markup
    )
    return "ESPERANDO_TEMPORADA"

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

async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("No entiendo tu mensaje. Por favor, usa los comandos disponibles.")

async def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text(["Consultar horario"]), consultar_horario))
    application.add_handler(MessageHandler(filters.ALL, mensaje_desconocido))

    await application.start()
    await application.updater.start_polling()
    await application.idle()

if __name__ == "__main__":
    asyncio.run(main())
