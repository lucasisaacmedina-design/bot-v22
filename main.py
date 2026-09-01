import os
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Servidor falso para Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot V22 Lobo andando!"

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Que es Bitcoin?", callback_data="btc"),
        types.InlineKeyboardButton("Como empiezo con $10?", callback_data="10"),
        types.InlineKeyboardButton("Que es una vela?", callback_data="vela"),
        types.InlineKeyboardButton("Palabra del dia", callback_data="palabra"),
        types.InlineKeyboardButton("Calcular mi ganancia", callback_data="ganancia")
    )
    bot.send_message(message.chat.id, "Hola! Soy Lobo V22. Te enseno trading DESDE CERO, sin humo. Toca un boton:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def botones(call):
    if call.data == "btc":
        bot.send_message(call.message.chat.id, "Bitcoin es oro digital. No lo hace un banco, lo hace la gente.")
    elif call.data == "10":
        bot.send_message(call.message.chat.id, "Con $10 ya podes empezar. Compras $10 de Bitcoin y lo dejas.")
    elif call.data == "vela":
        bot.send_message(call.message.chat.id, "Una vela es una foto del precio. Verde subio, roja bajo.")
    elif call.data == "palabra":
        bot.send_message(call.message.chat.id, "Palabra: HOLD = Guardar y no vender por miedo.")
    elif call.data == "ganancia":
        bot.send_message(call.message.chat.id, "Escribi: /inverti 100 130")

@bot.message_handler(commands=['inverti'])
def calcular(message):
    try:
        partes = message.text.split()
        invertido = float(partes[1])
        ahora = float(partes[2])
        ganancia = ahora - invertido
        porc = (ganancia / invertido) * 100
        bot.send_message(message.chat.id, f"Invertiste ${invertido}, ahora ${ahora}. Ganancia ${ganancia:.2f} ({porc:.1f}%)")
    except:
        bot.send_message(message.chat.id, "Usalo asi: /inverti 100 150")

def run_bot():
    print("POLLING INICIADO")
    bot.infinity_polling()

# Hilo del bot
threading.Thread(target=run_bot).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
