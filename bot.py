from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# Comando para verificar el funcionamiento del bot
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡El bot está funcionando correctamente!")

# Configuración de Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_json = os.getenv('CREDENTIALS_JSON')
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(credentials_json), scope)
client = gspread.authorize(creds)

# Acceder a las hojas de cálculo
sheet_bd = client.open("BD de horarios").worksheet("BD")
sheet_notas = client.open("BD de horarios").worksheet("Notas")

# Función para obtener información del servicio
def get_service_info(service_code, season=None, day=None):
    """Obtiene los datos de un servicio específico filtrado por temporada y días."""
    data_bd = sheet_bd.get_all_records()
    data_notas = sheet_notas.get_all_records()

    # Filtrar por código de servicio
    filtered_data = [row for row in data_bd if row['Servicio'] == service_code]

    # Filtrar por temporada si es necesario
    if season:
        filtered_data = [row for row in filtered_data if row['Temporada'] == season]

    # Filtrar por días si es necesario
    if day:
        filtered_data = [row for row in filtered_data if row['Días'] == day]

    # Ordenar por hora
    filtered_data = sorted(filtered_data, key=lambda x: x['Hora'])

    # Obtener descripciones de notas
    notas_map = {nota['Código']: nota['Descripción'] for nota in data_notas}

    # Formatear respuesta
    response = f"Servicio: {service_code}\n--------------------------------\n"
    for row in filtered_data:
        response += f"Hora: {row['Hora']}\nLínea: {row['Línea']}\nLugar: {row['Lugar']}\nNotas: {row['Notas']}\n--------------------------------\n"

    # Añadir descripciones de notas
    response += "Descripción de Notas:\n"
    notas_usadas = set(note for row in filtered_data for note in row['Notas'].split(", "))
    for nota in notas_usadas:
        response += f"{nota}: {notas_map.get(nota, 'Descripción no disponible')}\n"

    return response

# Comando para buscar servicios
async def servicio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        service_code = context.args[0].upper()
        season = None
        day = None

        # Obtener la respuesta del servicio
        response = get_service_info(service_code, season, day)

        # Dividir el mensaje si es muy largo
        if len(response) > 4096:
            for chunk in [response[i:i+4096] for i in range(0, len(response), 4096)]:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response)
    except IndexError:
        await update.message.reply_text("Por favor, proporciona un código de servicio. Uso: /servicio <código>")
    except Exception as e:
        await update.message.reply_text(f"Ocurrió un error: {e}")

# Configuración del bot
def main():
    # Leer el token desde la variable de entorno
    TOKEN = os.getenv("TOKEN")
    application = Application.builder().token(TOKEN).build()

    # Agregar manejadores
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("servicio", servicio_command))

    # Ejecutar el bot
    application.run_polling()

if __name__ == "__main__":
    main()
