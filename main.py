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
    return 0 if total == 0 else round((ESTADO["ganadas"] / total) * 100)

def get_estado_texto():
    # Solo para Telegram, en la web no se muestra
    return "🟢 PRENDIDO" if ESTADO["prendido"] else "🔴 APAGADO"

def motor_demo():
    while True:
        time.sleep(random.randint(45, 90))
        if not ESTADO["prendido"]: continue
        if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]: continue
        
        es_ganada = random.random() < 0.66
        hora = datetime.now().strftime('%H:%M')
        if es_ganada:
            ESTADO["ganadas"] += 1; ESTADO["ops_hoy"] += 1
            ESTADO["neto_hoy"] = round(ESTADO["neto_hoy"] + 0.60, 2)
            ESTADO["balance"] = round(ESTADO["balance"] + 0.60, 2)
            ESTADO["historial"].append(f"{hora} - BTC - LOBO - TP +0.3% = +$0.60 Neto")
        else:
            ESTADO["perdidas"] += 1; ESTADO["ops_hoy"] += 1
            ESTADO["neto_hoy"] = round(ESTADO["neto_hoy"] - 0.80, 2)
            ESTADO["balance"] = round(ESTADO["balance"] - 0.80, 2)
            ESTADO["historial"].append(f"{hora} - BNB - RATA - SL -0.7% = -$0.80 Neto")
            ESTADO["pausa_hasta"] = datetime.now() + timedelta(minutes=10)
        
        if len(ESTADO["historial"]) > 20:
            ESTADO["historial"] = ESTADO["historial"][-20:]

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 ¡Bienvenido a LOBOBOT22 🐺!\n1️⃣ /introduccion 2️⃣ /estrategias 3️⃣ /modo 4️⃣ /prender 5️⃣ /balance 6️⃣ /historial 7️⃣ /help 8️⃣ /apagar")

@bot.message_handler(commands=['introduccion', 'start_intro'])
def introduccion(message):
    bot.send_message(message.chat.id, "👋 BIENVENIDO V32.5 LIMPIO\nBTC ~$78k BNB ~$737 USDT=1 Dolar\nBal $199.60 Neto -0.40\nTP +0.3% SL -0.7% ATR 0.30%")

@bot.message_handler(commands=['estrategias'])
def estrategias(message):
    bot.send_message(message.chat.id, "📊 ESTRATEGIAS\n🐺 LOBO NORMAL 0.30% TP +0.3% SL -0.7%\n🐀 RATA LATERAL 0.10%\n🦈 TIBURON VOLATIL")

@bot.message_handler(commands=['modo'])
def modo(message):
    win = calcular_winrate(); estado = get_estado_texto()
    bot.send_message(message.chat.id, f"⚙️ MODO\nMercado: {ESTADO['mercado']}\nModo: 🐺 {ESTADO['modo']}\nBTC: ${ESTADO['btc']} BNB: ${ESTADO['bnb']}\nEstado: {estado} | Win {win}%")

@bot.message_handler(commands=['prender', 'iniciar'])
def prender(message):
    ESTADO["prendido"] = True
    bot.send_message(message.chat.id, f"🚀 BOT PRENDIDO\n{get_estado_texto()} | Bal ${ESTADO['balance']} | {ESTADO['mercado']} MODO {ESTADO['modo']}")

@bot.message_handler(commands=['balance'])
def balance(message):
    win = calcular_winrate(); estado = get_estado_texto()
    bot.send_message(message.chat.id, f"💰 BALANCE\nBalance: ${ESTADO['balance']} USDT\nNeto hoy: ${ESTADO['neto_hoy']} ({ESTADO['ops_hoy']} ops)\nOps: {ESTADO['ops_hoy']} | W:{ESTADO['ganadas']} L:{ESTADO['perdidas']} Win {win}%\nEstado: {estado}")

@bot.message_handler(commands=['historial'])
def historial(message):
    win = calcular_winrate(); hist = "\n".join(ESTADO["historial"])
    bot.send_message(message.chat.id, f"📜 HISTORIAL\n{hist}\n\nTotal Neto: ${ESTADO['neto_hoy']} | Win {win}%")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    win = calcular_winrate(); estado = get_estado_texto()
    bot.send_message(message.chat.id, f"❓ HELP\nBal ${ESTADO['balance']} Neto ${ESTADO['neto_hoy']} Estado: {estado} Win {win}%")

@bot.message_handler(commands=['apagar', 'stop'])
def apagar(message):
    ESTADO["prendido"] = False
    bot.send_message(message.chat.id, f"🛑 BOT PAUSADO\n🔴 APAGADO | Bal ${ESTADO['balance']} USDT")

HTML = """
<!DOCTYPE html><html translate="no" class="notranslate"><head>
<meta charset="utf-8"><meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>LOBOBOT22</title>
<script src="https://s3.tradingview.com/tv.js"></script>
<style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial,sans-serif}
.header{background:#1e222d;padding:10px 14px;border-bottom:1px solid #2a2e39}
.header b{color:#fff;font-size:16px}.line{font-size:13px;margin-top:4px}
.orange{border-left:3px solid #ff9800;padding-left:8px;margin:8px 0;color:#d1d4dc;font-size:13px}
#chart_btc{height:56vh;width:100%}#chart_bnb{height:38vh;width:100%;border-top:2px solid #2a2e39}</style>
</head><body>
<div class="header notranslate">
<b>🐺 LOBOBOT22</b><br>
<div class="line notranslate" id="topbar">Bal $199.60 | Neta $-0.40 | Ops 4 | Win 50%</div>
<div class="orange">MERCADO: NORMAL | MODO: LOBO 🐺<br>TP +0.3% | SL -0.7% | ATR 0.30%</div>
<div class="line notranslate" id="livebar">BTC $78,308 | BNB $737 | NORMAL (0.30%) | Bal $199.6 | Win 50%</div>
</div><div id="chart_btc"></div><div id="chart_bnb"></div>
<script>
new TradingView.widget({"autosize": true,"symbol": "BINANCE:BTCUSDT","interval": "5","timezone": "America/Argentina/Buenos_Aires","theme": "dark","style": "1","locale": "es","toolbar_bg": "#131722","container_id": "chart_btc"});
new TradingView.widget({"autosize": true,"symbol": "BINANCE:BNBUSDT","interval": "5","timezone": "America/Argentina/Buenos_Aires","theme": "dark","style": "1","locale": "es","toolbar_bg": "#131722","container_id": "chart_bnb"});
async function refresh(){try{let r=await fetch('/api/data');let d=await r.json();
document.getElementById('topbar').innerHTML=`Bal $${d.balance} | Neta $${d.neto_hoy} | Ops ${d.ops_hoy} | Win ${d.winrate}%`;
document.getElementById('livebar').innerHTML=`BTC $${d.btc} | BNB $${d.bnb} | ${d.mercado} | Bal $${d.balance} | Neta $${d.neto_hoy} | Win ${d.winrate}%`;}catch(e){}}
setInterval(refresh,8000);refresh();
</script></body></html>
"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    ESTADO["btc"] = round(78430 + random.uniform(-150,150),2)
    ESTADO["bnb"] = round(737.50 + random.uniform(-2,2),2)
    return jsonify({
        "balance": ESTADO["balance"], "neto_hoy": ESTADO["neto_hoy"], "ops_hoy": ESTADO["ops_hoy"],
        "winrate": calcular_winrate(), "ganadas": ESTADO["ganadas"], "perdidas": ESTADO["perdidas"],
        "modo": ESTADO["modo"], "mercado": ESTADO["mercado"], "btc": ESTADO["btc"], "bnb": ESTADO["bnb"],
        "estado_texto": get_estado_texto()
    })

def run_bot(): bot.infinity_polling(skip_pending=True)
threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
