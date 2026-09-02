import os
import telebot

# Carga el token de forma segura desde Render
TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")

if not TOKEN:
    print("ERROR: No se encontro TOKEN en Environment Variables!")
    raise ValueError("TOKEN no configurado")

print(f"Token OK: {TOKEN[:6]}... Iniciando bot...")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "🔥 ¡Hola Lobo! Soy tu Bot V22 Lobo Sin Culpa y estoy LIVE 24/7 en la nube! 🐺\n\nEscribime lo que quieras.")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    bot.reply_to(message, f"Recibido Lobo: {message.text} 🐺")

print("Bot corriendo...")
bot.infinity_polling()
