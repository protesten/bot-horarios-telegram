from telegram.ext import Application, CommandHandler
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

# Función para manejar el comando /start
async def start(update, context):
    await update.message.reply_text("¡El bot está funcionando correctamente!")

# Función para manejar el comando /servicio
async def servicio(update, context):
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text("Por favor, proporciona al menos la línea. Uso: /servicio <línea> [código_servicio] [días] [temporada]")
            return

        linea = args[0]
        codigo_servicio = args[1] if len(args) > 1 else None
        dias = args[2] if len(args) > 2 else None
        temporada = args[3] if len(args) > 3 else None

        # Obtener datos de la hoja BD
        data_bd = sheet_bd.get_all_records()
        data_notas = sheet_notas.get_all_records()

        # Filtrar por línea
        filtered_data = [row for row in data_bd if str(row['Línea']) == linea]

        # Filtrar por código de servicio, días y temporada
        if codigo_servicio:
            filtered_data = [row for row in filtered_data if str(row['Servicio']) == codigo_servicio]
        if dias:
            filtered_data = [row for row in filtered_data if row['Días'] == dias]
        if temporada:
            filtered_data = [row for row in filtered_data if row['Temporada'] == temporada]

        # Verificar si hay resultados
        if not filtered_data:
            await update.message.reply_text("No se encontraron resultados para los parámetros especificados.")
            return

        # Formatear la respuesta
        response = f"Resultados para la línea {linea}:\n"
        notas_map = {nota['Nota']: nota['Descripción'] for nota in data_notas}

        for row in filtered_data:
            response += (
                f"\nServicio: {row['Servicio']}\n"
                f"Hora: {row['Hora']}\n"
                f"Lugar: {row['Lugar']}\n"
                f"Días: {row['Días']}\n"
                f"Temporada: {row['Temporada']}\n"
                f"Notas: {row['Notas']}\n"
            )
            # Añadir descripciones de las notas
            notas_usadas = row['Notas'].split(", ")
            for nota in notas_usadas:
                response += f"  - {nota}: {notas_map.get(nota, 'Descripción no disponible')}\n"

        # Dividir el mensaje si es demasiado largo
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await update.message.reply_text(response[i:i+4096])
        else:
            await update.message.reply_text(response)

    except Exception as e:
        await update.message.reply_text(f"Ocurrió un error: {e}")

# Configurar el bot
def main():
    TOKEN = os.getenv("TOKEN")
    application = Application.builder().token(TOKEN).build()

    # Registrar manejadores de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("servicio", servicio))

    # Iniciar el bot
    application.run_polling()

if __name__ == "__main__":
    main()
