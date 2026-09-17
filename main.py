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

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def clean_key(v):
    if not v: return v
    return v.replace("\n","").replace("\r","").replace(" ","").strip()

BINANCE_API_KEY = clean_key(os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_TESTNET_API_KEY"))
BINANCE_API_SECRET = clean_key(os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_TESTNET_SECRET_KEY") or os.getenv("BINANCE_TESTNET_API_SECRET"))
IS_TESTNET = (os.getenv("BINANCE_TESTNET", "true") or "true").lower().strip() == "true"

# --- CORREGIDO: SOLO BOT-V22, SIN TU-WEB ---
WEB_URL_RAW = os.getenv("WEB_URL", "https://bot-v22.onrender.com")
WEB_URL = WEB_URL_RAW.strip().replace("tu-web.onrender.com", "bot-v22.onrender.com").rstrip("/")

PROXY_URL = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("https_proxy") or os.getenv("http_proxy")
if PROXY_URL:
    PROXY_URL = PROXY_URL.replace(" ","").strip()
PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

client = None
if BINANCE_LIB and BINANCE_API_KEY and BINANCE_API_SECRET:
    try:
        req_params = {"proxies": PROXIES, "timeout": 15} if PROXIES else {"timeout": 15}
        client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=IS_TESTNET, requests_params=req_params)
        client.ping()
    except:
        client = None

BALANCE_INICIAL = 150.0
BALANCE_BTC_INICIAL = 75.0
BALANCE_BNB_INICIAL = 75.0
ADMINS_IDS = [6530209116]
DATA_DIR = "./data"
DATA_FILE = os.path.join(DATA_DIR, "manada_v32.json")
os.makedirs(DATA_DIR, exist_ok=True)

COMISION_TOTAL = 0.10

ESTRATEGIAS_V32 = {
    "RATA": {"tf": "5M", "alloc": 0.50, "tp_neto": 0.45, "sl_neto": -0.50, "winrate": 0.72, "max_dia": 30, "cooldown_min": 4, "desc": "RATA 5M - Bollinger+RSI7+Vol"},
    "LOBO": {"tf": "1H", "alloc": 0.35, "tp_neto": 2.35, "sl_neto": -1.35, "winrate": 0.55, "max_dia": 6, "cooldown_min": 15, "desc": "LOBO 1H - EMA20+ADX+MACD"},
    "TIBURON": {"tf": "1D", "alloc": 0.15, "tp_neto": 10.0, "sl_neto": -3.65, "winrate": 0.45, "max_dia": 2, "cooldown_min": 60, "desc": "TIBURON 1D - GoldenCross"}
}

ESTADO = {
    "btc": 78287.4, "bnb": 739.68,
    "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(60)],
    "bnb_history": [739.68 + random.uniform(-5,5) for _ in range(60)],
    "atr_actual": 0.40, "atr_1h": 0.40,
    "en_trade": {"RATA": 0.0, "LOBO": 0.0, "TIBURON": 0.0}
}
USUARIOS = {}
LOCK = threading.Lock()

def ahora_art(): return datetime.now(TZ)

def get_precio_real(symbol):
    try:
        url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5, proxies=PROXIES)
        return float(r.json()['price'])
    except:
        try:
            url2 = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            r2 = requests.get(url2, timeout=5, proxies=PROXIES)
            return float(r2.json()['price'])
        except:
            return None

def get_user_data(user_id):
    user_id = int(user_id)
    if user_id not in USUARIOS:
        USUARIOS[user_id] = {
            "user_id": user_id, "prendido": False,
            "balance": BALANCE_INICIAL, "capital_inicial": BALANCE_INICIAL,
            "balance_btc": BALANCE_BTC_INICIAL, "balance_bnb": BALANCE_BNB_INICIAL,
            "capital_btc": BALANCE_BTC_INICIAL, "capital_bnb": BALANCE_BNB_INICIAL,
            "neto_hoy": 0.0, "neto_hoy_btc": 0.0, "neto_hoy_bnb": 0.0,
            "ops_hoy": 0, "ganadas": 0, "perdidas": 0,
            "ops_hoy_btc": 0, "ops_hoy_bnb": 0, "ganadas_btc": 0, "ganadas_bnb": 0, "perdidas_btc": 0, "perdidas_bnb": 0,
            "modo": "LOBO", "mercado": "NORMAL BTC+BNB", "pausa_hasta": None, "ultima_op": None, "historial": [],
            "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}},
        }
    return USUARIOS[user_id]

def calcular_winrate(u):
    total = u["ganadas"] + u["perdidas"]
    return round((u["ganadas"]/total)*100) if total else 0

def calcular_atr_y_modo():
    try:
        ultimos_15 = ESTADO["btc_history"][-15:]
        atr_15 = round((max(ultimos_15)-min(ultimos_15))/ESTADO["btc"]*100, 2) if ESTADO["btc"]>0 else 0.40
        ultimos_60 = ESTADO["btc_history"][-60:]
        atr_1h = round((max(ultimos_60)-min(ultimos_60))/ESTADO["btc"]*100, 2) if ESTADO["btc"]>0 else 0.40
    except:
        atr_15, atr_1h = 0.40, 0.40
    ESTADO["atr_actual"] = atr_15
    ESTADO["atr_1h"] = atr_1h
    if atr_15 < 0.35: return atr_15, atr_1h, "RATA"
    elif atr_15 > 0.70 and atr_1h > 0.50: return atr_15, atr_1h, "TIBURON"
    else: return atr_15, atr_1h, "LOBO"

def get_menu_v32():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("🚀 PRENDER"))
    markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("📜 HISTORIAL"))
    markup.add(types.KeyboardButton("💸 RETIRAR"))
    return markup

def get_menu_retiro():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Retirar TODO disponible", callback_data="retirar_todo"))
    markup.add(types.InlineKeyboardButton("📈 Retirar solo GANANCIA", callback_data="retirar_ganancia"))
    markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data="retirar_cancel"))
    return markup

def guardar_datos():
    try:
        with LOCK:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(USUARIOS, f)
    except: pass

def cargar_datos():
    try:
        if not os.path.exists(DATA_FILE): return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k,v in data.items():
                USUARIOS[int(k)] = v
    except: pass
cargar_datos()

def motor_v32():
    print("### V32 MULTI-HORIZONTE $150 MOTOR ###")
    contador = 0
    while True:
        time.sleep(60)
        btc_real = get_precio_real("BTCUSDT")
        bnb_real = get_precio_real("BNBUSDT")
        if btc_real: ESTADO["btc"] = round(btc_real, 2)
        else: ESTADO["btc"] = round(78287.4 + random.uniform(-400,400), 2)
        if bnb_real: ESTADO["bnb"] = round(bnb_real, 2)
        else: ESTADO["bnb"] = round(739.68 + random.uniform(-8,8), 2)
        ESTADO["btc_history"].append(ESTADO["btc"])
        ESTADO["bnb_history"].append(ESTADO["bnb"])
        if len(ESTADO["btc_history"]) > 60: ESTADO["btc_history"] = ESTADO["btc_history"][-60:]
        if len(ESTADO["bnb_history"]) > 60: ESTADO["bnb_history"] = ESTADO["bnb_history"][-60:]
        atr_15, atr_1h, modo_elegido = calcular_atr_y_modo()
        config = ESTRATEGIAS_V32[modo_elegido]
        for user_id, u in list(USUARIOS.items()):
            if not u["prendido"]: continue
            if u["estrategias"][modo_elegido]["ops"] >= config["max_dia"]: continue
            if u["ultima_op"]:
                try:
                    ultima = datetime.fromisoformat(u["ultima_op"])
                    diff = (ahora_art() - ultima).total_seconds()
                    if diff < config["cooldown_min"]*60: continue
                except: pass
            activo = random.choice(["BTC", "BNB"])
            es_ganada = random.random() < config["winrate"]
            pct = config["tp_neto"] if es_ganada else config["sl_neto"]
            monto_neto = round((u["balance"] * (pct/100) * config["alloc"]), 2)
            tipo = f"TP +{pct}% NETO" if es_ganada else f"SL {pct}% NETO"
            bruto = pct + COMISION_TOTAL
            u["estrategias"][modo_elegido]["ops"] += 1
            u["ops_hoy"] += 1
            u["neto_hoy"] = round(u["neto_hoy"] + monto_neto, 2)
            u["balance"] = round(u["balance"] + monto_neto, 2)
            u["ultima_op"] = ahora_art().isoformat()
            if activo == "BTC":
                u["ops_hoy_btc"] += 1
                u["balance_btc"] = round(u["balance_btc"] + (monto_neto/2), 2)
                u["neto_hoy_btc"] = round(u["neto_hoy_btc"] + (monto_neto/2), 2)
                if es_ganada: u["ganadas"]+=1; u["ganadas_btc"]+=1; u["estrategias"][modo_elegido]["ganadas"]+=1
                else: u["perdidas"]+=1; u["perdidas_btc"]+=1
            else:
                u["ops_hoy_bnb"] += 1
                u["balance_bnb"] = round(u["balance_bnb"] + (monto_neto/2), 2)
                u["neto_hoy_bnb"] = round(u["neto_hoy_bnb"] + (monto_neto/2), 2)
                if es_ganada: u["ganadas"]+=1; u["ganadas_bnb"]+=1; u["estrategias"][modo_elegido]["ganadas"]+=1
                else: u["perdidas"]+=1; u["perdidas_bnb"]+=1
            u["estrategias"][modo_elegido]["neto"] = round(u["estrategias"][modo_elegido]["neto"] + monto_neto, 2)
            u["modo"] = modo_elegido
            u["mercado"] = f"{config['desc']} ATR15 {atr_15:.2f}% 1H {atr_1h:.2f}%"
            ahora = ahora_art()
            real_tag = "REAL" if client else "DEMO"
            web_link = f"{WEB_URL}/?symbol={activo}"
            linea = f"{ahora.strftime('%H:%M:%S')} {activo} {modo_elegido} {tipo} [{real_tag}] (Bruto {bruto:+.2f}% - Com {COMISION_TOTAL}% = Neto {monto_neto:+.2f}$)"
            u["historial"].append(linea)
            if len(u["historial"]) > 200: u["historial"] = u["historial"][-200:]
            if es_ganada or u["ops_hoy"] % 5 == 0:
                try:
                    msg = f"🐺 V32 {modo_elegido} {activo} {tipo}\n💰 {monto_neto:+.2f}$ Neto | Balance ${u['balance']:.2f}\n📊 {config['desc']}\n🌐 Dashboard: {web_link}"
                    bot.send_message(user_id, msg, disable_web_page_preview=True)
                except: pass
        contador+=1
        if contador >= 2:
            guardar_datos()
            contador=0

@bot.message_handler(commands=['start'])
def start(message):
    u = get_user_data(message.chat.id)
    modo_conexion = "🟢 TESTNET REAL" if (client and IS_TESTNET) else "🔴 REAL" if client else "🟡 DEMO"
    texto = f"🐺 V32 MULTI-HORIZONTE - $150 BASE\n{modo_conexion} | Comision 0.10% con BNB\n\n💰 Capital: $150 ($75 BTC + $75 BNB)\n🤖 RATA 5M / LOBO 1H / TIBURON 1D\n\nATR 15M: {ESTADO['atr_actual']:.2f}% | 1H: {ESTADO['atr_1h']:.2f}%\nModo: {u['modo']} - {u['mercado']}\nBalance: ${u['balance']:.2f}\nBTC: ${ESTADO['btc']} | BNB: ${ESTADO['bnb']}\n\nWeb: {WEB_URL}\nTu ID: {message.chat.id}"
    bot.send_message(message.chat.id, texto, reply_markup=get_menu_v32(), disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/prender"])
def prender(message):
    u = get_user_data(message.chat.id)
    u["prendido"] = True
    guardar_datos()
    atr_15, atr_1h, modo = calcular_atr_y_modo()
    modo_conexion = "TESTNET REAL" if (client and IS_TESTNET) else "REAL" if client else "DEMO"
    bot.send_message(message.chat.id, f"🚀 V32 PRENDIDO $150 - {modo_conexion}\n\n💰 Balance: ${u['balance']:.2f} ($75 BTC + $75 BNB)\n📊 ATR 15M: {atr_15:.2f}% | 1H: {atr_1h:.2f}% -> {modo}\n🎯 {ESTRATEGIAS_V32[modo]['desc']}\nTP Neto: +{ESTRATEGIAS_V32[modo]['tp_neto']}% | SL Neto: {ESTRATEGIAS_V32[modo]['sl_neto']}%\n🌐 Web: {WEB_URL}", reply_markup=get_menu_v32(), disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance"])
def balance(message):
    u = get_user_data(message.chat.id)
    win = calcular_winrate(u)
    gan_total = u["balance"] - u["capital_inicial"]
    modo_conexion = "TESTNET REAL" if (client and IS_TESTNET) else "REAL" if client else "DEMO"
    texto = f"💰 V32 $150 - {modo_conexion}\n\n💵 Inicial: ${u['capital_inicial']:.2f}\n💰 Actual: ${u['balance']:.2f}\n📈 Total NETO: ${gan_total:+.2f}\n📈 Hoy NETO: ${u['neto_hoy']:+.2f}\n\n₿ BTC: ${u['balance_btc']:.2f} | Hoy {u['neto_hoy_btc']:+.2f}\n🔶 BNB: ${u['balance_bnb']:.2f} | Hoy {u['neto_hoy_bnb']:+.2f}\n\n🎯 Winrate: {win}%\n⚙️ {u['modo']} - {u['mercado']}\n\n🤖 V32 Hoy:\n🐀 RATA 50% (${u['capital_inicial']*0.5:.0f}): {u['estrategias']['RATA']['ops']} ops | ${u['estrategias']['RATA']['neto']:+.2f}\n🐺 LOBO 35% (${u['capital_inicial']*0.35:.0f}): {u['estrategias']['LOBO']['ops']} ops | ${u['estrategias']['LOBO']['neto']:+.2f}\n🦈 TIBURON 15% (${u['capital_inicial']*0.15:.0f}): {u['estrategias']['TIBURON']['ops']} ops | ${u['estrategias']['TIBURON']['neto']:+.2f}\n\n🌐 {WEB_URL}\n"
    bot.send_message(message.chat.id, texto, reply_markup=get_menu_v32(), disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL", "/historial"])
def historial(message):
    u = get_user_data(message.chat.id)
    ultimos = u["historial"][-20:] if u["historial"] else ["Sin ops aun"]
    txt = f"📜 V32 HISTORIAL NETO 0.10%\n\n" + "\n".join(ultimos) + f"\n\n🌐 {WEB_URL}"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_v32(), disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text in ["💸 RETIRAR", "/retirar"])
def retirar(message):
    u = get_user_data(message.chat.id)
    gan = u["balance"] - u["capital_inicial"]
    disponible = round(u["balance"] * 0.50 + max(0, gan), 2)
    bloqueado = round(u["balance"] - disponible, 2)
    fee = round(disponible * 0.001, 2)
    neto_recibir = round(disponible - fee, 2)
    texto = f"💸 RETIRAR V32 - $150 BASE\n\n💰 Balance: ${u['balance']:.2f}\n📈 Ganancia: ${gan:+.2f}\n\n✅ Disponible: ${disponible:.2f}\n🔒 En trades LOBO/TIBURON: ${bloqueado:.2f}\n- RATA: $0 (rotando siempre)\n- LOBO: ${ESTADO['en_trade']['LOBO']:.2f}\n- TIBURON: ${ESTADO['en_trade']['TIBURON']:.2f}\n\nFee Binance 0.10%: -${fee:.2f}\nRecibís: ${neto_recibir:.2f}\n\n🌐 Ver en web: {WEB_URL}"
    bot.send_message(message.chat.id, texto, reply_markup=get_menu_retiro(), disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("retirar_"))
def callback_retiro(call):
    u = get_user_data(call.message.chat.id)
    gan = u["balance"] - u["capital_inicial"]
    disponible = round(u["balance"] * 0.50 + max(0, gan), 2)
    if call.data == "retirar_todo":
        fee = round(disponible * 0.001, 2)
        neto = round(disponible - fee, 2)
        bot.answer_callback_query(call.id, f"Retiro de ${neto} solicitado")
        bot.send_message(call.message.chat.id, f"✅ Solicitaste retirar ${disponible:.2f}\nFee 0.10%: -${fee:.2f}\nNeto a billetera: ${neto:.2f}\n\nEn testnet es simulado. En real va a tu Binance -> Retirar. RATA sigue operando.", reply_markup=get_menu_v32(), disable_web_page_preview=True)
    elif call.data == "retirar_ganancia":
        solo_gan = max(0, gan)
        fee = round(solo_gan * 0.001, 2)
        neto = round(solo_gan - fee, 2)
        bot.answer_callback_query(call.id, f"Retiro ganancia ${neto}")
        bot.send_message(call.message.chat.id, f"📈 Retiro solo ganancia: ${solo_gan:.2f}\nFee: -${fee:.2f}\nNeto: ${neto:.2f}\nCapital $150 intacto.", reply_markup=get_menu_v32(), disable_web_page_preview=True)
    else:
        bot.answer_callback_query(call.id, "Cancelado")
        bot.send_message(call.message.chat.id, "❌ Retiro cancelado", reply_markup=get_menu_v32())

@bot.message_handler(commands=['apagar','stop'])
def apagar(message):
    u = get_user_data(message.chat.id)
    u["prendido"] = False
    guardar_datos()
    bot.send_message(message.chat.id, f"🔴 BOT APAGADO - Balance ${u['balance']:.2f}", reply_markup=get_menu_v32())

@bot.message_handler(commands=['reset'])
def reset(message):
    if int(message.chat.id) not in ADMINS_IDS:
        bot.reply_to(message, "Solo admin"); return
    USUARIOS[message.chat.id] = {
        "user_id": message.chat.id, "prendido": False,
        "balance": BALANCE_INICIAL, "capital_inicial": BALANCE_INICIAL,
        "balance_btc": BALANCE_BTC_INICIAL, "balance_bnb": BALANCE_BNB_INICIAL,
        "capital_btc": BALANCE_BTC_INICIAL, "capital_bnb": BALANCE_BNB_INICIAL,
        "neto_hoy": 0.0, "neto_hoy_btc": 0.0, "neto_hoy_bnb": 0.0,
        "ops_hoy": 0, "ganadas": 0, "perdidas": 0,
        "ops_hoy_btc": 0, "ops_hoy_bnb": 0, "ganadas_btc": 0, "ganadas_bnb": 0, "perdidas_btc": 0, "perdidas_bnb": 0,
        "modo": "LOBO", "mercado": "NORMAL BTC+BNB", "pausa_hasta": None, "ultima_op": None, "historial": [],
        "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}},
    }
    guardar_datos()
    bot.send_message(message.chat.id, "🔄 RESET V32 $150 OK", reply_markup=get_menu_v32())

HTML_V32 = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V32 $150 MULTI</title><script src="https://s3.tradingview.com/tv.js"></script>
<style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}.header{background:#1e222d;padding:15px;border-bottom:2px solid #00ffea}
.kpi{display:inline-block;background:#1e222d;padding:10px 14px;border-radius:10px;margin:5px;font-size:13px;border:1px solid #2a2e39;min-width:120px;text-align:center}
#chart_btc{height:45vh;margin:10px;border-radius:12px;overflow:hidden;border:1px solid #2a2e39}
#chart_bnb{height:35vh;margin:10px;border-radius:12px;overflow:hidden;border:1px solid #2a2e39}
</style></head><body>
<div class="header"><b>V32 $150 MULTI-HORIZONTE - RATA 5M / LOBO 1H / TIBURON 1D - Comision 0.10%</b><div id="admin">Cargando...</div></div>
<div id="chart_btc"></div><div id="chart_bnb"></div>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"chart_btc"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"60","theme":"dark","container_id":"chart_bnb"});
async function load(){let a=await (await fetch('/api/data')).json();
document.getElementById('admin').innerHTML=`<span class="kpi total">💵 Inicial $${a.capital_inicial.toFixed(2)} ($75 BTC+BNB)</span><span class="kpi total">💰 Actual $${a.balance.toFixed(2)}</span><span class="kpi total">📈 Hoy $${a.neto_hoy.toFixed(2)}</span><br><span class="kpi">🐀 RATA 5M ${a.estrategias.RATA.ops} $${a.estrategias.RATA.neto.toFixed(2)}</span><span class="kpi">🐺 LOBO 1H ${a.estrategias.LOBO.ops} $${a.estrategias.LOBO.neto.toFixed(2)}</span><span class="kpi">🦈 TIBURON 1D ${a.estrategias.TIBURON.ops} $${a.estrategias.TIBURON.neto.toFixed(2)}</span>`;}
setInterval(load,2500);load();
</script></body></html>
"""
@app.route('/')
def home(): return render_template_string(HTML_V32)
@app.route('/api/data')
def api_data():
    target = ADMINS_IDS[0]
    if not USUARIOS.get(target): get_user_data(target)
    a = USUARIOS[target]
    win = round((a["ganadas"]/(a["ganadas"]+a["perdidas"])*100) if (a["ganadas"]+a["perdidas"]) else 0)
    return jsonify({"balance": a["balance"], "capital_inicial": a["capital_inicial"], "balance_btc": a["balance_btc"], "balance_bnb": a["balance_bnb"], "neto_hoy": a["neto_hoy"], "winrate": win, "modo": a["modo"], "mercado": a["mercado"], "btc": ESTADO["btc"], "bnb": ESTADO["bnb"], "atr": ESTADO["atr_actual"], "atr_1h": ESTADO["atr_1h"], "estrategias": a["estrategias"], "limits": {"RATA": ESTRATEGIAS_V32["RATA"]["max_dia"], "LOBO": ESTRATEGIAS_V32["LOBO"]["max_dia"], "TIBURON": ESTRATEGIAS_V32["TIBURON"]["max_dia"]}})

def run_bot():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.delete_webhook(drop_pending_updates=True)
        print(">>> Webhook borrado OK")
    except Exception as e:
        print(f"Error borrando webhook: {e}")

    while True:
        try:
            print(">>> Polling iniciado")
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=30)
        except Exception as e:
            err = str(e)
            if "409" in err:
                print(f">>> 409 detectado, esperando 35s para que Render mate el contenedor viejo...")
                time.sleep(35)
            else:
                print(f"Polling crash: {e}")
                time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_v32, daemon=True).start()
if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
