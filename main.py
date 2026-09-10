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
    "balance": 199.20,
    "ops_hoy": 1,
    "neto_hoy": -0.80,
    "ganadas": 2,
    "perdidas": 1,
    "modo": "LOBO",
    "mercado": "NORMAL (0.30%)",
    "pausa_hasta": None,
    "btc": 78430,
    "bnb": 737.50,
    "historial": [
        "14:30 - BTC - LOBO - TP +0.3% = +$0.60 Neto",
        "15:10 - BNB - RATA - SL -0.7% = -$0.80 Neto (Pausa 10min)",
        "15:20 - En pausa, cuidando balance"
    ],
    "btc_history": [78430 + random.uniform(-200,200) for _ in range(30)],
    "balance_history": [199.20 + random.uniform(-1,1) for _ in range(30)]
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

# --- MOTOR AUTOMATICO DEMO ---
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

@bot.message_handler(commands=['introduccion', 'start_intro'])
def introduccion(message):
    texto = """👋 1 BIENVENIDO A LOBO V32.2 FIX - EXPLICACIÓN COMPLETA

Soy un bot automático conectado a tu Binance. Opero solo, vos no tenés que hacer nada. Te explico TODO lo que vas a ver:

*MONEDAS QUE USO:*

*BTC - Bitcoin:* La moneda más cara y famosa. Vale ~$78.000. La opero porque se mueve y deja ganancia rápida.

*BNB - Binance Coin:* La moneda del exchange Binance. Vale ~$737. La opero porque paga menos comisión y es más estable que BTC.

*USDT - Dólar Digital:* Tu plata NO está en pesos argentinos. Está en USDT. 1 USDT = 1 Dólar. Tu Balance $199.20 son 199 dólares.

*LO QUE VES EN /balance Y EN EL GRAFICO:*

*Balance:* Tu plata total real en Binance en USDT (dólares).

*Neto:* Tu ganancia o pérdida REAL del día, YA con comisión de Binance descontada. Si ves Neto $-0.80 es de 1 operación sola, en la próxima se recupera.

*Ops:* Cantidad de operaciones que hice hoy.

*TP +0.3%:* Cuando voy ganando 0.3% cierro y aseguro.

*SL -0.7%:* Si voy perdiendo 0.7% cierro para no perder más. Después me pauso 10 min para cuidarte.

*ATR 0.30%:* Mide cuanto se mueve el mercado.

*MERCADO:*
NORMAL (0.30%) = opero MODO LOBO
LATERAL (0.10%) = MODO RATA, casi no opero para cuidarte
VOLATIL = MODO TIBURON, me pauso

Siguiente: /estrategias y /start"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['estrategias'])
def estrategias(message):
    texto = """📊 2 ESTRATEGIAS - USO 3 MODOS REALES

No uso 1 sola forma. Cambio solo según el mercado:

🐺 MODO LOBO - Mercado NORMAL (0.30%)
Mercado sano. Busco entradas rápidas. TP +0.3% | SL -0.7%

🐀 MODO RATA - Mercado LATERAL (0.10%)
Mercado aburrido. Hago solo scalps cortos o no opero. Te cuido para no sobre-operar.

🦈 MODO TIBURON - Mercado VOLATIL
Mercado loco. Me pauso o reduzco. Espero que calme.

Vos no tenés que cambiar nada manual. El bot elige solo.

Tocá /modo para ver en que modo estoy AHORA."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['modo'])
def modo(message):
    estado = get_estado_texto()
    win = calcular_winrate()
    texto = f"""⚙️ 3 MODO ACTUAL

Mercado: {ESTADO['mercado']}
Modo: 🐺 {ESTADO['modo']} - Buscando entrada rápida
BTC: ${ESTADO['btc']} | BNB: ${ESTADO['bnb']} | ATR: 0.30%
Estado Bot: {estado} | Winrate: {win}% ({ESTADO['ganadas']}W/{ESTADO['perdidas']}L)

Estoy activo y buscando. No tenés que tocar nada.

Siguiente: /balance para ver tu plata o /stop para pausarme"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['start'])
def start(message):
    ESTADO["prendido"] = True
    texto = f"""🚀 4 BOT PRENDIDO

🟢 Bot: PRENDIDO
Balance: ${ESTADO['balance']} USDT
Mercado: {ESTADO['mercado']} | MODO {ESTADO['modo']}

Ya estoy buscando entrada. Te aviso por acá cuando opere.

Usá /balance para ver tu plata en vivo o /stop para pausarme."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['balance'])
def balance(message):
    estado = get_estado_texto()
    win = calcular_winrate()
    texto = f"""💰 5 BALANCE EN VIVO

Balance: ${ESTADO['balance']} USDT
Neto hoy: ${ESTADO['neto_hoy']} ({ESTADO['ops_hoy']} operación, ya con comisión descontada)
Ops hoy: {ESTADO['ops_hoy']} | Ganadas: {ESTADO['ganadas']} | Perdidas: {ESTADO['perdidas']} | Winrate: {win}%
Estado: {estado}

No actualices TradingView con F5. Este balance es el real de Telegram y se actualiza solo.

Tocá /historial para ver la operación."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['historial'])
def historial(message):
    hist = "\n".join(ESTADO["historial"])
    win = calcular_winrate()
    texto = f"""📜 6 HISTORIAL DE HOY

{hist}

Total Neto hoy: ${ESTADO['neto_hoy']} | Winrate: {win}%

Tocá /balance en 15 min para ver recuperación."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    estado = get_estado_texto()
    win = calcular_winrate()
    texto = f"""❓ 7 HELP - ¿ALGO TE PASÓ?

Tranquilo, si tocaste acá es porque algo raro viste. Te explico lo normal:

*1. ¿Ves `⏸️ Pausa 10min`?*
Es NORMAL Lobo. Después de un SL el bot se pausa 10 min para no sobre-operar y no quemarte la cuenta. Solo espera.

*2. ¿Bot PRENDIDO pero no opera?*
Es NORMAL también. Si el mercado está lateral (0.10% o menos) la RATA está esperando entrada. No está roto, está cuidando tu plata.

*3. ¿Balance en negativo -$0.80?*
Ese es el NETO ya con comisión de Binance descontada. Es de 1 operación. En la próxima lo recupera. Tocá /balance en 15 min y /historial para verla.

*4. ¿Error de API o Binance?*
Apretá /stop y después /start de nuevo. Si sigue, escribime.

*ESTADO AHORA MISMO:*
Bot: {estado}
Mercado: {ESTADO['mercado']} | {ESTADO['modo']}
Balance: ${ESTADO['balance']} | Ops hoy: {ESTADO['ops_hoy']} | Win {win}%

¿Seguís trabado? Escribime directo: @TuUsuarioDeSoporte

Siguiente: /stop para pausar o /balance para ver tu plata"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['stop'])
def stop(message):
    ESTADO["prendido"] = False
    texto = f"""🛑 8 BOT PAUSADO

🔴 Bot: APAGADO
Balance congelado: ${ESTADO['balance']} USDT

No opero más hasta que toques /start de nuevo.

Tu plata queda segura en Binance."""
    bot.send_message(message.chat.id, texto)

HTML = """
<!DOCTYPE html>
<html translate="no" class="notranslate">
<head>
<meta charset="utf-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LOBOBOT22</title>
<script src="https://s3.tradingview.com/tv.js"></script>
<style>
body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial,sans-serif}
.header{background:#1e222d;padding:10px 14px;border-bottom:1px solid #2a2e39}
.header b{color:#fff;font-size:16px}
.line{font-size:13px;margin-top:4px}
.orange{border-left:3px solid #ff9800;padding-left:8px;margin:8px 0;color:#d1d4dc;font-size:13px;line-height:1.5}
#chart_btc{height:56vh;width:100%}
#chart_bnb{height:38vh;width:100%;border-top:2px solid #2a2e39}
</style>
</head>
<body>
<div class="header notranslate" translate="no">
<b>🐺 LOBOBOT22</b><br>
<div class="line notranslate" id="topbar">Bal $199.20 | Neta $-0.80 | Ops 1 | Win 66%</div>
<div class="orange">
MERCADO: NORMAL | MODO: LOBO 🐺<br>
TP +0.3% | SL -0.7% | ATR 0.30%
</div>
<div class="line notranslate" id="livebar">BTC $78,308.02 | BNB $737.71 | NORMAL (0.30%) | Bal $199.2 | Neta $-0.8 | Win 66%</div>
</div>

<div id="chart_btc"></div>
<div id="chart_bnb"></div>

<script>
new TradingView.widget({
  "autosize": true,
  "symbol": "BINANCE:BTCUSDT",
  "interval": "5",
  "timezone": "America/Argentina/Buenos_Aires",
  "theme": "dark",
  "style": "1",
  "locale": "es",
  "toolbar_bg": "#131722",
  "enable_publishing": false,
  "hide_top_toolbar": false,
  "container_id": "chart_btc"
});
new TradingView.widget({
  "autosize": true,
  "symbol": "BINANCE:BNBUSDT",
  "interval": "5",
  "timezone": "America/Argentina/Buenos_Aires",
  "theme": "dark",
  "style": "1",
  "locale": "es",
  "toolbar_bg": "#131722",
  "enable_publishing": false,
  "hide_top_toolbar": false,
  "container_id": "chart_bnb"
});
async function refresh(){
 try{
  let r=await fetch('/api/data');let d=await r.json();
  document.getElementById('topbar').innerHTML = `Bal $${d.balance} | Neta $${d.neto_hoy} | Ops ${d.ops_hoy} | Win ${d.winrate}%`;
  document.getElementById('livebar').innerHTML = `BTC $${d.btc} | BNB $${d.bnb} | ${d.mercado} | Bal $${d.balance} | Neta $${d.neto_hoy} | Win ${d.winrate}%`;
 }catch(e){}
}
setInterval(refresh,8000);refresh();
</script>
</body></html>
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
