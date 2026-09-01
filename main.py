import os
import telebot
from telebot import types

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🟢 ¿Qué es Bitcoin?", callback_data="btc"),
        types.InlineKeyboardButton("💵 ¿Cómo empiezo con $10?", callback_data="10"),
        types.InlineKeyboardButton("📊 ¿Qué es una vela?", callback_data="vela"),
        types.InlineKeyboardButton("🧠 Palabra del día", callback_data="palabra"),
        types.InlineKeyboardButton("💰 Calcular mi ganancia", callback_data="ganancia")
    )
    bot.send_message(message.chat.id,
        "🐺 ¡Hola! Soy Lobo V22\n\nTe enseño trading DESDE CERO, sin humo.\n\n¿Vos sabés algo o arrancamos de 0?\n\nTocá un botón:",
        reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def botones(call):
    if call.data == "btc":
        bot.send_message(call.message.chat.id, "Bitcoin es oro digital. No lo hace un banco, lo hace la gente. Sube y baja, y vos ganás comprando barato y vendiendo caro. Fin.")
    elif call.data == "10":
        bot.send_message(call.message.chat.id, "Con $10 ya podés empezar. Comprás $10 de Bitcoin en un exchange y lo dejás. Si sube 10%, tenés $11. Así se empieza, sin miedo.")
    elif call.data == "vela":
        bot.send_message(call.message.chat.id, "Una vela es como una foto del precio. Si es verde, subió. Si es roja, bajó. No hace falta más.")
    elif call.data == "palabra":
        bot.send_message(call.message.chat.id, "Palabra de hoy: HOLD = Guardar y no vender por miedo. Los lobos hacen HOLD.")
    elif call.data == "ganancia":
        bot.send_message(call.message.chat.id, "Escribí así:\n\n/inverti 100 130\n\nEl primer número es lo que pusiste, el segundo lo que tenés ahora.\n\nEj: si pusiste 100 y ahora tenés 130, ganaste 30.")

@bot.message_handler(commands=['inverti'])
def calcular(message):
    try:
        partes = message.text.split()
        invertido = float(partes[1])
        ahora = float(partes[2])
        ganancia = ahora - invertido
        porc = (ganancia / invertido) * 100

        if ganancia >= 0:
            bot.send_message(message.chat.id, f"🐺 ¡VAMOS LOBO!\n\nInvertiste: ${invertido}\nAhora tenés: ${ahora}\n\n✅ Ganaste: ${ganancia:.2f} ({porc:.1f}%)\n\n¡Seguí así!")
        else:
            bot.send_message(message.chat.id, f"🐺 Tranquilo Lobo\n\nInvertiste: ${invertido}\nAhora tenés: ${ahora}\n\n📉 Vas: ${ganancia:.2f} ({porc:.1f}%)\n\nEs parte del juego, hacemos HOLD.")
    except:
        bot.send_message(message.chat.id, "Usalo así: /inverti 100 150")

print("POLLING INICIADO")
bot.infinity_polling()
