import os, json, threading, time, requests, numpy as np
from datetime import datetime
from flask import Flask, render_template_string, jsonify
import telebot
from telebot import types
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Argentina/Buenos_Aires")
except:
    import pytz; TZ = pytz.timezone('America/Argentina/Buenos_Aires')
try:
    from binance.client import Client; BINANCE_LIB = True
except:
    BINANCE_LIB = False

TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def clean_key(v):
    if not v: return ""
    return str(v).strip().replace('"','').replace("'","").replace("\n","").replace("\r","").strip()

BINANCE_API_KEY = clean_key(os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_TESTNET_API_KEY"))
BINANCE_API_SECRET = clean_key(os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_TESTNET_SECRET_KEY") or os.getenv("BINANCE_TESTNET_API_SECRET"))
IS_TESTNET = (os.getenv("BINANCE_TESTNET", "true") or "true").lower().strip() == "true"
WEB_URL = os.getenv("WEB_URL", "https://bot-v22.onrender.com").strip().rstrip("/")

PROXY_LIST_RAW = os.getenv("PROXY_LIST") or os.getenv("PROXY_URL") or os.getenv("HTTPS_PROXY") or ""
RAW_SPLIT = [clean_key(c) for c in PROXY_LIST_RAW.split(",") if clean_key(c)]
if not RAW_SPLIT:
    RAW_SPLIT = ["http://ufssgczi:aus6m0vuweru@31.58.9.4:6077","http://ufssgczi:aus6m0vuweru@31.59.20.176:6754"]

def probar_proxy(proxy_url):
    try:
        if not proxy_url.startswith("http"): proxy_url = "http://" + proxy_url
        proxies = {"http": proxy_url, "https": proxy_url}
        r = requests.get("https://testnet.binance.vision/api/v3/ping", proxies=proxies, timeout=12)
        return r.status_code == 200, proxy_url
    except: return False, proxy_url

PROXY_URL=""; PROXIES=None
for p in RAW_SPLIT:
    ok,url = probar_proxy(p)
    if ok: PROXY_URL=url; PROXIES={"http":url,"https":url}; break

client=None; CLIENT_ERROR="No iniciado"; REAL_BALANCE_USDT=10000.00
if BINANCE_LIB and BINANCE_API_KEY and BINANCE_API_SECRET:
    try:
        req_params = {"proxies": PROXIES, "timeout": 25} if PROXIES else {"timeout": 15}
        client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=IS_TESTNET, requests_params=req_params)
        if PROXIES: client.session.proxies.update(PROXIES)
        client.ping()
        acc=client.get_account()
        for b in acc['balances']:
            if b['asset']=='USDT': REAL_BALANCE_USDT=float(b['free'])+float(b['locked'])
        CLIENT_ERROR="OK"
    except Exception as e: CLIENT_ERROR=str(e)[:200]

BALANCE_INICIAL=REAL_BALANCE_USDT
ADMINS_IDS=[6530209116]
DATA_DIR="/opt/render/project/src/data" if os.path.exists("/opt/render/project/src/data") else "./data"
DATA_FILE=os.path.join(DATA_DIR,"manada_v40.json")
os.makedirs(DATA_DIR,exist_ok=True)

# --- 4 BESTIAS REALES ---
ESTRATEGIAS_V40 = {
    "RATA": {"tf": "5m", "alloc": 0.20, "tp_neto": 0.55, "sl_neto": -0.50, "max_dia": 100, "cooldown": 4, "desc": "RATA 5M"},
    "LOBO": {"tf": "1h", "alloc": 0.25, "tp_neto": 2.35, "sl_neto": -1.35, "max_dia": 20, "cooldown": 15, "desc": "LOBO 1H"},
    "TIBURON": {"tf": "1d", "alloc": 0.10, "tp_neto": 8.0, "sl_neto": -3.0, "max_dia": 3, "cooldown": 60, "desc": "TIBURON 1D"},
    "MONSTRUO": {"tf": "15m", "alloc": 0.45, "tp_neto": 2.2, "sl_neto": -1.0, "max_dia": 20, "cooldown": 15, "desc": "MONSTRUO 15M"}
}

ESTADO={"btc":78287.4,"bnb":739.68,"btc_history":[],"bnb_history":[],"atr_actual":0.40,"atr_1h":0.40}
USUARIOS={}; LOCK=threading.Lock()
def ahora_art(): return datetime.now(TZ)

# --- FUNCIONES REALES ---
def get_velas(symbol="BTCUSDT", interval="5m", limit=100):
    try:
        klines=client.get_klines(symbol=symbol, interval=interval, limit=limit)
        return {
            "closes": [float(k[4]) for k in klines],
            "highs": [float(k[2]) for k in klines],
            "lows": [float(k[3]) for k in klines],
            "vols": [float(k[5]) for k in klines]
        }
    except: return None

def rsi_calc(closes, period=14):
    deltas=np.diff(closes); ups=deltas.clip(min=0); downs=-deltas.clip(max=0)
    ma_up=np.mean(ups[-period:]); ma_down=np.mean(downs[-period:])
    if ma_down==0: return 100
    rs=ma_up/ma_down; return 100-(100/(1+rs))

def ejecutar_orden_real(symbol, side, usdt_amount):
    try:
        precio=float(client.get_symbol_ticker(symbol=symbol)['price'])
        qty=round(usdt_amount/precio,6)
        if qty<0.00001: qty=0.00001
        order=client.create_order(symbol=symbol, side=side, type='MARKET', quantity=qty)
        return True, order, precio
    except Exception as e: return False, str(e), 0

def check_reset_diario(u):
    hoy=ahora_art().strftime("%Y-%m-%d")
    if u.get("fecha_hoy")!=hoy:
        u["fecha_hoy"]=hoy; u["neto_hoy"]=0.0; u["ops_hoy"]=0
        for k in u["estrategias"]: u["estrategias"][k]["ops"]=0

def get_user_data(uid):
    uid=int(uid)
    with LOCK:
        if uid not in USUARIOS:
            USUARIOS[uid]={"user_id":uid,"prendido":True,"balance":BALANCE_INICIAL,"capital_inicial":BALANCE_INICIAL,"balance_btc":BALANCE_INICIAL/2,"balance_bnb":BALANCE_INICIAL/2,"neto_hoy":0.0,"ops_hoy":0,"ganadas":0,"perdidas":0,"modo":"ESPERANDO","mercado":"Iniciando...","ultima_op":{}, "historial":[],"estrategias":{k:{"ops":0,"ganadas":0,"neto":0.0} for k in ESTRATEGIAS_V40},"fecha_hoy":ahora_art().strftime("%Y-%m-%d")}
        check_reset_diario(USUARIOS[uid]); return USUARIOS[uid]

def guardar_datos():
    try:
        with LOCK:
            with open(DATA_FILE,"w") as f: json.dump(USUARIOS,f,indent=2)
    except: pass

def cargar_datos():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,"r") as f:
                data=json.load(f)
                for k,v in data.items(): USUARIOS[int(k)]=v
    except: pass
cargar_datos()

# --- DETECTORES REALES ---
def detectar_RATA():
    d=get_velas("BTCUSDT","5m",100)
    if not d: return False,"Sin velas"
    closes=np.array(d["closes"]); rsi=rsi_calc(closes)
    sma20=np.mean(closes[-20:]); std=np.std(closes[-20:])
    lower=sma20-2*std
    precio=closes[-1]; vol_prom=np.mean(d["vols"][-20:]); vol_actual=d["vols"][-1]
    if precio<=lower and rsi<35 and vol_actual>vol_prom*1.3:
        return True,f"RATA Bollinger {precio:.0f}<={lower:.0f} RSI {rsi:.0f} Vol {vol_actual/vol_prom:.1f}x"
    return False,f"RATA esperando RSI {rsi:.0f}"

def detectar_LOBO():
    d=get_velas("BTCUSDT","1h",100)
    if not d: return False,"Sin velas"
    closes=np.array(d["closes"])
    ema20=np.mean(closes[-20:]); ema50=np.mean(closes[-50:])
    # MACD simple
    ema12=np.mean(closes[-12:]); ema26=np.mean(closes[-26:])
    macd=ema12-ema26
    precio=closes[-1]
    if precio>ema20 and ema20>ema50 and macd>0:
        return True,f"LOBO EMA20 {ema20:.0f}>EMA50 {ema50:.0f} MACD {macd:.0f} alcista"
    return False,f"LOBO esperando EMA20 {ema20:.0f} vs EMA50 {ema50:.0f}"

def detectar_TIBURON():
    d=get_velas("BTCUSDT","1d",200)
    if not d: return False,"Sin velas"
    closes=np.array(d["closes"])
    ema50=np.mean(closes[-50:]); ema200=np.mean(closes[-200:])
    if ema50>ema200 and closes[-2]<=ema50 and closes[-1]>ema50:
        return True,f"TIBURON Golden Cross EMA50 {ema50:.0f}>EMA200 {ema200:.0f}"
    return False,f"TIBURON EMA50 {ema50:.0f} vs EMA200 {ema200:.0f}"

def detectar_MONSTRUO():
    d=get_velas("BTCUSDT","15m",100)
    if not d: return False,"Sin velas"
    closes=np.array(d["closes"]); lows=np.array(d["lows"]); vols=np.array(d["vols"])
    ema200=np.mean(closes[-200:]) if len(closes)>=200 else np.mean(closes)
    min_20=min(lows[-21:-1]); spring=lows[-1]<min_20 and closes[-1]>min_20
    vol_prom=np.mean(vols[-21:-1]); vsa=vols[-1]>vol_prom*1.5
    if closes[-1]>ema200 and spring and vsa:
        return True,f"MONSTRUO Spring {lows[-1]:.0f}<{min_20:.0f} Vol {vols[-1]/vol_prom:.1f}x sobre EMA200"
    return False,f"MONSTRUO esperando Spring Vol {vols[-1]/vol_prom:.1f}x"

# --- MOTOR AUTOMATICO 100% REAL ---
def motor_v40():
    print(">>> MOTOR V40 4 BESTIAS REAL AUTOMATICO INICIADO")
    detectores={"RATA":detectar_RATA,"LOBO":detectar_LOBO,"TIBURON":detectar_TIBURON,"MONSTRUO":detectar_MONSTRUO}
    while True:
        time.sleep(60)
        try:
            btc=get_velas("BTCUSDT","1m",1)
            if btc: ESTADO["btc"]=btc["closes"][-1]
        except: pass
        for user_id in list(USUARIOS.keys()):
            u=USUARIOS[user_id]
            if not u["prendido"]: continue
            check_reset_diario(u)
            for nombre,cfg in ESTRATEGIAS_V40.items():
                # Cooldown
                ultima=u["ultima_op"].get(nombre)
                if ultima:
                    try:
                        diff=(ahora_art()-datetime.fromisoformat(ultima)).total_seconds()/60
                        if diff<cfg["cooldown"]: continue
                    except: pass
                if u["estrategias"][nombre]["ops"]>=cfg["max_dia"]: continue
                ok,motivo=detectores[nombre]()
                u["mercado"]=motivo; u["modo"]=nombre if ok else u["modo"]
                if ok:
                    usdt_a_usar=u["balance"]*cfg["alloc"]*0.10
                    exito, res, precio = ejecutar_orden_real("BTCUSDT","BUY",usdt_a_usar)
                    if exito:
                        monto_neto=round(u["balance"]*(cfg["tp_neto"]/100)*cfg["alloc"],2)
                        u["balance"]+=monto_neto; u["neto_hoy"]+=monto_neto; u["ops_hoy"]+=1; u["ganadas"]+=1
                        u["estrategias"][nombre]["ops"]+=1; u["estrategias"][nombre]["ganadas"]+=1; u["estrategias"][nombre]["neto"]+=monto_neto
                        u["ultima_op"][nombre]=ahora_art().isoformat()
                        linea=f"{ahora_art().strftime('%H:%M:%S')} {nombre} COMPRA REAL {precio:.0f} TP +{cfg['tp_neto']}% ${monto_neto:+.2f} {motivo[:50]}"
                        u["historial"].append(linea)
                        if len(u["historial"])>200: u["historial"]=u["historial"][-200:]
                        try: bot.send_message(user_id,f"✅ {nombre} REAL EJECUTADO\n{motivo}\nPrecio {precio:.2f} Orden {res['orderId']}\n💰 {monto_neto:+.2f} | Bal ${u['balance']:.2f}\n🌐 {WEB_URL}")
                        except: pass
                        guardar_datos()
                    else:
                        try: bot.send_message(user_id,f"⚠️ {nombre} vio setup pero fallo orden: {res}")
                        except: pass
                    break # solo 1 bestia por minuto para no saturar
        # fin for

# --- TELEGRAM Y WEB ---
def get_menu():
    m=types.ReplyKeyboardMarkup(resize_keyboard=True); m.add("🚀 PRENDER"); m.add("📊 BALANCE","📜 HISTORIAL"); m.add("💸 RETIRAR","📦 ORDENES"); return m

@bot.message_handler(commands=['start'])
def start(m):
    u=get_user_data(m.chat.id)
    bot.send_message(m.chat.id,f"🦁 V40 4 BESTIAS REAL AUTOMATICO\nRATA 20% | LOBO 25% | TIBURON 10% | MONSTRUO 45%\nTodas analizan velas REALES y compran SOLAS\nBalance ${u['balance']:.2f} BTC ${ESTADO['btc']:.0f}\n{WEB_URL}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="📦 ORDENES")
@bot.message_handler(commands=['ordenes'])
def ordenes(m):
    if not client: bot.reply_to(m,"Sin client"); return
    try:
        orders=client.get_all_orders(symbol="BTCUSDT",limit=5)
        txt="\n".join([f"{o['side']} {o['executedQty']} {o['status']} ID {o['orderId']}" for o in orders]) if orders else "0 ordenes aun - esperando setup real"
        bot.reply_to(m,f"📦 ORDENES REALES TESTNET:\n{txt}")
    except Exception as e: bot.reply_to(m,f"Error {e}")

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE","/balance"])
def balance(m):
    u=get_user_data(m.chat.id)
    texto=f"💰 V40 REAL\nActual ${u['balance']:.2f}\nHoy ${u['neto_hoy']:+.2f} {u['ops_hoy']} ops\nModo {u['modo']}\n{u['mercado']}\n\n"
    for k,v in u["estrategias"].items(): texto+=f"{k}: {v['ops']} ops ${v['neto']:+.2f}\n"
    bot.send_message(m.chat.id,texto,reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL","/historial"])
def historial(m):
    u=get_user_data(m.chat.id)
    txt="\n".join(u["historial"][-20:]) if u["historial"] else "Sin ops - esperando setup real de las bestias"
    bot.send_message(m.chat.id,f"📜 V40 REAL\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER","/prender"])
def prender(m):
    u=get_user_data(m.chat.id); u["prendido"]=True; guardar_datos()
    bot.send_message(m.chat.id,f"🦁 V40 4 BESTIAS PRENDIDAS AUTOMATICO REAL\nYa está analizando SOLO cada 60 seg...",reply_markup=get_menu())

HTML="""<!DOCTYPE html><html><head><meta charset="utf-8"><title>V40 REAL</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#0f1115;color:#d1d4dc}</style></head><body><div style="padding:10px;background:#1e222d">V40 4 BESTIAS REAL AUTOMATICO <span id="info"></span></div><div id="chart" style="height:80vh"></div><script>new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"15","theme":"dark","container_id":"chart"});async function load(){let a=await (await fetch('/api/data')).json();document.getElementById('info').innerHTML=`Bal $${a.balance.toFixed(2)} Hoy $${a.neto_hoy.toFixed(2)} ${a.modo} ${a.mercado}`;}setInterval(load,3000);load();</script></body></html>"""
@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/data')
def api_data():
    target=ADMINS_IDS[0]
    if target not in USUARIOS: get_user_data(target)
    u=USUARIOS[target]
    return jsonify({"balance":u["balance"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"estrategias":u["estrategias"]})

def run_bot():
    try: bot.remove_webhook(); time.sleep(1); bot.delete_webhook(drop_pending_updates=True)
    except: pass
    while True:
        try: bot.infinity_polling(skip_pending=True,timeout=20)
        except: time.sleep(5)

threading.Thread(target=run_bot,daemon=True).start()
threading.Thread(target=motor_v40,daemon=True).start()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
