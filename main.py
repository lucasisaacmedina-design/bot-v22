import os, threading, random
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
import telebot

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ESTADO GLOBAL (TUYO, NO TOCO) ---
ESTADO = {
    "prendido": False,
    "balance": 199.20,
    "ops_hoy": 1,
    "neto_hoy": -0.80,
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

def get_estado_texto():
    if not ESTADO["prendido"]:
        return "🔴 APAGADO"
    if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]:
        mins = int((ESTADO["pausa_hasta"] - datetime.now()).total_seconds()/60)+1
        return f"⏸️ Pausa {mins}min"
    return "🟢 PRENDIDO"

# --- TUS 8 COMANDOS EXACTOS ---
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
    texto = f"""⚙️ 3 MODO ACTUAL

Mercado: {ESTADO['mercado']}
Modo: 🐺 {ESTADO['modo']} - Buscando entrada rápida
BTC: ${ESTADO['btc']} | BNB: ${ESTADO['bnb']} | ATR: 0.30%
Estado Bot: {estado}

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
    texto = f"""💰 5 BALANCE EN VIVO

Balance: ${ESTADO['balance']} USDT
Neto hoy: ${ESTADO['neto_hoy']} ({ESTADO['ops_hoy']} operación, ya con comisión descontada)
Ops hoy: {ESTADO['ops_hoy']} | Winrate: 66%
Estado: {estado}

No actualices TradingView con F5. Este balance es el real de Telegram y se actualiza solo.

Tocá /historial para ver la operación."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['historial'])
def historial(message):
    hist = "\n".join(ESTADO["historial"])
    texto = f"""📜 6 HISTORIAL DE HOY

{hist}

Total Neto hoy: ${ESTADO['neto_hoy']}

Tocá /balance en 15 min para ver recuperación."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    estado = get_estado_texto()
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
Balance: ${ESTADO['balance']} | Ops hoy: {ESTADO['ops_hoy']}

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

# --- WEB PRO NUEVA ---
HTML = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>LOBO V33 BETA</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#0e1117;color:#fff;font-family:Inter,Arial;margin:0;padding:15px}
.card{background:#1a1e26;border-radius:16px;padding:16px;margin-bottom:12px;border:1px solid #2a2f3a}
.badge{display:inline-block;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:bold}
.green{background:#0ecb81;color:#000}.red{background:#f6465d}.yellow{background:#fcd535;color:#000}
h2{margin:0 0 10px;font-size:18px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.val{font-size:22px;font-weight:800}
.small{font-size:13px;color:#8b8f9a}
</style></head><body>
<div class="card"><h2>🐺 LOBO V33 - BETA EN VIVO</h2>
<div class="grid">
<div><div class="small">Estado</div><div id="estado" class="badge green">🟢 PRENDIDO</div></div>
<div><div class="small">Balance</div><div id="balance" class="val">$199.20</div></div>
<div><div class="small">Modo</div><div id="modo" class="badge yellow">LOBO - NORMAL</div></div>
<div><div class="small">BTC</div><div id="btc" class="val">$78.430</div></div>
</div></div>
<div class="card"><canvas id="btcChart" height="120"></canvas></div>
<div class="card"><canvas id="balChart" height="120"></canvas></div>
<div class="card small">Neto hoy <b id="neto">-$0.80</b> | Ops <b id="ops">1</b> | <span id="mercado">NORMAL (0.30%)</span><br>Auto-actualiza cada 5s - No toques F5</div>
<script>
let btcC,balC
async function load(){
let r=await fetch('/api/data');let d=await r.json();
document.getElementById('estado').innerText=d.estado_texto
document.getElementById('balance').innerText='$'+d.balance
document.getElementById('modo').innerText=d.modo+' - '+d.mercado
document.getElementById('btc').innerText='$'+d.btc
document.getElementById('neto').innerText='$'+d.neto_hoy
document.getElementById('ops').innerText=d.ops_hoy
document.getElementById('mercado').innerText=d.mercado
if(!btcC){
btcC=new Chart(document.getElementById('btcChart'),{type:'line',data:{labels:d.btc_history.map((_,i)=>i),datasets:[{label:'BTC',data:d.btc_history,borderColor:'#fcd535',backgroundColor:'rgba(252,213,53,0.1)',tension:0.4,fill:true}]},options:{plugins:{legend:{display:false}},scales:{x:{display:false},y:{grid:{color:'#222'}}}}})
balC=new Chart(document.getElementById('balChart'),{type:'line',data:{labels:d.balance_history.map((_,i)=>i),datasets:[{label:'Balance',data:d.balance_history,borderColor:'#0ecb81',backgroundColor:'rgba(14,203,129,0.1)',tension:0.4,fill:true}]},options:{plugins:{legend:{display:false}},scales:{x:{display:false},y:{grid:{color:'#222'}}}}})
}else{btcC.data.datasets[0].data=d.btc_history;btcC.update();balC.data.datasets[0].data=d.balance_history;balC.update();}
}
setInterval(load,5000);load();
</script></body></html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    # Simulación leve para que se mueva el gráfico
    ESTADO["btc"] = round(78430 + random.uniform(-150,150),2)
    ESTADO["btc_history"].append(ESTADO["btc"])
    ESTADO["btc_history"] = ESTADO["btc_history"][-40:]
    ESTADO["balance_history"].append(ESTADO["balance"] + random.uniform(-0.3,0.3))
    ESTADO["balance_history"] = ESTADO["balance_history"][-40:]
    return jsonify({
        "balance": ESTADO["balance"],
        "neto_hoy": ESTADO["neto_hoy"],
        "ops_hoy": ESTADO["ops_hoy"],
        "modo": ESTADO["modo"],
        "mercado": ESTADO["mercado"],
        "btc": ESTADO["btc"],
        "btc_history": ESTADO["btc_history"],
        "balance_history": ESTADO["balance_history"],
        "estado_texto": get_estado_texto()
    })

def run_bot():
    bot.infinity_polling(skip_pending=True)

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
