import telebot
from datetime import datetime, timedelta

TOKEN = "TU_TOKEN_ACA"  # <-- PONE TU TOKEN DE BOTFATHER ACA
bot = telebot.TeleBot(TOKEN)

ESTADO = {
    "prendido": False,
    "balance": 199.20,
    "ops_hoy": 1,
    "neto_hoy": -0.80,
    "modo": "LOBO",
    "mercado": "NORMAL (0.30%)",
    "pausa_hasta": None,
    "historial": [
        "14:30 - BTC - LOBO - TP +0.3% = +$0.60 Neto",
        "15:10 - BNB - RATA - SL -0.7% = -$0.80 Neto (Pausa 10min)",
        "15:20 - En pausa, cuidando balance"
    ]
}

def get_estado_texto():
    if not ESTADO["prendido"]:
        return "🔴 APAGADO"
    if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]:
        return "⏸️ Pausa 10min"
    return "🟢 PRENDIDO"

@bot.message_handler(commands=['introduccion'])
def introduccion(message):
    texto = """👋 1 BIENVENIDO A LOBO V32.2 FIX - EXPLICACIÓN COMPLETA

*MONEDAS QUE USO:*
*BTC - Bitcoin:* Vale ~$78.000. La opero porque se mueve.
*BNB - Binance Coin:* Vale ~$737. Paga menos comisión.
*USDT - Dólar Digital:* Tu plata NO está en pesos. 1 USDT = 1 Dólar. Tu Balance $199.20 son 199 dólares.

*LO QUE VES:*
*Balance:* Tu plata real en USDT.
*Neto:* Ganancia REAL ya con comisión descontada.
*TP +0.3% / SL -0.7%:* Cierro ganando 0.3% o perdiendo 0.7% y me pauso 10 min.
*ATR 0.30%:* Cuanto se mueve el mercado.
NORMAL=LOBO, LATERAL= RATA, VOLATIL=TIBURON

Siguiente: /estrategias y /start"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['estrategias'])
def estrategias(message):
    texto = """📊 2 ESTRATEGIAS - USO 3 MODOS REALES
🐺 MODO LOBO - NORMAL (0.30%): TP +0.3% | SL -0.7%
🐀 MODO RATA - LATERAL (0.10%): Scalps cortos o no opero
🦈 MODO TIBURON - VOLATIL: Me pauso
Tocá /modo para ver en que modo estoy AHORA."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['modo'])
def modo(message):
    bot.send_message(message.chat.id, f"⚙️ 3 MODO ACTUAL\nMercado: {ESTADO['mercado']}\nModo: 🐺 {ESTADO['modo']}\nEstado: {get_estado_texto()}")

@bot.message_handler(commands=['start'])
def start(message):
    ESTADO["prendido"] = True
    bot.send_message(message.chat.id, f"🚀 4 BOT PRENDIDO\n🟢 PRENDIDO\nBalance: ${ESTADO['balance']} USDT\nMercado: {ESTADO['mercado']} | MODO {ESTADO['modo']}")

@bot.message_handler(commands=['balance'])
def balance(message):
    bot.send_message(message.chat.id, f"💰 5 BALANCE EN VIVO\nBalance: ${ESTADO['balance']} USDT\nNeto hoy: ${ESTADO['neto_hoy']} | Estado: {get_estado_texto()}")

@bot.message_handler(commands=['historial'])
def historial(message):
    hist = "\n".join(ESTADO["historial"])
    bot.send_message(message.chat.id, f"📜 6 HISTORIAL\n{hist}")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    texto = f"""❓ 7 HELP - ¿ALGO TE PASÓ?
1. ¿Pausa 10min? NORMAL después de SL.
2. ¿No opera? NORMAL si está lateral RATA.
3. ¿Negativo? Neto con comisión, se recupera.
ESTADO: {get_estado_texto()} | {ESTADO['mercado']} | ${ESTADO['balance']}
Soporte: @TuUsuarioDeSoporte"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['stop'])
def stop(message):
    ESTADO["prendido"] = False
    bot.send_message(message.chat.id, f"🛑 8 BOT PAUSADO\n🔴 APAGADO\nBalance: ${ESTADO['balance']} USDT")

print("LOBO V32.2 FIX corriendo...")
bot.infinity_polling()
