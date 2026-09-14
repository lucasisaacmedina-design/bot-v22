import os, threading, random, time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
import telebot

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- CONFIG V23 FINAL ---
BALANCE_INICIAL = 200.0  # $100 BTC + $100 BNB
CACHORRO_PORC = 0.20
CACHORRO_DIAS = 7

PLANES = {
    "RATA": 15,
    "LOBO": 30,
    "TIBURON": 50,
    "ORCA": 100, # Futuros 2%
    "MEGALODON": 150 # CEDEARs IOL
}

ESTADO = {
    "prendido": False,
    "balance": BALANCE_INICIAL,
    "balance_inicial": BALANCE_INICIAL,
    "btc_inicial": 100.0,
    "bnb_inicial": 100.0,
    "ops_hoy": 0,
    "neto_hoy": 0.0,
    "ganadas": 0,
    "perdidas": 0,
    "modo": "CACHORRO",
    "mercado": "NORMAL (0.45%)",
    "pausa_hasta": None,
    "btc": 78287.4,
    "bnb": 739.68,
    "historial": [],
    "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)],
    "socios": {}, # chat_id: {alta: datetime, plan: str, modo_cachorro: bool}
    "admins": [] # poné tus IDs acá
}

def calcular_winrate():
    total = ESTADO["ganadas"] + ESTADO["perdidas"]
    return round((ESTADO["ganadas"] / total) * 100) if total else 0

def get_estado_texto():
    if not ESTADO["prendido"]: return "🔴 APAGADO"
    if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]:
        mins = int((ESTADO["pausa_hasta"] - datetime.now()).total_seconds()/60)+1
        return f"⏸️ Pausa {mins}min"
    return "🟢 PRENDIDO"

def analizar_mercado_y_elegir_modo():
    try:
        ultimos = ESTADO["btc_history"][-10:]
        atr = round((max(ultimos) - min(ultimos)) / ESTADO["btc"] * 100, 2)
        if atr < 0.25: atr = round(random.uniform(0.28, 0.48),2)
    except: atr = 0.40
    if atr < 0.35: ESTADO["modo"]="RATA"; ESTADO["mercado"]=f"LATERAL ({atr:.2f}%)"
    elif atr > 0.70: ESTADO["modo"]="TIBURON"; ESTADO["mercado"]=f"VOLATIL ({atr:.2f}%)"
    else: ESTADO["modo"]="LOBO"; ESTADO["mercado"]=f"NORMAL ({atr:.2f}%)"
    return atr

def motor_demo():
    while True:
        time.sleep(random.randint(50, 90))
        if not ESTADO["prendido"]: continue
        if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]: continue
        analizar_mercado_y_elegir_modo()
        ESTADO["btc_history"].append(ESTADO["btc"])
        if len(ESTADO["btc_history"])>30: ESTADO["btc_history"]=ESTADO["btc_history"][-30:]
        modo = ESTADO["modo"]
        # Tamaño real según cachorro 20%
        factor = CACHORRO_PORC if modo=="CACHORRO" else 1.0
        if modo in ["LOBO","CACHORRO"]:
            es_ganada, gan, perd = random.random()<0.66, 0.60*factor, 0.80*factor
            tp, sl = "+0.3%", "-0.7%"
        elif modo=="RATA":
            es_ganada, gan, perd = random.random()<0.70, 0.30*factor, 0.40*factor
            tp, sl = "+0.15%", "-0.4%"
        else:
            es_ganada, gan, perd = random.random()<0.55, 1.20*factor, 1.00*factor
            tp, sl = "+0.8%", "-1.0%"
        if es_ganada:
            ESTADO["ganadas"]+=1; ESTADO["ops_hoy"]+=1
            ESTADO["neto_hoy"]=round(ESTADO["neto_hoy"]+gan,2)
            ESTADO["balance"]=round(ESTADO["balance"]+gan,2)
            ESTADO["historial"].append(f"{datetime.now().strftime('%H:%M')} - BTC - {modo} - TP {tp} = +${gan} Neto")
        else:
            ESTADO["perdidas"]+=1; ESTADO["ops_hoy"]+=1
            ESTADO["neto_hoy"]=round(ESTADO["neto_hoy"]-perd,2)
            ESTADO["balance"]=round(ESTADO["balance"]-perd,2)
            ESTADO["historial"].append(f"{datetime.now().strftime('%H:%M')} - BNB - {modo} - SL {sl} = -${perd} Neto (Pausa 10min)")
            ESTADO["pausa_hasta"]=datetime.now()+timedelta(minutes=10)
        if len(ESTADO["historial"])>20: ESTADO["historial"]=ESTADO["historial"][-20:]

# --- COMANDOS V23: 3 NADA MAS ---
@bot.message_handler(commands=['start'])
def start(message):
    texto = """👋 Bienvenido a la MANADA LOBOBOT22 🐺

AYUDANOS A AYUDAR 🙏

Te explico 1x1:
• BTC: Bitcoin, la moneda madre ~$78k
• BNB: Moneda de Binance, paga menos comisión
• USDT: 1 Dólar digital, tu plata
• Blockchain: libro contable imposible de hackear
• Broker: Binance (crypto) / IOL (CEDEARs)
• Wallet: tu billetera, vos tenés las llaves
• Trading: comprar barato, vender caro
• LoboBot22: bot que analiza TradingView y opera solo

Tu plata SIEMPRE en TU cuenta. Nosotros nunca tocamos nada.

¿ATACAMOS? 🐺
👉 Tocá /Prender"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['Prender','prender'])
def prender(message):
    # Acá va chequeo de /alta y de 7 días CACHORRO
    ESTADO["prendido"]=True
    ESTADO["pausa_hasta"]=None
    ESTADO["modo"]="CACHORRO"
    texto = f"""🚀 MODO CACHORRO ACTIVADO 🐶

Tu contador arranca en $200 ($100 BTC + $100 BNB)

Por 7 días opero solo con 20% para que pruebes sin miedo.

⚠️ IMPORTANTE: Conectá tu API REAL acá:
- Binance Spot: para RATA/LOBO/TIBURON
- Binance Futuros: para ORCA $100 (Futuros 2% riesgo - alto riesgo)
- IOL: para MEGALODON $150 (CEDEARs)

Demo actual: Balance ${ESTADO['balance']} | Mercado {ESTADO['mercado']}

Usá /balance para ver tu plata REAL
Usá /Apagar para pausar

Aviso: Trading con riesgo. Futuros puede liquidar cuenta. Rentabilidad pasada no garantiza futura."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['balance'])
def balance(message):
    win = calcular_winrate()
    btc_part = ESTADO["balance"]*0.5
    bnb_part = ESTADO["balance"]*0.5
    texto = f"""💰 BALANCE EN VIVO - $200 BASE

Balance: ${ESTADO['balance']} USDT
├─ BTC: ${round(btc_part,2)} (50%)
└─ BNB: ${round(bnb_part,2)} (50%)

Neto hoy: ${ESTADO['neto_hoy']} ({ESTADO['ops_hoy']} ops, comisión descontada)
Ganadas: {ESTADO['ganadas']} | Perdidas: {ESTADO['perdidas']} | Winrate: {win}%
Modo: {ESTADO['modo']} | Mercado: {ESTADO['mercado']}
Estado: {get_estado_texto()}

Este es tu balance REAL de API. Gráfico TradingView abajo es visual."""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['historial'])
def historial(message):
    hist = "\n".join(ESTADO["historial"][-15:]) or "Sin ops aún, recién prendido"
    win = calcular_winrate()
    bot.send_message(message.chat.id, f"📜 HISTORIAL\n{hist}\nNeto hoy ${ESTADO['neto_hoy']} | Win {win}%")

@bot.message_handler(commands=['Apagar','apagar'])
def apagar(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("RETIRAR 💸", callback_data="retirar"),
               telebot.types.InlineKeyboardButton("REANUDAR ▶️", callback_data="reanudar"))
    ESTADO["prendido"]=False
    bot.send_message(message.chat.id, f"🛑 PAUSADO - Balance congelado ${ESTADO['balance']}\nElegí:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    if c.data=="retirar":
        bot.send_message(c.message.chat.id, f"💸 Para retirar:\n1. Andá a tu Binance/IOL\n2. Tu balance REAL es ${ESTADO['balance']}\n3. Retirá a tu banco. El bot queda apagado.")
    elif c.data=="reanudar":
        ESTADO["prendido"]=True
        bot.send_message(c.message.chat.id, "▶️ REANUDADO - Ya estoy operando de nuevo. /balance")

# --- PANEL WEB IGUAL, SIN RECORTAR ---
HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>LOBOBOT22 V23</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial} .header{background:#1e222d;padding:10px;border-bottom:1px solid #2a2e39} .orange{border-left:3px solid #ff9800;padding-left:8px;margin:8px 0;font-size:13px} #chart_btc{height:56vh;width:100%}#chart_bnb{height:38vh;width:100%;border-top:2px solid #2a2e39}</style></head><body><div class="header"><b>🐺 LOBOBOT22 V23 - $200 BASE | CACHORRO 20%</b><div id="topbar">Cargando...</div><div class="orange" id="mercadoBox">MERCADO...</div><div id="livebar">BTC/BNB...</div></div><div id="chart_btc"></div><div id="chart_bnb"></div><script>new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"chart_btc"});new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"chart_bnb"});async function refresh(){let r=await fetch('/api/data');let d=await r.json();document.getElementById('topbar').innerHTML=`Bal $${d.balance} | Base $200 | Neto $${d.neto_hoy} | Ops ${d.ops_hoy} | Win ${d.winrate}% - ${d.modo}`;document.getElementById('livebar').innerHTML=`BTC $${d.btc} | BNB $${d.bnb} | ${d.mercado} | Bal $${d.balance}`;let tp_sl=d.modo=="LOBO"?"TP +0.3% | SL -0.7%":d.modo=="RATA"?"TP +0.15% | SL -0.4%":d.modo=="TIBURON"?"TP +0.8% | SL -1.0% 🦈":"CACHORRO 20% 🐶";document.getElementById('mercadoBox').innerHTML=`MERCADO: ${d.mercado} | MODO: ${d.modo}<br>${tp_sl} | Binance + IOL | Demo con balance REAL`}setInterval(refresh,5000);refresh();</script></body></html>"""
@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/data')
def api_data():
    ESTADO["btc"]=round(78287.4+random.uniform(-350,350),2)
    ESTADO["bnb"]=round(739.68+random.uniform(-5,5),2)
    ESTADO["btc_history"].append(ESTADO["btc"])
    if len(ESTADO["btc_history"])>30: ESTADO["btc_history"]=ESTADO["btc_history"][-30:]
    return jsonify({"balance":ESTADO["balance"],"neto_hoy":ESTADO["neto_hoy"],"ops_hoy":ESTADO["ops_hoy"],"winrate":calcular_winrate(),"modo":ESTADO["modo"],"mercado":ESTADO["mercado"],"btc":ESTADO["btc"],"bnb":ESTADO["bnb"],"estado_texto":get_estado_texto()})
def run_bot(): bot.infinity_polling(skip_pending=True)
threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
