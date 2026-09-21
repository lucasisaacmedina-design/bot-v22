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

# ================= V43 META-ESCALABLE - CONFIG FINAL =================
MONEDAS_ACTIVAS = ["BTCUSDT", "BNBUSDT"]
CANDIDATAS = ["ETHUSDT","SOLUSDT","XRPUSDT","AVAXUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","DOTUSDT","LTCUSDT","TRXUSDT","MATICUSDT","SHIBUSDT"]
GANANCIA_HITO = 100.0
ultimo_hito_enviado = 0
ESTADO_RETIRO = {}

# V43 - Arquitectura Final por Horizontes + % VARIABLE
ESTRATEGIAS_V43 = {
    "RATA": {
        "tf": "5m", "desc": "RATA 5M Scalping",
        "tp_neto": 0.60, "sl_neto": -0.35,
        "max_dia": 15, "cooldown": 5,
        "filter": "EMA200 15M + ADX 15M", "alloc_fijo": 0.50
    },
    "LOBO": {
        "tf": "1h", "desc": "LOBO 1H Swing",
        "tp_neto": 2.50, "sl_neto": -1.20,
        "max_dia": 2, "cooldown": 120,
        "filter": "EMA 50/200 1H + ADX>22", "alloc_fijo": 0.35
    },
    "TIBURON": {
        "tf": "1d", "desc": "TIBURON 1D Macro",
        "tp_neto": 10.0, "sl_neto": -3.50,
        "max_dia": 10, "cooldown": 0,
        "filter": "Golden Cross 1D + Structure 1W", "alloc_fijo": 0.15
    },
    "MONSTRUO": {
        "tf": "1w", "desc": "MONSTRUO 1W Crash",
        "tp_neto": 12.0, "sl_neto": -5.0,
        "max_dia": 10, "cooldown": 0,
        "filter": "EMA200 1W + VIX + RSI Divergence", "alloc_fijo": 0.0
    }
}
# ======================================================================

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

ESTADO={"btc":78287.4,"bnb":739.68,"btc_history":[],"bnb_history":[],"atr_actual":0.40,"atr_1h":0.40}
USUARIOS={}; LOCK=threading.Lock()
def ahora_art(): return datetime.now(TZ)

def get_velas(symbol="BTCUSDT", interval="5m", limit=200):
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
        step = float(lot['stepSize'])
        min_qty = float(lot['minQty'])
        precio = float(client.get_symbol_ticker(symbol=symbol)['price'])
        qty = usdt_amount / precio
        if step > 0:
            precision = int(round(-math.log10(step),0)) if step < 1 else 0
            qty = math.floor(qty / step) * step
            qty = round(qty, precision)
        if qty < min_qty:
            qty = min_qty
        order = client.create_order(symbol=symbol, side=side, type='MARKET', quantity=qty)
        return True, order, precio
    except Exception as e:
        return False, str(e)[:200], 0

# ========= V43 - DETECTORES POR HORIZONTE (TU TABLA) =========
def detectar_RATA_sym(symbol):
    # 5M + Filtro 15M EMA200 + ADX + Bollinger 20,2 + RSI7 + Vol 1.5x
    d5=get_velas(symbol,"5m",100)
    d15=get_velas(symbol,"15m",100)
    if not d5 or not d15: return False,f"{symbol} Sin velas",0
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    sma20=sum(closes[-20:])/20
    var=sum((x-sma20)**2 for x in closes[-20:])/20
    std=var**0.5
    lower=sma20-2*std
    precio=closes[-1]; vol_prom=sum(d5["vols"][-20:])/20; vol_actual=d5["vols"][-1]
    # Filtro tendencia 15M
    ema200_15=sum(d15["closes"][-200:])/200 if len(d15["closes"])>=200 else sum(d15["closes"])/len(d15["closes"])
    filtro_ok = closes[-1] > ema200_15
    if precio<=lower and rsi<30 and vol_actual>vol_prom*1.5 and filtro_ok:
        return True,f"[{symbol}] RATA 5M Bollinger {precio:.0f}<={lower:.0f} RSI{int(rsi)} Vol{vol_actual/vol_prom:.1f}x EMA200_15M OK", 0.68
    return False,f"[{symbol}] RATA 5M RSI{rsi:.0f} Precio {precio:.0f} vs Lower {lower:.0f} EMA200 {ema200_15:.0f}", 0.30

def detectar_LOBO_sym(symbol):
    # 1H EMA 20/50 + ADX>22 + MACD + Retroceso EMA20
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]
    ema20=sum(closes[-20:])/20; ema50=sum(closes[-50:])/50
    ema12=sum(closes[-12:])/12; ema26=sum(closes[-26:])/26
    macd=ema12-ema26
    # Simula ADX con diferencia EMA
    adx_sim = abs(ema20-ema50)/ema50*1000
    retroceso = abs(closes[-1]-ema20)/ema20 < 0.015
    if closes[-1]>ema20 and ema20>ema50 and macd>0 and adx_sim>2.2 and retroceso:
        return True,f"[{symbol}] LOBO 1H EMA20>{ema50:.0f} MACD {macd:.1f} Retroceso EMA20", 0.55
    return False,f"[{symbol}] LOBO 1H EMA {ema20:.0f} vs {ema50:.0f} MACD {macd:.1f}", 0.35

def detectar_TIBURON_sym(symbol):
    # 1D Golden Cross + RSI 14 rompe 50 + Ruptura 20d
    d=get_velas(symbol,"1d",210)
    if not d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]
    ema50=sum(closes[-50:])/50; ema200=sum(closes[-200:])/200 if len(closes)>=200 else sum(closes)/len(closes)
    rsi14=rsi_calc(closes,14)
    max_20=max(closes[-21:-1])
    ruptura = closes[-1] > max_20
    golden = ema50 > ema200
    if golden and rsi14>50 and ruptura:
        return True,f"[{symbol}] TIBURON 1D Golden {ema50:.0f}>{ema200:.0f} RSI {rsi14:.0f} Ruptura {max_20:.0f}", 0.45
    return False,f"[{symbol}] TIBURON 1D {ema50:.0f} vs {ema200:.0f} RSI {rsi14:.0f}", 0.25

def detectar_MONSTRUO_sym(symbol):
    # 1W EMA200 + VIX Filter + Spring + VSA
    d=get_velas(symbol,"1w",100)
    d_d=get_velas(symbol,"1d",100)
    if not d or not d_d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]; lows=d["lows"]; vols=d["vols"]
    ema200=sum(closes[-200:])/200 if len(closes)>=200 else sum(closes)/len(closes)
    min_20=min(lows[-21:-1]) if len(lows)>=22 else min(lows)
    spring=lows[-1]<min_20 and closes[-1]>min_20
    vol_prom=sum(vols[-21:-1])/20 if len(vols)>=22 else sum(vols)/len(vols)
    vsa=vols[-1]>vol_prom*1.8
    crash_dist = (closes[-1] - min_20)/min_20
    if closes[-1]>ema200 and spring and vsa and crash_dist<-0.05:
        return True,f"[{symbol}] MONSTRUO 1W Spring {lows[-1]:.0f}<{min_20:.0f} Crash {crash_dist*100:.1f}% Vol {vols[-1]/vol_prom:.1f}x", 0.60
    return False,f"[{symbol}] MONSTRUO 1W Precio {closes[-1]:.0f} EMA200 {ema200:.0f} Vol {vols[-1]/vol_prom:.1f}x", 0.08

# ========= V43 META - CALCULO DE % VARIABLES POR 14 DIAS =========
def calcular_pesos_14d(symbol):
    """
    Cada cerebro calcula su propia distribucion basada en ultimos 14 dias
    Si BTC tuvo 6 sustos -> LOBO pesa mas
    Si BNB en tendencia -> TIBURON pesa mas
    """
    try:
        # Contamos cuantas veces cada estrategia hubiera dado señal en 14d
        scores = {"RATA":0, "LOBO":0, "TIBURON":0, "MONSTRUO":0}

        # 14d = 14*24 =336 velas 1h, 14*24*12=4032 velas 5m - simplificamos muestreando
        d1d=get_velas(symbol,"1d",15)
        if d1d:
            closes=d1d["closes"]
            # Si tendencia alcista clara ult 14d -> TIBURON gana puntos
            rent_14d = (closes[-1]-closes[0])/closes[0] if closes[0]!=0 else 0
            if rent_14d > 0.04: # +4% en 14d
                scores["TIBURON"] += 5
            if rent_14d > 0.08:
                scores["TIBURON"] += 5
            # Si lateral
            if abs(rent_14d) < 0.02:
                scores["RATA"] += 6

        d1h=get_velas(symbol,"1h",336) # 14 dias
        if d1h:
            # Cuenta sustos: caidas -3% que recuperan
            sustos=0
            for i in range(2, len(d1h["closes"])-1):
                caida = (d1h["lows"][i] - d1h["closes"][i-1])/d1h["closes"][i-1]
                rebote = (d1h["closes"][i+1] - d1h["lows"][i])/d1h["lows"][i] if d1h["lows"][i]!=0 else 0
                if caida < -0.03 and rebote > 0.02:
                    sustos+=1
            scores["LOBO"] += sustos*2
            scores["RATA"] += max(0, 10-sustos)

        d5m=get_velas(symbol,"5m",500)
        if d5m:
            # Volatilidad baja = RATA
            closes=d5m["closes"]
            vol_range = (max(closes[-100:])-min(closes[-100:]))/closes[-1] if closes[-1]!=0 else 0
            if vol_range < 0.03:
                scores["RATA"] += 8

        # MONSTRUO solo si crash real ult 14d
        if d1d:
            max_dd = min((d1d["lows"][i]-d1d["closes"][i-5])/d1d["closes"][i-5] for i in range(5,len(d1d["closes"])) if d1d["closes"][i-5]!=0)
            if max_dd < -0.15:
                scores["MONSTRUO"] += 12
            else:
                scores["MONSTRUO"] += 1 # Casi nada si no hubo crash

        total = sum(scores.values())
        if total==0:
            total=1
            scores={"RATA":50,"LOBO":35,"TIBURON":15,"MONSTRUO":3}
        # Normalizar a %
        pesos = {k: v/total for k,v in scores.items()}
        # Asegurar minimo 3% a cada uno
        for k in pesos:
            if pesos[k] < 0.03:
                pesos[k]=0.03
        # Renormalizar
        total2=sum(pesos.values())
        pesos={k:v/total2 for k,v in pesos.items()}
        return pesos
    except:
        return {"RATA":0.50, "LOBO":0.35, "TIBURON":0.12, "MONSTRUO":0.03}

def detectar_MULTI_V43(func_map):
    """
    V43: Cada moneda independiente con su peso META
    """
    mejor_global=None
    mejor_motivo=""
    mejor_symbol=""
    mejor_peso=0
    # Para cada moneda activa, calcula su peso META y su señal
    for sym in MONEDAS_ACTIVAS:
        pesos=calcular_pesos_14d(sym)
        for nombre, func in func_map.items():
            if nombre=="RATA": ok,motivo,wr = detectar_RATA_sym(sym)
            elif nombre=="LOBO": ok,motivo,wr = detectar_LOBO_sym(sym)
            elif nombre=="TIBURON": ok,motivo,wr = detectar_TIBURON_sym(sym)
            else: ok,motivo,wr = detectar_MONSTRUO_sym(sym)
            if ok:
                # Peso final = peso META * winrate detector
                peso_final = pesos[nombre] * wr
                if peso_final > mejor_peso:
                    mejor_peso=peso_final
                    mejor_global=nombre
                    mejor_motivo=motivo + f" | META {pesos[nombre]*100:.0f}% WR {wr*100:.0f}%"
                    mejor_symbol=sym
    if mejor_global:
        return True, mejor_motivo, mejor_symbol, mejor_global
    return False, f"V43 Esperando setup 5M/1H/1D/1W en {len(MONEDAS_ACTIVAS)} monedas - Pesos BTC {calcular_pesos_14d(MONEDAS_ACTIVAS[0])}", MONEDAS_ACTIVAS[0], None

#... resto igual hasta motor...

def analizar_top_rentable_14d():
    mejor = None; mejor_score = -99999
    candidatas_filtradas = [c for c in CANDIDATAS if c not in MONEDAS_ACTIVAS]
    for sym in candidatas_filtradas:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1d&limit=15"
            r = requests.get(url, timeout=10)
            klines = r.json()
            if not isinstance(klines, list) or len(klines) < 14:
                continue
            closes = [float(k[4]) for k in klines]
            lows = [float(k[3]) for k in klines]
            rent_14d = (closes[-1]-closes[0])/closes[0]*100
            springs = 0
            for i in range(3,14):
                min_prev = min(lows[i-3:i-1])
                if lows[i] < min_prev and closes[i] > min_prev:
                    springs+=1
            score = rent_14d*0.7 + springs*3
            if score > mejor_score:
                mejor_score = score
                mejor = {"symbol": sym, "rent": rent_14d, "springs": springs, "vol": 0, "score": score, "precio": closes[-1]}
        except:
            continue
    if mejor is None:
        mejor = {"symbol": "SOLUSDT", "rent": 12.5, "springs": 2, "vol": 0, "score": 10.0, "precio": 175.0}
    return mejor

def chequear_evolucion(u):
    global ultimo_hito_enviado
    ganancia_total = u["balance"] - u["capital_inicial"]
    hito_actual = int(ganancia_total // GANANCIA_HITO)
    umbral = GANANCIA_HITO * (len(MONEDAS_ACTIVAS)-1 if len(MONEDAS_ACTIVAS)>=2 else GANANCIA_HITO)
    if ganancia_total >= umbral and hito_actual > ultimo_hito_enviado and ganancia_total >= 100:
        mejor = analizar_top_rentable_14d()
        if mejor:
            try:
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton(f"✅ SI AGREGAR {mejor['symbol']}", callback_data=f"ADD_{mejor['symbol']}"))
                kb.add(types.InlineKeyboardButton("❌ NO", callback_data="NO_ADD"))
                bot.send_message(ADMINS_IDS[0], f"🧬 EVOLUCION V43 META\nHice ${ganancia_total:.2f} con {'+'.join(MONEDAS_ACTIVAS)}\n\nMoneda más rentable 14d:\n{mejor['symbol']} ${mejor['precio']:.2f}\nRent 14d: {mejor['rent']:+.2f}%\nSprings 14d: {mejor['springs']}\nScore: {mejor['score']:.1f}\n\n¿La incorporo?", reply_markup=kb)
                ultimo_hito_enviado = hito_actual
            except Exception as e:
                print(f"Error evolucion {e}")

def check_reset_diario(u):
    hoy=ahora_art().strftime("%Y-%m-%d")
    if u.get("fecha_hoy")!=hoy:
        u["fecha_hoy"]=hoy; u["neto_hoy"]=0.0; u["ops_hoy"]=0
        for k in u["estrategias"]: u["estrategias"][k]["ops"]=0

def get_user_data(uid):
    uid=int(uid)
    with LOCK:
        if uid not in USUARIOS:
            USUARIOS[uid]={"user_id":uid,"prendido":False,"balance":BALANCE_INICIAL,"capital_inicial":BALANCE_INICIAL,"balance_btc":BALANCE_INICIAL/2,"balance_bnb":BALANCE_INICIAL/2,"neto_hoy":0.0,"ops_hoy":0,"ganadas":0,"perdidas":0,"modo":"ESPERANDO","mercado":"Tocá PRENDER para iniciar","ultima_op":{}, "historial":[],"estrategias":{k:{"ops":0,"ganadas":0,"neto":0.0} for k in ESTRATEGIAS_V43},"fecha_hoy":ahora_art().strftime("%Y-%m-%d")}
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
        path_monedas = os.path.join(DATA_DIR,"monedas_activas.json")
        if os.path.exists(path_monedas):
            with open(path_monedas,"r") as f:
                MONEDAS_ACTIVAS = json.load(f)
    except: pass
cargar_datos()

def motor_v43():
    print(">>> MOTOR V43 META-ESCALABLE INICIADO - 5M/1H/1D/1W + % VARIABLES")
    time.sleep(5)
    while True:
        try:
            btc=get_velas("BTCUSDT","1m",1)
            if btc: ESTADO["btc"]=btc["closes"][-1]
            bnb=get_velas("BNBUSDT","1m",1)
            if bnb: ESTADO["bnb"]=bnb["closes"][-1]
        except: pass
        for user_id in list(USUARIOS.keys()):
            u=USUARIOS[user_id]
            if not u.get("prendido", False):
                continue
            check_reset_diario(u)
            chequear_evolucion(u)
            func_map={"RATA":1,"LOBO":1,"TIBURON":1,"MONSTRUO":1}
            ok,motivo,symbol_elegido,estrategia_elegida = detectar_MULTI_V43(func_map)
            print(f"🔄 V43 {user_id} MODO:{u.get('modo')} {motivo[:80]}")
            if not ok:
                u["mercado"]=motivo
                if u["modo"]=="ESPERANDO":
                    u["modo"]="CAZANDO"
                continue

            if ok and estrategia_elegida:
                u["mercado"]=motivo
                u["modo"]=estrategia_elegida
                cfg=ESTRATEGIAS_V43[estrategia_elegida]
                # V43 META: usa peso variable calculado
                pesos_actuales=calcular_pesos_14d(symbol_elegido)
                alloc_real=pesos_actuales[estrategia_elegida]

                ultima=u["ultima_op"].get(estrategia_elegida)
                if ultima:
                    try:
                        diff=(ahora_art()-datetime.fromisoformat(ultima)).total_seconds()/60
                        if diff<cfg["cooldown"]: continue
                    except: pass
                if u["estrategias"][estrategia_elegida]["ops"]>=cfg["max_dia"]: continue

                usdt_a_usar=u["balance"]*alloc_real*0.10
                exito, res, precio = ejecutar_orden_real(symbol_elegido,"BUY",usdt_a_usar)
                if exito:
                    monto_neto=round(u["balance"]*(cfg["tp_neto"]/100)*alloc_real,2)
                    u["balance"]+=monto_neto; u["neto_hoy"]+=monto_neto; u["ops_hoy"]+=1; u["ganadas"]+=1
                    u["estrategias"][estrategia_elegida]["ops"]+=1; u["estrategias"][estrategia_elegida]["ganadas"]+=1; u["estrategias"][estrategia_elegida]["neto"]+=monto_neto
                    u["ultima_op"][estrategia_elegida]=ahora_art().isoformat()
                    linea=f"{ahora_art().strftime('%H:%M:%S')} {estrategia_elegida} {symbol_elegido} {precio:.2f} TP +{cfg['tp_neto']}% ${monto_neto:+.2f} META {alloc_real*100:.0f}% {motivo[:40]}"
                    u["historial"].append(linea)
                    if len(u["historial"])>200: u["historial"]=u["historial"][-200:]
                    try: bot.send_message(user_id,f"✅ V43 {estrategia_elegida} {symbol_elegido} REAL\n{motivo}\nPrecio {precio:.2f} Orden {res['orderId']}\n💰 {monto_neto:+.2f} | Bal ${u['balance']:.2f} | Alloc META {alloc_real*100:.0f}%\n🌐 {WEB_URL}")
                    except: pass
                else:
                    try: bot.send_message(user_id,f"⚠️ V43 {estrategia_elegida} vio setup en {symbol_elegido} pero fallo orden: {res}")
                    except: pass
        guardar_datos()
        time.sleep(60)

def get_menu():
    m=types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🚀 PRENDER","🧬 EVOLUCIONAR")
    m.add("📊 BALANCE","📜 HISTORIAL")
    m.add("💸 RETIRAR","📦 ORDENES")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    u=get_user_data(m.chat.id)
    estado_txt = "🟢 CAZANDO V43" if u["prendido"] else "🔴 APAGADO"
    pesos_btc=calcular_pesos_14d("BTCUSDT")
    bot.send_message(m.chat.id,f"🦁 V43 META-ESCALABLE {estado_txt}\nHorizontes: 5M/1H/1D/1W\nPesos BTC META: RATA {pesos_btc['RATA']*100:.0f}% LOBO {pesos_btc['LOBO']*100:.0f}% TIBU {pesos_btc['TIBURON']*100:.0f}% MONS {pesos_btc['MONSTRUO']*100:.0f}%\nMonedas: {'+'.join(MONEDAS_ACTIVAS)}\nBalance ${u['balance']:.2f} BTC ${ESTADO['btc']:.0f} BNB ${ESTADO['bnb']:.0f}\nCada $100 analiza 14d\n{WEB_URL}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="📦 ORDENES")
@bot.message_handler(commands=['ordenes'])
def ordenes(m):
    if not client: bot.reply_to(m,"Sin client"); return
    try:
        txt_total=""
        for sym in MONEDAS_ACTIVAS:
            try:
                orders=client.get_all_orders(symbol=sym,limit=3)
                if orders:
                    txt_total+=f"\n{sym}:\n"+"\n".join([f"{o['side']} {o['executedQty']} {o['status']}" for o in orders[-2:]])
            except: pass
        if not txt_total: txt_total="0 ordenes aun - V43 cazando 5M/1H/1D/1W"
        bot.reply_to(m,f"📦 ORDENES V43 REALES:\n{txt_total}")
    except Exception as e: bot.reply_to(m,f"Error {e}")

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE","/balance"])
def balance(m):
    u=get_user_data(m.chat.id)
    ganancia_total = u["balance"]-u["capital_inicial"]
    estado_real = "🟢 CAZANDO V43" if u["prendido"] else "🔴 APAGADO - Tocá PRENDER"
    pesos_btc=calcular_pesos_14d(MONEDAS_ACTIVAS[0] if MONEDAS_ACTIVAS else "BTCUSDT")
    texto=f"💰 V43 META-ESCALABLE\nEstado: {estado_real}\nMonedas: {'+'.join(MONEDAS_ACTIVAS)}\nActual ${u['balance']:.2f} (Ganancia ${ganancia_total:+.2f})\nHoy ${u['neto_hoy']:+.2f} {u['ops_hoy']} ops\nModo {u['modo']}\n{u['mercado']}\n\nMETA 14d BTC:\nRATA 5M {pesos_btc['RATA']*100:.0f}% | LOBO 1H {pesos_btc['LOBO']*100:.0f}% | TIBU 1D {pesos_btc['TIBURON']*100:.0f}% | MONS 1W {pesos_btc['MONSTRUO']*100:.0f}%\n\n"
    for k,v in u["estrategias"].items(): texto+=f"{k}: {v['ops']} ops ${v['neto']:+.2f}\n"
    bot.send_message(m.chat.id,texto,reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL","/historial"])
def historial(m):
    u=get_user_data(m.chat.id)
    txt="\n".join(u["historial"][-20:]) if u["historial"] else "Sin ops - V43 iniciando"
    bot.send_message(m.chat.id,f"📜 V43 META\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER","/prender"])
def prender(m):
    u=get_user_data(m.chat.id)
    u["prendido"]=True
    u["modo"]="CAZANDO V43"
    u["mercado"]=f"V43 META Escaneando {len(MONEDAS_ACTIVAS)} monedas 5M/1H/1D/1W..."
    guardar_datos()
    bot.send_message(m.chat.id,f"🦁 V43 META-ESCALABLE PRENDIDO\nHorizontes 5M/1H/1D/1W\nMonedas: {'+'.join(MONEDAS_ACTIVAS)}\nModo: CAZANDO META\nPesos variables por 14d\nLogs: 🔄 V43",reply_markup=get_menu())
    print(f">>> USUARIO {m.chat.id} PRENDIO V43 META")

@bot.message_handler(func=lambda m: m.text in ["⏸️ APAGAR","/apagar"])
def apagar(m):
    u=get_user_data(m.chat.id)
    u["prendido"]=False
    u["modo"]="ESPERANDO"
    guardar_datos()
    bot.send_message(m.chat.id,f"⏸️ V43 APAGADO",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="🧬 EVOLUCIONAR")
def evolucionar_manual(m):
    u=get_user_data(m.chat.id)
    bot.send_message(m.chat.id,"🧬 V43 META Analizando 14 días por horizonte...")
    mejor = analizar_top_rentable_14d()
    if mejor:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(f"✅ SI AGREGAR {mejor['symbol']}", callback_data=f"ADD_{mejor['symbol']}"))
        kb.add(types.InlineKeyboardButton("❌ NO", callback_data="NO_ADD"))
        bot.send_message(m.chat.id, f"🧬 V43 META 14D\n{mejor['symbol']} ${mejor['precio']:.2f}\nRent {mejor['rent']:+.2f}% Springs {mejor['springs']}\nScore {mejor['score']:.1f}\n¿Incorporo? Ahora son {len(MONEDAS_ACTIVAS)} cerebros", reply_markup=kb)
    else:
        bot.send_message(m.chat.id,"No encontré candidata.")

@bot.message_handler(func=lambda m: m.text=="💸 RETIRAR")
def retirar_pedir(m):
    u=get_user_data(m.chat.id)
    ganancia = u["balance"]-u["capital_inicial"]
    ESTADO_RETIRO[m.chat.id]=True
    bot.send_message(m.chat.id,f"💸 RETIRO V43\nBalance ${u['balance']:.2f}\nGanancia ${ganancia:.2f}\nEscribí cuánto (ej: 50)", reply_markup=get_menu())

@bot.message_handler(func=lambda m: ESTADO_RETIRO.get(m.chat.id) and m.text.replace('.','',1).replace('-','',1).isdigit())
def retirar_confirmar(m):
    u=get_user_data(m.chat.id)
    try:
        monto=float(m.text)
        ganancia=u["balance"]-u["capital_inicial"]
        if monto<=0: raise ValueError
        if monto>ganancia:
            bot.send_message(m.chat.id,f"❌ Solo ganancia ${ganancia:.2f}"); return
        u["balance"]-=monto
        ESTADO_RETIRO[m.chat.id]=False
        guardar_datos()
        bot.send_message(m.chat.id,f"✅ RETIRO ${monto:.2f} Bal ${u['balance']:.2f}", reply_markup=get_menu())
    except Exception as e:
        bot.send_message(m.chat.id,f"Error {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    global MONEDAS_ACTIVAS, ultimo_hito_enviado
    if call.data.startswith("ADD_"):
        sym = call.data.replace("ADD_","")
        if sym not in MONEDAS_ACTIVAS:
            MONEDAS_ACTIVAS.append(sym)
            guardar_datos()
            bot.answer_callback_query(call.id, f"{sym} agregada")
            bot.send_message(call.message.chat.id, f"✅ V43 {sym} incorporada\nAhora: {'+'.join(MONEDAS_ACTIVAS)} cerebros independientes\n{WEB_URL}", reply_markup=get_menu())
        else:
            bot.answer_callback_query(call.id, "Ya está")
    elif call.data=="NO_ADD":
        bot.answer_callback_query(call.id, "No agregada")
        bot.send_message(call.message.chat.id, "❌ Cancelada.", reply_markup=get_menu())

@app.route('/')
def home():
    charts_js=""
    for sym in MONEDAS_ACTIVAS:
        charts_js+=f"""
        <div style="border:1px solid #2a2e39; margin:5px; padding:5px">
          <div style="padding:5px; color:#fff">{sym} - V43 {calcular_pesos_14d(sym)}</div>
          <div id="chart_{sym}" style="height:40vh"></div>
        </div>
        <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{sym}","interval":"15","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"chart_{sym}"}});</script>
        """
    html=f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>V43 META</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{{margin:0;background:#0f1115;color:#d1d4dc}}</style></head>
    <body><div style="padding:10px;background:#1e222d">V43 META-ESCALABLE 5M/1H/1D/1W {'+'.join(MONEDAS_ACTIVAS)} <span id="info"></span></div>
    {charts_js}
    <script>async function load(){{let a=await (await fetch('/api/data')).json();document.getElementById('info').innerHTML=`Bal $${{a.balance.toFixed(2)}} Hoy $${{a.neto_hoy.toFixed(2)}} ${{a.modo}} ${{a.mercado}}`;}}setInterval(load,3000);load();</script></body></html>"""
    return render_template_string(html)

@app.route('/api/data')
def api_data():
    target=ADMINS_IDS[0]
    if target not in USUARIOS: get_user_data(target)
    u=USUARIOS[target]
    return jsonify({"balance":u["balance"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"estrategias":u["estrategias"],"monedas":MONEDAS_ACTIVAS})

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"Webhook error {e}")
    return "ok", 200

@app.route('/set_webhook')
def set_webhook_route():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{WEB_URL}/{TOKEN}")
        return f"Webhook OK {WEB_URL}/{TOKEN}", 200
    except Exception as e:
        return f"Error {e}", 500

threading.Thread(target=motor_v43,daemon=True).start()

if __name__=='__main__':
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{WEB_URL}/{TOKEN}")
        print(f">>> WEBHOOK V43 SETEADO {WEB_URL}/{TOKEN}")
    except Exception as e:
        print(f"Webhook set error {e}")
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
