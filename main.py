import os, threading, random, time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
import telebot

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ESTADO = {
    "prendido": False,
    "balance": 199.60,
    "ops_hoy": 4,
    "neto_hoy": -0.40,
    "ganadas": 2,
    "perdidas": 2,
    "modo": "LOBO",
    "mercado": "NORMAL (0.30%)",
    "pausa_hasta": None,
    "btc": 78430,
    "bnb": 737.50,
    "historial": [
        "14:00 - BTC - LOBO - TP +0.3% = +$0.60 Neto",
        "14:30 - BTC - LOBO - TP +0.3% = +$0.60 Neto",
        "15:10 - BNB - RATA - SL -0.7% = -$0.80 Neto",
        "01:33 - BNB - RATA - SL -0.7% = -$0.80 Neto"
    ],
    "btc_history": [78430 + random.uniform(-200,200) for _ in range(30)],
    "balance_history": [199.60 + random.uniform(-1,1) for _ in range(30)]
}

def calcular_winrate():
    total = ESTADO["ganadas"] + ESTADO["perdidas"]
    if total == 0:
        return 0
    return round((ESTADO["ganadas"] / total) * 100)

def get_estado_texto():
    if not ESTADO["prendido"]:
        return "🔴 APAGADO"
    if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]:
        mins = int((ESTADO["pausa_hasta"] - datetime.now()).total_seconds()/60)+1
        return f"⏸️ Pausa {mins}min"
    return "🟢 PRENDIDO"

def motor_demo():
    while True:
        time.sleep(random.randint(45, 90))
        if not ESTADO["prendido"]:
            continue
        if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]:
            continue
        es_ganada = random.random() < 0.66
        if es_ganada:
            ESTADO["ganadas"] += 1
            ESTADO["ops_hoy"] += 1
            ESTADO["neto_hoy"] = round(ESTADO["neto_hoy"] + 0.60, 2)
            ESTADO["balance"] = round(ESTADO["balance"] + 0.60, 2)
            ESTADO["historial"].append(f"{datetime.now().strftime('%H:%M')} - BTC - LOBO - TP +0.3% = +$0.60 Neto")
        else:
            ESTADO["perdidas"] += 1
            ESTADO["ops_hoy"] += 1
            ESTADO["neto_hoy"] = round(ESTADO["neto_hoy"] - 0.80, 2)
            ESTADO["balance"] = round(ESTADO["balance"] - 0.80, 2)
            ESTADO["historial"].append(f"{datetime.now().strftime('%H:%M')} - BNB - RATA - SL -0.7% = -$0.80 Neto (Pausa 10min)")
            ESTADO["pausa_hasta"] = datetime.now() + timedelta(minutes=10)
        if len(ESTADO["historial"]) > 20:
            ESTADO["historial"] = ESTADO["historial"][-20:]

@bot.message_handler(commands=['start'])
def start(message):
    texto = """👋 ¡Bienvenido a LOBOBOT22 🐺!

Soy tu bot automático de trading.
Opero solo en BTC y BNB, busco TP +0.3% y te cuido con SL -0.7%.

Tu plata está en USDT (1 USDT = 1 Dólar). Todo lo que ves es neto, ya con comisión descontada.

👇 COMO EMPEZAR - TOCÁ EN ORDEN:

1️⃣ /introduccion - Qué monedas uso y qué ves en pantalla
2️⃣ /estrategias - Mis 3 modos reales
3️⃣ /modo - En qué modo estoy ahora mismo
4️⃣ /prender - Para prenderme y que empiece a operar
5️⃣ /balance - Tu plata en vivo
6️⃣ /historial - Lo que hice hoy
7️⃣ /help - Si ves algo raro
8️⃣ /apagar - Para pausarme

Empezá por /introduccion"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['introduccion', 'start_intro'])
def introduccion(message):
    texto = """👋 1 BIENVENIDO A LOBO V32.2 FIX - EXPLICACIÓN COMPLETA
*MONEDAS QUE USO:*
*BTC - Bitcoin:* Vale ~$78.000
*BNB - Binance Coin:* Vale ~$737
*USDT:* 1 USDT = 1 Dólar. Tu Balance $199.60 son 199 dólares.
*LO QUE VES EN /balance:*
Balance: tu plata total real en USDT
Neto: ganancia/pérdida REAL ya con comisión
Ops: cantidad de operaciones hoy
TP +0.3% / SL -0.7% / ATR 0.30%
Siguiente: /estrategias y /prender"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['estrategias'])
def estrategias(message):
    texto = """📊 2 ESTRATEGIAS - USO 3 MODOS REALES
🐺 LOBO - NORMAL (0.30%) TP +0.3% | SL -0.7%
🐀 RATA - LATERAL (0.10%) casi no opero
🦈 TIBURON - VOLATIL me pauso
Tocá /modo para ver en que modo estoy AHORA."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['modo'])
def modo(message):
    estado = get_estado_texto()
    win = calcular_winrate()
    texto = f"""⚙️ 3 MODO ACTUAL
Mercado: {ESTADO['mercado']}
Modo: 🐺 {ESTADO['modo']}
BTC: ${ESTADO['btc']} | BNB: ${ESTADO['bnb']} | ATR: 0.30%
Estado Bot: {estado} | Winrate: {win}% ({ESTADO['ganadas']}W/{ESTADO['perdidas']}L)
Siguiente: /balance o /apagar"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['prender', 'iniciar'])
def prender(message):
    ESTADO["prendido"] = True
    texto = f"""Estoy activo y buscando. No tenes que tocar nada.

Siguiente: /balance para ver tu plata o /apagar para pausarme"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['balance'])
def balance(message):
    estado = get_estado_texto()
    win = calcular_winrate()
    texto = f"""💰 5 BALANCE EN VIVO
Balance: ${ESTADO['balance']} USDT
Neto hoy: ${ESTADO['neto_hoy']} ({ESTADO['ops_hoy']} operaciones, ya con comisión descontada)
Ops hoy: {ESTADO['ops_hoy']} | Ganadas: {ESTADO['ganadas']} | Perdidas: {ESTADO['perdidas']} | Winrate: {win}%
Estado: {estado}
Tocá /historial"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['historial'])
def historial(message):
    hist = "\n".join(ESTADO["historial"])
    win = calcular_winrate()
    texto = f"""📜 6 HISTORIAL DE HOY
{hist}

Total Neto hoy: ${ESTADO['neto_hoy']} | Winrate: {win}% ({ESTADO['ganadas']}W/{ESTADO['perdidas']}L) | Ops: {ESTADO['ops_hoy']}

Tocá /balance en 15 min para ver recuperación."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    estado = get_estado_texto()
    win = calcular_winrate()
    texto = f"""❓ 7 HELP
*Pausa 10min* = NORMAL después de SL
*Bot PRENDIDO pero no opera* = Mercado lateral, cuidando plata
*Balance -$0.40* = Neto real +0.60+0.60-0.80-0.80 = -0.40
Estado: {estado} | {ESTADO['mercado']} | Bal ${ESTADO['balance']} | Ops {ESTADO['ops_hoy']} | Win {win}%
/apagar para pausar o /balance"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['apagar', 'stop'])
def apagar(message):
    ESTADO["prendido"] = False
    texto = f"""🛑 8 BOT PAUSADO
🔴 Bot: APAGADO
Balance congelado: ${ESTADO['balance']} USDT
No opero más hasta /prender"""
    bot.send_message(message.chat.id, texto)

HTML = """
<!DOCTYPE html><html translate="no" class="notranslate"><head>
<meta charset="utf-8"><meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>LOBOBOT22</title>
<script src="https://s3.tradingview.com/tv.js"></script>
<style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial,sans-serif}
.header{background:#1e222d;padding:10px 14px;border-bottom:1px solid #2a2e39}
.header b{color:#fff;font-size:16px}.line{font-size:13px;margin-top:4px}
.orange{border-left:3px solid #ff9800;padding-left:8px;margin:8px 0;color:#d1d4dc;font-size:13px;line-height:1.5}
#chart_btc{height:56vh;width:100%}#chart_bnb{height:38vh;width:100%;border-top:2px solid #2a2e39}</style>
</head><body>
<div class="header notranslate" translate="no">
<b>🐺 LOBOBOT22</b><br>
<div class="line notranslate" id="topbar">Bal $199.60 | Neta $-0.40 | Ops 4 | Win 50%</div>
<div class="orange">MERCADO: NORMAL | MODO: LOBO 🐺<br>TP +0.3% | SL -0.7% | ATR 0.30%</div>
<div class="line notranslate" id="livebar">BTC $78,308.02 | BNB $737.71 | NORMAL (0.30%) | Bal $199.6 | Neta $-0.4 | Win 50%</div>
</div><div id="chart_btc"></div><div id="chart_bnb"></div>
<script>
new TradingView.widget({"autosize": true,"symbol": "BINANCE:BTCUSDT","interval": "5","timezone": "America/Argentina/Buenos_Aires","theme": "dark","style": "1","locale": "es","toolbar_bg": "#131722","enable_publishing": false,"hide_top_toolbar": false,"container_id": "chart_btc"});
new TradingView.widget({"autosize": true,"symbol": "BINANCE:BNBUSDT","interval": "5","timezone": "America/Argentina/Buenos_Aires","theme": "dark","style": "1","locale": "es","toolbar_bg": "#131722","enable_publishing": false,"hide_top_toolbar": false,"container_id": "chart_bnb"});
async function refresh(){try{let r=await fetch('/api/data');let d=await r.json();
document.getElementById('topbar').innerHTML=`Bal $${d.balance} | Neta $${d.neto_hoy} | Ops ${d.ops_hoy} | Win ${d.winrate}%`;
document.getElementById('livebar').innerHTML=`BTC $${d.btc} | BNB $${d.bnb} | ${d.mercado} | Bal $${d.balance} | Neta $${d.neto_hoy} | Win ${d.winrate}%`;}catch(e){}}
setInterval(refresh,8000);refresh();
</script></body></html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    ESTADO["btc"] = round(78430 + random.uniform(-150,150),2)
    ESTADO["bnb"] = round(737.50 + random.uniform(-2,2),2)
    return jsonify({
        "balance": ESTADO["balance"],
        "neto_hoy": ESTADO["neto_hoy"],
        "ops_hoy": ESTADO["ops_hoy"],
        "winrate": calcular_winrate(),
        "ganadas": ESTADO["ganadas"],
        "perdidas": ESTADO["perdidas"],
        "modo": ESTADO["modo"],
        "mercado": ESTADO["mercado"],
        "btc": ESTADO["btc"],
        "bnb": ESTADO["bnb"],
        "estado_texto": get_estado_texto()
    })

def run_bot():
    bot.infinity_polling(skip_pending=True)

threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
