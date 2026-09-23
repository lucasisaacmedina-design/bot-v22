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
WEB_URL = os.getenv("WEB_URL", "https://lobobot22-v45.onrender.com").strip().rstrip("/")

MONEDAS_ACTIVAS = ["BTCUSDT", "BNBUSDT"]
CANDIDATAS = ["ETHUSDT","SOLUSDT","XRPUSDT","AVAXUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","DOTUSDT","LTCUSDT","TRXUSDT","MATICUSDT","SHIBUSDT"]

# ===== V45.1 FINAL CON AUTO-LIMPIEZA =====
TANQUE_BNB_USDT = 10.0
TANQUE_BNB_MIN = 2.0
TANQUE_BNB_RECARGA = 8.0
COMISION_TOTAL = 0.15
FILTRO_NETO_MIN = 0.5

ESTRATEGIAS_V45 = {
    "RATA": {"tf": "5m", "desc": "RATA 5M BANDA", "rango_tp": (1.0, 1.4), "sl_neto": -0.60, "max_dia": 100, "cooldown": 5, "mercado_ideal": "LINEAL", "tp_fijo_banda": 1.0},
    "LOBO": {"tf": "1h", "desc": "LOBO 1H BANDA", "rango_tp": (1.5, 3.5), "sl_neto": -1.20, "max_dia": 100, "cooldown": 15, "mercado_ideal": "ALCISTA", "tp_fijo_banda": 2.5},
    "TIBURON": {"tf": "1d", "desc": "TIBURON 1D 10% FIJA BANDA", "rango_tp": (10.0, 10.0), "sl_neto": -3.50, "max_dia": 100, "cooldown": 0, "mercado_ideal": "ALCISTA_FUERTE"},
    "KRAKEN": {"tf": "1w", "desc": "KRAKEN 1W 18%", "rango_tp": (18.0, 18.0), "sl_neto": -5.0, "max_dia": 100, "cooldown": 0, "mercado_ideal": "CRASH"}
}

MAPA_ESTRATEGIA = {
    "LINEAL": "RATA 1.0-1.4%",
    "ALCISTA": "LOBO 1.5-3.5%",
    "ALCISTA_FUERTE": "TIBURON 10% BANDA",
    "CRASH": "KRAKEN 18%",
    "BAJISTA": "KRAKEN 18%"
}
def estrategia_prevista(regimen_txt):
    reg = regimen_txt.split()[0] if regimen_txt else "LINEAL"
    return MAPA_ESTRATEGIA.get(reg, "RATA 1.0-1.4%")

# PROXY
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

client=None; CLIENT_ERROR="No iniciado"; REAL_BALANCE_USDT=10000.00; REAL_BALANCE_BNB=0.0
if BINANCE_LIB and BINANCE_API_KEY and BINANCE_API_SECRET:
    try:
        req_params = {"proxies": PROXIES, "timeout": 25} if PROXIES else {"timeout": 15}
        client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=IS_TESTNET, requests_params=req_params)
        if PROXIES: client.session.proxies.update(PROXIES)
        client.ping()
        acc=client.get_account()
        for b in acc['balances']:
            if b['asset']=='USDT': REAL_BALANCE_USDT=float(b['free'])+float(b['locked'])
            if b['asset']=='BNB': REAL_BALANCE_BNB=float(b['free'])+float(b['locked'])
        CLIENT_ERROR="OK"
    except Exception as e: CLIENT_ERROR=str(e)[:200]

BALANCE_INICIAL=REAL_BALANCE_USDT
ADMINS_IDS=[6530209116]
DATA_DIR="/opt/render/project/src/data" if os.path.exists("/opt/render/project/src/data") else "./data"
DATA_FILE=os.path.join(DATA_DIR,"manada_v40.json")
POS_FILE=os.path.join(DATA_DIR,"posiciones_abiertas.json")
BANDA_FILE=os.path.join(DATA_DIR,"bandas_v45.json")
os.makedirs(DATA_DIR,exist_ok=True)

ESTADO={"btc":0,"bnb":0,"regimen":"LINEAL","regimen_detalle":"Iniciando","regimenes":{},"estrategias_activas":{}}
USUARIOS={}; LOCK=threading.Lock()
POSICIONES_ABIERTAS = {}
BANDAS_ACTIVAS = {}

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
def adx_calc(highs, lows, closes, period=14):
    if len(closes) < period*2 + 1: return 15.0
    tr_list, plus_dm_list, minus_dm_list = [], [], []
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        tr = max(hl, hc, lc)
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        plus_dm = up if up > down and up > 0 else 0
        minus_dm = down if down > up and down > 0 else 0
        tr_list.append(tr)
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
    atr = sum(tr_list[:period]) / period
    plus_dm_s = sum(plus_dm_list[:period]) / period
    minus_dm_s = sum(minus_dm_list[:period]) / period
    for i in range(period, len(tr_list)):
        atr = (atr * (period-1) + tr_list[i]) / period
        plus_dm_s = (plus_dm_s * (period-1) + plus_dm_list[i]) / period
        minus_dm_s = (minus_dm_s * (period-1) + minus_dm_list[i]) / period
    if atr == 0: return 15.0
    plus_di = 100 * plus_dm_s / atr
    minus_di = 100 * minus_dm_s / atr
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di)!= 0 else 0
    return round(dx, 2)

def verificar_tanque_bnb():
    global REAL_BALANCE_BNB
    try:
        if not client: return True
        acc=client.get_account()
        bnb=0
        for b in acc['balances']:
            if b['asset']=='BNB': bnb=float(b['free'])+float(b['locked'])
        REAL_BALANCE_BNB=bnb
        precio_bnb = float(client.get_symbol_ticker(symbol="BNBUSDT")['price'])
        valor_bnb_usdt = bnb * precio_bnb
        if valor_bnb_usdt < TANQUE_BNB_MIN:
            ejecutar_orden_real("BNBUSDT","BUY", TANQUE_BNB_RECARGA)
            return False
        return True
    except: return True

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
    ema50=sum(closes_1h[-50:])/50
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
    rent_14d = (closes_1d[-1]-closes_1d[0])/closes_1d[0] if closes_1d[0]!=0 else 0
    if adx_1h < 20 and abs(rent_14d) < 0.03: return "LINEAL", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
    elif rent_14d < -0.12: return "CRASH", f"ADX{adx_1h:.0f} {rent_14d*100:.1f}%"
    elif rent_14d > 0.06 and closes_1h[-1] > ema50: return "ALCISTA_FUERTE", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
    elif closes_1h[-1] > ema50 and adx_1h > 20: return "ALCISTA", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
    else: return "BAJISTA", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"

def detectar_RATA_sym(symbol):
    d5=get_velas(symbol,"5m",100)
    if not d5: return False,f"{symbol} Sin velas",0
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    sma20=sum(closes[-20:])/20; var=sum((x-sma20)**2 for x in closes[-20:])/20; std=var**0.5; lower=sma20-2*std
    precio=closes[-1]; vol_prom=sum(d5["vols"][-20:])/20; vol_actual=d5["vols"][-1]
    if precio<=lower and rsi<15 and vol_actual>vol_prom*1.5:
        return True,f"[{symbol}] RATA 5M RSI{int(rsi)}", 0.68
    return False,f"[{symbol}] RATA esperando RSI{int(rsi)}", 0.30

def detectar_LOBO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]; ema20=sum(closes[-20:])/20; ema50=sum(closes[-50:])/50
    ema12=sum(closes[-12:])/12; ema26=sum(closes[-26:])/26; macd=ema12-ema26
    adx = adx_calc(d["highs"], d["lows"], d["closes"], 14)
    retroceso = abs(closes[-1]-ema20)/ema20 < 0.025 if ema20!=0 else False
    if closes[-1]>ema20 and ema20>ema50 and macd>0 and adx>20 and retroceso:
        return True,f"[{symbol}] LOBO 1H ADX{adx:.0f} RET2.5%", 0.65
    return False,f"[{symbol}] LOBO ADX{adx:.0f} esperando", 0.35

def detectar_TIBURON_sym(symbol):
    d=get_velas(symbol,"1d",210)
    if not d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]; ema50=sum(closes[-50:])/50; rsi14=rsi_calc(closes,14)
    if closes[-1] > ema50 and rsi14 > 45:
        return True,f"[{symbol}] TIBURON CAZADOR RSI{int(rsi14)}", 0.85
    return False,f"[{symbol}] TIBU esperando", 0.25

def detectar_KRAKEN_sym(symbol):
    d=get_velas(symbol,"1w",100)
    if not d: return False,f"{symbol} Sin velas",0
    closes=d["closes"]; lows=d["lows"]; vols=d["vols"]
    min_20=min(lows[-21:-1]) if len(lows)>=22 else min(lows)
    spring=lows[-1]<min_20 and closes[-1]>min_20
    vol_prom=sum(vols[-21:-1])/20 if len(vols)>=22 else sum(vols)/len(vols)
    vsa=vols[-1]>vol_prom*1.8 if vol_prom!=0 else False
    if spring and vsa: return True,f"[{symbol}] KRAKEN Spring", 0.70
    return False,f"[{symbol}] KRAKEN esperando", 0.08

def es_rentable(tp_bruto):
    neto = tp_bruto - COMISION_TOTAL
    return neto >= FILTRO_NETO_MIN, neto

def detectar_BI_CEREBRO(regimen):
    # CEREBRO 2 - BANDA
    for sym, banda in list(BANDAS_ACTIVAS.items()):
        if not banda.get("activa"): continue
        precio_actual = ESTADO.get("btc" if "BTC" in sym else "bnb", 0)
        if precio_actual==0: continue
        if banda["entrada_tiburon"] <= precio_actual <= banda["tope"] or banda["tipo"]=="RECUPERACION":
            d5=get_velas(sym,"5m",50)
            if d5:
                rsi = rsi_calc(d5["closes"],7)
                if rsi < 30:
                    ok_neto, neto = es_rentable(1.0)
                    if ok_neto:
                        return True, f"[BANDA {sym}] RATA 1% dentro {banda['entrada_tiburon']:.0f}->{banda['tope']:.0f} RSI{rsi:.0f}", sym, "RATA", 0.9
                if rsi < 40:
                    ok_neto, neto = es_rentable(2.5)
                    if ok_neto:
                        return True, f"[BANDA {sym}] LOBO 2.5% dentro", sym, "LOBO", 0.85
    # CEREBRO 1 - TENDENCIA
    todas = ["RATA","LOBO","TIBURON","KRAKEN"]
    mejor_motivo=""; mejor_sym=""; mejor_fuerza=0; mejor_est=None
    for sym in MONEDAS_ACTIVAS:
        # V45.1: check global TIBURON existente
        tiene_tib = False
        for lista in POSICIONES_ABIERTAS.values():
            for p in (lista if isinstance(lista, list) else []):
                if p["symbol"]==sym and p["estrategia"]=="TIBURON":
                    tiene_tib = True
        for nombre in todas:
            if nombre=="TIBURON" and tiene_tib: continue
            if nombre=="RATA": ok,motivo,wr = detectar_RATA_sym(sym)
            elif nombre=="LOBO": ok,motivo,wr = detectar_LOBO_sym(sym)
            elif nombre=="TIBURON": ok,motivo,wr = detectar_TIBURON_sym(sym)
            else: ok,motivo,wr = detectar_KRAKEN_sym(sym)
            if ok:
                reg_sym = ESTADO.get("regimenes",{}).get(sym, regimen).split()[0]
                bonus = 0.25 if ESTRATEGIAS_V45[nombre]["mercado_ideal"]==reg_sym else 0
                fuerza_final = wr + bonus
                if fuerza_final > mejor_fuerza:
                    tp_check = ESTRATEGIAS_V45[nombre]["rango_tp"][0]
                    ok_rent, _ = es_rentable(tp_check)
                    if not ok_rent: continue
                    mejor_fuerza=fuerza_final; mejor_est=nombre; mejor_motivo=motivo; mejor_sym=sym
    if mejor_est:
        return True, mejor_motivo, mejor_sym, mejor_est, mejor_fuerza
    return False, f"V45 BI-CEREBRO ESPERANDO", MONEDAS_ACTIVAS[0], None, 0

def check_reset_diario(u):
    hoy=ahora_art().strftime("%Y-%m-%d")
    if u.get("fecha_hoy")!=hoy:
        u["fecha_hoy"]=hoy; u["neto_hoy"]=0.0; u["ops_hoy"]=0
        for k in u["estrategias"]: u["estrategias"][k]["ops"]=0

def get_user_data(uid):
    uid=int(uid)
    with LOCK:
        if uid not in USUARIOS:
            USUARIOS[uid]={"user_id":uid,"prendido":False,"balance":BALANCE_INICIAL,"capital_inicial":BALANCE_INICIAL,"neto_hoy":0.0,"ops_hoy":0,"ganadas":0,"perdidas":0,"modo":"ESPERANDO","mercado":"Tocá PRENDER","ultima_op":{}, "historial":[],"estrategias":{k:{"ops":0,"ganadas":0,"neto":0.0} for k in ESTRATEGIAS_V45},"fecha_hoy":ahora_art().strftime("%Y-%m-%d")}
        check_reset_diario(USUARIOS[uid]); return USUARIOS[uid]

def guardar_datos():
    try:
        with LOCK:
            with open(DATA_FILE,"w") as f: json.dump(USUARIOS,f,indent=2)
            with open(os.path.join(DATA_DIR,"monedas_activas.json"),"w") as f: json.dump(MONEDAS_ACTIVAS,f)
            with open(POS_FILE,"w") as f: json.dump(POSICIONES_ABIERTAS,f,indent=2)
            with open(BANDA_FILE,"w") as f: json.dump(BANDAS_ACTIVAS,f,indent=2)
    except: pass

def cargar_datos():
    global MONEDAS_ACTIVAS, POSICIONES_ABIERTAS, BANDAS_ACTIVAS
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,"r") as f:
                data=json.load(f)
                for k,v in data.items(): USUARIOS[int(k)]=v
                for uid in USUARIOS:
                    if "MONSTRUO" in USUARIOS[uid]["estrategias"]:
                        USUARIOS[uid]["estrategias"]["KRAKEN"] = USUARIOS[uid]["estrategias"].pop("MONSTRUO")
                    if "KRAKEN" not in USUARIOS[uid]["estrategias"]:
                        USUARIOS[uid]["estrategias"]["KRAKEN"] = {"ops":0,"ganadas":0,"neto":0.0}
        path=os.path.join(DATA_DIR,"monedas_activas.json")
        if os.path.exists(path):
            with open(path,"r") as f: MONEDAS_ACTIVAS=json.load(f)
        if os.path.exists(POS_FILE):
            with open(POS_FILE,"r") as f:
                raw=json.load(f)
                for k,v in raw.items():
                    try: POSICIONES_ABIERTAS[int(k)]=v
                    except: POSICIONES_ABIERTAS[k]=v
        if os.path.exists(BANDA_FILE):
            with open(BANDA_FILE,"r") as f: BANDAS_ACTIVAS=json.load(f)
    except: pass

# === PARCHE V45.1 AUTO-LIMPIEZA DE POSICIONES V44.8 BUG ===
def limpiar_pos_viejas():
    global POSICIONES_ABIERTAS, BANDAS_ACTIVAS
    borradas = 0
    for uid in list(POSICIONES_ABIERTAS.keys()):
        lista = POSICIONES_ABIERTAS[uid]
        if not isinstance(lista, list): continue
        nuevas = []
        vistos_tib = set()
        for p in lista:
            # BORRA TP 12,14,18 del bug V44.8
            if p.get("estrategia")=="TIBURON" and float(p.get("tp",0)) in [12.0,14.0,18.0]:
                borradas+=1
                continue
            key = (p.get("symbol"), p.get("estrategia"))
            if p.get("estrategia") in ["TIBURON","KRAKEN"]:
                if key in vistos_tib:
                    borradas+=1
                    continue
                vistos_tib.add(key)
            nuevas.append(p)
        POSICIONES_ABIERTAS[uid]=nuevas
    if borradas>0:
        print(f"🧹 V45.1 Limpieza: borradas {borradas} pos viejas TP12/14/18")
        # Si borramos, reseteamos bandas para fijar nueva 10% limpia
        BANDAS_ACTIVAS = {}
    guardar_datos()

cargar_datos()
limpiar_pos_viejas()

def motor_v45():
    print(">>> MOTOR V45.1 BI-CEREBRO + TANQUE BNB + AUTO-LIMPIEZA")
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
        verificar_tanque_bnb()
        for user_id in list(USUARIOS.keys()):
            u=USUARIOS[user_id]
            if user_id not in POSICIONES_ABIERTAS: POSICIONES_ABIERTAS[user_id] = []
            for pos in POSICIONES_ABIERTAS[user_id][:]:
                try:
                    precio_actual = float(client.get_symbol_ticker(symbol=pos["symbol"])['price'])
                    if pos["estrategia"] in ["TIBURON","KRAKEN"]:
                        profit_actual = (precio_actual - pos["entrada"])/pos["entrada"]*100
                        if pos["estrategia"]=="TIBURON":
                            if profit_actual >= 8 and pos["sl"] < 5:
                                pos["sl"]=5.0
                                guardar_datos()
                            elif profit_actual >= 5 and pos["sl"] < 0:
                                pos["sl"]=0.0
                                guardar_datos()
                    tp_price = pos["entrada"] * (1 + pos["tp"]/100)
                    sl_price = pos["entrada"] * (1 + pos["sl"]/100)
                    cerrar = None
                    if precio_actual >= tp_price: cerrar = "TP"
                    elif precio_actual <= sl_price:
                        cerrar = "TRAILING" if pos["sl"]>=0 and pos["estrategia"] in ["TIBURON","KRAKEN"] else "SL"
                    if cerrar:
                        usdt_a_vender = pos["usdt"]
                        ejecutar_orden_real(pos["symbol"], "SELL", usdt_a_vender)
                        pnl_bruto = (precio_actual - pos["entrada"]) / pos["entrada"] * pos["usdt"]
                        comision = pos["usdt"] * COMISION_TOTAL/100
                        pnl = pnl_bruto - comision
                        if pos["estrategia"]=="TIBURON":
                            if cerrar=="TP":
                                if pos["symbol"] in BANDAS_ACTIVAS:
                                    BANDAS_ACTIVAS[pos["symbol"]]["activa"]=False
                            else:
                                entrada = pos["entrada"]
                                sl_price_val = entrada * 0.965
                                banda_rec_base = sl_price_val * 0.97
                                BANDAS_ACTIVAS[pos["symbol"]] = {"entrada_tiburon": banda_rec_base, "tope": sl_price_val, "tipo": "RECUPERACION", "activa": True}
                                try: bot.send_message(user_id,f"🩹 BANDA RECUPERACION 3% {pos['symbol']} {banda_rec_base:.0f}->{sl_price_val:.0f}")
                                except: pass
                        if cerrar in ["TP","TRAILING"]:
                            u["balance"]+=abs(pnl); u["neto_hoy"]+=abs(pnl); u["ganadas"]+=1
                            u["estrategias"][pos["estrategia"]]["ganadas"]+=1
                        else:
                            u["balance"]-=abs(pnl); u["neto_hoy"]-=abs(pnl); u["perdidas"]+=1
                        u["estrategias"][pos["estrategia"]]["ops"]+=1
                        u["estrategias"][pos["estrategia"]]["neto"]+=pnl
                        u["ops_hoy"]+=1
                        u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} {pos['estrategia']} {pos['symbol']} {cerrar} ${pnl:+.2f}")
                        POSICIONES_ABIERTAS[user_id].remove(pos)
                        guardar_datos()
                        icono = "✅" if cerrar=="TP" else "🔒" if cerrar=="TRAILING" else "❌"
                        link = f"{WEB_URL}/chart?symbol={pos['symbol']}&interval=15m"
                        try: bot.send_message(user_id,f"{icono} {pos['estrategia']} {pos['symbol']} {cerrar}\nEnt {pos['entrada']:.2f}->{precio_actual:.2f}\n${pnl:+.2f} Bal ${u['balance']:.2f}\n📊 {link}")
                        except: pass
                except: pass
            if not u.get("prendido", False): continue
            check_reset_diario(u)
            if len(POSICIONES_ABIERTAS[user_id]) >= 4: continue
            regimen_actual = ESTADO.get("regimen","LINEAL")
            ok,motivo,symbol_elegido,estrategia_elegida,fuerza = detectar_BI_CEREBRO(regimen_actual)
            if not ok: continue
            if ok and estrategia_elegida:
                if estrategia_elegida in ["TIBURON","KRAKEN"]:
                    ya_tiene = False
                    for p in POSICIONES_ABIERTAS[user_id]:
                        if p["symbol"]==symbol_elegido and p["estrategia"]==estrategia_elegida:
                            ya_tiene=True; break
                    if ya_tiene: continue
                cfg=ESTRATEGIAS_V45[estrategia_elegida]
                if estrategia_elegida in ["RATA","LOBO"] and symbol_elegido in BANDAS_ACTIVAS and BANDAS_ACTIVAS[symbol_elegido].get("activa"):
                    tp_inteligente = cfg["tp_fijo_banda"]
                else:
                    tp_inteligente = cfg["rango_tp"][0]
                    if estrategia_elegida=="LOBO": tp_inteligente=2.5
                    elif estrategia_elegida=="RATA": tp_inteligente=1.0
                ok_rent, neto = es_rentable(tp_inteligente)
                if not ok_rent: continue
                usdt_a_usar=u["balance"]*0.35*0.10
                if u["balance"] - usdt_a_usar < TANQUE_BNB_USDT:
                    usdt_a_usar = max(10, u["balance"] - TANQUE_BNB_USDT)
                exito, res, precio = ejecutar_orden_real(symbol_elegido,"BUY",usdt_a_usar)
                if exito:
                    pos = {"symbol": symbol_elegido, "estrategia": estrategia_elegida, "entrada": precio, "tp": tp_inteligente, "sl": cfg["sl_neto"], "usdt": usdt_a_usar, "hora": ahora_art().isoformat()}
                    POSICIONES_ABIERTAS[user_id].append(pos)
                    u["ultima_op"][estrategia_elegida]=ahora_art().isoformat()
                    u["modo"]=f"{estrategia_elegida} {symbol_elegido} TP{tp_inteligente}%"; u["mercado"]=f"{motivo}"
                    u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} {estrategia_elegida} {symbol_elegido} COMPRA {precio:.2f} TP {tp_inteligente}%")
                    if estrategia_elegida=="TIBURON":
                        BANDAS_ACTIVAS[symbol_elegido] = {"entrada_tiburon": precio, "tope": precio*1.10, "tipo": "NORMAL", "activa": True}
                    guardar_datos()
                    link = f"{WEB_URL}/chart?symbol={symbol_elegido}&interval=15m"
                    tipo_banda = " [FIJA BANDA]" if estrategia_elegida=="TIBURON" else " [DENTRO BANDA]" if symbol_elegido in BANDAS_ACTIVAS and BANDAS_ACTIVAS[symbol_elegido].get("activa") else ""
                    try: bot.send_message(user_id,f"🟢 V45.1 {estrategia_elegida}{tipo_banda} {symbol_elegido}\n{motivo}\nEnt {precio:.2f} TP {tp_inteligente}% SL {cfg['sl_neto']}% Neto {neto:.2f}%\n📊 {link}")
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
    estado_txt = "🟢 V45.1" if u["prendido"] else "🔴 APAGADO"
    regs="\n".join([f"{k}:{v} -> {estrategia_prevista(v)}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO['regimen']
    bandas_txt = "\n".join([f"🎯 BANDA {k} {v['entrada_tiburon']:.0f}->{v['tope']:.0f} {v['tipo']}" for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    bot.send_message(m.chat.id,f"🦁 V45.1 BI-CEREBRO {estado_txt}\n{regs}\n{bandas_txt}\n{'+'.join(MONEDAS_ACTIVAS)}\nBal ${u['balance']:.2f}\n{WEB_URL}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="📊 BALANCE")
def balance(m):
    u=get_user_data(m.chat.id)
    ganancia_total = u["balance"]-u["capital_inicial"]
    regs="\n".join([f"{k}: {v}" for k,v in ESTADO.get("regimenes",{}).items()])
    pos_txt = "\n".join([f"🔓 {p['symbol']} {p['estrategia']} Ent {p['entrada']:.2f} TP{p['tp']}% SL{p['sl']}%" for p in POSICIONES_ABIERTAS.get(m.chat.id,[])]) or "Sin pos"
    bandas_txt = "\n".join([f"🎯 BANDA {k} {v['entrada_tiburon']:.0f}->{v['tope']:.0f} {v['tipo']}" for k,v in BANDAS_ACTIVAS.items()]) or "Sin bandas"
    texto=f"💰 V45.1 BI-CEREBRO\n{regs}\n{bandas_txt}\nMonedas: {'+'.join(MONEDAS_ACTIVAS)}\nBalance ${u['balance']:.2f} Gan ${ganancia_total:+.2f} Tanque $10\nHoy ${u['neto_hoy']:+.2f} {u['ops_hoy']} ops\n{pos_txt}\n"
    for k,v in u["estrategias"].items():
        texto+=f"{k}: {v['ops']} ops ${v['neto']:+.2f}\n"
    bot.send_message(m.chat.id,texto,reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL","/historial"])
def historial(m):
    u=get_user_data(m.chat.id)
    txt="\n".join(u["historial"][-20:]) if u["historial"] else "Sin ops"
    bot.send_message(m.chat.id,f"📜 V45.1\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER","/prender"])
def prender(m):
    u=get_user_data(m.chat.id); u["prendido"]=True; u["modo"]="CAZANDO V45.1"
    guardar_datos()
    bot.send_message(m.chat.id,f"🦁 V45.1 PRENDIDO LIMPIO\n{'+'.join(MONEDAS_ACTIVAS)}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["⏸️ APAGAR","/apagar"])
def apagar(m):
    u=get_user_data(m.chat.id); u["prendido"]=False; guardar_datos()
    bot.send_message(m.chat.id,f"⏸️ V45.1 APAGADO",reply_markup=get_menu())

@app.route('/')
def home():
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>V45.1 BI-CEREBRO</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}.card{background:#1e222d;padding:10px;margin:5px;border-radius:8px;display:inline-block;min-width:150px}</style></head><body><div style="padding:10px;background:#1e222d" id="info"></div><div id="charts_grid" style="display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px"></div><script>async function load(){let a=await (await fetch('/api/data')).json();document.getElementById('info').innerHTML='V45.1 '+a.modo+' | '+a.bandas_txt+' | '+a.monedas.join('+');let grid=document.getElementById('charts_grid');if(grid.childElementCount!=a.monedas.length){grid.innerHTML='';a.monedas.forEach(sym=>{let div=document.createElement('div');div.innerHTML=`<div style="background:#1e293b;padding:6px">${sym}</div><div id="chart_${sym}" style="height:70vh"></div>`;grid.appendChild(div);setTimeout(()=>{new TradingView.widget({"autosize":true,"symbol":"BINANCE:"+sym,"interval":"15","timezone":"America/Argentina/Buenos_Aires","theme":"dark","container_id":"chart_"+sym});},200);});}}setInterval(load,3000);load();</script></body></html>"""
    return render_template_string(html)

@app.route('/chart')
def chart_page():
    symbol = request.args.get('symbol','BTCUSDT')
    interval = request.args.get('interval','15m')
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{symbol}</title><script src="https://s3.tradingview.com/tv.js"></script></head><body style="margin:0;background:#0f1115"><div style="padding:10px;background:#1e222d;color:#fff">{symbol} - V45.1 <a href="/" style="color:#facc15">Volver</a></div><div id="chart" style="height:90vh"></div><script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:{symbol}","interval":"{interval}","timezone":"America/Argentina/Buenos_Aires","theme":"dark","container_id":"chart"}});</script></body></html>"""
    return render_template_string(html)

@app.route('/api/data')
def api_data():
    target=ADMINS_IDS[0]
    if target not in USUARIOS: get_user_data(target)
    u=USUARIOS[target]
    bandas_txt = " | ".join([f"{k} {v['entrada_tiburon']:.0f}->{v['tope']:.0f} {v['tipo']}" for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    return jsonify({"balance":u["balance"],"capital_inicial":u["capital_inicial"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"regimen_btc":ESTADO.get("regimen","LINEAL"),"regimenes":ESTADO.get("regimenes",{"BTCUSDT":ESTADO.get("regimen","LINEAL"),"BNBUSDT":"LINEAL"}),"estrategias_activas":ESTADO.get("estrategias_activas",{}),"estrategias":u["estrategias"],"monedas":MONEDAS_ACTIVAS,"ganancia_total": u["balance"]-u["capital_inicial"],"bandas": BANDAS_ACTIVAS, "bandas_txt": bandas_txt})

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

threading.Thread(target=motor_v45,daemon=True).start()

if __name__=='__main__':
    try:
        bot.remove_webhook(); time.sleep(1)
        bot.set_webhook(url=f"{WEB_URL}/{TOKEN}")
    except Exception as e: print(f"Webhook error {e}")
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
