from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# Conectar con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_json = os.getenv('CREDENTIALS_JSON')
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(credentials_json), scope)
client = gspread.authorize(creds)

# Acceder a las hojas de cálculo
sheet_bd = client.open("BD de horarios").worksheet("BD")
sheet_notas_generales = client.open("BD de horarios").worksheet("Notas Generales")
sheet_notas = client.open("BD de horarios").worksheet("Notas")

# Funciones auxiliares para manejar datos de las hojas de cálculo
def get_lines():
    data_bd = sheet_bd.get_all_records()
    lines = sorted(set(row['Recorrido'] for row in data_bd))
    return lines

def get_services_by_line(line):
    data_bd = sheet_bd.get_all_records()
    services = sorted(set(row['Código Servicio'] for row in data_bd if row['Recorrido'] == line))
    return services

def get_schedule(line, service, day, season):
    data_bd = sheet_bd.get_all_records()
    data_notas_generales = sheet_notas_generales.get_all_records()
    data_notas = sheet_notas.get_all_records()

    # Filtrar horarios por línea, servicio, día y temporada
    filtered = [row for row in data_bd if row['Recorrido'] == line and row['Código Servicio'] == service]

    if day:
        filtered = [row for row in filtered if row['Días'] == day or row['Días'] == "TD"]

    if season:
        filtered = [row for row in filtered if row['Temporada'] == season or row['Temporada'] == "IV"]

    # Formatear la respuesta
    response = f"Línea: {line}\nServicio: {service}\nDías: {day or 'TD'}\n-------------\n"

    for row in filtered:
        response += f"* {row['Hora']} - {row['Lugar']}"
        if row['Notas']:
            notas = row['Notas'].split(" - ")
            for nota in notas:
                descripcion = next((n['Descripción'] for n in data_notas if n['Código'] == nota), "Descripción no disponible")
                response += f" - {descripcion}"
        response += "\n"

    # Agregar notas generales
    notas_generales = set(row['Notas Generales'] for row in filtered if row['Notas Generales'])
    response += "----------\n"
    for nota_general in notas_generales:
        descripcion = next((ng['Descripción'] for ng in data_notas_generales if ng['Código General'] == nota_general), "Descripción no disponible")
        response += f"{nota_general} - {descripcion}\n"

    return response or "No se encontraron horarios para los filtros especificados."

# Manejo de comandos del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(line, callback_data=f"line|{line}")] for line in get_lines()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una línea:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split('|')

    if data[0] == "line":
        line = data[1]
        services = get_services_by_line(line)
        keyboard = [[InlineKeyboardButton(service, callback_data=f"service|{line}|{service}")] for service in services]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Línea seleccionada: {line}\nSelecciona un servicio:", reply_markup=reply_markup)

    elif data[0] == "service":
        line, service = data[1], data[2]
        keyboard = [
            [InlineKeyboardButton("TD", callback_data=f"day|{line}|{service}|TD"),
             InlineKeyboardButton("SDF", callback_data=f"day|{line}|{service}|SDF"),
             InlineKeyboardButton("LAB", callback_data=f"day|{line}|{service}|LAB")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Línea: {line}\nServicio: {service}\nSelecciona un tipo de día:", reply_markup=reply_markup)

    elif data[0] == "day":
        line, service, day = data[1], data[2], data[3]
        keyboard = [
            [InlineKeyboardButton("IV", callback_data=f"season|{line}|{service}|{day}|IV"),
             InlineKeyboardButton("V", callback_data=f"season|{line}|{service}|{day}|V"),
             InlineKeyboardButton("I", callback_data=f"season|{line}|{service}|{day}|I")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Línea: {line}\nServicio: {service}\nDías: {day}\nSelecciona una temporada:", reply_markup=reply_markup)

    elif data[0] == "season":
        line, service, day, season = data[1], data[2], data[3], data[4]
        schedule = get_schedule(line, service, day, season)
        await query.edit_message_text(schedule)

# Configuración principal del bot
async def main():
    application = Application.builder().token(os.getenv("TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
