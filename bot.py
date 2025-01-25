from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
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
sheet_notas = client.open("BD de horarios").worksheet("Notas")

def get_service_info(line=None, service_code=None, day=None, season=None):
    """Obtiene los datos filtrados de la hoja de cálculo."""
    data_bd = sheet_bd.get_all_records()
    data_notas = sheet_notas.get_all_records()

    # Filtros dinámicos
    if line:
        data_bd = [row for row in data_bd if str(row['Línea']) == str(line)]
    if service_code:
        data_bd = [row for row in data_bd if str(row['Servicio']) == str(service_code)]
    if day:
        data_bd = [row for row in data_bd if row['Días'] == day]
    if season:
        data_bd = [row for row in data_bd if row['Temporada'] == season]

    # Ordenar por hora
    data_bd = sorted(data_bd, key=lambda x: x['Hora'])

    # Obtener descripciones de notas
    notas_map = {nota['Nota']: nota['Descripción'] for nota in data_notas}

    # Formatear respuesta
    if not data_bd:
        return "No se encontraron resultados con los filtros aplicados."

    response = "Resultados:\n" + "-" * 40 + "\n"
    for row in data_bd:
        response += (
            f"Línea: {row['Línea']}\n"
            f"Servicio: {row['Servicio']}\n"
            f"Hora: {row['Hora']}\n"
            f"Recorrido: {row['Recorrido']}\n"
            f"Lugar: {row['Lugar']}\n"
            f"Días: {row['Días']}\n"
            f"Temporada: {row['Temporada']}\n"
            f"Notas: {row['Notas']}\n"
            f"Descripción de Notas: {notas_map.get(row['Notas'], 'Descripción no disponible')}\n"
            + "-" * 40 + "\n"
        )
    return response

# Comandos para Telegram
def start_command(update: Update, context: CallbackContext):
    update.message.reply_text("¡El bot está funcionando correctamente! Puedes usar /servicio para buscar información.")

def servicio_command(update: Update, context: CallbackContext):
    try:
        args = context.args
        line = args[0] if len(args) > 0 else None
        service_code = args[1] if len(args) > 1 else None
        day = args[2] if len(args) > 2 else None
        season = args[3] if len(args) > 3 else None

        # Obtener la respuesta
        response = get_service_info(line=line, service_code=service_code, day=day, season=season)

        # Dividir el mensaje si es muy largo
        if len(response) > 4096:
            for chunk in [response[i:i+4096] for i in range(0, len(response), 4096)]:
                update.message.reply_text(chunk)
        else:
            update.message.reply_text(response)
    except Exception as e:
        update.message.reply_text(f"Ocurrió un error: {e}")

# Configuración del bot
async def main():
    TOKEN = os.getenv("TOKEN")
    application = Application.builder().token(TOKEN).build()

    # Registrar comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("servicio", servicio_command))

    # Iniciar el bot
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
