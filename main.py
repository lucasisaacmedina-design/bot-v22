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
WEB_URL = os.getenv("WEB_URL", "https://lobobot22-v45.onrender.com").strip().rstrip("/")

MONEDAS_ACTIVAS = ["BTCUSDT", "BNBUSDT"]
CANDIDATAS = ["ETHUSDT","SOLUSDT","XRPUSDT","AVAXUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","DOTUSDT","LTCUSDT","TRXUSDT","MATICUSDT","SHIBUSDT"]
MAX_MONEDAS = 10
META_TP_PARA_EXPANDIR = 120.0
CONTADOR_TP_EXPANSION = 0
TANQUE_POR_MONEDA = 2.0
TANQUE_BNB_USDT = float(os.getenv("TANQUE", os.getenv("TANQUE_BNB_USDT", "20")))
TANQUE_BNB_MIN = float(os.getenv("TANQUE_BNB_MIN", "5.0"))
TANQUE_BNB_RECARGA = float(os.getenv("TANQUE_BNB_RECARGA", "8.0"))
TANQUE = TANQUE_BNB_USDT
COMISION_TOTAL = 0.15
FILTRO_NETO_MIN = 0.5
PIRANA_CONFIG = {"LOTE_FACTOR": 0.5,"TP": 0.8,"SL": -3.5,"MAX_POR_BANDA": 5,"RSI_MAX": 38,"COMISION_RT": 0.20,"NETO_MIN": 0.5,}
PIRANA_NEGRA_CONFIG = {"LOTE_FACTOR": 0.25,"TP": 0.8,"SL": -3.5,"MAX_POR_BANDA": 2,"RSI_MAX": 28,"VOL_FACTOR": 1.5,"COMISION_RT": 0.20,"COOLDOWN": 600,}
ESTADO_PIRANA = {}
ESTADO_PIRANA_NEGRA = {}
BOLSA_PIRANA = {"neto": 0.0, "ops": 0}
BOLSA_PIRANA_NEGRA = {"neto": 0.0, "ops": 0}
BANDAS_TIEMPO_FUERA = {}
TIEMPO_FUERA_NORMAL = 3*3600
TIEMPO_FUERA_BAJISTA = 1.5*3600
CANDIDATAS_CACHE = {"_ultimo_scan": 0, "_aviso_meta": 0, "proxima": None}
TIEMPO_ESCANEO_CANDIDATAS = 600
ESTRATEGIAS_V45 = {
    "RATA": {"tf": "5m", "desc": "RATA 5M BANDA", "rango_tp": (0.8, 1.5), "sl_neto": -4.0, "max_dia": 100, "cooldown": 180, "cooldown_rec": 180, "mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "LOBO": {"tf": "1h", "desc": "LOBO 1H BANDA", "rango_tp": (1.2, 2.2), "sl_neto": -5.0, "max_dia": 100, "cooldown": 300, "cooldown_rec": 300, "mercado_ideal": "ALCISTA", "tp_fijo_banda": 1.2},
    "TIBURON": {"tf": "1d", "desc": "TIBURON 5-10% BANDA", "rango_tp": (5.0, 10.0), "sl_neto": -8.0, "max_dia": 2, "cooldown": 14400, "mercado_ideal": "ALCISTA_FUERTE"},
    "KRAKEN": {"tf": "1h", "desc": "KRAKEN PANICO DESPLOME 3-5%", "rango_tp": (3.0, 5.0), "sl_neto": -8.0, "max_dia": 2, "cooldown": 3600, "mercado_ideal": "CRASH"},
    "PIRANA": {"tf": "5m", "desc": "PIRAÑA 0.8% MATERIALIZA", "rango_tp": (0.8, 1.5), "sl_neto": -3.5, "max_dia": 100, "cooldown": 60, "mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "PIRAÑA_NEGRA": {"tf": "5m", "desc": "PIRAÑA NEGRA BAJISTA", "rango_tp": (0.8, 1.5), "sl_neto": -3.5, "max_dia": 100, "cooldown": 600, "mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.8}
}
MAPA_ESTRATEGIA = {"LINEAL": "RATA 0.8-1.5%", "ALCISTA": "LOBO 1.2-2.2%", "ALCISTA_FUERTE": "TIBURON 5-10% BANDA", "CRASH": "KRAKEN PANICO 3-5%", "BAJISTA": "KRAKEN PANICO 3-5%"}
def estrategia_prevista(regimen_txt):
    reg = regimen_txt.split()[0] if regimen_txt else "LINEAL"
    return MAPA_ESTRATEGIA.get(reg, "RATA 0.8-1.5%")
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
CONTADOR_FILE=os.path.join(DATA_DIR,"contador_expansion.json")
os.makedirs(DATA_DIR,exist_ok=True)
ESTADO={"btc":0,"bnb":0,"regimen":"LINEAL","regimen_detalle":"Iniciando","regimenes":{},"estrategias_activas":{}}
USUARIOS={}; LOCK=threading.Lock()
POSICIONES_ABIERTAS = {}; BANDAS_ACTIVAS = {}; ULTIMO_TRADE = {}; ULTIMO_PENSAMIENTO = 0
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
def tp_adaptativo(symbol, estrategia):
    try:
        d1h = get_velas(symbol,"1h",100)
        if not d1h: return ESTRATEGIAS_V45[estrategia]["rango_tp"][0]
        adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
        atr = atr_calc(d1h, 14)
        precio = d1h["closes"][-1]
        atr_pct = (atr/precio*100) if precio!=0 else 0
        base = ESTRATEGIAS_V45[estrategia].get("tp_fijo_banda", ESTRATEGIAS_V45[estrategia]["rango_tp"][0])
        if estrategia == "LOBO":
            if adx > 35 and atr_pct > 1.2: return 2.2
            if adx < 18 and atr_pct < 0.7: return 1.2
            return 1.5
        if estrategia == "RATA":
            if adx > 30 and atr_pct > 1.0: return 1.5
            if adx < 18: return 0.8
            return 0.9
        if estrategia == "TIBURON":
            if adx > 30 and atr_pct > 1.5: return 10.0
            if adx < 20: return 5.0
            return 7.0
        if estrategia == "KRAKEN":
            if atr_pct > 2.0: return 5.0
            if adx > 35: return 4.0
            return 3.0
        if estrategia == "PIRANA" or estrategia == "PIRAÑA_NEGRA":
            if adx > 25: return 1.5
            return 0.8
        return base
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

# V50.8 ADAPTATIVO COMPLETO - TODO EL BOT SE ADAPTA - RSI38 LINEAL
def get_umbral_adaptativo(regimen):
    reg = regimen.split()[0] if regimen else "LINEAL"
    if reg == "ALCISTA_FUERTE":
        return {"rsi_kraken": 30.5, "rsi_pirana": 35, "rsi_pirana_negra": 30, "vsa_kraken": 1.3, "vsa_negra": 1.3, "adx_tiburon": 25, "rsi_lobo_min": 50, "rsi_rata_max": 38}
    elif reg == "ALCISTA":
        return {"rsi_kraken": 29.5, "rsi_pirana": 33, "rsi_pirana_negra": 29, "vsa_kraken": 1.4, "vsa_negra": 1.4, "adx_tiburon": 28, "rsi_lobo_min": 52, "rsi_rata_max": 35}
    elif reg == "LINEAL":
        return {"rsi_kraken": 29.0, "rsi_pirana": 38, "rsi_pirana_negra": 28, "vsa_kraken": 1.3, "vsa_negra": 1.3, "adx_tiburon": 28, "rsi_lobo_min": 55, "rsi_rata_max": 38}
    else:
        return {"rsi_kraken": 27.5, "rsi_pirana": 30, "rsi_pirana_negra": 28, "vsa_kraken": 1.6, "vsa_negra": 1.6, "adx_tiburon": 35, "rsi_lobo_min": 999, "rsi_rata_max": 30}

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
    d5=get_velas(symbol,"5m",100); d1h=get_velas(symbol,"1h",50)
    if not d5: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    sma20=sum(closes[-20:])/20; var=sum((x-sma20)**2 for x in closes[-20:])/20; std=var**0.5; lower=sma20-2*std
    precio=closes[-1]; vol_prom=sum(d5["vols"][-20:])/20; vol_actual=d5["vols"][-1]
    adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 15
    if precio<=lower and rsi<umb["rsi_rata_max"] and vol_actual>vol_prom*1.2:
        return True,f"[{symbol}] RATA ADAPT {reg.split()[0]} RSI{int(rsi)}<{umb['rsi_rata_max']} BBaja ADX{adx:.0f}", 0.68
    return False,f"[{symbol}] RATA {reg.split()[0]} esperando RSI{int(rsi)}/{umb['rsi_rata_max']} ADX{adx:.0f}", 0.30

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
        return True,f"[{symbol}] LOBO ADAPT {reg.split()[0]} ADX{adx:.0f} RET2.5%", 0.65
    return False,f"[{symbol}] LOBO ADAPT {reg.split()[0]} ADX{adx:.0f} esperando", 0.35

def detectar_TIBURON_sym(symbol):
    d=get_velas(symbol,"1d",210); d1h=get_velas(symbol,"1h",50)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d["closes"]; ema50=sum(closes[-50:])/50; rsi14=rsi_calc(closes,14)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 20
    if closes[-1] > ema50 and rsi14 > 45 and adx_1h > umb["adx_tiburon"]:
        return True,f"[{symbol}] TIBURON ADAPT {reg.split()[0]} ADX{adx_1h:.0f}>{umb['adx_tiburon']} RSI{int(rsi14)}", 0.85
    return False,f"[{symbol}] TIBU ADAPT {reg.split()[0]} ADX{adx_1h:.0f}/{umb['adx_tiburon']} esperando", 0.25

def detectar_KRAKEN_sym(symbol):
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    d5 = get_velas(symbol,"5m",10)
    caida_30m = 0
    if d5 and len(d5["closes"])>=7:
        caida_30m = (d5["closes"][-1] - d5["closes"][-7]) / d5["closes"][-7] * 100 if d5["closes"][-7]!=0 else 0
        if reg.split()[0] in ["BAJISTA","CRASH"] and caida_30m > -2.5:
            return False,f"[{symbol}] KRAKEN ADAPT {reg.split()[0]} caída {caida_30m:.1f}% esperando >2.5%",0.05
    d1h=get_velas(symbol,"1h",100); d1d=get_velas(symbol,"1d",30)
    if not d1h or not d1d: return False,f"{symbol} Sin velas",0
    closes_1h=d1h["closes"]; vols_1h=d1h["vols"]
    rsi_1h=rsi_calc(closes_1h,14); adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
    vol_prom_1h=sum(vols_1h[-21:-1])/20 if len(vols_1h)>=22 else sum(vols_1h)/len(vols_1h)
    vsa_mult = vols_1h[-1]/vol_prom_1h if vol_prom_1h!=0 else 0
    vsa_1h=vols_1h[-1]>vol_prom_1h*umb["vsa_kraken"] if vol_prom_1h!=0 else False
    min_20d=min(d1d["lows"][-20:]) if len(d1d["lows"])>=20 else min(d1d["lows"])
    precio=closes_1h[-1]
    if rsi_1h<umb["rsi_kraken"] and vsa_1h and adx_1h>25 and precio < min_20d*1.03:
        return True,f"[{symbol}] KRAKEN ADAPT {reg.split()[0]} RSI{int(rsi_1h)}<{umb['rsi_kraken']} ADX{adx_1h:.0f} VSAx{vsa_mult:.1f}>{umb['vsa_kraken']} CAIDA {caida_30m:.1f}%",0.95
    return False,f"[{symbol}] KRAKEN ADAPT {reg.split()[0]} ACECHANDO RSI{int(rsi_1h)}/{umb['rsi_kraken']} VSAx{vsa_mult:.1f}/{umb['vsa_kraken']}",0.08

def oportunidad_pirana(symbol, rsi, precio, banda):
    if banda.get("tipo")!= "NORMAL": return False
    if not (banda["entrada_tiburon"] <= precio <= banda["tope"]): return False
    umb = get_umbral_adaptativo(ESTADO.get("regimenes",{}).get(symbol,"LINEAL"))
    return rsi < umb["rsi_pirana"]

def oportunidad_pirana_negra(symbol, rsi, precio, banda, vol_actual, vol_prom):
    if banda.get("tipo")!= "BAJISTA": return False
    umb = get_umbral_adaptativo(ESTADO.get("regimenes",{}).get(symbol,"LINEAL"))
    if rsi > umb["rsi_pirana_negra"]: return False
    if vol_prom>0 and vol_actual < vol_prom*umb["vsa_negra"]: return False
    if not (banda["entrada_tiburon"] <= precio <= banda["tope"]): return False
    return True

def gestionar_bandas_moviles():
    global BANDAS_ACTIVAS, BANDAS_TIEMPO_FUERA
    ahora = time.time()
    for sym in list(BANDAS_ACTIVAS.keys()):
        banda = BANDAS_ACTIVAS.get(sym)
        if not banda or not banda.get("activa"):
            BANDAS_TIEMPO_FUERA.pop(sym, None); continue
        try: precio = float(client.get_symbol_ticker(symbol=sym)['price']) if client else ESTADO.get("btc" if "BTC" in sym else "bnb",0)
        except: precio = ESTADO.get("btc" if "BTC" in sym else "bnb",0)
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
            nueva_entrada = precio*0.97; nuevo_tope = precio*0.995
            BANDAS_ACTIVAS[sym] = {"entrada_tiburon": nueva_entrada, "tope": nuevo_tope, "tipo": "BAJISTA", "activa": True, "origen_mov": f"AUTO PANICO {entrada:.0f}->{tiempo_fuera/3600:.1f}h opt:{tiempo_optimo/3600:.1f}h"}
            BANDAS_TIEMPO_FUERA.pop(sym, None); guardar_datos()
        elif tipo=="BAJISTA" and fuera_tipo=="ARRIBA" and tiempo_fuera > tiempo_optimo:
            nueva_entrada = precio; nuevo_tope = precio*1.10
            BANDAS_ACTIVAS[sym] = {"entrada_tiburon": nueva_entrada, "tope": nuevo_tope, "tipo": "NORMAL", "activa": True, "origen_mov": f"AUTO CAZA {tiempo_fuera/3600:.1f}h opt:{tiempo_optimo/3600:.1f}h"}
            BANDAS_TIEMPO_FUERA.pop(sym, None); guardar_datos()

def es_rentable(tp_bruto): return (tp_bruto - COMISION_TOTAL) >= FILTRO_NETO_MIN, tp_bruto - COMISION_TOTAL
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
def contar_por_moneda():
    counts = {}
    for uid, lista in POSICIONES_ABIERTAS.items():
        if not isinstance(lista, list): continue
        for p in lista:
            if p.get("estrategia") == "PIRANA": continue
            sym = p.get("symbol")
            counts[sym] = counts.get(sym, 0) + 1
    return counts
def contar_kraken_por_moneda(sym):
    c=0
    for uid, lista in POSICIONES_ABIERTAS.items():
        if not isinstance(lista, list): continue
        for p in lista:
            if p.get("symbol")==sym and p.get("estrategia")=="KRAKEN":
                c+=1
    return c
def banda_txt_display(k,v):
    base = f"🎯 BANDA {k} {v['entrada_tiburon']:.0f}->{v['tope']:.0f} {v['tipo']}"
    if v.get("origen_mov"): base += f" MOVIL"
    return base
def banda_txt_api(k,v):
    return f"{k.replace('USDT','')} {v.get('tipo','')}"

def notificar_caza(sym, tipo, precio, tp, sl, banda_txt, usdt, motivo=""):
    try:
        emojis = {"RATA":"🐀 RATA 5m","LOBO":"🐺 LOBO 1h","TIBURON":"🦈 TIBURON 1d","KRAKEN":"🐙 KRAKEN","PIRANA":"🐟 PIRAÑA","PIRAÑA_NEGRA":"🐟⚫ PIRAÑA NEGRA"}
        t = tipo if tipo in emojis else "PIRANA" if "NEGRA" in str(tipo) else tipo
        if tipo=="PIRANA" and "NEGRA" in str(banda_txt): t="PIRAÑA_NEGRA"
        emoji = emojis.get(t, "🎯")
        msg = f"{emoji} ¡PRESA CAZADA!\nPar: {sym}\nEntrada: ${precio:.2f}\nMonto: ${usdt:.2f}\nTP: {tp}% | SL: {sl}%\nBanda: {banda_txt}\n{motivo[:100]}\nExp: {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n🌐 {WEB_URL}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except Exception as e: print(f"notif caza err {e}")

def notificar_cierre(sym, tipo, entrada, salida, ganancia_usdt, ganancia_pct, es_tp, subtipo=""):
    try:
        emojis = {"RATA":"🐀","LOBO":"🐺","TIBURON":"🦈","KRAKEN":"🐙","PIRANA":"🐟","PIRAÑA_NEGRA":"🐟⚫"}
        tp_tipo = tipo
        if subtipo=="NEGRA": tp_tipo="PIRAÑA_NEGRA"
        emoji = emojis.get(tp_tipo, "🎯")
        u = USUARIOS.get(ADMINS_IDS[0], {})
        hoy = u.get("neto_hoy",0)
        total = (u.get("balance",0)-u.get("capital_inicial",0)+BOLSA_PIRANA["neto"]+BOLSA_PIRANA_NEGRA["neto"])
        if es_tp:
            msg = f"🐺☠️ PRESA DEVORADA ☠️🐺\n{emoji} {tp_tipo} {sym}\n${entrada:.2f} -> ${salida:.2f}\n+${ganancia_usdt:.2f} ({ganancia_pct:+.2f}%)\nHoy: ${hoy:+.2f} Total: ${total:+.2f}\nExp: {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}"
        else:
            msg = f"🏃💨 ¡ESCAPÓ LA PRESA! 💨🏃\n{emoji} {tp_tipo} {sym}\n${entrada:.2f} -> ${salida:.2f}\n${ganancia_usdt:.2f} ({ganancia_pct:+.2f}%)\nHoy: ${hoy:+.2f} Total: ${total:+.2f}\nLa manada la vuelve a oler..."
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except Exception as e: print(f"notif cierre err {e}")

def mandar_pensamiento_telegram():
    global ULTIMO_PENSAMIENTO
    ahora = time.time()
    if ahora - ULTIMO_PENSAMIENTO < 1800: return
    ULTIMO_PENSAMIENTO = ahora
    try:
        for uid in list(USUARIOS.keys()):
            if not USUARIOS[uid].get("prendido"): continue
            lineas = []
            for sym in MONEDAS_ACTIVAS:
                banda = BANDAS_ACTIVAS.get(sym)
                d5 = get_velas(sym,"5m",20)
                rsi = rsi_calc(d5["closes"],7) if d5 else 50
                precio = ESTADO.get("btc" if "BTC" in sym else "bnb",0)
                if sym not in ["BTCUSDT","BNBUSDT"]:
                    try: precio = float(client.get_symbol_ticker(symbol=sym)['price']) if client else 0
                    except: pass
                reg = ESTADO.get("regimenes",{}).get(sym,"LINEAL").split()[0]
                umb = get_umbral_adaptativo(reg)
                if banda and banda.get("activa"):
                    tipo = banda.get("tipo","NORMAL")
                    entrada = banda["entrada_tiburon"]; tope = banda["tope"]
                    adentro = entrada*0.997 <= precio <= tope
                    if tipo=="NORMAL":
                        if not adentro:
                            estado_rsi = f"🔴 ACECHANDO RSI{int(rsi):.0f}/{umb['rsi_pirana']} -> BAJISTA"
                        else:
                            estado_rsi = f"🟢 CAZANDO RSI{int(rsi):.0f}<38" if rsi<38 else f"🟡 ZONA RSI{int(rsi):.0f}"
                    else:
                        if not adentro:
                            estado_rsi = f"🟡 ESPERA BAJISTA -> NORMAL"
                        else:
                            estado_rsi = f"🟢 CAZANDO KRAKEN RSI{int(rsi):.0f}/{umb['rsi_kraken']}" if rsi<umb['rsi_kraken'] else f"🟡 ZONA KRAKEN RSI{int(rsi):.0f}"
                    lineas.append(f"{sym.replace('USDT','')} {estado_rsi} [{tipo} {entrada:.0f}->{tope:.0f}]")
                else:
                    lineas.append(f"{sym.replace('USDT','')} {reg} sin banda")
            if lineas:
                texto = f"🐺 V50.8 ADAPT COMPLETO RSI38 LINEAL\n" + "\n".join(lineas) + f"\n📊 {WEB_URL}"
                try: bot.send_message(uid, texto)
                except: pass
    except: pass

def detectar_BI_CEREBRO(regimen):
    counts_global, total_tib_global = contar_posiciones_globales()
    counts_moneda = contar_por_moneda()
    mejor_motivo=""; mejor_sym=""; mejor_fuerza=0; mejor_est=None
    for sym in MONEDAS_ACTIVAS:
        banda_sym = BANDAS_ACTIVAS.get(sym)
        try:
            if sym in ["BTCUSDT","BNBUSDT"]:
                precio_moneda = ESTADO.get("btc" if "BTC" in sym else "bnb",0)
            else:
                precio_moneda = float(client.get_symbol_ticker(symbol=sym)['price']) if client else 0
        except: continue
        total_en_sym = counts_moneda.get(sym,0)
        kraken_en_sym = contar_kraken_por_moneda(sym)
        reg_sym = ESTADO.get("regimenes",{}).get(sym,"LINEAL").split()[0]
        if reg_sym == "ALCISTA_FUERTE":
            orden = ["TIBURON","LOBO","RATA"]
        elif reg_sym == "CRASH" or reg_sym == "BAJISTA":
            orden = ["KRAKEN","RATA"]
        elif reg_sym == "ALCISTA":
            orden = ["LOBO","RATA","TIBURON"]
        else:
            orden = ["RATA","LOBO","TIBURON","KRAKEN"]
        for nombre in orden:
            if nombre == "KRAKEN":
                if kraken_en_sym >= 1: continue
                if total_en_sym >= 3: continue
            else:
                banda_ok = banda_sym and banda_sym.get("activa") and banda_sym.get("tipo")=="NORMAL"
                if total_en_sym >= 2 and not banda_ok and nombre!="TIBURON": continue
                if counts_global.get((sym,nombre),0) >= 2 and nombre!="TIBURON": continue
                if nombre == "TIBURON" and total_tib_global >= 2: continue
            if nombre=="RATA": ok,motivo,wr = detectar_RATA_sym(sym)
            elif nombre=="LOBO": ok,motivo,wr = detectar_LOBO_sym(sym)
            elif nombre=="TIBURON": ok,motivo,wr = detectar_TIBURON_sym(sym)
            else: ok,motivo,wr = detectar_KRAKEN_sym(sym)
            tp_a = tp_adaptativo(sym, nombre if nombre in ESTRATEGIAS_V45 else "RATA")
            if ok and wr > mejor_fuerza and es_rentable(tp_a)[0]:
                mejor_fuerza=wr; mejor_est=nombre; mejor_motivo=f"[{sym} {reg_sym}] {motivo} TP{tp_a}% ADAPT"; mejor_sym=sym
    if mejor_est: return True, mejor_motivo, mejor_sym, mejor_est, mejor_fuerza
    return False, f"V50.8 ADAPT COMPLETO ACECHANDO", MONEDAS_ACTIVAS[0], None, 0

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
            with open(CONTADOR_FILE,"w") as f: json.dump({"tps": CONTADOR_TP_EXPANSION, "monedas": MONEDAS_ACTIVAS, "tanque": TANQUE_BNB_USDT}, f, indent=2)
            with open(os.path.join(DATA_DIR,"pirana_v50.json"),"w") as f: json.dump({"estado": ESTADO_PIRANA, "estado_negra": ESTADO_PIRANA_NEGRA, "bolsa": BOLSA_PIRANA, "bolsa_negra": BOLSA_PIRANA_NEGRA, "cache": CANDIDATAS_CACHE, "bandas_tiempo": BANDAS_TIEMPO_FUERA},f,indent=2)
    except: pass
def cargar_datos():
    global MONEDAS_ACTIVAS, POSICIONES_ABIERTAS, BANDAS_ACTIVAS, ESTADO_PIRANA, ESTADO_PIRANA_NEGRA, BOLSA_PIRANA, BOLSA_PIRANA_NEGRA, CANDIDATAS_CACHE, BANDAS_TIEMPO_FUERA, CONTADOR_TP_EXPANSION, TANQUE_BNB_USDT
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,"r") as f:
                data=json.load(f)
                for k,v in data.items(): USUARIOS[int(k)]=v
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
                BOLSA_PIRANA=pj.get("bolsa",{"neto":0.0,"ops":0})
                BOLSA_PIRANA_NEGRA=pj.get("bolsa_negra",{"neto":0.0,"ops":0})
                BANDAS_TIEMPO_FUERA=pj.get("bandas_tiempo",{})
                c = pj.get("cache")
                if c: CANDIDATAS_CACHE.update(c)
    except Exception as e: print(f"cargar error {e}")
def limpiar_pos_viejas():
    global POSICIONES_ABIERTAS
    try:
        for uid in list(POSICIONES_ABIERTAS.keys()):
            lista = POSICIONES_ABIERTAS[uid]
            if not isinstance(lista, list): continue
            for p in lista:
                if p.get("estrategia")=="PIRANA":
                    if p.get("tp",0) > 1.6: p["tp"] = 0.8
                    try:
                        hora = datetime.fromisoformat(p.get("hora","")).timestamp()
                        precio_actual = float(client.get_symbol_ticker(symbol=p["symbol"])['price']) if client else p["entrada"]
                        pnl_pct = (precio_actual - p["entrada"])/p["entrada"]*100 if p["entrada"]!=0 else 0
                        if time.time() - hora > 24*3600 and pnl_pct < 1.0: p["tp"] = 0.5
                    except: pass
        guardar_datos()
    except: pass
def reconstruir_bandas_faltantes():
    for uid in list(POSICIONES_ABIERTAS.keys()):
        for p in POSICIONES_ABIERTAS[uid]:
            if p.get("estrategia")=="TIBURON":
                sym = p.get("symbol"); entrada = float(p.get("entrada",0))
                if sym and entrada>0 and (sym not in BANDAS_ACTIVAS or not BANDAS_ACTIVAS[sym].get("activa")):
                    BANDAS_ACTIVAS[sym] = {"entrada_tiburon": entrada, "tope": entrada*1.10, "tipo": "NORMAL", "activa": True}
def detectar_mejor_candidata():
    mejor = None; mejor_wr = 0
    for sym in CANDIDATAS:
        if sym in MONEDAS_ACTIVAS: continue
        if sym in ["DOGEUSDT","SHIBUSDT"] and len(MONEDAS_ACTIVAS) < 5: continue
        try:
            ok1,m1,wr1 = detectar_RATA_sym(sym)
            ok2,m2,wr2 = detectar_LOBO_sym(sym)
            ok3,m3,wr3 = detectar_TIBURON_sym(sym)
            ok4,m4,wr4 = detectar_KRAKEN_sym(sym)
            wr_total = wr1+wr2+wr3+wr4
            d1d = get_velas(sym,"1d",15)
            if not d1d: continue
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
    tanque_sugerido = TANQUE_BNB_USDT + TANQUE_POR_MONEDA
    msg = f"🚀 META {META_TP_PARA_EXPANDIR:.0f} TPs (interna)\nCandidata: {mejor_sym} WR {wr:.2f}\nActual {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} -> {len(MONEDAS_ACTIVAS)+1}/{MAX_MONEDAS}\nTanque: {TANQUE_BNB_USDT:.1f} -> {tanque_sugerido:.1f} USDT (+{TANQUE_POR_MONEDA})\n¿Autorizas sumar {mejor_sym}?"
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
@bot.callback_query_handler(func=lambda call: True)
def callback_candidata(call):
    global MONEDAS_ACTIVAS, CONTADOR_TP_EXPANSION, TANQUE_BNB_USDT
    try:
        data = call.data
        if data.startswith("AUTH_ADD_"):
            sym = data.replace("AUTH_ADD_","")
            if sym not in MONEDAS_ACTIVAS and len(MONEDAS_ACTIVAS) < MAX_MONEDAS:
                MONEDAS_ACTIVAS.append(sym); CONTADOR_TP_EXPANSION = 0; TANQUE_BNB_USDT += TANQUE_POR_MONEDA
                try: ejecutar_orden_real("BNBUSDT","BUY", TANQUE_POR_MONEDA)
                except: pass
                guardar_datos()
                bot.answer_callback_query(call.id, f"{sym} AUTORIZADA!")
                bot.edit_message_text(f"✅ {sym} AGREGADA {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\nTanque -> {TANQUE_BNB_USDT:.1f} USDT\n{'+'.join(MONEDAS_ACTIVAS)}", call.message.chat.id, call.message.message_id)
            else: bot.answer_callback_query(call.id, "Ya agregada")
        elif data.startswith("REJECT_"):
            sym = data.replace("REJECT_","")
            bot.answer_callback_query(call.id, "Rechazada")
            bot.edit_message_text(f"❌ {sym} rechazada. Sigue cazando 0/{META_TP_PARA_EXPANDIR:.0f} interno", call.message.chat.id, call.message.message_id)
        elif data.startswith("ADD_"):
            sym = data.replace("ADD_","")
            if sym not in MONEDAS_ACTIVAS and len(MONEDAS_ACTIVAS) < MAX_MONEDAS:
                MONEDAS_ACTIVAS.append(sym); guardar_datos()
                bot.answer_callback_query(call.id, f"{sym} AGREGADA!")
    except Exception as e:
        try: bot.answer_callback_query(call.id, f"Error {e}")
        except: pass
cargar_datos()
limpiar_pos_viejas()
reconstruir_bandas_faltantes()
def motor_v45():
    global ESTADO_PIRANA, ESTADO_PIRANA_NEGRA, CONTADOR_TP_EXPANSION
    print(f">>> MOTOR V50.8 ADAPT COMPLETO RSI38 {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}")
    time.sleep(5)
    while True:
        try:
            for sym in list(MONEDAS_ACTIVAS):
                reg, det = detectar_regimen_sym(sym)
                ESTADO["regimenes"][sym] = f"{reg} {det}"
                if sym=="BTCUSDT":
                    d=get_velas(sym,"1m",1)
                    if d: ESTADO["btc"]=d["closes"][-1]
                    ESTADO["regimen"]=reg
                if sym=="BNBUSDT":
                    d=get_velas(sym,"1m",1)
                    if d: ESTADO["bnb"]=d["closes"][-1]
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
                    if not client: continue
                    precio_actual = float(client.get_symbol_ticker(symbol=pos["symbol"])['price'])
                    tp_price = pos["entrada"] * (1 + pos["tp"]/100)
                    sl_price = pos["entrada"] * (1 + pos["sl"]/100)
                    cerrar = None
                    if precio_actual >= tp_price: cerrar = "TP"
                    elif precio_actual <= sl_price: cerrar = "TRAILING" if pos["sl"]>=0 and pos["estrategia"] in ["TIBURON","KRAKEN"] else "SL"
                    if cerrar:
                        ejecutar_orden_real(pos["symbol"], "SELL", pos["usdt"])
                        pnl_bruto = (precio_actual - pos["entrada"]) / pos["entrada"] * pos["usdt"]
                        comision = pos["usdt"] * COMISION_TOTAL/100
                        pnl = pnl_bruto - comision
                        pnl_pct = (precio_actual - pos["entrada"])/pos["entrada"]*100 if pos["entrada"]!=0 else 0
                        es_tp = cerrar in ["TP","TRAILING"]
                        if pos["estrategia"]=="PIRANA":
                            if pos.get("subtipo")=="NEGRA":
                                key_banda = f"{pos['symbol']}_NEGRA_{int(pos.get('banda_id', pos['entrada']))}"
                                ESTADO_PIRANA_NEGRA[key_banda] = max(0, ESTADO_PIRANA_NEGRA.get(key_banda,1)-1)
                                BOLSA_PIRANA_NEGRA["neto"] += pnl
                            else:
                                key_banda = f"{pos['symbol']}_{int(pos.get('banda_id', pos['entrada']))}"
                                ESTADO_PIRANA[key_banda] = max(0, ESTADO_PIRANA.get(key_banda,1)-1)
                                BOLSA_PIRANA["neto"] += pnl
                        if pos["estrategia"]=="TIBURON":
                            if cerrar=="TP":
                                if pos["symbol"] in BANDAS_ACTIVAS: BANDAS_ACTIVAS[pos["symbol"]]["activa"]=False
                            else:
                                entrada = pos["entrada"]; sl_price_val = entrada * 0.965; banda_rec_base = sl_price_val * 0.97
                                BANDAS_ACTIVAS[pos["symbol"]] = {"entrada_tiburon": banda_rec_base, "tope": sl_price_val, "tipo": "BAJISTA", "activa": True, "perdida_origen": abs(pnl)}
                        if es_tp:
                            u["balance"]+=abs(pnl); u["neto_hoy"]+=abs(pnl); u["ganadas"]+=1
                            u["estrategias"][pos["estrategia"]]["ganadas"]+=1
                            CONTADOR_TP_EXPANSION += 1
                            guardar_datos()
                            if CONTADOR_TP_EXPANSION >= META_TP_PARA_EXPANDIR: intentar_expandir(user_id)
                        else:
                            u["balance"]-=abs(pnl); u["neto_hoy"]-=abs(pnl); u["perdidas"]+=1
                        u["estrategias"][pos["estrategia"]]["ops"]+=1; u["estrategias"][pos["estrategia"]]["neto"]+=pnl; u["ops_hoy"]+=1
                        u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} {pos['estrategia']} {pos.get('subtipo','')} {pos['symbol']} {cerrar} ${pnl:+.2f} TP:{pos['tp']}% ADAPT")
                        notificar_cierre(pos["symbol"], pos["estrategia"], pos["entrada"], precio_actual, pnl, pnl_pct, es_tp, pos.get("subtipo",""))
                        POSICIONES_ABIERTAS[user_id].remove(pos); guardar_datos()
                except: pass
            if not u.get("prendido", False): continue
            try:
                for sym in list(MONEDAS_ACTIVAS):
                    if sym not in BANDAS_ACTIVAS or not BANDAS_ACTIVAS[sym].get("activa") or BANDAS_ACTIVAS[sym].get("tipo")!= "NORMAL": continue
                    precio_actual = 0
                    try:
                        if sym in ["BTCUSDT","BNBUSDT"]: precio_actual = ESTADO.get("btc" if "BTC" in sym else "bnb", 0)
                        else: precio_actual = float(client.get_symbol_ticker(symbol=sym)['price']) if client else 0
                    except: continue
                    if precio_actual==0: continue
                    d5 = get_velas(sym,"5m",20)
                    if not d5: continue
                    rsi = rsi_calc(d5["closes"],7)
                    if oportunidad_pirana(sym, rsi, precio_actual, BANDAS_ACTIVAS[sym]):
                        key_banda = f"{sym}_{int(BANDAS_ACTIVAS[sym]['entrada_tiburon'])}"
                        if ESTADO_PIRANA.get(key_banda,0) >= PIRANA_CONFIG["MAX_POR_BANDA"]: continue
                        lock_key = f"{key_banda}_PIRANA"
                        if lock_key in ULTIMO_TRADE and time.time() - ULTIMO_TRADE[lock_key] < 60: continue
                        usdt_pirana = max(10, u["balance"]*0.35*0.10*PIRANA_CONFIG["LOTE_FACTOR"])
                        exito, res, precio_entrada = ejecutar_orden_real(sym, "BUY", usdt_pirana)
                        if exito:
                            ULTIMO_TRADE[lock_key] = time.time()
                            ESTADO_PIRANA[key_banda] = ESTADO_PIRANA.get(key_banda,0)+1
                            pos = {"symbol": sym, "estrategia": "PIRANA", "entrada": precio_entrada, "tp": tp_adaptativo(sym,"PIRANA"), "sl": PIRANA_CONFIG["SL"], "usdt": usdt_pirana, "hora": ahora_art().isoformat(), "banda_id": BANDAS_ACTIVAS[sym]["entrada_tiburon"]}
                            POSICIONES_ABIERTAS[user_id].append(pos)
                            banda_txt = f"{BANDAS_ACTIVAS[sym]['entrada_tiburon']:.0f}->{BANDAS_ACTIVAS[sym]['tope']:.0f} {BANDAS_ACTIVAS[sym]['tipo']}"
                            notificar_caza(sym, "PIRANA", precio_entrada, pos["tp"], pos["sl"], banda_txt, usdt_pirana, f"RSI{rsi:.0f} ADAPT38 LINEAL")
                            guardar_datos()
            except: pass
            try:
                for sym in list(MONEDAS_ACTIVAS):
                    if sym not in BANDAS_ACTIVAS or not BANDAS_ACTIVAS[sym].get("activa") or BANDAS_ACTIVAS[sym].get("tipo")!= "BAJISTA": continue
                    precio_actual = 0
                    try:
                        if sym in ["BTCUSDT","BNBUSDT"]: precio_actual = ESTADO.get("btc" if "BTC" in sym else "bnb", 0)
                        else: precio_actual = float(client.get_symbol_ticker(symbol=sym)['price']) if client else 0
                    except: continue
                    if precio_actual==0: continue
                    d5 = get_velas(sym,"5m",20)
                    if not d5: continue
                    rsi = rsi_calc(d5["closes"],7)
                    vol_prom = sum(d5["vols"][-20:])/20 if len(d5["vols"])>=20 else 1
                    vol_actual = d5["vols"][-1]
                    if oportunidad_pirana_negra(sym, rsi, precio_actual, BANDAS_ACTIVAS[sym], vol_actual, vol_prom):
                        key_banda = f"{sym}_NEGRA_{int(BANDAS_ACTIVAS[sym]['entrada_tiburon'])}"
                        if ESTADO_PIRANA_NEGRA.get(key_banda,0) >= PIRANA_NEGRA_CONFIG["MAX_POR_BANDA"]: continue
                        lock_key = f"{key_banda}_PIRANA_NEGRA"
                        if lock_key in ULTIMO_TRADE and time.time() - ULTIMO_TRADE[lock_key] < PIRANA_NEGRA_CONFIG["COOLDOWN"]: continue
                        usdt_negra = max(10, u["balance"]*0.35*0.10*PIRANA_NEGRA_CONFIG["LOTE_FACTOR"])
                        exito, res, precio_entrada = ejecutar_orden_real(sym, "BUY", usdt_negra)
                        if exito:
                            ULTIMO_TRADE[lock_key] = time.time()
                            ESTADO_PIRANA_NEGRA[key_banda] = ESTADO_PIRANA_NEGRA.get(key_banda,0)+1
                            pos = {"symbol": sym, "estrategia": "PIRANA", "subtipo": "NEGRA", "entrada": precio_entrada, "tp": PIRANA_NEGRA_CONFIG["TP"], "sl": PIRANA_NEGRA_CONFIG["SL"], "usdt": usdt_negra, "hora": ahora_art().isoformat(), "banda_id": BANDAS_ACTIVAS[sym]["entrada_tiburon"]}
                            POSICIONES_ABIERTAS[user_id].append(pos)
                            banda_txt = f"{BANDAS_ACTIVAS[sym]['entrada_tiburon']:.0f}->{BANDAS_ACTIVAS[sym]['tope']:.0f} BAJISTA NEGRA"
                            notificar_caza(sym, "PIRAÑA_NEGRA", precio_entrada, pos["tp"], pos["sl"], banda_txt, usdt_negra, f"RSI{rsi:.0f} VSAx{vol_actual/vol_prom:.1f} ADAPT")
                            guardar_datos()
            except: pass
            check_reset_diario(u)
            ok,motivo,symbol_elegido,estrategia_elegida,fuerza = detectar_BI_CEREBRO(ESTADO.get("regimen","LINEAL"))
            if ok and estrategia_elegida:
                key_lock = f"{symbol_elegido}_{estrategia_elegida}"
                if key_lock in ULTIMO_TRADE and (time.time() - ULTIMO_TRADE[key_lock]) < ESTRATEGIAS_V45[estrategia_elegida]["cooldown"]: continue
                total_en_moneda = contar_por_moneda().get(symbol_elegido,0)
                kraken_en_moneda = contar_kraken_por_moneda(symbol_elegido)
                if estrategia_elegida == "KRAKEN":
                    if kraken_en_moneda >= 1: continue
                    if total_en_moneda >= 3: continue
                else:
                    banda = BANDAS_ACTIVAS.get(symbol_elegido,{})
                    es_normal = banda.get("activa") and banda.get("tipo")=="NORMAL"
                    if total_en_moneda >= 1 and not es_normal: continue
                cfg=ESTRATEGIAS_V45[estrategia_elegida]
                tp_inteligente = tp_adaptativo(symbol_elegido, estrategia_elegida)
                if not es_rentable(tp_inteligente)[0]: continue
                usdt_a_usar = max(10, u["balance"]*0.35*0.10)
                if estrategia_elegida == "KRAKEN": usdt_a_usar = max(200, min(300, u["balance"]*0.20))
                exito, res, precio = ejecutar_orden_real(symbol_elegido,"BUY",usdt_a_usar)
                if exito:
                    ULTIMO_TRADE[key_lock]=time.time()
                    pos = {"symbol": symbol_elegido, "estrategia": estrategia_elegida, "entrada": precio, "tp": tp_inteligente, "sl": cfg["sl_neto"], "usdt": usdt_a_usar, "hora": ahora_art().isoformat()}
                    POSICIONES_ABIERTAS[user_id].append(pos)
                    u["modo"]=f"{estrategia_elegida} {symbol_elegido} TP{tp_inteligente}%"; u["mercado"]=motivo
                    if estrategia_elegida=="TIBURON": BANDAS_ACTIVAS[symbol_elegido] = {"entrada_tiburon": precio, "tope": precio*1.10, "tipo": "NORMAL", "activa": True}
                    if estrategia_elegida=="KRAKEN": BANDAS_ACTIVAS[symbol_elegido] = {"entrada_tiburon": precio*0.97, "tope": precio*0.995, "tipo": "BAJISTA", "activa": True}
                    b = BANDAS_ACTIVAS.get(symbol_elegido,{})
                    banda_txt = f"{b.get('entrada_tiburon',precio*0.97):.0f}->{b.get('tope',precio*1.10):.0f} {b.get('tipo','')}"
                    notificar_caza(symbol_elegido, estrategia_elegida, precio, tp_inteligente, cfg["sl_neto"], banda_txt, usdt_a_usar, motivo)
                    guardar_datos()
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
    estado_txt = f"🟢 V50.8 ADAPT 120TP {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}" if u["prendido"] else "🔴 APAGADO"
    regs="\n".join([f"{k}:{v.split()[0]}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO['regimen'].split()[0]
    bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    ganancia = u["balance"] - u["capital_inicial"] + BOLSA_PIRANA["neto"] + BOLSA_PIRANA_NEGRA["neto"]
    bot.send_message(m.chat.id,f"🦁 V50.8 ADAPT RSI38 {estado_txt}\n{regs}\n{bandas_txt}\n{'+'.join(MONEDAS_ACTIVAS)}\nBal ${u['balance']:.2f} B ${BOLSA_PIRANA['neto']:+.2f} N ${BOLSA_PIRANA_NEGRA['neto']:+.2f}\nGan ${ganancia:.2f}\n{WEB_URL}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="📊 BALANCE")
def balance(m):
    u=get_user_data(m.chat.id)
    ganancia_total = u["balance"]-u["capital_inicial"]+BOLSA_PIRANA["neto"]+BOLSA_PIRANA_NEGRA["neto"]
    regs="\n".join([f"{k}: {v.split()[0]}" for k,v in ESTADO.get("regimenes",{}).items()])
    pos_txt = "\n".join([f"🔒 {p['symbol']} {p['estrategia']} {p.get('subtipo','')} Ent {p['entrada']:.2f} TP{p['tp']}%" for p in POSICIONES_ABIERTAS.get(m.chat.id,[])]) or "Sin pos"
    bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    bot.send_message(m.chat.id,f"💰 V50.8 ADAPT RSI38 {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n{regs}\n{bandas_txt}\n{pos_txt}\nBal ${u['balance']:.2f} Total ${ganancia_total:+.2f}\nHoy ${u['neto_hoy']:+.2f}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL","/historial"])
def historial(m):
    u=get_user_data(m.chat.id)
    txt="\n".join(u["historial"][-25:]) if u["historial"] else "Sin ops"
    bot.send_message(m.chat.id,f"📜 V50.8 ADAPT\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER","/prender"])
def prender(m):
    u=get_user_data(m.chat.id); u["prendido"]=True; u["modo"]=f"CAZANDO BTC+BNB ESPEJO 120TP ADAPT RSI38"
    guardar_datos()
    bot.send_message(m.chat.id,f"🐺 LOBO V50.8 ADAPT PRENDIDO - RSI38 LINEAL - 6 bestias adaptativas",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text in ["⏸️ APAGAR","/apagar"])
def apagar(m):
    u=get_user_data(m.chat.id); u["prendido"]=False; guardar_datos()
    bot.send_message(m.chat.id,f"⏸️ V50.8 APAGADO",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text and any(x in m.text.upper() for x in ['ORDENES','ESTADO','STATUS','/ORDENES','/ESTADO','/STATUS']))
def ordenes_estado(m):
    uid = m.chat.id
    u = get_user_data(uid)
    lista = POSICIONES_ABIERTAS.get(uid, []) or POSICIONES_ABIERTAS.get(ADMINS_IDS[0], [])
    if not lista:
        ganancia_total = u["balance"]-u["capital_inicial"]+BOLSA_PIRANA["neto"]+BOLSA_PIRANA_NEGRA["neto"]
        bot.send_message(uid, f"📦 Sin posiciones abiertas\nBal ${u['balance']:.2f} Total ${ganancia_total:.2f} Hoy ${u['neto_hoy']:+.2f}\nFalta EVOLUCIONAR: ${120-ganancia_total:.2f} / $120", reply_markup=get_menu())
        return
    ganancia_total = u["balance"]-u["capital_inicial"]+BOLSA_PIRANA["neto"]+BOLSA_PIRANA_NEGRA["neto"]
    txt = f"📦 MANADA V50.8 ADAPT - {len(lista)} POS ABIERTAS\n"
    for p in lista:
        try: precio_actual = float(client.get_symbol_ticker(symbol=p["symbol"])['price']) if client else p["entrada"]
        except: precio_actual = p["entrada"]
        pnl_pct = (precio_actual - p["entrada"])/p["entrada"]*100 if p["entrada"]!=0 else 0
        txt += f"🔒 {p['symbol']} {p['estrategia']} {p.get('subtipo','')} Ent {p['entrada']:.2f} Ahora {precio_actual:.2f} P/L {pnl_pct:+.2f}% TP{p['tp']}%\n"
    txt += f"\nBal ${u['balance']:.2f} Total ${ganancia_total:.2f} Hoy ${u['neto_hoy']:+.2f}\nFalta EVOLUCIONAR: ${120-ganancia_total:.2f} / $120"
    bot.send_message(uid, txt, reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text and 'EVOLUCIONAR' in m.text.upper())
def evolucionar(m):
    u = get_user_data(m.chat.id)
    ganancia_total = u["balance"]-u["capital_inicial"]+BOLSA_PIRANA["neto"]+BOLSA_PIRANA_NEGRA["neto"]
    if ganancia_total < 120:
        bot.send_message(m.chat.id, f"🔒 EVOLUCIONAR BLOQUEADO\nTotal: ${ganancia_total:.2f} / $120\nFalta: ${120-ganancia_total:.2f}\nLa manada sigue cazando... 🐺🦈\n", reply_markup=get_menu())
        return
    bot.send_message(m.chat.id, f"🚀 OBJETIVO CUMPLIDO ${ganancia_total:.2f} >= $120\nMANADA EVOLUCIONANDO A V51\n$36 cada $100 desbloqueado", reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text and 'RETIRAR' in m.text.upper())
def retirar(m):
    uid = m.chat.id
    u = get_user_data(uid)
    lista = POSICIONES_ABIERTAS.get(uid, []) or POSICIONES_ABIERTAS.get(ADMINS_IDS[0], [])
    es_todo = "TODO" in m.text.upper()
    try:
        tipo_txt = "TODO" if es_todo else "GANANCIAS"
        bot.send_message(uid, f"💸 RETIRANDO {tipo_txt} - Cerrando {len(lista)} posiciones...", reply_markup=get_menu())
        cerradas = 0
        for p in lista[:]:
            try: ejecutar_orden_real(p["symbol"], "SELL", p["usdt"]); cerradas += 1
            except: pass
        if uid in POSICIONES_ABIERTAS: POSICIONES_ABIERTAS[uid] = []
        if ADMINS_IDS[0] in POSICIONES_ABIERTAS: POSICIONES_ABIERTAS[ADMINS_IDS[0]] = []
        try:
            acc = client.get_account()
            bal_usdt = sum([float(b['free'])+float(b['locked']) for b in acc['balances'] if b['asset']=='USDT'])
            txt_bal = f"${bal_usdt:.2f}"
        except:
            txt_bal = f"${u['balance']:.2f} (local)"
        ahora = ahora_art().strftime('%d/%m %H:%M')
        if es_todo:
            u["historial"].append(f"{ahora} RETIRO TOTAL: -{cerradas} pos | {txt_bal} -> BINANCE")
            u["balance"] = 0
            guardar_datos()
            bot.send_message(uid, f"✅ RETIRO TOTAL - {cerradas} cerradas\n💰 TODO en BINANCE: {txt_bal}", reply_markup=get_menu())
        else:
            u["historial"].append(f"{ahora} RETIRO GANANCIAS: -{cerradas} pos | {txt_bal} -> BINANCE")
            guardar_datos()
            bot.send_message(uid, f"✅ MANADA LIQUIDADA - {cerradas} cerradas\n💰 En BINANCE: {txt_bal}\nBase ${u['balance']:.2f} intacta", reply_markup=get_menu())
    except Exception as e:
        bot.send_message(uid, f"❌ Error al retirar: {e}", reply_markup=get_menu())

@app.route('/')
def home():
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>V50.8 ADAPT</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}.top{padding:10px;background:#1e222d;position:sticky;top:0;z-index:20;font-size:13px;border-bottom:2px solid #00ff88;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.card{position:relative;background:#1e222d;border-radius:8px;overflow:hidden;border:1px solid #2a2e39}.badge{position:absolute;top:36px;left:6px;z-index:5;background:rgba(0,0,0,0.85);padding:6px 8px;border-radius:6px;font-size:11px;line-height:14px;max-width:90%}.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px}@media(max-width:900px){.grid{grid-template-columns:1fr}}</style></head><body><div class="top" id="info">Cargando V50.8 ADAPT RSI38...</div><div class="grid" id="charts_grid"></div><script>async function load(){let a=await (await fetch('/api/data')).json();let bandas=a.bandas||{};let pos=a.posiciones||[];let regs = Object.entries(a.regimenes).map(e=>{let first = e[1].split(' ')[0]; return e[0].replace('USDT','')+':'+first;}).join(' | ');document.getElementById('info').innerHTML='<b>V50.8 ADAPT RSI38 | Bal $'+a.balance.toFixed(2)+'</b> | '+regs;let grid=document.getElementById('charts_grid');if(grid.childElementCount!=a.monedas.length){grid.innerHTML='';a.monedas.forEach(sym=>{let pSym=pos.filter(p=>p.symbol==sym);let b=bandas[sym];let badgeHtml='';if(b&&b.activa){badgeHtml+='<div>🎯 '+sym.replace('USDT','')+' '+b.tipo+' '+b.entrada_tiburon.toFixed(0)+'->'+b.tope.toFixed(0)+'</div>';}pSym.forEach(p=>{if(p.estrategia!='LOBO' && p.estrategia!='TIBURON' && p.estrategia!='KRAKEN') return;let precio=a.precios[sym]||p.entrada;let pnl=((precio-p.entrada)/p.entrada*100);badgeHtml+='<div>🔒 '+p.estrategia+' '+pnl.toFixed(2)+'% TP'+p.tp+'%</div>';});let div=document.createElement('div');div.className='card';div.innerHTML='<div style="background:#1e293b;padding:8px"><b>'+sym+'</b> '+(a.regimenes[sym]||'').split(' ')[0]+' $'+(a.precios[sym]||0).toFixed(2)+'</div><div class="badge">'+badgeHtml+'</div><div id="chart_'+sym+'" style="height:74vh"></div>';grid.appendChild(div);setTimeout(()=>{new TradingView.widget({"autosize":true,"symbol":"BINANCE:"+sym,"interval":"15","timezone":"America/Argentina/Buenos_Aires","theme":"dark","container_id":"chart_"+sym});},300);});}}setInterval(load,3000);load();</script></body></html>"""
    return render_template_string(html)

@app.route('/api/data')
def api_data():
    target=ADMINS_IDS[0]
    if target not in USUARIOS: get_user_data(target)
    u=USUARIOS[target]
    bandas_txt = " | ".join([banda_txt_api(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    precios = {}
    for sym in MONEDAS_ACTIVAS:
        try: precios[sym] = float(client.get_symbol_ticker(symbol=sym)['price']) if client else 0
        except: precios[sym]=0
    posiciones = POSICIONES_ABIERTAS.get(target, [])
    ganancia_total = u["balance"]-u["capital_inicial"]
    return jsonify({"balance":u["balance"],"capital_inicial":u["capital_inicial"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"regimen_btc":ESTADO.get("regimen","LINEAL"),"regimenes":ESTADO.get("regimenes",{}),"estrategias":u["estrategias"],"monedas":MONEDAS_ACTIVAS,"ganancia_total": ganancia_total,"bandas": BANDAS_ACTIVAS, "bandas_txt": bandas_txt, "posiciones": posiciones, "precios": precios, "bolsa_pirana": BOLSA_PIRANA, "bolsa_negra": BOLSA_PIRANA_NEGRA, "meta_proxima": META_TP_PARA_EXPANDIR, "tps_actual": CONTADOR_TP_EXPANSION, "proxima_moneda": CANDIDATAS_CACHE.get("proxima")})

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

threading.Thread(target=motor_v45,daemon=True).start()
if __name__=='__main__':
    try: bot.remove_webhook(); time.sleep(1); bot.set_webhook(url=f"{WEB_URL}/{TOKEN}")
    except: pass
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
