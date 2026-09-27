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
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or "dummy_token_for_build"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
def clean_key(v):
    if not v: return ""
    return str(v).strip().replace('"','').replace("'","").replace("\n","").replace("\r","").strip()
BINANCE_API_KEY = clean_key(os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_TESTNET_API_KEY"))
BINANCE_API_SECRET = clean_key(os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_TESTNET_SECRET_KEY") or os.getenv("BINANCE_TESTNET_API_SECRET"))
IS_TESTNET = (os.getenv("BINANCE_TESTNET", "true") or "true").lower().strip() == "true"
WEB_URL = os.getenv("WEB_URL", "https://lobobot22-v50-9.onrender.com").strip().rstrip("/")
MONEDAS_ACTIVAS = ["BTCUSDT", "BNBUSDT"]
CANDIDATAS = ["ETHUSDT","SOLUSDT","XRPUSDT","AVAXUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","DOTUSDT","LTCUSDT","TRXUSDT","MATICUSDT","SHIBUSDT","PEPEUSDT","SUIUSDT","APTUSDT","ARBUSDT","OPUSDT","NEARUSDT","FILUSDT","INJUSDT"]
MAX_MONEDAS = 20
META_TP_PARA_EXPANDIR = 120.0
CONTADOR_TP_EXPANSION = 0
TANQUE_POR_MONEDA = 2.0
TANQUE_BNB_USDT = float(os.getenv("TANQUE", os.getenv("TANQUE_BNB_USDT", "20")))
TANQUE_BNB_MIN = float(os.getenv("TANQUE_BNB_MIN", "5.0"))
TANQUE_BNB_RECARGA = float(os.getenv("TANQUE_BNB_RECARGA", "8.0"))
TANQUE = TANQUE_BNB_USDT
COMISION_TOTAL = 0.15
FILTRO_NETO_MIN = 0.5
FILTRO_NETO_MIN_MOJARRA = 0.10
MAX_MOJARRA_POR_MONEDA = 3
MAX_PIRANA_POR_MONEDA = 2
DISTANCIA_CARDUMEN_PCT = 0.15
DISTANCIA_PIRANA_PCT = 0.30
DISTANCIA_MOJARRA_PCT = 0.15
ESTADO_PIRANA = {}
ESTADO_PIRANA_NEGRA = {}
BANDAS_TIEMPO_FUERA = {}
TIEMPO_FUERA_NORMAL = 720
TIEMPO_FUERA_BAJISTA = 360
CANDIDATAS_CACHE = {"_ultimo_scan": 0, "_aviso_meta": 0, "proxima": None}
TIEMPO_ESCANEO_CANDIDATAS = 600
ESTRATEGIAS_V45 = {
    "MOJARRA": {"tf": "5m", "desc": "MOJARRA 0.3-0.5% LONG","rango_tp": (0.3, 0.5), "sl_neto": -1.5, "max_dia": 200,"cooldown": 60, "cooldown_rec": 60,"mercado_ideal": "UNIVERSAL", "tp_fijo_banda": 0.4},
    "PIRANA_BLANCA": {"tf": "5m", "desc": "PIRANA BLANCA 0.5-0.8% LONG","rango_tp": (0.5, 0.8), "sl_neto": -2.5, "max_dia": 150,"cooldown": 90, "cooldown_rec": 90,"mercado_ideal": "UNIVERSAL", "tp_fijo_banda": 0.6},
    "RATA": {"tf": "5m", "desc": "Madre RATA 0.8-1.5% LONG","rango_tp": (0.8, 1.5), "sl_neto": -4.0, "max_dia": 100,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "LOBO": {"tf": "1h", "desc": "Madre LOBO 1.2-2.2% LONG","rango_tp": (1.2, 2.2), "sl_neto": -5.0, "max_dia": 100,"cooldown": 300, "cooldown_rec": 300,"mercado_ideal": "ALCISTA", "tp_fijo_banda": 1.2},
    "TIBURON": {"tf": "1d", "desc": "Madre TIBURON 5-10% LONG","rango_tp": (5.0, 10.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 14400, "cooldown_rec": 14400,"mercado_ideal": "ALCISTA_FUERTE"},
    "KRAKEN": {"tf": "1h", "desc": "Madre KRAKEN 3-5% LONG","rango_tp": (3.0, 5.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 3600, "cooldown_rec": 3600,"mercado_ideal": "CRASH"},
    "MOJARRA_NEGRA": {"tf": "5m", "desc": "MOJARRA NEGRA 0.3-0.5% SHORT","rango_tp": (0.3, 0.5), "sl_neto": -1.5, "max_dia": 200,"cooldown": 60, "cooldown_rec": 60,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.3},
    "PIRANA_NEGRA": {"tf": "5m", "desc": "PIRANA NEGRA 0.5-0.8% SHORT","rango_tp": (0.5, 0.8), "sl_neto": -3.5, "max_dia": 100,"cooldown": 600, "cooldown_rec": 600,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.5},
    "RATA_NEGRA": {"tf": "5m", "desc": "RATA NEGRA 0.8-1.5% SHORT","rango_tp": (0.8, 1.5), "sl_neto": -4.0, "max_dia": 100,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.8},
    "LOBO_NEGRO": {"tf": "1h", "desc": "LOBO NEGRO 1.2-2.2% SHORT","rango_tp": (1.2, 2.2), "sl_neto": -5.0, "max_dia": 100,"cooldown": 300, "cooldown_rec": 300,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 1.2},
}
ESTRATEGIAS_V45["PIRANA"] = ESTRATEGIAS_V45["PIRANA_BLANCA"]
ESTRATEGIAS_V45["PIRAÑA_NEGRA"] = ESTRATEGIAS_V45["PIRANA_NEGRA"]
MAPA_ANIDADO_V50_9 = {
    "LINEAL_MUERTO": ["MOJARRA", "PIRANA_BLANCA"],
    "LINEAL": ["MOJARRA", "PIRANA_BLANCA", "RATA"],
    "ALCISTA": ["MOJARRA", "PIRANA_BLANCA", "RATA", "LOBO"],
    "ALCISTA_FUERTE": ["MOJARRA", "PIRANA_BLANCA", "RATA", "LOBO", "TIBURON"],
    "BAJISTA": ["MOJARRA_NEGRA", "PIRANA_NEGRA", "RATA_NEGRA", "LOBO_NEGRO", "KRAKEN"],
    "CRASH": ["MOJARRA", "PIRANA_BLANCA", "KRAKEN", "MOJARRA_NEGRA", "PIRANA_NEGRA", "RATA_NEGRA"]
}
MAPA_ESTRATEGIA = {"LINEAL_MUERTO": "MANADA LIBRE MOJARRA+PIRANA", "LINEAL": "MOJARRA 0.3% + RATA", "ALCISTA": "MOJARRA + LOBO", "ALCISTA_FUERTE": "MOJARRA + TIBURON", "CRASH": "MOJARRA + KRAKEN PANICO", "BAJISTA": "KRAKEN + SHORTS"}
def estrategia_prevista(regimen_txt):
    reg = regimen_txt.split()[0] if regimen_txt else "LINEAL"
    return MAPA_ESTRATEGIA.get(reg, "MANADA LIBRE")
PROXY_LIST_RAW = os.getenv("PROXY_LIST") or os.getenv("PROXY_URL") or os.getenv("HTTPS_PROXY") or ""
RAW_SPLIT = [clean_key(c) for c in PROXY_LIST_RAW.split(",") if clean_key(c)]
if not RAW_SPLIT: RAW_SPLIT = ["http://ufssgczi:aus6m0vuweru@31.58.9.4:6077","http://ufssgczi:aus6m0vuweru@31.59.20.176:6754"]
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
client=None
CLIENT_ERROR="No iniciado"; REAL_BALANCE_USDT=10000.00; REAL_BALANCE_BNB=0.0
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
CAPITAL_BASE = 10000.0
if REAL_BALANCE_USDT < 100:
    REAL_BALANCE_USDT = CAPITAL_BASE
BALANCE_INICIAL = CAPITAL_BASE
ADMINS_IDS=[6530209116]
DATA_DIR="/opt/render/project/src/data" if os.path.exists("/opt/render/project/src/data") else "./data"
DATA_FILE=os.path.join(DATA_DIR,"manada_v40.json")
POS_FILE=os.path.join(DATA_DIR,"posiciones_abiertas.json")
BANDA_FILE=os.path.join(DATA_DIR,"bandas_v45.json")
CONTADOR_FILE=os.path.join(DATA_DIR,"contador_expansion.json")
os.makedirs(DATA_DIR,exist_ok=True)
ESTADO={"btc":0,"bnb":0,"regimen":"LINEAL","regimen_detalle":"Iniciando","regimenes":{},"estrategias_activas":{}}
USUARIOS={}; LOCK=threading.Lock()
POSICIONES_ABIERTAS = {}; BANDAS_ACTIVAS = {}; ULTIMO_TRADE = {}; ULTIMO_PENSAMIENTO = 0; ULTIMO_CAZANDO = {}
def ahora_art(): return datetime.now(TZ)
def get_precio_robusto(symbol):
    try:
        if client:
            return float(client.get_symbol_ticker(symbol=symbol)['price'])
    except: pass
    for base in ["https://data-api.binance.vision","https://api.binance.com","https://api1.binance.com","https://api2.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/price?symbol={symbol}", timeout=4)
            if r.status_code==200:
                return float(r.json()['price'])
        except: pass
    return ESTADO.get("btc" if "BTC" in symbol else "bnb",0) or 0.0
def get_velas(symbol="BTCUSDT", interval="5m", limit=200):
    try:
        if client:
            klines=client.get_klines(symbol=symbol, interval=interval, limit=limit)
            return {"closes": [float(k[4]) for k in klines],"highs": [float(k[2]) for k in klines],"lows": [float(k[3]) for k in klines],"vols": [float(k[5]) for k in klines]}
    except: pass
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}", timeout=6)
        if r.status_code==200:
            klines=r.json()
            return {"closes": [float(k[4]) for k in klines],"highs": [float(k[2]) for k in klines],"lows": [float(k[3]) for k in klines],"vols": [float(k[5]) for k in klines]}
    except: pass
    return None
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
        tr_list.append(tr); plus_dm_list.append(plus_dm); minus_dm_list.append(minus_dm)
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
def atr_calc(d, period=14):
    if not d or len(d["closes"]) < period+1: return 0.0
    trs=[]
    for i in range(1, len(d["closes"])):
        hl = d["highs"][i]-d["lows"][i]
        hc = abs(d["highs"][i]-d["closes"][i-1])
        lc = abs(d["lows"][i]-d["closes"][i-1])
        trs.append(max(hl,hc,lc))
    return sum(trs[-period:])/period if trs else 0.0
def ema_calc(closes, period):
    if len(closes) < period: return sum(closes)/len(closes) if closes else 0
    k = 2/(period+1)
    ema = sum(closes[:period])/period
    for c in closes[period:]:
        ema = c*k + ema*(1-k)
    return ema
def tp_adaptativo(symbol, estrategia):
    try:
        rango = ESTRATEGIAS_V45[estrategia]["rango_tp"]
        if estrategia in ["MOJARRA", "PIRANA_BLANCA", "PIRANA", "MOJARRA_NEGRA"]:
            return rango[0]
        d1h = get_velas(symbol,"1h",100)
        if not d1h: return rango[0]
        adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
        atr = atr_calc(d1h, 14)
        precio = d1h["closes"][-1]
        atr_pct = (atr/precio*100) if precio!=0 else 0
        if estrategia == "LOBO" or estrategia == "LOBO_NEGRO":
            if adx > 35 and atr_pct > 1.2: return rango[1]
            if adx < 18: return rango[0]
            return (rango[0]+rango[1])/2
        if estrategia in ["RATA","RATA_NEGRA"]:
            if adx > 30 and atr_pct > 1.0: return rango[1]
            return rango[0]
        if estrategia == "TIBURON":
            if adx > 30 and atr_pct > 1.5: return rango[1]
            return rango[0]
        if estrategia == "KRAKEN":
            if atr_pct > 2.0: return rango[1]
            return rango[0]
        return rango[0]
    except:
        return ESTRATEGIAS_V45[estrategia]["rango_tp"][0]
def tiempo_fuera_inteligente(symbol, tipo_actual):
    try:
        d1h = get_velas(symbol,"1h",60)
        d5 = get_velas(symbol,"5m",60)
        if not d1h or not d5:
            return TIEMPO_FUERA_NORMAL if tipo_actual=="NORMAL" else TIEMPO_FUERA_BAJISTA
        adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
        rsi_5 = rsi_calc(d5["closes"],7)
        atr = atr_calc(d1h,14)
        precio = d1h["closes"][-1]
        atr_pct = (atr/precio*100) if precio!=0 else 0
        vol_prom = sum(d1h["vols"][-20:])/20 if len(d1h["vols"])>=20 else 1
        vol_actual = d1h["vols"][-1]
        if tipo_actual == "NORMAL":
            if rsi_5 < 18 and adx > 32 and vol_actual > vol_prom*1.8: return 0.3*3600
            if rsi_5 < 28 and adx > 25: return 0.8*3600
            if rsi_5 < 35 and atr_pct > 1.5: return 1.0*3600
            if adx < 20: return 3.0*3600
            return 1.5*3600
        else:
            if rsi_5 > 55 and adx > 25: return 0.3*3600
            if rsi_5 > 45: return 0.6*3600
            return 1.0*3600
    except:
        return TIEMPO_FUERA_NORMAL if tipo_actual=="NORMAL" else TIEMPO_FUERA_BAJISTA
def get_umbral_adaptativo(regimen):
    reg = regimen.split()[0] if regimen else "LINEAL"
    if reg == "ALCISTA_FUERTE":
        return {"rsi_kraken": 30.5, "rsi_pirana": 35, "rsi_pirana_negra": 30, "vsa_kraken_base": 1.3, "vsa_negra_base": 1.3, "adx_tiburon": 25, "rsi_lobo_min": 50, "rsi_rata_max": 38}
    elif reg == "ALCISTA":
        return {"rsi_kraken": 29.5, "rsi_pirana": 33, "rsi_pirana_negra": 29, "vsa_kraken_base": 1.4, "vsa_negra_base": 1.4, "adx_tiburon": 28, "rsi_lobo_min": 52, "rsi_rata_max": 35}
    elif reg == "LINEAL":
        return {"rsi_kraken": 29.0, "rsi_pirana": 38, "rsi_pirana_negra": 28, "vsa_kraken_base": 1.3, "vsa_negra_base": 1.3, "adx_tiburon": 28, "rsi_lobo_min": 55, "rsi_rata_max": 38}
    else:
        return {"rsi_kraken": 27.5, "rsi_pirana": 30, "rsi_pirana_negra": 28, "vsa_kraken_base": 1.6, "vsa_negra_base": 1.6, "adx_tiburon": 35, "rsi_lobo_min": 999, "rsi_rata_max": 30}
def detectar_regimen_sym(symbol):
    d1h=get_velas(symbol,"1h",210); d1d=get_velas(symbol,"1d",15)
    if not d1h or not d1d: return "LINEAL", "Sin datos"
    closes_1h=d1h["closes"]; closes_1d=d1d["closes"]
    ema200 = ema_calc(closes_1h, 200)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
    atr = atr_calc(d1h, 14)
    precio = closes_1h[-1]
    atr_pct = (atr/precio*100) if precio!=0 else 0
    rent_14d = (closes_1d[-1]-closes_1d[0])/closes_1d[0] if closes_1d[0]!=0 else 0
    if adx_1h < 15 and atr_pct < 0.6:
        return "LINEAL_MUERTO", f"MUERTO ADX{adx_1h:.0f} ATR{atr_pct:.2f}% MANADA LIBRE"
    if adx_1h < 20 and abs(rent_14d) < 0.05: return "LINEAL", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
    elif rent_14d < -0.12: return "CRASH", f"ADX{adx_1h:.0f} {rent_14d*100:.1f}%"
    elif rent_14d > 0.06 and closes_1h[-1] > ema200: return "ALCISTA_FUERTE", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}% >EMA200"
    elif closes_1h[-1] > ema200 and adx_1h > 20: return "ALCISTA", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}% >EMA200"
    else: return "BAJISTA", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}% <EMA200"
def get_vol_requerido_auto(estrategia, reg_simple, adx, atr_pct=0):
    if IS_TESTNET:
        return 0.0
    if estrategia == "MOJARRA": return 0.10
    if estrategia in ["PIRANA_BLANCA", "PIRANA"]: return 0.25
    return 1.2
def detectar_RATA_sym(symbol, estrategia_nombre="RATA"):
    d5=get_velas(symbol,"5m",100); d1h=get_velas(symbol,"1h",50)
    if not d5: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    sma20=sum(closes[-20:])/20; var=sum((x-sma20)**2 for x in closes[-20:])/20; std=var**0.5; lower=sma20-2*std
    precio=closes[-1]; vol_prom=sum(d5["vols"][-20:])/20; vol_actual=d5["vols"][-1]
    adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 15
    reg_simple = reg.split()[0] if reg else "LINEAL"
    vol_requerido = get_vol_requerido_auto(estrategia_nombre, reg_simple, adx, 0)
    if estrategia_nombre in ["MOJARRA", "PIRANA_BLANCA", "PIRANA"]:
        if IS_TESTNET:
            if rsi <= 35:
                return True,f"[{symbol}] {estrategia_nombre} TESTNET RSI{int(rsi)}<=35 Vol ignorado {reg_simple} LIBRE", 0.85
            return False,f"[{symbol}] {estrategia_nombre} TESTNET RSI{int(rsi)}/35 ESPERANDO {reg_simple}", 0.30
        if rsi <= 35 and vol_actual > vol_prom*vol_requerido:
            return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}<=35 Vol{vol_actual/vol_prom:.1f}>{vol_requerido:.2f} {reg_simple} LIBRE", 0.85
        return False,f"[{symbol}] {estrategia_nombre} Vol{vol_actual/vol_prom:.1f}/{vol_requerido:.2f} RSI{int(rsi)}/35 {reg_simple}", 0.30
    if IS_TESTNET:
        check_vol = True
    else:
        check_vol = vol_actual>vol_prom*vol_requerido
    if precio<=lower and rsi<umb["rsi_rata_max"] and check_vol:
        return True,f"[{symbol}] {estrategia_nombre} V50.15 {reg_simple} RSI{int(rsi)}<{umb['rsi_rata_max']} Vol{vol_actual/vol_prom:.1f}>{vol_requerido:.2f} ADX{adx:.0f}", 0.68
    return False,f"[{symbol}] {estrategia_nombre} {reg_simple} Vol{vol_actual/vol_prom:.1f}/{vol_requerido:.2f} RSI{int(rsi)}/{umb['rsi_rata_max']} ADX{adx:.0f}", 0.30
def detectar_LOBO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    if umb["rsi_lobo_min"] > 90: return False,f"[{symbol}] LOBO ESCONDIDO {reg.split()[0]} BAJISTA", 0.10
    closes=d["closes"]; ema20=sum(closes[-20:])/20; ema50=sum(closes[-50:])/50
    ema12=sum(closes[-12:])/12; ema26=sum(closes[-26:])/26; macd=ema12-ema26
    adx = adx_calc(d["highs"], d["lows"], d["closes"], 14)
    retroceso = abs(closes[-1]-ema20)/ema20 < 0.025 if ema20!=0 else False
    if closes[-1]>ema20 and ema20>ema50 and macd>0 and adx>20 and retroceso:
        return True,f"[{symbol}] LOBO V50.15 {reg.split()[0]} ADX{adx:.0f} RET2.5%", 0.65
    return False,f"[{symbol}] LOBO {reg.split()[0]} ADX{adx:.0f} esperando", 0.35
def detectar_TIBURON_sym(symbol):
    d=get_velas(symbol,"1d",210); d1h=get_velas(symbol,"1h",50)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d["closes"]; ema50=sum(closes[-50:])/50; rsi14=rsi_calc(closes,14)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 20
    if closes[-1] > ema50 and rsi14 > 45 and adx_1h > umb["adx_tiburon"]:
        return True,f"[{symbol}] TIBURON V50.15 {reg.split()[0]} ADX{adx_1h:.0f}>{umb['adx_tiburon']} RSI{int(rsi14)}", 0.85
    return False,f"[{symbol}] TIBU {reg.split()[0]} ADX{adx_1h:.0f}/{umb['adx_tiburon']} esperando", 0.25
def detectar_KRAKEN_sym(symbol):
    d1h=get_velas(symbol,"1h",210); d1d=get_velas(symbol,"1d",30)
    if not d1h or not d1d: return False,f"{symbol} Sin velas",0
    closes_1h=d1h["closes"]; vols_1h=d1h["vols"]
    rsi_1h=rsi_calc(closes_1h,14)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
    ema200 = ema_calc(closes_1h, 200)
    precio = closes_1h[-1]
    vol_prom_1h=sum(vols_1h[-21:-1])/20 if len(vols_1h)>=22 else sum(vols_1h)/len(vols_1h) if vols_1h else 1
    vsa_mult = vols_1h[-1]/vol_prom_1h if vol_prom_1h!=0 else 0
    panico_real = rsi_1h < 20 and vsa_mult > 1.4 and precio < ema200 and adx_1h > 25
    if panico_real:
        return True,f"[{symbol}] KRAKEN PANICO REAL RSI{int(rsi_1h)}<20 VSA{vsa_mult:.1f}>1.4 <EMA200 ADX{adx_1h:.0f}",0.99
    return False,f"[{symbol}] KRAKEN ESPERA PANICO RSI{int(rsi_1h)}/20 VSA{vsa_mult:.1f}/1.4",0.05
def gestionar_bandas_moviles():
    global BANDAS_ACTIVAS, BANDAS_TIEMPO_FUERA
    ahora = time.time()
    for sym in list(BANDAS_ACTIVAS.keys()):
        banda = BANDAS_ACTIVAS.get(sym)
        if not banda or not banda.get("activa"):
            BANDAS_TIEMPO_FUERA.pop(sym, None); continue
        reg = ESTADO.get("regimenes",{}).get(sym,"LINEAL").split()[0]
        if reg == "LINEAL_MUERTO" and banda.get("tipo")=="BAJISTA":
            precio = get_precio_robusto(sym)
            if precio>0:
                BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio*0.995, "tope": precio*1.08, "tipo": "NORMAL", "activa": True, "origen_mov": f"ESCLAVA V50.15 {reg} BAJISTA->NORMAL", "creada_en": ahora}
                BANDAS_TIEMPO_FUERA.pop(sym, None)
                continue
        precio = get_precio_robusto(sym)
        if precio==0: continue
        entrada = banda["entrada_tiburon"]; tope = banda["tope"]; tipo = banda.get("tipo","NORMAL")
        adentro = entrada*0.997 <= precio <= tope
        if adentro: BANDAS_TIEMPO_FUERA.pop(sym, None); continue
        fuera_tipo = "ABAJO" if precio < entrada else "ARRIBA"
        if sym not in BANDAS_TIEMPO_FUERA or BANDAS_TIEMPO_FUERA[sym]["tipo_fuera"]!= fuera_tipo:
            BANDAS_TIEMPO_FUERA[sym] = {"fuera_desde": ahora, "tipo_fuera": fuera_tipo}
        tiempo_fuera = ahora - BANDAS_TIEMPO_FUERA[sym]["fuera_desde"]
        tiempo_optimo = tiempo_fuera_inteligente(sym, tipo)
        if tipo=="NORMAL" and fuera_tipo=="ABAJO" and tiempo_fuera > tiempo_optimo:
            BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio*0.97, "tope": precio*0.995, "tipo": "BAJISTA", "activa": True, "origen_mov": f"AUTO PANICO {entrada:.0f}->{tiempo_fuera/3600:.1f}h", "creada_en": ahora}
            BANDAS_TIEMPO_FUERA.pop(sym, None)
        elif tipo=="BAJISTA" and fuera_tipo=="ARRIBA" and tiempo_fuera > tiempo_optimo:
            BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio, "tope": precio*1.10, "tipo": "NORMAL", "activa": True, "origen_mov": f"AUTO CAZA {tiempo_fuera/3600:.1f}h", "creada_en": ahora}
            BANDAS_TIEMPO_FUERA.pop(sym, None)
def es_rentable(tp_bruto, estrategia="RATA"):
    min_neto = FILTRO_NETO_MIN_MOJARRA if estrategia in ["MOJARRA","PIRANA_BLANCA","PIRANA"] else FILTRO_NETO_MIN
    return (tp_bruto - COMISION_TOTAL) >= min_neto, tp_bruto - COMISION_TOTAL
def contar_posiciones_globales():
    counts = {}; total_tib = 0
    for uid, lista in POSICIONES_ABIERTAS.items():
        if not isinstance(lista, list): continue
        for p in lista:
            if p.get("estrategia") == "PIRANA": continue
            key = (p.get("symbol"), p.get("estrategia"))
            counts[key] = counts.get(key, 0) + 1
            if p.get("estrategia") == "TIBURON": total_tib += 1
    return counts, total_tib
def banda_txt_display(k,v):
    base = f"🎯 BANDA {k} {v['entrada_tiburon']:.0f}->{v['tope']:.0f} {v['tipo']}"
    if v.get("origen_mov"):
        base += f" MOVIL"
    return base
def banda_txt_api(k,v):
    return f"{k.replace('USDT','')} {v.get('tipo','')}"
def notificar_caza(sym, tipo, precio, tp, sl, banda_txt, usdt, motivo=""):
    try:
        emojis = {"RATA":"🐀 RATA 5m","LOBO":"🐺 LOBO 1h","TIBURON":"🦈 TIBURON 1d","KRAKEN":"🦑 KRAKEN","PIRANA":"🐟 PIRAÑA","MOJARRA":"🐟 MOJARRA","PIRANA_BLANCA":"🐟 PIRAÑA"}
        emoji = emojis.get(tipo, "🎯")
        msg = f"{emoji} ¡PRESA CAZADA!\nPar: {sym}\nEntrada: ${precio:.2f}\nMonto: ${usdt:.2f}\nTP: {tp}% | SL: {sl}%\nBanda: {banda_txt}\n{motivo[:100]}\nExp: {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n🌐 {WEB_URL}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except Exception as e: print(f"notif caza err {e}")
def notificar_cierre(sym, tipo, entrada, salida, ganancia_usdt, ganancia_pct, es_tp, subtipo=""):
    try:
        emojis = {"RATA":"🐀","LOBO":"🐺","TIBURON":"🦈","KRAKEN":"🦑","PIRANA":"🐟","PIRANA_BLANCA":"🐟","MOJARRA":"🐟"}
        emoji = emojis.get(tipo, "🎯")
        u = USUARIOS.get(ADMINS_IDS[0], {})
        hoy = u.get("neto_hoy",0)
        total = (u.get("balance",0)-u.get("capital_inicial",0))
        if es_tp:
            msg = f"🐺☠️ PRESA DEVORADA ☠️🐺\n{emoji} {tipo} {sym}\n${entrada:.2f} -> ${salida:.2f}\n+${ganancia_usdt:.2f} ({ganancia_pct:+.2f}%)\nHoy: ${hoy:+.2f} Total: ${total:+.2f}\nExp: {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}"
        else:
            msg = f"🏃‍♂️💨 ¡ESCAPÓ LA PRESA! 💨🏃\n{emoji} {tipo} {sym}\n${entrada:.2f} -> ${salida:.2f}\n${ganancia_usdt:.2f} ({ganancia_pct:+.2f}%)\nHoy: ${hoy:+.2f} Total: ${total:+.2f}\nLa manada la vuelve a oler..."
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except Exception as e: print(f"notif cierre err {e}")

def notificar_cazando(sym, regimen):
    try:
        msg = f"👀 CAZANDO {sym} {regimen} V50.15 MOJx3 0.15% PIRAx2 0.30%"
        ahora = time.time()
        key = f"caz_{sym}"
        if key in ULTIMO_CAZANDO and ahora - ULTIMO_CAZANDO[key] < 300:
            return
        ULTIMO_CAZANDO[key] = ahora
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except: pass

def mandar_pensamiento_telegram():
    global ULTIMO_PENSAMIENTO
    try:
        ahora = time.time()
        if ahora - ULTIMO_PENSAMIENTO < 1800:
            return
        ULTIMO_PENSAMIENTO = ahora
        regs_txt = "\n".join([f"{k}: {v}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO.get("regimen","LINEAL")
        bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
        ok, motivo, sym, est, fuerza = detectar_BI_CEREBRO(ESTADO.get("regimen","LINEAL"))
        if ok:
            texto = f"🧠 PENSAMIENTO LOBO V50.15\n{regs_txt}\n{bandas_txt}\nEstrategia: {est} en {sym} ({fuerza:.2f})\n{motivo[:120]}"
        else:
            texto = f"🧠 MERCADO EN LECTURA V50.15\n{regs_txt}\n{bandas_txt}\nAcechando... {motivo[:100]}\nTPs {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, texto)
                except: pass
    except Exception as e:
        print(f"pensamiento err {e}")

def detectar_BI_CEREBRO(regimen):
    counts_global, total_tib_global = contar_posiciones_globales()
    tib_por_moneda = {}; kraken_por_moneda = {}
    for uid, lista in POSICIONES_ABIERTAS.items():
        if not isinstance(lista, list): continue
        for p in lista:
            sym = p.get("symbol")
            if p.get("estrategia") == "TIBURON": tib_por_moneda[sym] = tib_por_moneda.get(sym,0)+1
            if p.get("estrategia") == "KRAKEN": kraken_por_moneda[sym] = kraken_por_moneda.get(sym,0)+1
    mejor_motivo=""; mejor_sym=""; mejor_fuerza=0; mejor_est=None
    for sym in MONEDAS_ACTIVAS:
        total_madres_en_sym = sum(1 for uid2, lista2 in POSICIONES_ABIERTAS.items() for p in lista2 if p.get("symbol")==sym and p.get("estrategia") in ["RATA","LOBO","TIBURON","KRAKEN","RATA_NEGRA","LOBO_NEGRO"])
        tib_en_sym = tib_por_moneda.get(sym,0)
        kraken_en_sym = kraken_por_moneda.get(sym,0)
        reg_sym = ESTADO.get("regimenes",{}).get(sym,"LINEAL").split()[0]
        if reg_sym == "ALCISTA_FUERTE": orden = ["MOJARRA","PIRANA_BLANCA","LOBO","RATA","TIBURON"]
        elif reg_sym in ["CRASH","BAJISTA"]: orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","KRAKEN","RATA_NEGRA","LOBO_NEGRO","MOJARRA"]
        elif reg_sym == "ALCISTA": orden = ["MOJARRA","PIRANA_BLANCA","RATA","LOBO"]
        elif reg_sym == "LINEAL_MUERTO": orden = ["MOJARRA", "PIRANA_BLANCA"]
        else: orden = ["MOJARRA","PIRANA_BLANCA","RATA","LOBO","TIBURON","KRAKEN"]
        permitidas = MAPA_ANIDADO_V50_9.get(reg_sym, ["MOJARRA","PIRANA_BLANCA"])
        for nombre in orden:
            if nombre not in permitidas: continue
            MADRES = ["RATA","LOBO","TIBURON","KRAKEN","RATA_NEGRA","LOBO_NEGRO"]
            if nombre in MADRES and total_madres_en_sym >= 3: continue
            if nombre == "KRAKEN" and kraken_en_sym >= 1: continue
            if nombre == "TIBURON" and tib_en_sym >= 1: continue
            if nombre == "TIBURON" and total_tib_global >= 2: continue
            if nombre=="RATA": ok,motivo,wr = detectar_RATA_sym(sym, "RATA")
            elif nombre=="MOJARRA": ok,motivo,wr = detectar_RATA_sym(sym, "MOJARRA")
            elif nombre in ["PIRANA_BLANCA","PIRANA"]: ok,motivo,wr = detectar_RATA_sym(sym, "PIRANA_BLANCA")
            elif nombre in ["RATA_NEGRA","PIRANA_NEGRA","MOJARRA_NEGRA","LOBO_NEGRO"]: ok,motivo,wr = detectar_RATA_sym(sym, nombre)
            elif nombre=="LOBO": ok,motivo,wr = detectar_LOBO_sym(sym)
            elif nombre=="TIBURON": ok,motivo,wr = detectar_TIBURON_sym(sym)
            else: ok,motivo,wr = detectar_KRAKEN_sym(sym)
            tp_a = tp_adaptativo(sym, nombre if nombre in ESTRATEGIAS_V45 else "RATA")
            if ok and wr > mejor_fuerza and es_rentable(tp_a, nombre)[0]:
                mejor_fuerza=wr; mejor_est=nombre; mejor_motivo=f"[{sym} {reg_sym}] {motivo} TP{tp_a}% V50.15"; mejor_sym=sym
    if mejor_est: return True, mejor_motivo, mejor_sym, mejor_est, mejor_fuerza
    return False, f"V50.15 ACECHANDO TESTNET MANADA LIBRE", MONEDAS_ACTIVAS[0], None, 0

def check_reset_diario(u):
    hoy=ahora_art().strftime("%Y-%m-%d")
    if u.get("fecha_hoy")!=hoy:
        u["fecha_hoy"]=hoy; u["neto_hoy"]=0.0; u["ops_hoy"]=0
        for k in list(u.get("estrategias", {}).keys()):
            try: u["estrategias"][k]["ops"]=0
            except: pass

def get_user_data(uid):
    uid=int(uid)
    with LOCK:
        if uid not in USUARIOS:
            USUARIOS[uid]={"user_id":uid,"prendido":False,"balance":BALANCE_INICIAL,"capital_inicial":BALANCE_INICIAL,"neto_hoy":0.0,"ops_hoy":0,"ganadas":0,"perdidas":0,"modo":"ESPERANDO","mercado":"Tocá PRENDER","ultima_op":{}, "historial":[],"estrategias":{k:{"ops":0,"ganadas":0,"neto":0.0} for k in ESTRATEGIAS_V45},"fecha_hoy":ahora_art().strftime("%Y-%m-%d")}
        u = USUARIOS[uid]
        if u.get("balance",0) < 100:
            u["balance"] = BALANCE_INICIAL
        if u.get("capital_inicial",0) < 100:
            u["capital_inicial"] = BALANCE_INICIAL
        if "estrategias" not in u or not isinstance(u.get("estrategias"), dict):
            u["estrategias"] = {}
        for k in ESTRATEGIAS_V45:
            if k not in u["estrategias"]:
                u["estrategias"][k] = {"ops":0,"ganadas":0,"neto":0.0}
        check_reset_diario(u)
        return u

def guardar_datos():
    try:
        with LOCK:
            with open(DATA_FILE,"w") as f: json.dump(USUARIOS,f,indent=2)
            with open(os.path.join(DATA_DIR,"monedas_activas.json"),"w") as f: json.dump(MONEDAS_ACTIVAS,f)
            with open(POS_FILE,"w") as f: json.dump(POSICIONES_ABIERTAS,f,indent=2)
            with open(BANDA_FILE,"w") as f: json.dump(BANDAS_ACTIVAS,f,indent=2)
            with open(CONTADOR_FILE,"w") as f: json.dump({"tps": CONTADOR_TP_EXPANSION, "monedas": MONEDAS_ACTIVAS, "tanque": TANQUE_BNB_USDT}, f, indent=2)
            with open(os.path.join(DATA_DIR,"pirana_v50.json"),"w") as f: json.dump({"estado": ESTADO_PIRANA, "estado_negra": ESTADO_PIRANA_NEGRA, "cache": CANDIDATAS_CACHE, "bandas_tiempo": BANDAS_TIEMPO_FUERA},f,indent=2)
    except: pass

def cargar_datos():
    global MONEDAS_ACTIVAS, POSICIONES_ABIERTAS, BANDAS_ACTIVAS, ESTADO_PIRANA, ESTADO_PIRANA_NEGRA, CANDIDATAS_CACHE, BANDAS_TIEMPO_FUERA, CONTADOR_TP_EXPANSION, TANQUE_BNB_USDT
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,"r") as f:
                data=json.load(f)
                for k,v in data.items():
                    if isinstance(v, dict):
                        if v.get("balance",0) < 100:
                            v["balance"] = BALANCE_INICIAL
                        if v.get("capital_inicial",0) < 100:
                            v["capital_inicial"] = BALANCE_INICIAL
                        if "estrategias" not in v or not isinstance(v.get("estrategias"), dict):
                            v["estrategias"] = {}
                        for ek in ESTRATEGIAS_V45:
                            if ek not in v["estrategias"]:
                                v["estrategias"][ek] = {"ops":0,"ganadas":0,"neto":0.0}
                    USUARIOS[int(k)]=v
        if os.path.exists(os.path.join(DATA_DIR,"monedas_activas.json")):
            with open(os.path.join(DATA_DIR,"monedas_activas.json"),"r") as f: MONEDAS_ACTIVAS=json.load(f)
        if os.path.exists(POS_FILE):
            with open(POS_FILE,"r") as f:
                raw=json.load(f)
                for k,v in raw.items():
                    try: POSICIONES_ABIERTAS[int(k)]=v
                    except: POSICIONES_ABIERTAS[k]=v
        if os.path.exists(BANDA_FILE):
            with open(BANDA_FILE,"r") as f: BANDAS_ACTIVAS=json.load(f)
        if os.path.exists(CONTADOR_FILE):
            with open(CONTADOR_FILE,"r") as f:
                d=json.load(f)
                CONTADOR_TP_EXPANSION = float(d.get("tps",0))
                if d.get("monedas"): MONEDAS_ACTIVAS = d.get("monedas")
                if d.get("tanque"): TANQUE_BNB_USDT = float(d.get("tanque"))
        if os.path.exists(os.path.join(DATA_DIR,"pirana_v50.json")):
            with open(os.path.join(DATA_DIR,"pirana_v50.json"),"r") as f:
                pj=json.load(f)
                ESTADO_PIRANA=pj.get("estado",{})
                ESTADO_PIRANA_NEGRA=pj.get("estado_negra",{})
                BANDAS_TIEMPO_FUERA=pj.get("bandas_tiempo",{})
                c = pj.get("cache")
                if c: CANDIDATAS_CACHE.update(c)
    except Exception as e: print(f"cargar error {e}")

def limpiar_pos_viejas():
    try:
        for uid in list(POSICIONES_ABIERTAS.keys()):
            lista = POSICIONES_ABIERTAS[uid]
            if not isinstance(lista, list): continue
            for p in lista:
                if p.get("estrategia")=="PIRANA" and p.get("tp",0) > 1.6:
                    p["tp"] = 0.6
        guardar_datos()
    except: pass

def verificar_tanque_bnb():
    global REAL_BALANCE_BNB
    try:
        if not client: return True
        acc=client.get_account()
        bnb=0
        for b in acc['balances']:
            if b['asset']=='BNB': bnb=float(b['free'])+float(b['locked'])
        REAL_BALANCE_BNB=bnb
        precio_bnb = get_precio_robusto("BNBUSDT")
        valor_bnb_usdt = bnb * precio_bnb
        if valor_bnb_usdt < TANQUE_BNB_MIN:
            ejecutar_orden_real("BNBUSDT","BUY", TANQUE_BNB_RECARGA)
            return False
        return True
    except: return True

def ejecutar_orden_real(symbol, side, usdt_amount):
    try:
        if not client:
            return True, {"simulado": True}, get_precio_robusto(symbol)
        info = client.get_symbol_info(symbol)
        lot = [f for f in info['filters'] if f['filterType']=='LOT_SIZE'][0]
        step = float(lot['stepSize']); min_qty = float(lot['minQty'])
        precio = get_precio_robusto(symbol)
        qty = usdt_amount / precio if precio!=0 else usdt_amount/1000
        if step > 0:
            precision = int(round(-math.log10(step),0)) if step < 1 else 0
            qty = math.floor(qty / step) * step
            qty = round(qty, precision)
        if qty < min_qty: qty = min_qty
        order = client.create_order(symbol=symbol, side=side, type='MARKET', quantity=qty)
        return True, order, precio
    except Exception as e:
        if IS_TESTNET:
            return True, {"simulado": True, "error": str(e)}, get_precio_robusto(symbol)
        return False, str(e)[:200], 0

def detectar_mejor_candidata():
    mejor = None; mejor_wr = 0
    for sym in CANDIDATAS:
        if sym in MONEDAS_ACTIVAS: continue
        try:
            ok1,m1,wr1 = detectar_RATA_sym(sym)
            ok2,m2,wr2 = detectar_LOBO_sym(sym)
            ok3,m3,wr3 = detectar_TIBURON_sym(sym)
            ok4,m4,wr4 = detectar_KRAKEN_sym(sym)
            wr_total = wr1+wr2+wr3+wr4
            if wr_total > mejor_wr:
                mejor_wr = wr_total
                mejor = sym
        except: continue
    return mejor, mejor_wr

def intentar_expandir(user_id_notify=None):
    global CONTADOR_TP_EXPANSION, MONEDAS_ACTIVAS
    if CONTADOR_TP_EXPANSION < META_TP_PARA_EXPANDIR: return False
    if len(MONEDAS_ACTIVAS) >= MAX_MONEDAS: return False
    mejor_sym, wr = detectar_mejor_candidata()
    if not mejor_sym: return False
    msg = f"🚀 META {META_TP_PARA_EXPANDIR:.0f} TPs\nCandidata: {mejor_sym} WR {wr:.2f}\nActual {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} -> {len(MONEDAS_ACTIVAS)+1}/{MAX_MONEDAS}\n¿Autorizas sumar {mejor_sym}?"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"✅ AUTORIZAR {mejor_sym}", callback_data=f"AUTH_ADD_{mejor_sym}"), types.InlineKeyboardButton(f"❌ RECHAZAR", callback_data=f"REJECT_{mejor_sym}"))
    try:
        targets = ADMINS_IDS if not user_id_notify else [user_id_notify]
        for uid in targets: bot.send_message(uid, msg, reply_markup=kb)
    except: pass
    return False

def escanear_candidatas_y_proponer():
    ahora = time.time()
    if ahora - CANDIDATAS_CACHE.get("_ultimo_scan",0) < TIEMPO_ESCANEO_CANDIDATAS: return
    CANDIDATAS_CACHE["_ultimo_scan"] = ahora
    if CONTADOR_TP_EXPANSION < META_TP_PARA_EXPANDIR * 0.8: return
    mejor, wr = detectar_mejor_candidata()
    if mejor: CANDIDATAS_CACHE["proxima"] = mejor

def motor_v45():
    global CONTADOR_TP_EXPANSION
    print(f">>> MOTOR V50.15.1 FIX MANADA LIBRE MOJx3 0.15% PIRAx2 0.30% {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}")
    time.sleep(5)
    while True:
        try:
            for sym in list(MONEDAS_ACTIVAS):
                reg, det = detectar_regimen_sym(sym)
                ESTADO["regimenes"][sym] = f"{reg} {det}"
                if sym=="BTCUSDT":
                    ESTADO["btc"]=get_precio_robusto(sym)
                    ESTADO["regimen"]=reg
                if sym=="BNBUSDT":
                    ESTADO["bnb"]=get_precio_robusto(sym)
        except: pass
        gestionar_bandas_moviles()
        limpiar_pos_viejas()
        verificar_tanque_bnb()
        mandar_pensamiento_telegram()
        escanear_candidatas_y_proponer()
        for user_id in list(USUARIOS.keys()):
            u=USUARIOS[user_id]
            if user_id not in POSICIONES_ABIERTAS: POSICIONES_ABIERTAS[user_id] = []
            for pos in POSICIONES_ABIERTAS[user_id][:]:
                try:
                    precio_actual = get_precio_robusto(pos["symbol"])
                    if precio_actual == 0:
                        continue
                    tp_price = pos["entrada"] * (1 + pos["tp"]/100)
                    sl_price = pos["entrada"] * (1 + pos["sl"]/100)
                    cerrar = None
                    if precio_actual >= tp_price: cerrar = "TP"
                    elif precio_actual <= sl_price: cerrar = "SL"
                    if cerrar:
                        exito = True
                        res = None
                        if client:
                            try:
                                exito, res, _ = ejecutar_orden_real(pos["symbol"], "SELL", pos["usdt"])
                            except Exception as e:
                                exito = True
                                res = str(e)
                        pnl_bruto = (precio_actual - pos["entrada"]) / pos["entrada"] * pos["usdt"]
                        comision = pos["usdt"] * COMISION_TOTAL/100
                        pnl = pnl_bruto - comision
                        pnl_pct = (precio_actual - pos["entrada"])/pos["entrada"]*100 if pos["entrada"]!=0 else 0
                        es_tp = cerrar == "TP"
                        if es_tp:
                            u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["ganadas"]+=1
                            CONTADOR_TP_EXPANSION += 1
                            if CONTADOR_TP_EXPANSION >= META_TP_PARA_EXPANDIR: intentar_expandir(user_id)
                        else:
                            u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["perdidas"]+=1
                        # FIX V50.15.1 - ANTI KeyError MOJARRA
                        estr = pos.get("estrategia", "MOJARRA")
                        if estr not in u.get("estrategias", {}):
                            u["estrategias"][estr] = {"ops":0,"ganadas":0,"neto":0.0}
                        u["estrategias"][estr]["ops"]+=1
                        u["estrategias"][estr]["neto"]+=pnl
                        u["ops_hoy"]+=1
                        u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} {estr} {pos['symbol']} {cerrar} ${pnl:+.2f} TP:{pos['tp']}% V50.15.1")
                        notificar_cierre(pos["symbol"], estr, pos["entrada"], precio_actual, pnl, pnl_pct, es_tp, pos.get("subtipo",""))
                        POSICIONES_ABIERTAS[user_id].remove(pos)
                        guardar_datos()
                        if not exito:
                            print(f"WARN cierre con error pero liberado: {res}")
                except Exception as e:
                    print(f"Error cierre V50.15.1 {e} {pos.get('estrategia')}")
            if not u.get("prendido", False): continue
            ok,motivo,symbol_elegido,estrategia_elegida,fuerza = detectar_BI_CEREBRO(ESTADO.get("regimen","LINEAL"))
            if ok and estrategia_elegida:
                existentes = [p for p in POSICIONES_ABIERTAS.get(user_id,[]) if p.get('symbol')==symbol_elegido and p.get('estrategia')==estrategia_elegida]
                key_lock = f"{symbol_elegido}_{estrategia_elegida}"
                if key_lock in ULTIMO_TRADE and (time.time() - ULTIMO_TRADE[key_lock]) < ESTRATEGIAS_V45[estrategia_elegida]["cooldown"]:
                    continue
                if estrategia_elegida in ["MOJARRA","MOJARRA_NEGRA"]:
                    max_permitido = MAX_MOJARRA_POR_MONEDA
                    dist_requerida = DISTANCIA_MOJARRA_PCT
                elif estrategia_elegida in ["PIRANA_BLANCA","PIRANA","PIRANA_NEGRA"]:
                    max_permitido = MAX_PIRANA_POR_MONEDA
                    dist_requerida = DISTANCIA_PIRANA_PCT
                else:
                    max_permitido = 1
                    dist_requerida = 0.15
                if len(existentes) >= max_permitido:
                    continue
                precio_actual_tmp = get_precio_robusto(symbol_elegido)
                muy_cerca = False
                for ex in existentes:
                    dist = abs(precio_actual_tmp - ex['entrada']) / ex['entrada'] * 100 if ex['entrada']!=0 else 0
                    if dist < dist_requerida:
                        muy_cerca = True
                        break
                if muy_cerca:
                    continue
                if key_lock not in ULTIMO_CAZANDO or (time.time() - ULTIMO_CAZANDO.get(key_lock,0)) > 300:
                    notificar_cazando(symbol_elegido, motivo[:80])
                usdt_a_usar = max(10, u["balance"]*0.035)
                if estrategia_elegida == "KRAKEN": usdt_a_usar = max(200, min(300, u["balance"]*0.20))
                exito, res, precio = ejecutar_orden_real(symbol_elegido,"BUY",usdt_a_usar)
                if exito:
                    ULTIMO_TRADE[key_lock]=time.time()
                    ULTIMO_CAZANDO[key_lock]=time.time()
                    pos = {"symbol": symbol_elegido, "estrategia": estrategia_elegida, "entrada": precio, "tp": tp_adaptativo(symbol_elegido, estrategia_elegida), "sl": ESTRATEGIAS_V45[estrategia_elegida]["sl_neto"], "usdt": usdt_a_usar, "hora": ahora_art().isoformat()}
                    POSICIONES_ABIERTAS[user_id].append(pos)
                    u["modo"]=f"{estrategia_elegida} {symbol_elegido} TP{pos['tp']}%"; u["mercado"]=motivo
                    if estrategia_elegida=="TIBURON": BANDAS_ACTIVAS[symbol_elegido] = {"entrada_tiburon": precio, "tope": precio*1.10, "tipo": "NORMAL", "activa": True, "creada_en": time.time()}
                    if estrategia_elegida=="KRAKEN": BANDAS_ACTIVAS[symbol_elegido] = {"entrada_tiburon": precio*0.97, "tope": precio*0.995, "tipo": "BAJISTA", "activa": True, "creada_en": time.time()}
                    b = BANDAS_ACTIVAS.get(symbol_elegido,{})
                    banda_txt = f"{b.get('entrada_tiburon',precio*0.97):.0f}->{b.get('tope',precio*1.10):.0f} {b.get('tipo','')}"
                    notificar_caza(symbol_elegido, estrategia_elegida, precio, pos['tp'], ESTRATEGIAS_V45[estrategia_elegida]["sl_neto"], banda_txt, usdt_a_usar, motivo)
        guardar_datos()
        time.sleep(60)

def get_menu():
    m=types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("🚀 PRENDER","🧬 EVOLUCIONAR")
    m.add("📊 BALANCE","📜 HISTORIAL")
    m.add("💸 RETIRAR GANANCIAS","💸 RETIRAR TODO")
    m.add("📦 ORDENES")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    u=get_user_data(m.chat.id)
    estado_txt = f"🟢 V50.15.1 FIX MANADA LIBRE {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}" if u["prendido"] else "🔴 APAGADO"
    regs="\n".join([f"{k}:{v.split()[0]}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO['regimen'].split()[0]
    bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    ganancia = u["balance"] - u["capital_inicial"]
    bot.send_message(m.chat.id,f"🦁 V50.15.1 FIX {estado_txt}\n{regs}\n{bandas_txt}\n{'+'.join(MONEDAS_ACTIVAS)}\nBal ${u['balance']:.2f}\nGan ${ganancia:.2f}\n{WEB_URL}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="📊 BALANCE")
def balance(m):
    u=get_user_data(m.chat.id)
    ganancia_historica = u["balance"]-u["capital_inicial"]
    regs="\n".join([f"{k}: {v.split()[0]}" for k,v in ESTADO.get("regimenes",{}).items()])
    pos_txt = "\n".join([f"🔒 {p['symbol']} {p['estrategia']} Ent {p['entrada']:.2f} TP{p['tp']}%" for p in POSICIONES_ABIERTAS.get(m.chat.id,[])]) or "Sin pos"
    bot.send_message(m.chat.id,f"💰 V50.15.1 FIX {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n{regs}\n{pos_txt}\nBal ${u['balance']:.2f} Hist ${ganancia_historica:+.2f}\nHoy ${u['neto_hoy']:+.2f}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="🚀 PRENDER")
def prender(m):
    u=get_user_data(m.chat.id)
    u["prendido"]=True; u["modo"]="CAZANDO V50.15.1 MANADA LIBRE"
    guardar_datos()
    bot.send_message(m.chat.id,f"🚀 MANADA PRENDIDA V50.15.1 FIX MOJx3 0.15% PIRAx2 0.30% {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\nBolsa Unica ${u['balance']:.2f}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="🧬 EVOLUCIONAR")
def evolucionar(m):
    u=get_user_data(m.chat.id)
    regs="\n".join([f"{k}: {v}" for k,v in ESTADO.get("regimenes",{}).items()])
    bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas V50.15.1"
    clima = f"🌪️ CLIMA BTC {ESTADO.get('regimen','LINEAL')} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} TPs {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} MOJx3+PIRAx2 LIBRE"
    bot.send_message(m.chat.id,f"🧬 {clima}\n{regs}\n{bandas_txt}\n{'+'.join(MONEDAS_ACTIVAS)}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="📜 HISTORIAL")
def historial(m):
    u=get_user_data(m.chat.id)
    hist = u.get("historial",[])[-15:]
    txt = "\n".join(hist) or "Sin historial"
    bot.send_message(m.chat.id,f"📜 HISTORIAL V50.15.1 FIX\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="📦 ORDENES")
def ordenes(m):
    lista = POSICIONES_ABIERTAS.get(m.chat.id,[])
    if not lista:
        bot.send_message(m.chat.id,"📦 Sin ordenes abiertas V50.15.1",reply_markup=get_menu())
        return
    txt=""
    for p in lista:
        txt+=f"{p['symbol']} {p['estrategia']} ${p['entrada']:.2f} TP{p['tp']}% SL{p['sl']}% ${p['usdt']:.0f}\n"
    bot.send_message(m.chat.id,f"📦 ORDENES V50.15.1 MANADA LIBRE {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="💸 RETIRAR GANANCIAS")
def retirar_gan(m):
    u=get_user_data(m.chat.id)
    gan = u["balance"]-u["capital_inicial"]
    if gan <= 0:
        bot.send_message(m.chat.id,f"💸 Sin ganancias para retirar. Gan ${gan:.2f}",reply_markup=get_menu())
        return
    u["balance"]=BALANCE_INICIAL
    u["capital_inicial"]=BALANCE_INICIAL
    u["neto_hoy"]=0
    guardar_datos()
    bot.send_message(m.chat.id,f"💸 GANANCIAS RETIRADAS V50.15.1 ${gan:.2f}\nBolsa unica vuelve a capital inicial ${u['capital_inicial']:.2f}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="💸 RETIRAR TODO")
def retirar_todo(m):
    u=get_user_data(m.chat.id)
    total=u["balance"]
    gan = total - u["capital_inicial"]
    u["balance"]=BALANCE_INICIAL
    u["capital_inicial"]=BALANCE_INICIAL
    u["neto_hoy"]=0
    u["ganadas"]=0
    u["perdidas"]=0
    u["ops_hoy"]=0
    u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} RETIRO TOTAL ${total:.2f} Gan ${gan:.2f} -> RESET 10k")
    POSICIONES_ABIERTAS[m.chat.id]=[]
    guardar_datos()
    bot.send_message(m.chat.id,f"💸 TODO RETIRADO V50.15.1 ${total:.2f} (Gan ${gan:.2f})\nBolsa reseteada a ${BALANCE_INICIAL:.2f}\nCerraste todo.",reply_markup=get_menu())

@bot.message_handler(func=lambda m: True)
def fallback(m):
    try:
        txt=m.text.upper()
        if "BNB" in txt or "BTC" in txt:
            sym = txt.replace(" ","").replace("$","")
            if "USDT" not in sym: sym+="USDT"
            precio=get_precio_robusto(sym)
            bot.send_message(m.chat.id,f"💲 {sym} ${precio:.2f} V50.15.1",reply_markup=get_menu())
        else:
            bot.send_message(m.chat.id,f"🦁 V50.15.1 FIX MANADA LIBRE MOJx3 0.15% PIRAx2 0.30% Comandos: PRENDER, BALANCE, EVOLUCIONAR, HISTORIAL, ORDENES\n{len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} TPs {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f}\n{WEB_URL}",reply_markup=get_menu())
    except:
        bot.send_message(m.chat.id,"🦁 V50.15.1 FIX",reply_markup=get_menu())

@app.route('/api/detalles_mercado')
def detalles_mercado():
    def info_sym(sym):
        try:
            d5 = get_velas(sym,"5m",100)
            d1h = get_velas(sym,"1h",100)
            precio = get_precio_robusto(sym)
            rsi = rsi_calc(d5["closes"],7) if d5 else 50
            adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 15
            atr = atr_calc(d1h,14) if d1h else 0
            atr_pct = (atr/precio*100) if precio else 0
            ema9 = ema_calc(d5["closes"][-20:],9) if d5 else 0
            ema20 = ema_calc(d5["closes"][-20:],20) if d5 else 0
            vol_ratio = (d5["vols"][-1] / (sum(d5["vols"][-20:])/20)) if d5 and len(d5["vols"])>=20 else 1.0
            reg_full = ESTADO.get("regimenes",{}).get(sym,"LINEAL")
            reg = reg_full.split()[0] if reg_full else "LINEAL"
            zona = "CAZANDO 🟢" if rsi<35 else "ZONA 🟡"
            mapa_mejor = {"LINEAL_MUERTO": "MANADA LIBRE MOJARRA+PIRANA","LINEAL": "MOJARRA 0.3% + RATA","ALCISTA": "MOJARRA + LOBO","ALCISTA_FUERTE": "MOJARRA + TIBURON","BAJISTA": "KRAKEN + SHORTS","CRASH": "MOJARRA + KRAKEN"}
            mejor = mapa_mejor.get(reg, "MANADA LIBRE")
            accion = "CAZAR AHORA" if rsi<35 else "NO CAZAR - ESPERAR RSI<35"
            banda = BANDAS_ACTIVAS.get(sym,{})
            madre = banda.get("tipo","NORMAL") if banda.get("activa") else "NORMAL"
            return {"regimen": reg, "reg_detalle": reg_full,"adx": round(adx,1), "rsi": round(rsi,1),"zona": zona, "ema": "9>20" if ema9>ema20 else "9<20","atr": round(atr_pct,2), "vol": round(vol_ratio,1),"precio": round(precio,2), "madre": madre,"mejor_estrategia": mejor, "accion": accion, "si_cae": mejor}
        except Exception as e:
            return {"regimen":"LINEAL","adx":15,"rsi":50,"zona":"ZONA","ema":"9=20","atr":0,"vol":1,"precio":0,"madre":"NORMAL","mejor_estrategia":"MANADA LIBRE","accion":"ESPERAR","si_cae":"MOJARRA+PIRANA","error":str(e)[:80]}
    return jsonify({ "BTCUSDT": info_sym("BTCUSDT"), "BNBUSDT": info_sym("BNBUSDT"), "BTC": info_sym("BTCUSDT"), "BNB": info_sym("BNBUSDT") })

@app.route('/')
def home():
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>V50.15.1 FIX MANADA LIBRE</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}.top{padding:10px;background:#1e222d;position:sticky;top:0;z-index:20;font-size:13px;border-bottom:2px solid #00ff88}.card{position:relative;background:#1e222d;border-radius:8px;overflow:hidden;border:1px solid #2a2e39;margin-bottom:6px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px}.detalle-box{background:#0e1a15;border-top:1px solid #1e3d2f;color:#a7f3d0;font-family:monospace;font-size:11px;padding:8px 10px;line-height:1.4;min-height:62px}</style></head><body><div class="top" id="info">Cargando V50.15.1 FIX MANADA LIBRE MOJx3+PIRAx2...</div><div class="grid" id="charts_grid"></div><script>const MONEDAS=['BTCUSDT','BNBUSDT'];function createChart(sym){let id='tv_'+sym;let card=document.createElement('div');card.className='card';card.innerHTML=`<div id="${id}" style="height:350px"></div><div class="detalle-box" id="detalle-${sym}">⏳ Cargando detalle ${sym}...</div>`;document.getElementById('charts_grid').appendChild(card);new TradingView.widget({autosize:true,symbol:'BINANCE:'+sym,interval:'5',container_id:id,theme:'dark',style:'1',locale:'es'});}MONEDAS.forEach(s=>createChart(s));async function load(){let a=await (await fetch('/api/data')).json();document.getElementById('info').innerHTML='<b>V50.15.1 FIX MANADA LIBRE MOJx3 0.15% PIRAx2 0.30% | Bal $'+a.balance.toFixed(2)+' Gan $'+a.ganancia_total.toFixed(2)+'</b> | '+Object.entries(a.regimenes).map(e=>e[0].replace('USDT','')+':'+e[1].split(' ')[0]).join(' | ')+' | '+a.bandas_txt;}async function loadDetalles(){try{let d=await (await fetch('/api/detalles_mercado')).json();for(let sym of MONEDAS){let info=d[sym];if(!info) continue;document.getElementById('detalle-'+sym).innerHTML=`REGIMEN: ${info.regimen} (ADX ${info.adx}) | Madre: ${info.madre} | RSI ${info.rsi} ${info.zona} | EMA ${info.ema} | ATR ${info.atr}% | Vol ${info.vol}x<br><b>Mejor estrategia: ${info.mejor_estrategia}</b> | ${info.accion} | Si cae: ${info.si_cae} | $${info.precio}`;}}catch(e){}}setInterval(load,3000);load();setInterval(loadDetalles,3000);loadDetalles();</script></body></html>"""
    return render_template_string(html)

@app.route('/api/data')
def api_data():
    target=ADMINS_IDS[0]
    if target not in USUARIOS: get_user_data(target)
    u=USUARIOS[target]
    bandas_txt = " | ".join([banda_txt_api(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    precios = {}
    for sym in MONEDAS_ACTIVAS:
        precios[sym] = get_precio_robusto(sym)
    posiciones = POSICIONES_ABIERTAS.get(target, [])
    ganancia_total = u["balance"]-u["capital_inicial"]
    return jsonify({"balance":u["balance"],"capital_inicial":u["capital_inicial"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"regimen_btc":ESTADO.get("regimen","LINEAL"),"regimenes":ESTADO.get("regimenes",{}),"estrategias":u["estrategias"],"monedas":MONEDAS_ACTIVAS,"ganancia_total": ganancia_total,"bandas": BANDAS_ACTIVAS, "bandas_txt": bandas_txt, "posiciones": posiciones, "precios": precios, "meta_proxima": META_TP_PARA_EXPANDIR, "tps_actual": CONTADOR_TP_EXPANSION, "mapa_anidado": MAPA_ANIDADO_V50_9, "version": "V50.15.1 FIX MANADA LIBRE MOJx3 0.15% PIRAx2 0.30%"})

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except: pass
    return "ok", 200

@app.route('/set_webhook')
def set_webhook_route():
    try:
        bot.remove_webhook(); time.sleep(1)
        bot.set_webhook(url=f"{WEB_URL}/{TOKEN}")
        return f"Webhook OK {WEB_URL}/{TOKEN}", 200
    except Exception as e: return f"Error {e}", 500

@bot.callback_query_handler(func=lambda call: True)
def callback_candidata(call):
    global MONEDAS_ACTIVAS, CONTADOR_TP_EXPANSION, TANQUE_BNB_USDT
    try:
        data = call.data
        if data.startswith("AUTH_ADD_"):
            sym = data.replace("AUTH_ADD_","")
            if sym not in MONEDAS_ACTIVAS and len(MONEDAS_ACTIVAS) < MAX_MONEDAS:
                MONEDAS_ACTIVAS.append(sym); CONTADOR_TP_EXPANSION = 0; TANQUE_BNB_USDT += TANQUE_POR_MONEDA
                guardar_datos()
                bot.answer_callback_query(call.id, f"{sym} AUTORIZADA!")
    except: pass

cargar_datos()
threading.Thread(target=motor_v45,daemon=True).start()
if __name__=='__main__':
    try: bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{WEB_URL}/{TOKEN}")
    except: pass
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
