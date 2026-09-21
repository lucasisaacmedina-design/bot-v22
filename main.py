import os, json, threading, time, requests, math
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
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

MONEDAS_ACTIVAS = ["BTCUSDT", "BNBUSDT"]
CANDIDATAS = ["ETHUSDT","SOLUSDT","XRPUSDT","AVAXUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","DOTUSDT","LTCUSDT","TRXUSDT","MATICUSDT","SHIBUSDT"]
ESTADO_RETIRO = {}
EVOLUCION_PROFIT_POR_MONEDA = 100.0

ESTRATEGIAS_V44 = {
    "RATA": {"tf": "5m", "desc": "RATA 5M", "rango_tp": (0.60, 0.90), "sl_neto": -0.35, "max_dia": 15, "cooldown": 5, "mercado_ideal": "LINEAL"},
    "LOBO": {"tf": "1h", "desc": "LOBO 1H", "rango_tp": (1.5, 3.5), "sl_neto": -1.20, "max_dia": 3, "cooldown": 60, "mercado_ideal": "ALCISTA"},
    "TIBURON": {"tf": "1d", "desc": "TIBURON 1D", "rango_tp": (4.0, 14.0), "sl_neto": -3.50, "max_dia": 10, "cooldown": 0, "mercado_ideal": "ALCISTA_FUERTE"},
    "MONSTRUO": {"tf": "1w", "desc": "MONSTRUO 1W", "rango_tp": (7.0, 18.0), "sl_neto": -5.0, "max_dia": 10, "cooldown": 0, "mercado_ideal": "CRASH"}
}

# === SOLO ESTO AGREGO ===
MAPA_ESTRATEGIA = {
    "LINEAL": "RATA 0.6-0.9%",
    "ALCISTA": "LOBO 1.5-3.5%",
    "ALCISTA_FUERTE": "TIBURON 4.0-14.0%",
    "CRASH": "MONSTRUO 7.0-18.0%",
    "BAJISTA": "MONSTRUO 7.0-18.0%"
}
def estrategia_prevista(regimen_txt):
    reg = regimen_txt.split()[0] if regimen_txt else "LINEAL"
    return MAPA_ESTRATEGIA.get(reg, "RATA 0.6-0.9%")

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

ESTADO={"btc":0,"bnb":0,"regimen":"LINEAL","regimen_detalle":"Iniciando","regimenes":{},"estrategias_activas":{}}
USUARIOS={}; LOCK=threading.Lock()
def ahora_art(): return datetime.now(TZ)

def get_velas(symbol="BTCUSDT", interval="5m", limit=200):
    try:
        klines=client.get_klines(symbol=symbol, interval=interval, limit=limit)
        return {"closes": [float(k[4]) for k in klines],"highs": [float(k[2]) for k in klines],"lows": [float(k[3]) for k in klines],"vols": [float(k[5]) for k in klines]}
    except: return None

def rsi_calc(closes, period=14):
    if len(closes) < period+1: return 50.0
    deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains = [d if d>0 else 0 for d in deltas[-period:]]
    losses = [-d if d<0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains)/period if gains else 0.01
    avg_loss = sum(losses)/period if losses else 0.01
    if avg_loss == 0: return 100.0
    rs = avg_gain/avg_loss
    return 100-(100/(1+rs))

def ejecutar_orden_real(symbol, side, usdt_amount):
    try:
        info = client.get_symbol_info(symbol)
        lot = [f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]
        step = float(lot['stepSize']); min_qty = float(lot['minQty'])
        precio = float(client.get_symbol_ticker(symbol=symbol)['price'])
        qty = usdt_amount / precio
        if step > 0:
            precision = int(round(-math.log10(step),0)) if step < 1 else 0
            qty = math.floor(qty / step) * step
            qty = round(qty, precision)
        if qty < min_qty: qty = min_qty
        order = client.create_order(symbol=symbol, side=side, type='MARKET', quantity=qty)
        return True, order, precio
    except Exception as e:
        return False, str(e)[:200], 0

def detectar_regimen_sym(symbol):
    d1h=get_velas(symbol,"1h",100); d1d=get_velas(symbol,"1d",15)
    if not d1h or not d1d: return "LINEAL", "Sin datos"
    closes_1h=d1h["closes"]; closes_1d=d1d["closes"]
    ema50=sum(closes_1h[-50:])/50; ema200=sum(closes_1h[-200:])/200 if len(closes_1h)>=200 else sum(closes_1h)/len(closes_1h)
    adx_sim = abs(ema50-ema200)/ema200*1000 if ema200!=0 else 0
    rent_14d = (closes_1d[-1]-closes_1d[0])/closes_1d[0] if closes_1d[0]!=0 else 0
    if adx_sim < 2.2 and abs(rent_14d) < 0.03: return "LINEAL", f"{rent_14d*100:+.1f}%"
    elif rent_14d < -0.12: return "CRASH", f"{rent_14d*100:.1f}%"
    elif rent_14d > 0.06 and closes_1h[-1] > ema50: return "ALCISTA_FUERTE", f"{rent_14d*100:+.1f}%"
    elif closes_1h[-1] > ema50: return "ALCISTA", f"{rent_14d*100:+.1f}%"
    else: return "BAJISTA", f"{rent_14d*100:+.1f}%"

def detectar_regimen_btc(): return detectar_regimen_sym("BTCUSDT")

def calcular_tp_inteligente(estrategia, fuerza):
    min_tp, max_tp = ESTRATEGIAS_V44[estrategia]["rango_tp"]
    fuerza_norm = max(0, min(1, (fuerza-0.3)/0.6))
    tp = min_tp + (max_tp - min_tp) * fuerza_norm
    return round(tp, 2)

def detectar_RATA_sym(symbol):
    d5=get_velas(symbol,"5m",100); d15=get_velas(symbol,"15m",100)
    if not d5 or not d15: return False,f"{symbol} Sin velas",0
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    sma20=sum(closes[-20:])/20; var=sum((x-sma20)**2 for x in closes[-20:])/20; std=var**0.5; lower=sma20-2*std
    precio=closes[-1]; vol_prom=sum(d5["vols"][-20:])/20; vol_actual=d5["vols"][-1]
    ema200_15=sum(d15["closes"][-200:])/200 if len(d15["closes"])>=200 else sum(d15["closes"])/len(d15["closes"])
    if precio<=lower and rsi<30 and vol_actual>vol_prom*1.5 and closes[-1]>ema200_15:
        return True,f"[{symbol}] RATA 5M Bollinger RSI{int(rsi)}", 0.68
    return False,f"[{symbol}] RATA esperando", 0.30

def detectar_LOBO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]; ema20=sum(closes[-20:])/20; ema50=sum(closes[-50:])/50
    ema12=sum(closes[-12:])/12; ema26=sum(closes[-26:])/26; macd=ema12-ema26
    adx_sim = abs(ema20-ema50)/ema50*1000 if ema50!=0 else 0
    retroceso = abs(closes[-1]-ema20)/ema20 < 0.015 if ema20!=0 else False
    if closes[-1]>ema20 and ema20>ema50 and macd>0 and adx_sim>2.2 and retroceso:
        return True,f"[{symbol}] LOBO 1H EMA20>EMA50 MACD {macd:.1f}", 0.65
    return False,f"[{symbol}] LOBO esperando", 0.35

def detectar_TIBURON_sym(symbol):
    d=get_velas(symbol,"1d",210)
    if not d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]; ema50=sum(closes[-50:])/50; ema200=sum(closes[-200:])/200 if len(closes)>=200 else sum(closes)/len(closes)
    rsi14=rsi_calc(closes,14); max_20=max(closes[-21:-1]) if len(closes)>=21 else closes[-1]
    if ema50>ema200 and rsi14>50 and closes[-1]>max_20:
        return True,f"[{symbol}] TIBURON 1D Golden RSI{int(rsi14)} Ruptura", 0.55
    return False,f"[{symbol}] TIBU esperando", 0.25

def detectar_MONSTRUO_sym(symbol):
    d=get_velas(symbol,"1w",100); d_d=get_velas(symbol,"1d",100)
    if not d or not d_d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]; lows=d["lows"]; vols=d["vols"]
    min_20=min(lows[-21:-1]) if len(lows)>=22 else min(lows)
    spring=lows[-1]<min_20 and closes[-1]>min_20
    vol_prom=sum(vols[-21:-1])/20 if len(vols)>=22 else sum(vols)/len(vols)
    vsa=vols[-1]>vol_prom*1.8 if vol_prom!=0 else False
    if spring and vsa:
        return True,f"[{symbol}] MONS 1W Spring Crash", 0.70
    return False,f"[{symbol}] MONS esperando", 0.08

def detectar_MULTI_V44(regimen):
    orden_prioridad = {
        "LINEAL": ["RATA","LOBO","TIBURON","MONSTRUO"],
        "ALCISTA": ["LOBO","RATA","TIBURON","MONSTRUO"],
        "ALCISTA_FUERTE": ["TIBURON","LOBO","MONSTRUO","RATA"],
        "CRASH": ["MONSTRUO","TIBURON","LOBO","RATA"],
        "BAJISTA": ["MONSTRUO","RATA","LOBO","TIBURON"]
    }
    prioridades = orden_prioridad.get(regimen, ["RATA","LOBO","TIBURON","MONSTRUO"])
    mejor_motivo=""; mejor_sym=""; mejor_fuerza=0; mejor_est=None
    for sym in MONEDAS_ACTIVAS:
        reg_sym = ESTADO.get("regimenes",{}).get(sym, regimen).split()[0]
        prio_sym = orden_prioridad.get(reg_sym, prioridades)
        for nombre in prio_sym:
            if nombre=="RATA": ok,motivo,wr = detectar_RATA_sym(sym)
            elif nombre=="LOBO": ok,motivo,wr = detectar_LOBO_sym(sym)
            elif nombre=="TIBURON": ok,motivo,wr = detectar_TIBURON_sym(sym)
            else: ok,motivo,wr = detectar_MONSTRUO_sym(sym)
            if ok:
                bonus = 0.25 if ESTRATEGIAS_V44[nombre]["mercado_ideal"]==reg_sym else 0
                fuerza_final = wr + bonus
                if fuerza_final > mejor_fuerza:
                    mejor_fuerza=fuerza_final; mejor_est=nombre; mejor_motivo=motivo; mejor_sym=sym
        if mejor_est and mejor_est==prioridades[0]: break
    if mejor_est:
        return True, mejor_motivo, mejor_sym, mejor_est, mejor_fuerza
    return False, f"V44 {regimen} - Esperando setup {prioridades[0]}", MONEDAS_ACTIVAS[0], None, 0

def analizar_top_rentable_14d():
    mejor=None; mejor_score=-99999
    for sym in [c for c in CANDIDATAS if c not in MONEDAS_ACTIVAS]:
        try:
            url=f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1d&limit=15"
            r=requests.get(url,timeout=10); klines=r.json()
            if not isinstance(klines,list) or len(klines)<14: continue
            closes=[float(k[4]) for k in klines]; lows=[float(k[3]) for k in klines]
            rent_14d=(closes[-1]-closes[0])/closes[0]*100
            springs=sum(1 for i in range(3,14) if lows[i]<min(lows[i-3:i-1]) and closes[i]>min(lows[i-3:i-1]))
            score=rent_14d*0.7+springs*3
            if score>mejor_score: mejor_score=score; mejor={"symbol":sym,"rent":rent_14d,"springs":springs,"score":score,"precio":closes[-1]}
        except: continue
    return mejor or {"symbol":"SOLUSDT","rent":12.5,"springs":2,"score":10.0,"precio":175.0}

def check_reset_diario(u):
    hoy=ahora_art().strftime("%Y-%m-%d")
    if u.get("fecha_hoy")!=hoy:
        u["fecha_hoy"]=hoy; u["neto_hoy"]=0.0; u["ops_hoy"]=0
        for k in u["estrategias"]: u["estrategias"][k]["ops"]=0

def get_user_data(uid):
    uid=int(uid)
    with LOCK:
        if uid not in USUARIOS:
            USUARIOS[uid]={"user_id":uid,"prendido":False,"balance":BALANCE_INICIAL,"capital_inicial":BALANCE_INICIAL,"neto_hoy":0.0,"ops_hoy":0,"ganadas":0,"perdidas":0,"modo":"ESPERANDO","mercado":"Tocá PRENDER","ultima_op":{}, "historial":[],"estrategias":{k:{"ops":0,"ganadas":0,"neto":0.0} for k in ESTRATEGIAS_V44},"fecha_hoy":ahora_art().strftime("%Y-%m-%d")}
        check_reset_diario(USUARIOS[uid]); return USUARIOS[uid]

def guardar_datos():
    try:
        with LOCK:
            with open(DATA_FILE,"w") as f: json.dump(USUARIOS,f,indent=2)
            with open(os.path.join(DATA_DIR,"monedas_activas.json"),"w") as f: json.dump(MONEDAS_ACTIVAS,f)
    except: pass

def cargar_datos():
    global MONEDAS_ACTIVAS
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,"r") as f:
                data=json.load(f)
                for k,v in data.items(): USUARIOS[int(k)]=v
        path=os.path.join(DATA_DIR,"monedas_activas.json")
        if os.path.exists(path):
            with open(path,"r") as f: MONEDAS_ACTIVAS=json.load(f)
    except: pass
cargar_datos()

def motor_v44():
    print(">>> MOTOR V44.1")
    time.sleep(5)
    while True:
        try:
            for sym in list(MONEDAS_ACTIVAS):
                reg, det = detectar_regimen_sym(sym)
                ESTADO["regimenes"][sym] = f"{reg} {det}"
                if sym=="BTCUSDT":
                    d=get_velas(sym,"1m",1)
                    if d: ESTADO["btc"]=d["closes"][-1]
                    ESTADO["regimen"]=reg; ESTADO["regimen_detalle"]=det
                if sym=="BNBUSDT":
                    d=get_velas(sym,"1m",1)
                    if d: ESTADO["bnb"]=d["closes"][-1]
        except: pass
        for user_id in list(USUARIOS.keys()):
            u=USUARIOS[user_id]
            if not u.get("prendido", False): continue
            check_reset_diario(u)
            ganancia_total = u["balance"] - u["capital_inicial"]
            monedas_desbloqueables = max(1, int(ganancia_total // EVOLUCION_PROFIT_POR_MONEDA) + 1)
            while len(MONEDAS_ACTIVAS) < monedas_desbloqueables and len(MONEDAS_ACTIVAS) < 8:
                mejor = analizar_top_rentable_14d()
                if mejor["symbol"] not in MONEDAS_ACTIVAS:
                    MONEDAS_ACTIVAS.append(mejor["symbol"])
                    try: bot.send_message(user_id, f"🧬 EVOLUCION: ${ganancia_total:.0f} profit\n✅ {mejor['symbol']} desbloqueada\nAhora: {'+'.join(MONEDAS_ACTIVAS)}")
                    except: pass
                    guardar_datos()
                else: break
            regimen_actual = ESTADO.get("regimen","LINEAL")
            ok,motivo,symbol_elegido,estrategia_elegida,fuerza = detectar_MULTI_V44(regimen_actual)
            if not ok:
                u["mercado"]=f"BTC {regimen_actual} - {motivo}"
                if u["modo"]=="ESPERANDO": u["modo"]="CAZANDO V44"
                continue
            if ok and estrategia_elegida:
                cfg=ESTRATEGIAS_V44[estrategia_elegida]
                tp_inteligente = calcular_tp_inteligente(estrategia_elegida, fuerza)
                ESTADO["estrategias_activas"][symbol_elegido] = f"{estrategia_elegida} {tp_inteligente}%"
                ultima=u["ultima_op"].get(estrategia_elegida)
                if ultima:
                    try:
                        diff=(ahora_art()-datetime.fromisoformat(ultima)).total_seconds()/60
                        if diff<cfg["cooldown"]: continue
                    except: pass
                if u["estrategias"][estrategia_elegida]["ops"]>=cfg["max_dia"]: continue
                reg_sym = ESTADO.get("regimenes",{}).get(symbol_elegido,"LINEAL").split()[0]
                alloc_map = {"LINEAL":0.5,"ALCISTA":0.35,"ALCISTA_FUERTE":0.6,"CRASH":0.7,"BAJISTA":0.3}
                alloc_real = alloc_map.get(reg_sym, 0.35)
                usdt_a_usar=u["balance"]*alloc_real*0.10
                exito, res, precio = ejecutar_orden_real(symbol_elegido,"BUY",usdt_a_usar)
                if exito:
                    monto_neto=round(u["balance"]*(tp_inteligente/100)*alloc_real,2)
                    u["balance"]+=monto_neto; u["neto_hoy"]+=monto_neto; u["ops_hoy"]+=1; u["ganadas"]+=1
                    u["estrategias"][estrategia_elegida]["ops"]+=1; u["estrategias"][estrategia_elegida]["ganadas"]+=1; u["estrategias"][estrategia_elegida]["neto"]+=monto_neto
                    u["ultima_op"][estrategia_elegida]=ahora_art().isoformat()
                    u["modo"]=f"{estrategia_elegida} {symbol_elegido} TP{tp_inteligente}%"; u["mercado"]=f"{motivo}"
                    linea=f"{ahora_art().strftime('%H:%M:%S')} {estrategia_elegida} {symbol_elegido} TP {tp_inteligente}% ${monto_neto:+.2f} {ESTADO['regimenes'].get(symbol_elegido,'')}"
                    u["historial"].append(linea)
                    if len(u["historial"])>200: u["historial"]=u["historial"][-200:]
                    try: bot.send_message(user_id,f"✅ V44 {estrategia_elegida} {symbol_elegido}\n{motivo}\nTP {tp_inteligente}% rango {cfg['rango_tp'][0]}-{cfg['rango_tp'][1]}%\n💰 ${monto_neto:+.2f} | Bal ${u['balance']:.2f}")
                    except: pass
        guardar_datos()
        time.sleep(60)

def get_menu():
    m=types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🚀 PRENDER","🧬 EVOLUCIONAR"); m.add("📊 BALANCE","📜 HISTORIAL"); m.add("💸 RETIRAR","📦 ORDENES")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    u=get_user_data(m.chat.id)
    estado_txt = "🟢 CAZANDO V44" if u["prendido"] else "🔴 APAGADO"
    regs=[]
    for k,v in ESTADO.get("regimenes",{}).items():
        regs.append(f"{k.replace('USDT','')}:{v} -> Usara {estrategia_prevista(v)}")
    regs_txt = "\n".join(regs) or f"BTC {ESTADO['regimen']} -> Usara {estrategia_prevista(ESTADO['regimen'])}"
    bot.send_message(m.chat.id,f"🦁 V44.1 SABIO {estado_txt}\n{regs_txt}\nMonedas: {'+'.join(MONEDAS_ACTIVAS)}\nBalance ${u['balance']:.2f}\n{WEB_URL}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="📦 ORDENES")
def ordenes(m):
    if not client: bot.reply_to(m,"Sin client"); return
    try:
        txt_total=""
        for sym in MONEDAS_ACTIVAS:
            try:
                orders=client.get_all_orders(symbol=sym,limit=3)
                if orders: txt_total+=f"\n{sym}:\n"+"\n".join([f"{o['side']} {o['executedQty']} {o['status']}" for o in orders[-2:]])
            except: pass
        if not txt_total: txt_total="0 ordenes"
        bot.reply_to(m,f"📦 ORDENES:\n{txt_total}")
    except Exception as e: bot.reply_to(m,f"Error {e}")

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE","/balance"])
def balance(m):
    u=get_user_data(m.chat.id)
    ganancia_total = u["balance"]-u["capital_inicial"]
    regs=[]
    for k,v in ESTADO.get("regimenes",{}).items():
        regs.append(f"{k}: {v} => Usara {estrategia_prevista(v)}")
    regs_txt = "\n".join(regs) or f"BTC {ESTADO.get('regimen','LINEAL')}"
    texto=f"💰 V44.1\n{regs_txt}\nMonedas: {'+'.join(MONEDAS_ACTIVAS)}\nBalance ${u['balance']:.2f} Ganancia ${ganancia_total:+.2f}\nHoy ${u['neto_hoy']:+.2f} {u['ops_hoy']} ops\nProxima en ${len(MONEDAS_ACTIVAS)*100} (faltan ${len(MONEDAS_ACTIVAS)*100-ganancia_total:.0f})\n"
    for k,v in u["estrategias"].items():
        rango=ESTRATEGIAS_V44[k]["rango_tp"]
        texto+=f"{k} {rango[0]}-{rango[1]}%: {v['ops']} ops ${v['neto']:+.2f}\n"
    bot.send_message(m.chat.id,texto,reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL","/historial"])
def historial(m):
    u=get_user_data(m.chat.id)
    txt="\n".join(u["historial"][-20:]) if u["historial"] else "Sin ops"
    bot.send_message(m.chat.id,f"📜 V44.1\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER","/prender"])
def prender(m):
    u=get_user_data(m.chat.id); u["prendido"]=True; u["modo"]="CAZANDO V44"
    guardar_datos()
    bot.send_message(m.chat.id,f"🦁 V44.1 PRENDIDO\n{'+'.join(MONEDAS_ACTIVAS)}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["⏸️ APAGAR","/apagar"])
def apagar(m):
    u=get_user_data(m.chat.id); u["prendido"]=False; u["modo"]="ESPERANDO"; guardar_datos()
    bot.send_message(m.chat.id,f"⏸️ V44 APAGADO",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="🧬 EVOLUCIONAR")
def evolucionar_manual(m):
    mejor = analizar_top_rentable_14d()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"✅ SI {mejor['symbol']}", callback_data=f"ADD_{mejor['symbol']}"))
    kb.add(types.InlineKeyboardButton("❌ NO", callback_data="NO_ADD"))
    bot.send_message(m.chat.id, f"🧬 {mejor['symbol']} Rent {mejor['rent']:+.1f}%", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text=="💸 RETIRAR")
def retirar_pedir(m):
    u=get_user_data(m.chat.id); ESTADO_RETIRO[m.chat.id]=True
    bot.send_message(m.chat.id,f"💸 RETIRO Bal ${u['balance']:.2f} Gan ${u['balance']-u['capital_inicial']:.2f}", reply_markup=get_menu())

@bot.message_handler(func=lambda m: ESTADO_RETIRO.get(m.chat.id) and m.text.replace('.','',1).replace('-','',1).isdigit())
def retirar_confirmar(m):
    u=get_user_data(m.chat.id)
    try:
        monto=float(m.text); ganancia=u["balance"]-u["capital_inicial"]
        if monto<=0 or monto>ganancia: bot.send_message(m.chat.id,f"❌ Solo ${ganancia:.2f}"); return
        u["balance"]-=monto; ESTADO_RETIRO[m.chat.id]=False; guardar_datos()
        bot.send_message(m.chat.id,f"✅ RETIRO ${monto:.2f}", reply_markup=get_menu())
    except Exception as e: bot.send_message(m.chat.id,f"Error {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    global MONEDAS_ACTIVAS
    if call.data.startswith("ADD_"):
        sym=call.data.replace("ADD_","")
        if sym not in MONEDAS_ACTIVAS:
            MONEDAS_ACTIVAS.append(sym); guardar_datos()
            bot.send_message(call.message.chat.id, f"✅ {sym} incorporada\nAhora: {'+'.join(MONEDAS_ACTIVAS)}", reply_markup=get_menu())
    elif call.data=="NO_ADD":
        bot.answer_callback_query(call.id, "No agregada")

@app.route('/')
def home():
    html = """
<!DOCTYPE html><html><head><meta charset="utf-8"><title>V44.1</title>
<script src="https://s3.tradingview.com/tv.js"></script>
<style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}
.card{background:#1e222d;padding:10px;margin:5px;border-radius:8px;display:inline-block;min-width:150px}
.label{color:#868993;font-size:11px}.val{color:#fff;font-size:13px;font-weight:bold}
.badge{color:#facc15}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px}
</style></head><body>
<div style="padding:10px;background:#1e222d;display:flex;flex-wrap:wrap">
  <div class="card"><div class="label">BALANCE INICIAL</div><div class="val" id="b_ini">$0</div></div>
  <div class="card"><div class="label">PROFIT HOY</div><div class="val" id="p_hoy">$0</div></div>
  <div class="card"><div class="label">BTC</div><div class="val" id="btc_reg">-</div></div>
  <div class="card"><div class="label">BNB</div><div class="val" id="bnb_reg">-</div></div>
  <div class="card"><div class="label">ESTRATEGIA ACTIVA</div><div class="val badge" id="strat">-</div></div>
  <div class="card"><div class="label">EVOLUCION $100</div><div class="val" id="evo">-</div></div>
</div>
<div class="grid">
  <div><div style="background:#1e293b;padding:6px;font-size:12px" id="btc_title">BTCUSDT</div><div id="chart_BTCUSDT" style="height:70vh"></div></div>
  <div><div style="background:#1e293b;padding:6px;font-size:12px" id="bnb_title">BNBUSDT</div><div id="chart_BNBUSDT" style="height:70vh"></div></div>
</div>
<script>
function estrat(reg){
  if(!reg) return 'RATA 0.6-0.9%';
  if(reg.includes('ALCISTA_FUERTE')) return 'TIBURON 4.0-14.0%';
  if(reg.includes('ALCISTA')) return 'LOBO 1.5-3.5%';
  if(reg.includes('CRASH')||reg.includes('BAJISTA')) return 'MONSTRUO 7.0-18.0%';
  return 'RATA 0.6-0.9%';
}
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"15","timezone":"America/Argentina/Buenos_Aires","theme":"dark","container_id":"chart_BTCUSDT"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"15","timezone":"America/Argentina/Buenos_Aires","theme":"dark","container_id":"chart_BNBUSDT"});
async function load(){
  let a=await (await fetch('/api/data')).json();
  document.getElementById('b_ini').innerHTML='$'+a.capital_inicial.toFixed(0);
  let s=a.neto_hoy>=0?'+':'';
  document.getElementById('p_hoy').innerHTML='$'+s+a.neto_hoy.toFixed(2);
  document.getElementById('p_hoy').style.color=a.neto_hoy>=0?'#22c55e':'#ef4444';
  let btcR = a.regimenes['BTCUSDT']||a.regimen_btc;
  let bnbR = a.regimenes['BNBUSDT']||'';
  document.getElementById('btc_reg').innerHTML=btcR+' <span class=badge>-> '+estrat(btcR)+'</span>';
  document.getElementById('bnb_reg').innerHTML=bnbR+' <span class=badge>-> '+estrat(bnbR)+'</span>';
  document.getElementById('strat').innerHTML=a.modo;
  document.getElementById('btc_title').innerHTML='BTCUSDT - '+btcR+' -> Usara '+estrat(btcR)+' | Activa '+(a.estrategias_activas['BTCUSDT']||a.modo);
  document.getElementById('bnb_title').innerHTML='BNBUSDT - '+bnbR+' -> Usara '+estrat(bnbR)+' | Activa '+(a.estrategias_activas['BNBUSDT']||'');
  document.getElementById('evo').innerHTML=a.monedas.join('+')+' | $'+a.ganancia_total.toFixed(0)+'/'+(a.monedas.length*100);
}
setInterval(load,3000);load();
</script></body></html>
"""
    return render_template_string(html)

@app.route('/api/data')
def api_data():
    target=ADMINS_IDS[0]
    if target not in USUARIOS: get_user_data(target)
    u=USUARIOS[target]
    return jsonify({"balance":u["balance"],"capital_inicial":u["capital_inicial"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"regimen_btc":ESTADO.get("regimen","LINEAL"),"regimenes":ESTADO.get("regimenes",{"BTCUSDT":ESTADO.get("regimen","LINEAL"),"BNBUSDT":"LINEAL"}),"estrategias_activas":ESTADO.get("estrategias_activas",{}),"estrategias":u["estrategias"],"monedas":MONEDAS_ACTIVAS,"ganancia_total": u["balance"]-u["capital_inicial"]})

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e: print(f"Webhook error {e}")
    return "ok", 200

@app.route('/set_webhook')
def set_webhook_route():
    try:
        bot.remove_webhook(); time.sleep(1)
        bot.set_webhook(url=f"{WEB_URL}/{TOKEN}")
        return f"Webhook OK {WEB_URL}/{TOKEN}", 200
    except Exception as e: return f"Error {e}", 500

threading.Thread(target=motor_v44,daemon=True).start()

if __name__=='__main__':
    try:
        bot.remove_webhook(); time.sleep(1)
        bot.set_webhook(url=f"{WEB_URL}/{TOKEN}")
    except Exception as e: print(f"Webhook error {e}")
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
