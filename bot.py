from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# Comando para verificar el funcionamiento del bot
async def start_command(update: Update, context: CallbackContext):
    await update.message.reply_text("¡El bot está funcionando correctamente!")

# Conectar con Google Sheets
def connect_to_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials_json = os.getenv('CREDENTIALS_JSON')
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(credentials_json), scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error conectando con Google Sheets: {e}")
        return None

client = connect_to_sheets()

if client:
    try:
        sheet_bd = client.open("BD de horarios").worksheet("BD")
        sheet_notas = client.open("BD de horarios").worksheet("Notas")
    except Exception as e:
        print(f"Error accediendo a las hojas de cálculo: {e}")
else:
    sheet_bd, sheet_notas = None, None

async def servicio_command(update: Update, context: CallbackContext):
    """Busca información de un servicio por código."""
    if not sheet_bd or not sheet_notas:
        await update.message.reply_text("Error: No se pudo acceder a las hojas de cálculo.")
        return

    try:
        service_code = context.args[0].upper()
        season = None
        day = None

        # Leer datos de las hojas
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

        # Dividir la respuesta si es muy larga
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
async def main():
    # Leer el token desde la variable de entorno
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
