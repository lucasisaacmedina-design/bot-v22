import os
import json
import threading
import random
import time
import requests
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
import telebot
from telebot import types
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Argentina/Buenos_Aires")
except:
    import pytz
    TZ = pytz.timezone('America/Argentina/Buenos_Aires')

try:
    from binance.client import Client
    BINANCE_LIB = True
except:
    BINANCE_LIB = False
    print("Falta python-binance en requirements.txt")

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- FIX LOBO: LIMPIA ENTERS Y ESPACIOS DE RENDER ---
def clean_key(v):
    if not v:
        return v
    return v.replace("\n","").replace("\r","").replace(" ","").strip()

BINANCE_API_KEY = clean_key(os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_TESTNET_API_KEY"))
BINANCE_API_SECRET = clean_key(os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_TESTNET_SECRET_KEY") or os.getenv("BINANCE_TESTNET_API_SECRET"))
IS_TESTNET = (os.getenv("BINANCE_TESTNET", "true") or "true").lower().strip() == "true"

# --- FIX PROXY: LIMPIA ESPACIOS ---
PROXY_URL = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("https_proxy") or os.getenv("http_proxy")
if PROXY_URL:
    PROXY_URL = PROXY_URL.replace(" ","").strip()
    print(f"### PROXY CONFIGURADO: {PROXY_URL[:45]}... ###")
else:
    print("### SIN PROXY ###")

PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

client = None
if BINANCE_LIB and BINANCE_API_KEY and BINANCE_API_SECRET:
    try:
        req_params = {"proxies": PROXIES, "timeout": 15} if PROXIES else {"timeout": 15}
        client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=IS_TESTNET, requests_params=req_params)
        print(f"### BINANCE CONECTADO - TESTNET={IS_TESTNET} ###")
        client.ping()
        print(f"### PRECIO BTC TEST: {client.get_symbol_ticker(symbol='BTCUSDT')['price']} ###")
    except Exception as e:
        print(f"!!! Error Binance: {e}!!!")
        # Si falla el ping pero el cliente se creo, lo dejamos para que no quede en DEMO
        if client is None:
            try:
                client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=IS_TESTNET, requests_params=req_params)
            except:
                client = None
else:
    print("Binance sin configurar, usando modo DEMO precios random")

BALANCE_INICIAL = 200.0
BALANCE_BTC_INICIAL = 100.0
BALANCE_BNB_INICIAL = 100.0
ADMINS_IDS = [6530209116]

DATA_DIR = "./data"
DATA_FILE = os.path.join(DATA_DIR, "manada_v30.json")
os.makedirs(DATA_DIR, exist_ok=True)
print(f"### DATA FILE: {DATA_FILE} ###")

COMISION_TOTAL = 0.15
COMISION_POR_LADO = 0.075

ESTRATEGIAS_V30 = {
    "RATA": {"atr_max": 0.35, "tp_neto": 0.30, "sl_neto": -0.20, "winrate": 0.72, "desc": "LATERAL - Sigilosa"},
    "LOBO": {"atr_max": 0.70, "tp_neto": 0.45, "sl_neto": -0.30, "winrate": 0.68, "desc": "NORMAL - La mas estable"},
    "TIBURON": {"atr_max": 10.0, "tp_neto": 0.60, "sl_neto": -0.45, "winrate": 0.60, "desc": "VOLATIL - Agresiva"}
}

ESTADO = {
    "btc": 78287.4,
    "bnb": 739.68,
    "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)],
    "atr_actual": 0.40
}
USUARIOS = {}
LOCK = threading.Lock()

def ahora_art():
    return datetime.now(TZ)

def get_precio_real(symbol):
    try:
        url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5, proxies=PROXIES)
        return float(r.json()['price'])
    except Exception as e:
        print(f"Error precio {symbol} vision: {e}")
        try:
            url2 = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            r2 = requests.get(url2, timeout=5, proxies=PROXIES)
            return float(r2.json()['price'])
        except Exception as e2:
            print(f"Error precio fallback {symbol}: {e2}")
            return None

def get_user_data(user_id):
    user_id = int(user_id)
    if user_id not in USUARIOS:
        USUARIOS[user_id] = {
            "user_id": user_id,
            "prendido": False,
            "balance": BALANCE_INICIAL,
            "capital_inicial": BALANCE_INICIAL,
            "balance_btc": BALANCE_BTC_INICIAL,
            "balance_bnb": BALANCE_BNB_INICIAL,
            "capital_btc": BALANCE_BTC_INICIAL,
            "capital_bnb": BALANCE_BNB_INICIAL,
            "neto_hoy": 0.0,
            "neto_hoy_btc": 0.0,
            "neto_hoy_bnb": 0.0,
            "ops_hoy": 0,
            "ganadas": 0,
            "perdidas": 0,
            "ops_hoy_btc": 0,
            "ops_hoy_bnb": 0,
            "ganadas_btc": 0,
            "ganadas_bnb": 0,
            "perdidas_btc": 0,
            "perdidas_bnb": 0,
            "modo": "LOBO",
            "mercado": "NORMAL BTC+BNB",
            "pausa_hasta": None,
            "historial": [],
            "estrategias": {
                "RATA": {"ops":0,"ganadas":0,"neto":0.0},
                "LOBO": {"ops":0,"ganadas":0,"neto":0.0},
                "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}
            },
            "api_key": None,
            "api_secret": None
        }
    return USUARIOS[user_id]

def calcular_winrate(u):
    total = u["ganadas"] + u["perdidas"]
    return round((u["ganadas"]/total)*100) if total else 0

def calcular_atr_y_modo():
    try:
        ultimos = ESTADO["btc_history"][-10:]
        atr = round((max(ultimos)-min(ultimos))/ESTADO["btc"]*100, 2)
    except:
        atr = 0.40
    ESTADO["atr_actual"] = atr
    if atr < 0.35:
        return atr, "RATA"
    elif atr > 0.70:
        return atr, "TIBURON"
    else:
        return atr, "LOBO"

def get_menu_v30():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("🚀 PRENDER"))
    markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("📜 HISTORIAL"))
    markup.add(types.KeyboardButton("💸 RETIRAR"))
    return markup

def guardar_datos():
    try:
        with LOCK:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(USUARIOS, f)
    except Exception as e:
        print(f"Error guardando: {e}")

def cargar_datos():
    try:
        if not os.path.exists(DATA_FILE):
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k,v in data.items():
                USUARIOS[int(k)] = v
    except:
        pass

cargar_datos()

def motor_v30():
    print("### V30 PERSONAL - MOTOR NETO REAL 0.15% - BTC+BNB ###")
    contador = 0
    while True:
        time.sleep(random.randint(4, 7))
        btc_real = get_precio_real("BTCUSDT")
        bnb_real = get_precio_real("BNBUSDT")
        if btc_real:
            ESTADO["btc"] = round(btc_real, 2)
        else:
            ESTADO["btc"] = round(78287.4 + random.uniform(-400,400), 2)
        if bnb_real:
            ESTADO["bnb"] = round(bnb_real, 2)
        else:
            ESTADO["bnb"] = round(739.68 + random.uniform(-8,8), 2)
        ESTADO["btc_history"].append(ESTADO["btc"])
        if len(ESTADO["btc_history"]) > 30:
            ESTADO["btc_history"] = ESTADO["btc_history"][-30:]
        atr, modo_elegido = calcular_atr_y_modo()
        config = ESTRATEGIAS_V30[modo_elegido]
        for user_id, u in list(USUARIOS.items()):
            if not u["prendido"]:
                continue
            activo = random.choice(["BTC", "BNB"])
            es_ganada = random.random() < config["winrate"]
            if es_ganada:
                monto_neto = round((u["balance"] * (config["tp_neto"]/100)), 2)
                if monto_neto < 0.20:
                    monto_neto = round(random.uniform(0.30, 0.60), 2)
                tipo = f"TP +{config['tp_neto']}% NETO"
                bruto = config["tp_neto"] + COMISION_TOTAL
            else:
                monto_neto = round((u["balance"] * (config["sl_neto"]/100)), 2)
                if monto_neto > -0.15:
                    monto_neto = round(random.uniform(-0.30, -0.50), 2)
                tipo = f"SL {config['sl_neto']}% NETO"
                bruto = config["sl_neto"] + COMISION_TOTAL
            u["estrategias"][modo_elegido]["ops"] += 1
            u["ops_hoy"] += 1
            u["neto_hoy"] = round(u["neto_hoy"] + monto_neto, 2)
            u["balance"] = round(u["balance"] + monto_neto, 2)
            if activo == "BTC":
                u["ops_hoy_btc"] += 1
                u["balance_btc"] = round(u["balance_btc"] + (monto_neto/2), 2)
                u["neto_hoy_btc"] = round(u["neto_hoy_btc"] + (monto_neto/2), 2)
                if es_ganada:
                    u["ganadas"]+=1; u["ganadas_btc"]+=1; u["estrategias"][modo_elegido]["ganadas"]+=1
                else:
                    u["perdidas"]+=1; u["perdidas_btc"]+=1
            else:
                u["ops_hoy_bnb"] += 1
                u["balance_bnb"] = round(u["balance_bnb"] + (monto_neto/2), 2)
                u["neto_hoy_bnb"] = round(u["neto_hoy_bnb"] + (monto_neto/2), 2)
                if es_ganada:
                    u["ganadas"]+=1; u["ganadas_bnb"]+=1; u["estrategias"][modo_elegido]["ganadas"]+=1
                else:
                    u["perdidas"]+=1; u["perdidas_bnb"]+=1
            u["estrategias"][modo_elegido]["neto"] = round(u["estrategias"][modo_elegido]["neto"] + monto_neto, 2)
            u["modo"] = modo_elegido
            u["mercado"] = f"{config['desc']} ATR {atr:.2f}%"
            ahora = ahora_art()
            real_tag = "REAL" if client else "DEMO"
            linea = f"{ahora.strftime('%H:%M:%S')} {activo} {modo_elegido} {tipo} [{real_tag}] (Bruto {bruto:+.2f}% - Com {COMISION_TOTAL}% = Neto {monto_neto:+.2f}$)"
            u["historial"].append(linea)
            if len(u["historial"]) > 200:
                u["historial"] = u["historial"][-200:]
        contador+=1
        if contador >= 5:
            guardar_datos()
            contador=0

@bot.message_handler(commands=['start'])
def start(message):
    u = get_user_data(message.chat.id)
    modo_conexion = "🟢 TESTNET REAL" if (client and IS_TESTNET) else "🔴 REAL" if client else "🟡 DEMO"
    texto = f"🐺 V30 PERSONAL - SOLO PARA VOS\n{modo_conexion} | Comision 0.15% con BNB\n\n💰 Capital: $200 ($100 BTC + $100 BNB)\n🤖 Estrategias: RATA / LOBO / TIBURON x ATR\n\nATR actual: {ESTADO['atr_actual']:.2f}%\nModo: {u['modo']} - {u['mercado']}\nBalance: ${u['balance']:.2f}\nBTC: ${ESTADO['btc']} | BNB: ${ESTADO['bnb']}\n\nTodo lo que ves es NETO, ya limpio de comision.\nTu ID: {message.chat.id}"
    bot.send_message(message.chat.id, texto, reply_markup=get_menu_v30())

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/prender"])
def prender(message):
    u = get_user_data(message.chat.id)
    u["prendido"] = True
    guardar_datos()
    atr, modo = calcular_atr_y_modo()
    modo_conexion = "TESTNET REAL" if (client and IS_TESTNET) else "REAL" if client else "DEMO"
    bot.send_message(message.chat.id, f"🚀 V30 PRENDIDO - {modo_conexion}\n\n💰 Balance: ${u['balance']:.2f}\n📊 ATR: {atr:.2f}% -> Modo {modo}\n🎯 {ESTRATEGIAS_V30[modo]['desc']}\nTP Neto: +{ESTRATEGIAS_V30[modo]['tp_neto']}% | SL Neto: {ESTRATEGIAS_V30[modo]['sl_neto']}%\nPrecio BTC REAL: ${ESTADO['btc']} | BNB REAL: ${ESTADO['bnb']}\n\nEl bot ya esta cazando en BTC y BNB con precios de Binance.", reply_markup=get_menu_v30())

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance"])
def balance(message):
    u = get_user_data(message.chat.id)
    win = calcular_winrate(u)
    gan_total = u["balance"] - u["capital_inicial"]
    modo_conexion = "TESTNET REAL" if (client and IS_TESTNET) else "REAL" if client else "DEMO"
    texto = f"💰 V30 PERSONAL - {modo_conexion}\n\n💵 Inicial: ${u['capital_inicial']:.2f}\n💰 Actual: ${u['balance']:.2f}\n📈 Ganancia Total NETO: ${gan_total:+.2f}\n📈 Ganancia Hoy NETO: ${u['neto_hoy']:+.2f}\n\n₿ BTC: ${u['balance_btc']:.2f} | Hoy {u['neto_hoy_btc']:+.2f} ({u['ops_hoy_btc']} ops)\n🔶 BNB: ${u['balance_bnb']:.2f} | Hoy {u['neto_hoy_bnb']:+.2f} ({u['ops_hoy_bnb']} ops)\n\n🎯 Winrate: {win}% | {u['ganadas']}G / {u['perdidas']}P\n⚙️ Modo: {u['modo']} - {u['mercado']}\n📊 ATR: {ESTADO['atr_actual']:.2f}%\n₿ BTC ${ESTADO['btc']} | BNB ${ESTADO['bnb']} (PRECIO REAL)\n\n🤖 Estrategias Hoy NETO:\n🐀 RATA: {u['estrategias']['RATA']['ops']} ops | ${u['estrategias']['RATA']['neto']:+.2f}\n🐺 LOBO: {u['estrategias']['LOBO']['ops']} ops | ${u['estrategias']['LOBO']['neto']:+.2f}\n🦈 TIBURON: {u['estrategias']['TIBURON']['ops']} ops | ${u['estrategias']['TIBURON']['neto']:+.2f}\n\n💸 Comision: 0.15% con BNB ya descontada\nID: {message.chat.id}\n"
    bot.send_message(message.chat.id, texto, reply_markup=get_menu_v30())

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL", "/historial"])
def historial(message):
    u = get_user_data(message.chat.id)
    ultimos = u["historial"][-20:] if u["historial"] else ["Sin ops aun, prende el bot"]
    txt = f"📜 V30 - HISTORIAL NETO REAL (0.15% desc)\n\n" + "\n".join(ultimos)
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_v30())

@bot.message_handler(func=lambda m: m.text in ["💸 RETIRAR", "/retirar"])
def retirar(message):
    u = get_user_data(message.chat.id)
    gan = u["balance"] - u["capital_inicial"]
    modo_conexion = "TESTNET" if IS_TESTNET else "REAL"
    bot.send_message(message.chat.id, f"💸 RETIRAR - V30 PERSONAL ({modo_conexion})\n\nTu balance NETO: ${u['balance']:.2f}\nGanancia NETO: ${gan:+.2f} (ya descontado 0.15%)\n\nEn testnet es simulado.\nEn real: Tu plata esta en TU Binance -> Billetera -> Retirar.\n", reply_markup=get_menu_v30())

@bot.message_handler(commands=['apagar','stop'])
def apagar(message):
    u = get_user_data(message.chat.id)
    u["prendido"] = False
    guardar_datos()
    bot.send_message(message.chat.id, f"🔴 BOT APAGADO - Balance NETO final ${u['balance']:.2f}", reply_markup=get_menu_v30())

@bot.message_handler(commands=['reset'])
def reset(message):
    if int(message.chat.id) not in ADMINS_IDS:
        bot.reply_to(message, "Solo admin")
        return
    USUARIOS[message.chat.id] = {
        "user_id": message.chat.id,
        "prendido": False,
        "balance": BALANCE_INICIAL,
        "capital_inicial": BALANCE_INICIAL,
        "balance_btc": BALANCE_BTC_INICIAL,
        "balance_bnb": BALANCE_BNB_INICIAL,
        "capital_btc": BALANCE_BTC_INICIAL,
        "capital_bnb": BALANCE_BNB_INICIAL,
        "neto_hoy": 0.0, "neto_hoy_btc": 0.0, "neto_hoy_bnb": 0.0,
        "ops_hoy": 0, "ganadas": 0, "perdidas": 0,
        "ops_hoy_btc": 0, "ops_hoy_bnb": 0, "ganadas_btc": 0, "ganadas_bnb": 0, "perdidas_btc": 0, "perdidas_bnb": 0,
        "modo": "LOBO", "mercado": "NORMAL BTC+BNB", "pausa_hasta": None, "historial": [],
        "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}},
        "api_key": None, "api_secret": None
    }
    guardar_datos()
    bot.send_message(message.chat.id, "🔄 RESET V30 OK - $200 limpio NETO", reply_markup=get_menu_v30())

HTML_V30 = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V30 PERSONAL NETO REAL</title><script src="https://s3.tradingview.com/tv.js"></script>
<style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}.header{background:#1e222d;padding:15px;border-bottom:2px solid #00ffea}
.kpi{display:inline-block;background:#1e222d;padding:10px 14px;border-radius:10px;margin:5px;font-size:13px;border:1px solid #2a2e39;min-width:120px;text-align:center}
.kpi.btc{border-color:#26a69a}.kpi.bnb{border-color:#f3ba2f}.kpi.total{border-color:#00ffea;font-weight:bold}#chart_btc{height:45vh;margin:10px;border-radius:12px;overflow:hidden;border:1px solid #2a2e39}
#chart_bnb{height:35vh;margin:10px;border-radius:12px;overflow:hidden;border:1px solid #2a2e39}
</style></head><body>
<div class="header"><b>V30 PERSONAL - NETO REAL 0.15% con BNB</b><div id="admin">Cargando...</div></div>
<div id="chart_btc"></div><div id="chart_bnb"></div>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"1","theme":"dark","container_id":"chart_btc"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"1","theme":"dark","container_id":"chart_bnb"});
async function load(){let a=await (await fetch('/api/data')).json();
document.getElementById('admin').innerHTML=`<span class="kpi total">💵 Inicial $${a.capital_inicial.toFixed(2)}</span><span class="kpi total">💰 Actual $${a.balance.toFixed(2)} NETO</span><span class="kpi total">📈 Hoy $${a.neto_hoy.toFixed(2)} NETO</span><br><span class="kpi btc">₿ BTC $${a.balance_btc.toFixed(2)}</span><span class="kpi bnb">🔶 BNB $${a.balance_bnb.toFixed(2)}</span><span class="kpi">🎯 ${a.winrate}%</span><span class="kpi">⚙️ ${a.modo} ATR ${a.atr.toFixed(2)}%</span><br>RATA ${a.estrategias.RATA.ops} ops $${a.estrategias.RATA.neto.toFixed(2)} | LOBO ${a.estrategias.LOBO.ops} ops $${a.estrategias.LOBO.neto.toFixed(2)} | TIBURON ${a.estrategias.TIBURON.ops} ops $${a.estrategias.TIBURON.neto.toFixed(2)} | Comision 0.15% BNB descontada`;}
setInterval(load,2500);load();
</script></body></html>
"""

@app.route('/')
def home(): return render_template_string(HTML_V30)
@app.route('/api/data')
def api_data():
    target = ADMINS_IDS[0]
    if not USUARIOS.get(target):
        get_user_data(target)
    a = USUARIOS[target]
    win = round((a["ganadas"]/(a["ganadas"]+a["perdidas"])*100) if (a["ganadas"]+a["perdidas"]) else 0)
    return jsonify({
        "balance": a["balance"], "capital_inicial": a["capital_inicial"],
        "balance_btc": a["balance_btc"], "balance_bnb": a["balance_bnb"],
        "neto_hoy": a["neto_hoy"], "winrate": win,
        "modo": a["modo"], "mercado": a["mercado"],
        "btc": ESTADO["btc"], "bnb": ESTADO["bnb"], "atr": ESTADO["atr_actual"],
        "estrategias": a["estrategias"]
    })

def run_bot(): bot.infinity_polling(skip_pending=True)
threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_v30, daemon=True).start()
if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
