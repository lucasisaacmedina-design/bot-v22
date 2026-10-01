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
TANQUE_BNB_USDT = 20.0
TANQUE_BNB_MIN = 5.0
TANQUE_BNB_RECARGA = 8.0
TANQUE = TANQUE_BNB_USDT
COMISION_TOTAL = 0.15
FILTRO_NETO_MIN = 0.5
FILTRO_NETO_MIN_MOJARRA = 0.10
MAX_MOJARRA_POR_MONEDA = 6
MAX_PIRANA_POR_MONEDA = 2
MAX_MOJARRITA_POR_MONEDA = 3
DISTANCIA_CARDUMEN_PCT = 0.10
DISTANCIA_PIRANA_PCT = 0.20
DISTANCIA_MOJARRA_PCT = 0.10
DISTANCIA_MOJARRA_NEGRA_PCT = 0.20
DISTANCIA_PIRANA_NEGRA_PCT = 0.30
ESTADO_PIRANA = {}
ESTADO_PIRANA_NEGRA = {}
BANDAS_TIEMPO_FUERA = {}
TIEMPO_FUERA_NORMAL = 720
TIEMPO_FUERA_BAJISTA = 360
CANDIDATAS_CACHE = {"_ultimo_scan": 0, "_aviso_meta": 0, "proxima": None}
TIEMPO_ESCANEO_CANDIDATAS = 600
KRAKEN_SL_COUNT = 0
KRAKEN_BLOQUEO_HASTA = 0

# === V51 BLINDADA - CONTADORES EVOLUCION ===
CONTADOR_POR_REGIMEN = {}
EVOLUCION_NIVEL = {}
REG_ANT = {}

ESTRATEGIAS_V45 = {
    "MOJARRA": {"tf": "1m", "desc": "MOJARRA 0.2-0.4% LONG","rango_tp": (0.2, 0.4), "sl_neto": -2.5, "max_dia": 300,"cooldown": 45, "cooldown_rec": 45,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.2},
    "MOJARRITA": {"tf": "5m", "desc": "MOJARRITA 0.2-0.3% LONG BOOSTER","rango_tp": (0.2, 0.3), "sl_neto": -1.5, "max_dia": 200,"cooldown": 45, "cooldown_rec": 45,"mercado_ideal": "LINEAL_MUERTO", "tp_fijo_banda": 0.2},
    "PIRANA_BLANCA": {"tf": "3m", "desc": "PIRANA BLANCA 0.5-0.8% LONG","rango_tp": (0.5, 0.8), "sl_neto": -2.8, "max_dia": 150,"cooldown": 90, "cooldown_rec": 90,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.5},
    "RATITA": {"tf": "5m", "desc": "RATITA 0.6-1.0% LONG NEW","rango_tp": (0.6, 1.0), "sl_neto": -3.0, "max_dia": 40,"cooldown": 120, "cooldown_rec": 120,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "RATA": {"tf": "5m", "desc": "Madre RATA 0.8-1.2% LONG","rango_tp": (0.8, 1.2), "sl_neto": -3.0, "max_dia": 30,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "LINEAL", "tp_fijo_banda": 1.0},
    "LOBO": {"tf": "1h", "desc": "Madre LOBO 1.7% LONG JEFE V50.23","rango_tp": (1.2, 2.2), "sl_neto": -5.0, "max_dia": 100,"cooldown": 300, "cooldown_rec": 300,"mercado_ideal": "ALCISTA", "tp_fijo_banda": 1.7},
    "TIBURON": {"tf": "1d", "desc": "Madre TIBURON 5-10% LONG JEFE FUERTE V50.23","rango_tp": (5.0, 10.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 14400, "cooldown_rec": 14400,"mercado_ideal": "ALCISTA_FUERTE"},
    "KRAKEN": {"tf": "1h", "desc": "Madre KRAKEN 3-5% LONG REBOTE CRASH V50.23","rango_tp": (3.0, 5.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 3600, "cooldown_rec": 3600,"mercado_ideal": "CRASH"},
    "MOJARRA_NEGRA": {"tf": "5m", "desc": "MOJARRA NEGRA 0.3-0.5% SHORT REBOTE V50.23","rango_tp": (0.3, 0.5), "sl_neto": -1.5, "max_dia": 200,"cooldown": 60, "cooldown_rec": 60,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.3},
    "PIRANA_NEGRA": {"tf": "5m", "desc": "PIRANA NEGRA 0.5-0.8% SHORT REBOTE V50.23","rango_tp": (0.5, 0.8), "sl_neto": -3.5, "max_dia": 100,"cooldown": 600, "cooldown_rec": 600,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.5},
    "RATA_NEGRA": {"tf": "5m", "desc": "RATA NEGRA 0.8-1.5% SHORT REBOTE V50.23","rango_tp": (0.8, 1.5), "sl_neto": -4.0, "max_dia": 100,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.8},
    "LOBO_NEGRO": {"tf": "1h", "desc": "LOBO NEGRO 1.7% JEFE SHORT V50.23","rango_tp": (1.2, 2.2), "sl_neto": -5.0, "max_dia": 100,"cooldown": 300, "cooldown_rec": 300,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 1.7},
}
ESTRATEGIAS_V45["PIRANA"] = ESTRATEGIAS_V45["PIRANA_BLANCA"]
ESTRATEGIAS_V45["PIRAÑA_NEGRA"] = ESTRATEGIAS_V45["PIRANA_NEGRA"]

BLANCAS = {"MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATA","RATITA","LOBO","TIBURON"}
NEGRAS = {"MOJARRA_NEGRA","PIRANA_NEGRA","PIRAÑA_NEGRA","RATA_NEGRA","LOBO_NEGRO","KRAKEN"}

def candado(est, regimen):
    r = regimen.split()[0]
    if est=="LOBO" and r not in ["ALCISTA","ALCISTA_FUERTE"]: return False
    if est=="TIBURON" and r!="ALCISTA_FUERTE": return False
    if est=="KRAKEN" and r!="CRASH": return False
    if est in NEGRAS and r not in ["BAJISTA","CRASH"]: return False
    if est in BLANCAS and r in ["BAJISTA","CRASH"]: return False
    return True

def reset_si_cambio_regimen(sym, reg_nuevo):
    global CONTADOR_POR_REGIMEN, EVOLUCION_NIVEL, REG_ANT
    reg_nuevo_simple = reg_nuevo.split()[0]
    reg_ant = REG_ANT.get(sym, "")
    if reg_ant!= reg_nuevo_simple and reg_ant!= "":
       print(f"V51 RESET {sym} {reg_ant}->{reg_nuevo_simple}")
    REG_ANT[sym] = reg_nuevo_simple

def registrar_caza_V51(sym, estrategia, regimen):
    global CONTADOR_POR_REGIMEN, EVOLUCION_NIVEL
    if sym not in CONTADOR_POR_REGIMEN: CONTADOR_POR_REGIMEN[sym] = {}
    if regimen not in CONTADOR_POR_REGIMEN[sym]: CONTADOR_POR_REGIMEN[sym][regimen] = {}
    if sym not in EVOLUCION_NIVEL: EVOLUCION_NIVEL[sym] = {}
    if regimen not in EVOLUCION_NIVEL[sym]: EVOLUCION_NIVEL[sym][regimen] = 1
    CONTADOR_POR_REGIMEN[sym][regimen][estrategia] = CONTADOR_POR_REGIMEN[sym][regimen].get(estrategia, 0) + 1
    nivel = EVOLUCION_NIVEL[sym][regimen]
    print(f"V51 REGISTRO {sym} {regimen} {estrategia} x{CONTADOR_POR_REGIMEN[sym][regimen][estrategia]} Nv{nivel}")

def candado_evolucion_V51(sym, estrategia, regimen):
    reg_simple = regimen.split()[0]
    nivel = EVOLUCION_NIVEL.get(sym, {}).get(reg_simple, 1)
    cont = CONTADOR_POR_REGIMEN.get(sym, {}).get(reg_simple, {})

    mojarra_count = cont.get("MOJARRA",0) + cont.get("MOJARRITA",0)
    pirana_count = cont.get("PIRANA_BLANCA",0)
    ratita_count = cont.get("RATITA",0)

    # CANDADO V52 - CON RATITA PUENTE - SIN RETORNO A MOJARRA
    if mojarra_count >= 2 and nivel == 1:
        EVOLUCION_NIVEL[sym][reg_simple] = 2
        print(f"V52 EVOLUCION {sym} {reg_simple} Nv1->Nv2 MOJARRA x{mojarra_count} -> PIRANA_BLANCA")
        nivel = 2

    if pirana_count >= 1 and nivel == 2:
        EVOLUCION_NIVEL[sym][reg_simple] = 3
        print(f"V52 EVOLUCION {sym} {reg_simple} Nv2->Nv3 PIRANA x{pirana_count} -> RATITA")
        nivel = 3

    if ratita_count >= 1 and nivel == 3:
        EVOLUCION_NIVEL[sym][reg_simple] = 4
        print(f"V52 EVOLUCION {sym} {reg_simple} Nv3->Nv4 RATITA x{ratita_count} -> RATA")
        nivel = 4

    # IDEA MADRE + RATITA PUENTE
    if reg_simple == "LINEAL_MUERTO":
        if nivel == 1: return estrategia in ["MOJARRA","MOJARRITA"]
        return estrategia == "MOJARRITA"

    if reg_simple == "LINEAL":
        if nivel == 1: return estrategia == "MOJARRA"
        if nivel == 2: return estrategia == "PIRANA_BLANCA"
        if nivel == 3: return estrategia == "RATITA"
        if nivel >= 4: return estrategia == "RATA"

        # PARA TODOS LOS OTROS REGIMENES (03 ALCISTA, 04 ALCISTA FUERTE, 05 BAJISTA)
    # Respeta el regimen pero mantiene la evolucion sin retorno
    if nivel == 1: return estrategia == "MOJARRA"
    if nivel == 2: return estrategia == "PIRANA_BLANCA"
    if nivel == 3: return estrategia == "RATITA"
    if nivel >= 4: return estrategia in ["RATA","LOBO"]

    return False
def cierre_market_cambio(sym, reg_nuevo):
    viejo = REG_ANT.get(sym, "LINEAL").split()[0] if REG_ANT.get(sym) else "LINEAL"
    nuevo = reg_nuevo.split()[0]
    if viejo==nuevo: return
    print(f"CAMBIO {sym} {viejo}->{nuevo} -> CIERRE MARKET")
    for uid in list(POSICIONES_ABIERTAS.keys()):
        for p in POSICIONES_ABIERTAS[uid][:]:
            if not candado(p["estrategia"], reg_nuevo):
                lado = "BUY" if p["estrategia"] in NEGRAS else "SELL"
                try: ejecutar_orden_real(p["symbol"], lado, p["usdt"])
                except: pass
                try: POSICIONES_ABIERTAS[uid].remove(p)
                except: pass
    guardar_datos()

MAPA_ANIDADO_V50_9 = {
    "LINEAL_MUERTO": ["MOJARRA", "MOJARRITA"],
    "LINEAL": ["MOJARRA", "PIRANA_BLANCA", "RATITA", "RATA"],
    "ALCISTA": ["MOJARRA", "PIRANA_BLANCA","RATITA", "RATA", "LOBO"],
    "ALCISTA_FUERTE": ["MOJARRA", "PIRANA_BLANCA","RATITA", "RATA", "LOBO", "TIBURON"],
    "BAJISTA": ["MOJARRA_NEGRA", "PIRANA_NEGRA", "RATA_NEGRA", "LOBO_NEGRO"],
    "CRASH": ["MOJARRA_NEGRA", "PIRANA_NEGRA", "RATA_NEGRA", "LOBO_NEGRO", "KRAKEN"]
}
MAPA_ESTRATEGIA = {"LINEAL_MUERTO": "MANADA LIBRE MOJARRA+MOJARRITA x6", "LINEAL": "MOJARRA 0.2% + RATA DIST 0.10%", "ALCISTA": "REGIMEN 3 LOBO 1.7% JEFE V50.23", "ALCISTA_FUERTE": "REGIMEN 4 LOBO 1.7% + TIBURON 5-10% V50.23", "BAJISTA": "REGIMEN 5 LOBO_NEGRO 1.7% JEFE V50.23", "CRASH": "REGIMEN 6 CRASH LOBO_NEGRO 1.7% + KRAKEN V50.23"}
def estrategia_prevista(regimen_txt):
    reg = regimen_txt.split()[0] if regimen_txt else "LINEAL"
    return MAPA_ESTRATEGIA.get(reg, "MANADA LIBRE")
BLANCAS_SET = {"MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATITA","RATA","LOBO","TIBURON"}
def mercado_esta_rojo():
    for reg in ESTADO.get("regimenes", {}).values():
        rs = reg.split()[0] if reg else ""
        if rs in ("BAJISTA","CRASH"):
            return True, reg
    try:
        for sym, banda in BANDAS_ACTIVAS.items():
            if not banda.get("activa"): continue
            tipo = str(banda.get("tipo","")).upper()
            if "BAJISTA" in tipo or "CRASH" in tipo:
                return True, f"BANDA {sym} {tipo}"
    except: pass
    return False, ""
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
if REAL_BALANCE_USDT < 100: REAL_BALANCE_USDT = CAPITAL_BASE
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
        if client: return float(client.get_symbol_ticker(symbol=symbol)['price'])
    except: pass
    for base in ["https://data-api.binance.vision","https://api.binance.com","https://api1.binance.com","https://api2.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/price?symbol={symbol}", timeout=4)
            if r.status_code==200: return float(r.json()['price'])
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
        if estrategia in ["MOJARRA", "MOJARRITA", "PIRANA_BLANCA", "PIRANA", "MOJARRA_NEGRA"]: return rango[0]
        if estrategia == "LOBO" or estrategia == "LOBO_NEGRO": return 1.7
        d1h = get_velas(symbol,"1h",100)
        if not d1h: return rango[0]
        adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
        atr = atr_calc(d1h, 14)
        precio = d1h["closes"][-1]
        atr_pct = (atr/precio*100) if precio!=0 else 0
        if estrategia in ["RATA","RATA_NEGRA","RATITA"]:
            if adx > 30 and atr_pct > 1.0: return rango[1]
            return rango[0]
        if estrategia == "TIBURON":
            if adx > 30 and atr_pct > 1.5: return rango[1]
            return rango[0]
        if estrategia == "KRAKEN":
            if atr_pct > 2.0: return rango[1]
            return rango[0]
        return rango[0]
    except: return ESTRATEGIAS_V45[estrategia]["rango_tp"][0]
def tiempo_fuera_inteligente(symbol, tipo_actual):
    try:
        d1h = get_velas(symbol,"1h",60)
        d5 = get_velas(symbol,"5m",60)
        if not d1h or not d5: return TIEMPO_FUERA_NORMAL if tipo_actual=="NORMAL" else TIEMPO_FUERA_BAJISTA
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
    except: return TIEMPO_FUERA_NORMAL if tipo_actual=="NORMAL" else TIEMPO_FUERA_BAJISTA
def get_cambio_24h(symbol):
    try:
        d = get_velas(symbol, "1d", 3)
        if not d or len(d["closes"]) < 2: return 0
        return (d["closes"][-1] - d["closes"][-2]) / d["closes"][-2] * 100 if d["closes"][-2]!=0 else 0
    except: return 0
def kraken_inteligente_ok(symbol):
    global KRAKEN_BLOQUEO_HASTA
    if time.time() < KRAKEN_BLOQUEO_HASTA: return False
    cambio = get_cambio_24h(symbol)
    if cambio > -8: return False
    d1h = get_velas(symbol,"1h",60)
    if not d1h: return False
    rsi = rsi_calc(d1h["closes"],14)
    vol_prom = sum(d1h["vols"][-20:])/20 if len(d1h["vols"])>=20 else 1
    vol_x = d1h["vols"][-1]/vol_prom if vol_prom else 0
    if rsi > 20 or vol_x < 2.0: return False
    return True
def kraken_registrar_sl():
    global KRAKEN_SL_COUNT, KRAKEN_BLOQUEO_HASTA
    KRAKEN_SL_COUNT += 1
    if KRAKEN_SL_COUNT == 1:
        KRAKEN_BLOQUEO_HASTA = time.time() + 43200
    elif KRAKEN_SL_COUNT >= 2:
        KRAKEN_BLOQUEO_HASTA = time.time() + 86400
        KRAKEN_SL_COUNT = 0
def kraken_reset_si_tp():
    global KRAKEN_SL_COUNT
    KRAKEN_SL_COUNT = 0
def vender_mojarra_vieja_en_profit_y_recargar():
    try:
        mejor=None; mejor_pnl=0
        for uid, lista in POSICIONES_ABIERTAS.items():
            if not isinstance(lista, list): continue
            for p in lista:
                if p.get("estrategia") in ["MOJARRA","MOJARRITA"]:
                    precio = get_precio_robusto(p["symbol"])
                    if p["entrada"]==0: continue
                    pnl = (precio - p["entrada"])/p["entrada"]*100
                    if pnl > 0.20 and pnl > mejor_pnl:
                        mejor=(uid,p); mejor_pnl=pnl
        if mejor:
            uid,p = mejor
            POSICIONES_ABIERTAS[uid].remove(p)
            ejecutar_orden_real("BNBUSDT","BUY", TANQUE_BNB_RECARGA)
            return True
    except: pass
    return False
def get_umbral_adaptativo(regimen):
    reg = regimen.split()[0] if regimen else "LINEAL"
    if reg == "ALCISTA_FUERTE": return {"rsi_kraken": 30.5, "rsi_pirana": 35, "rsi_pirana_negra": 30, "vsa_kraken_base": 1.3, "vsa_negra_base": 1.3, "adx_tiburon": 28, "rsi_lobo_min": 48, "rsi_rata_max": 42, "rsi_lobo_negro_max": 60, "rsi_rata_negra_min": 65}
    elif reg == "ALCISTA": return {"rsi_kraken": 29.5, "rsi_pirana": 33, "rsi_pirana_negra": 29, "vsa_kraken_base": 1.4, "vsa_negra_base": 1.4, "adx_tiburon": 30, "rsi_lobo_min": 45, "rsi_rata_max": 45, "rsi_lobo_negro_max": 55, "rsi_rata_negra_min": 65}
    elif reg == "BAJISTA": return {"rsi_kraken": 27.5, "rsi_pirana": 30, "rsi_pirana_negra": 35, "vsa_kraken_base": 1.6, "vsa_negra_base": 1.3, "adx_tiburon": 35, "rsi_lobo_min": 999, "rsi_rata_max": 30, "rsi_lobo_negro_max": 55, "rsi_rata_negra_min": 55}
    elif reg == "CRASH": return {"rsi_kraken": 30.0, "rsi_pirana": 28, "rsi_pirana_negra": 40, "vsa_kraken_base": 1.3, "vsa_negra_base": 1.3, "adx_tiburon": 35, "rsi_lobo_min": 999, "rsi_rata_max": 30, "rsi_lobo_negro_max": 60, "rsi_rata_negra_min": 50}
    elif reg == "LINEAL": return {"rsi_kraken": 29.0, "rsi_pirana": 38, "rsi_pirana_negra": 28, "vsa_kraken_base": 1.3, "vsa_negra_base": 1.3, "adx_tiburon": 28, "rsi_lobo_min": 52, "rsi_rata_max": 38, "rsi_lobo_negro_max": 55, "rsi_rata_negra_min": 60}
    else: return {"rsi_kraken": 27.5, "rsi_pirana": 30, "rsi_pirana_negra": 28, "vsa_kraken_base": 1.6, "vsa_negra_base": 1.6, "adx_tiburon": 35, "rsi_lobo_min": 999, "rsi_rata_max": 30, "rsi_lobo_negro_max": 55, "rsi_rata_negra_min": 60}
def detectar_regimen_sym(symbol):
    d1h=get_velas(symbol,"1h",210); d1d=get_velas(symbol,"1d",15)
    if not d1h or not d1d: return "LINEAL", "Sin datos"
    closes_1h=d1h["closes"]; closes_1d=d1d["closes"]
    ema200 = ema_calc(closes_1h, 200); ema50 = ema_calc(closes_1h, 50)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
    atr = atr_calc(d1h, 14); precio = closes_1h[-1]
    atr_pct = (atr/precio*100) if precio!=0 else 0
    rent_14d = (closes_1d[-1]-closes_1d[0])/closes_1d[0] if closes_1d[0]!=0 else 0
    dist_ema200 = (precio - ema200)/ema200 if ema200!=0 else 0
    rsi_1h = rsi_calc(closes_1h,14)
    if adx_1h < 15 and atr_pct < 0.6: return "LINEAL_MUERTO", f"MUERTO ADX{adx_1h:.0f} ATR{atr_pct:.2f}%"
    if rent_14d < -0.12 and precio < ema200 and precio < ema50 and adx_1h >= 28: return "CRASH", f"CRASH ADX{adx_1h:.0f} {rent_14d*100:.1f}%"
    if precio < ema200 and 18 <= adx_1h <= 35 and -0.12 <= rent_14d <= -0.01 and -0.08 <= dist_ema200 <= -0.01 and 22 <= rsi_1h <= 60: return "BAJISTA", f"BAJISTA ADX{adx_1h:.0f} {rent_14d*100:.1f}%"
    if precio > ema200 and precio > ema50 and adx_1h >= 28 and rent_14d > 0.06 and dist_ema200 > 0.02 and rsi_1h >= 50: return "ALCISTA_FUERTE", f"FUERTE ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
    if precio > ema200 and 18 <= adx_1h <= 35 and 0.01 <= rent_14d <= 0.12 and 0.01 <= dist_ema200 <= 0.08 and 40 <= rsi_1h <= 78: return "ALCISTA", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
    if precio < ema200 and adx_1h > 18 and rent_14d < -0.01: return "BAJISTA", f"BAJISTA ADX{adx_1h:.0f} {rent_14d*100:.1f}%"
    return "LINEAL", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
def get_vol_requerido_auto(estrategia, reg_simple, adx, atr_pct=0):
    if IS_TESTNET: return 0.0
    if estrategia == "MOJARRA": return 0.10
    if estrategia in ["PIRANA_BLANCA", "PIRANA", "MOJARRITA", "RATITA"]: return 0.25
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
    if estrategia_nombre in ["MOJARRA", "MOJARRITA", "PIRANA_BLANCA", "PIRANA", "RATITA"]:
        if IS_TESTNET:
            if rsi <= 35: return True,f"[{symbol}] {estrategia_nombre} TESTNET RSI{int(rsi)}<=35 {reg_simple}", 0.85
            return False,f"[{symbol}] {estrategia_nombre} TESTNET RSI{int(rsi)}/35 {reg_simple}", 0.30
        if rsi <= 35 and vol_actual > vol_prom*vol_requerido: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}<=35 Vol{vol_actual/vol_prom:.1f}>{vol_requerido:.2f} {reg_simple}", 0.85
        return False,f"[{symbol}] {estrategia_nombre} Vol{vol_actual/vol_prom:.1f}/{vol_requerido:.2f} RSI{int(rsi)}/35 {reg_simple}", 0.30
    if IS_TESTNET: check_vol = True
    else: check_vol = vol_actual>vol_prom*vol_requerido
    if precio<=lower and rsi<umb["rsi_rata_max"] and check_vol: return True,f"[{symbol}] {estrategia_nombre} V51 {reg_simple} RSI{int(rsi)}<{umb['rsi_rata_max']} Vol{vol_actual/vol_prom:.1f}>{vol_requerido:.2f} ADX{adx:.0f}", 0.68
    return False,f"[{symbol}] {estrategia_nombre} {reg_simple} Vol{vol_actual/vol_prom:.1f}/{vol_requerido:.2f} RSI{int(rsi)}/{umb['rsi_rata_max']} ADX{adx:.0f}", 0.30
def detectar_SHORT_sym(symbol, estrategia_nombre="MOJARRA_NEGRA"):
    d5=get_velas(symbol,"5m",100); d1h=get_velas(symbol,"1h",50)
    if not d5: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    sma20=sum(closes[-20:])/20; var=sum((x-sma20)**2 for x in closes[-20:])/20; std=var**0.5; upper=sma20+2*std
    precio=closes[-1]; vol_prom=sum(d5["vols"][-20:])/20; vol_actual=d5["vols"][-1]
    adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 15
    reg_simple = reg.split()[0] if reg else "LINEAL"
    vol_requerido = get_vol_requerido_auto(estrategia_nombre, reg_simple, adx, 0)
    check_vol = True if IS_TESTNET else vol_actual>vol_prom*vol_requerido
    if estrategia_nombre == "MOJARRA_NEGRA":
        if IS_TESTNET:
            if rsi >= 65: return True,f"[{symbol}] {estrategia_nombre} TESTNET RSI{int(rsi)}>=65 SHORT {reg_simple}", 0.85
            return False,f"[{symbol}] {estrategia_nombre} TESTNET RSI{int(rsi)}/65 {reg_simple}", 0.30
        if precio>=upper*0.998 and rsi>=55 and check_vol: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}>=55 >=UPPER {reg_simple} SHORT", 0.85
        return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/55 {reg_simple}", 0.30
    if estrategia_nombre == "PIRANA_NEGRA":
        if precio>=upper*0.997 and rsi>=umb.get("rsi_pirana_negra",35) and check_vol: return True,f"[{symbol}] {estrategia_nombre} {reg_simple} RSI{int(rsi)}>={umb.get('rsi_pirana_negra')} >=UPPER ADX{adx:.0f}", 0.68
        return False,f"[{symbol}] {estrategia_nombre} {reg_simple} RSI{int(rsi)}/{umb.get('rsi_pirana_negra')} ADX{adx:.0f}", 0.30
    if estrategia_nombre == "RATA_NEGRA":
        if precio>=upper and rsi>=umb.get("rsi_rata_negra_min",55) and check_vol: return True,f"[{symbol}] {estrategia_nombre} {reg_simple} RSI{int(rsi)}>={umb.get('rsi_rata_negra_min')} >=UPPER ADX{adx:.0f}", 0.68
        return False,f"[{symbol}] {estrategia_nombre} {reg_simple} RSI{int(rsi)}/{umb.get('rsi_rata_negra_min')} ADX{adx:.0f}", 0.30
    return False,f"{symbol} {estrategia_nombre} no mapeado",0
def detectar_LOBO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if reg_simple not in ["ALCISTA","ALCISTA_FUERTE"]: return False,f"[{symbol}] LOBO BLOQUEADO Solo ALCISTA {reg_simple}",0.10
    closes=d["closes"]; ema20=sum(closes[-20:])/20; ema50=sum(closes[-50:])/50
    ema12=sum(closes[-12:])/12; ema26=sum(closes[-26:])/26; macd=ema12-ema26
    adx = adx_calc(d["highs"], d["lows"], d["closes"], 14)
    rsi = rsi_calc(closes,14)
    retroceso_ok = abs(closes[-1]-ema20)/ema20 < 0.035 if ema20!=0 else False
    tendencia_ok = closes[-1] > ema20 and ema20 > ema50
    momentum_ok = macd > 0 and rsi >= umb["rsi_lobo_min"] and adx >= 18
    if tendencia_ok and momentum_ok and retroceso_ok: return True,f"[{symbol}] LOBO V51 {reg_simple} ADX{adx:.0f} RSI{int(rsi)} RET3.5% TP1.7%", 0.75
    if tendencia_ok and rsi >= 55 and adx >= 20: return True,f"[{symbol}] LOBO V51 {reg_simple} ADX{adx:.0f} RSI{int(rsi)} DIRECTO TP1.7%", 0.68
    return False,f"[{symbol}] LOBO {reg_simple} ADX{adx:.0f} RSI{int(rsi)} esperando",0.35
def detectar_LOBO_NEGRO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if reg_simple not in ["BAJISTA","CRASH"]: return False,f"[{symbol}] LOBO_NEGRO BLOQUEADO Solo BAJISTA {reg_simple}",0.10
    closes=d["closes"]; ema20=sum(closes[-20:])/20; ema50=sum(closes[-50:])/50
    ema12=sum(closes[-12:])/12; ema26=sum(closes[-26:])/26; macd=ema12-ema26
    adx = adx_calc(d["highs"], d["lows"], d["closes"], 14)
    rsi = rsi_calc(closes,14)
    retroceso_ok = abs(closes[-1]-ema20)/ema20 < 0.035 if ema20!=0 else False
    tendencia_ok = closes[-1] < ema20 and ema20 < ema50
    momentum_ok = macd < 0 and rsi <= umb.get("rsi_lobo_negro_max",55) and adx >= 18
    if tendencia_ok and momentum_ok and retroceso_ok: return True,f"[{symbol}] LOBO_NEGRO V51 {reg_simple} ADX{adx:.0f} RSI{int(rsi)} RET3.5% TP1.7%", 0.75
    if tendencia_ok and rsi <= 45 and adx >= 20: return True,f"[{symbol}] LOBO_NEGRO V51 {reg_simple} ADX{adx:.0f} RSI{int(rsi)} DIRECTO TP1.7%", 0.68
    return False,f"[{symbol}] LOBO_NEGRO {reg_simple} ADX{adx:.0f} RSI{int(rsi)} esperando",0.35
def detectar_TIBURON_sym(symbol):
    d=get_velas(symbol,"1d",210); d1h=get_velas(symbol,"1h",50)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d["closes"]; ema50=sum(closes[-50:])/50; rsi14=rsi_calc(closes,14)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 20
    if closes[-1] > ema50 and rsi14 > 45 and adx_1h > umb["adx_tiburon"]: return True,f"[{symbol}] TIBURON V51 {reg.split()[0]} ADX{adx_1h:.0f}>{umb['adx_tiburon']} RSI{int(rsi14)}", 0.85
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
    if panico_real: return True,f"[{symbol}] KRAKEN PANICO REAL RSI{int(rsi_1h)}<20 VSA{vsa_mult:.1f}>1.4 <EMA200 ADX{adx_1h:.0f}",0.99
    return False,f"[{symbol}] KRAKEN ESPERA PANICO RSI{int(rsi_1h)}/20 VSA{vsa_mult:.1f}/1.4",0.05
def gestionar_bandas_moviles():
    global BANDAS_ACTIVAS, BANDAS_TIEMPO_FUERA
    ahora = time.time()
    for sym in list(BANDAS_ACTIVAS.keys()):
        banda = BANDAS_ACTIVAS.get(sym)
        if not banda or not banda.get("activa"): BANDAS_TIEMPO_FUERA.pop(sym, None); continue
        reg = ESTADO.get("regimenes",{}).get(sym,"LINEAL").split()[0]
        if reg == "LINEAL_MUERTO" and banda.get("tipo")=="BAJISTA":
            precio = get_precio_robusto(sym)
            if precio>0:
                BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio*0.995, "tope": precio*1.08, "tipo": "NORMAL", "activa": True, "origen_mov": f"ESCLAVA V51 {reg} BAJISTA->NORMAL", "creada_en": ahora}
                BANDAS_TIEMPO_FUERA.pop(sym, None); continue
        precio = get_precio_robusto(sym)
        if precio==0: continue
        entrada = banda["entrada_tiburon"]; tope = banda["tope"]; tipo = banda.get("tipo","NORMAL")
        adentro = entrada*0.997 <= precio <= tope
        if adentro: BANDAS_TIEMPO_FUERA.pop(sym, None); continue
        fuera_tipo = "ABAJO" if precio < entrada else "ARRIBA"
        if sym not in BANDAS_TIEMPO_FUERA or BANDAS_TIEMPO_FUERA[sym]["tipo_fuera"]!= fuera_tipo: BANDAS_TIEMPO_FUERA[sym] = {"fuera_desde": ahora, "tipo_fuera": fuera_tipo}
        tiempo_fuera = ahora - BANDAS_TIEMPO_FUERA[sym]["fuera_desde"]
        tiempo_optimo = tiempo_fuera_inteligente(sym, tipo)
        if tipo=="NORMAL" and fuera_tipo=="ABAJO" and tiempo_fuera > tiempo_optimo:
            BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio*0.97, "tope": precio*0.995, "tipo": "BAJISTA", "activa": True, "origen_mov": f"AUTO PANICO {entrada:.0f}->{tiempo_fuera/3600:.1f}h", "creada_en": ahora}
            BANDAS_TIEMPO_FUERA.pop(sym, None)
        elif tipo=="BAJISTA" and fuera_tipo=="ARRIBA" and tiempo_fuera > tiempo_optimo:
            BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio, "tope": precio*1.10, "tipo": "NORMAL", "activa": True, "origen_mov": f"AUTO CAZA {tiempo_fuera/3600:.1f}h", "creada_en": ahora}
            BANDAS_TIEMPO_FUERA.pop(sym, None)
def es_rentable(tp_bruto, estrategia="RATA"):
    min_neto = FILTRO_NETO_MIN_MOJARRA if estrategia in ["MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATITA","MOJARRA_NEGRA"] else FILTRO_NETO_MIN
    return (tp_bruto - COMISION_TOTAL) >= min_neto, tp_bruto - COMISION_TOTAL
def contar_posiciones_globales():
    counts = {}; total_tib = 0
    for uid, lista in POSICIONES_ABIERTAS.items():
        if not isinstance(lista, list): continue
        for p in lista:
            key = (p.get("symbol"), p.get("estrategia"))
            counts[key] = counts.get(key, 0) + 1
            if p.get("estrategia") == "TIBURON": total_tib += 1
    return counts, total_tib
def banda_txt_display(k,v):
    base = f"BANDA {k} {v['entrada_tiburon']:.0f}->{v['tope']:.0f} {v['tipo']}"
    if v.get("origen_mov"): base += f" MOVIL"
    return base
def banda_txt_api(k,v): return f"{k.replace('USDT','')} {v.get('tipo','')}"
def notificar_caza(sym, tipo, precio, tp, sl, banda_txt, usdt, motivo=""):
    try:
        msg = f"V51 {tipo} CAZADA!\nPar: {sym}\nEntrada: ${precio:.2f}\nMonto: ${usdt:.2f}\nTP: {tp:.1f}% | SL: {sl:.1f}%\nBanda: {banda_txt}\n{motivo[:100]}\nExp: {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n{WEB_URL}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except: pass
def notificar_cierre(sym, tipo, entrada, salida, ganancia_usdt, ganancia_pct, es_tp, subtipo=""):
    try:
        u = USUARIOS.get(ADMINS_IDS[0], {})
        hoy = u.get("neto_hoy",0); total = (u.get("balance",0)-u.get("capital_inicial",0))
        if es_tp: msg = f"V51 PRESA DEVORADA\n{tipo} {sym}\n${entrada:.2f} -> ${salida:.2f}\n+${ganancia_usdt:.2f} ({ganancia_pct:+.2f}%)\nHoy: ${hoy:+.2f} Total: ${total:+.2f}"
        else: msg = f"V51 ESCAPO!\n{tipo} {sym}\n${entrada:.2f} -> ${salida:.2f}\n${ganancia_usdt:.2f} ({ganancia_pct:+.2f}%)\nHoy: ${hoy:+.2f} Total: ${total:+.2f}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except: pass
def notificar_cazando(sym, regimen):
    try:
        msg = f"CAZANDO {sym} {regimen} V51 BLINDADA"
        ahora = time.time(); key = f"caz_{sym}"
        if key in ULTIMO_CAZANDO and ahora - ULTIMO_CAZANDO[key] < 300: return
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
        if ahora - ULTIMO_PENSAMIENTO < 1800: return
        ULTIMO_PENSAMIENTO = ahora
        regs_txt = "\n".join([f"{k}: {v}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO.get("regimen","LINEAL")
        bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
        ok, motivo, sym, est, fuerza = detectar_BI_CEREBRO(ESTADO.get("regimen","LINEAL"))

        monedas_txt = f"{len(MONEDAS_ACTIVAS)}/20 ({','.join([m.replace('USDT','') for m in MONEDAS_ACTIVAS])})"
        tanque_txt = f"TPs {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} Tanque {monedas_txt}"

        if ok:
            texto = f"PENSAMIENTO LOBO V51 BLINDADA\n{regs_txt}\n{bandas_txt}\nEstrategia: {est} en {sym} ({fuerza:.2f})\n{motivo[:120]}\n{tanque_txt}\n📊 Dashboard: {WEB_URL}"
        else:
            texto = f"MERCADO EN LECTURA V51 BLINDADA\n{regs_txt}\n{bandas_txt}\nAcechando... {motivo[:100]}\n{tanque_txt}\n📊 Dashboard: {WEB_URL}"

        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, texto)
                except: pass
    except Exception as e:
        print(f"Error pensamiento: {e}")        
def detectar_BI_CEREBRO(regimen):
    counts_global, total_tib_global = contar_posiciones_globales()
    tib_por_moneda = {}; kraken_por_moneda = {}
    for uid, lista in POSICIONES_ABIERTAS.items():
        if not isinstance(lista, list): continue
        for p in lista:
            sym = p.get("symbol")
            if p.get("estrategia") == "TIBURON": tib_por_moneda[sym] = tib_por_moneda.get(sym,0)+1
            if p.get("estrategia") == "KRAKEN": kraken_por_moneda[sym] = kraken_por_moneda.get(sym,0)+1
    rojo, motivo_rojo = mercado_esta_rojo()
    mejor_motivo=""; mejor_sym=""; mejor_fuerza=0; mejor_est=None
    for sym in MONEDAS_ACTIVAS:
        total_madres_en_sym = sum(1 for uid2, lista2 in POSICIONES_ABIERTAS.items() for p in lista2 if p.get("symbol")==sym and p.get("estrategia") in ["RATA","RATITA","LOBO","TIBURON","KRAKEN","RATA_NEGRA","LOBO_NEGRO"])
        tib_en_sym = tib_por_moneda.get(sym,0)
        kraken_en_sym = kraken_por_moneda.get(sym,0)
        reg_sym = ESTADO.get("regimenes",{}).get(sym,"LINEAL").split()[0]
        cambio_24h = get_cambio_24h(sym)
        if reg_sym in ("BAJISTA","CRASH") or rojo:
            if cambio_24h > -5:
                orden = ["MOJARRA_NEGRA","PIRANA_NEGRA"]
            elif cambio_24h > -8:
                orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","RATA_NEGRA","LOBO_NEGRO"]
            else:
                orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","RATA_NEGRA","LOBO_NEGRO"]
                if kraken_inteligente_ok(sym):
                    orden.append("KRAKEN")
        else:
            if reg_sym == "ALCISTA_FUERTE": orden = ["MOJARRA","PIRANA_BLANCA","RATITA","LOBO","RATA","TIBURON"]
            elif reg_sym == "BAJISTA": orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","RATA_NEGRA","LOBO_NEGRO"]
            elif reg_sym == "CRASH":
                orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","RATA_NEGRA","LOBO_NEGRO"]
                if kraken_inteligente_ok(sym): orden.append("KRAKEN")
            elif reg_sym == "ALCISTA": orden = ["MOJARRA","PIRANA_BLANCA","RATITA","RATA","LOBO"]
            elif reg_sym == "LINEAL_MUERTO": orden = ["MOJARRA", "MOJARRITA"]
            else: orden = ["MOJARRA","PIRANA_BLANCA","RATITA","RATA","LOBO","TIBURON","KRAKEN"]
        for nombre in orden:
            if not candado(nombre, reg_sym): continue
            if rojo and nombre in BLANCAS_SET: continue
            if not candado_evolucion_V51(sym, nombre, reg_sym): continue
            MADRES = ["RATA","RATITA","LOBO","TIBURON","KRAKEN","RATA_NEGRA","LOBO_NEGRO"]
            if nombre in MADRES and total_madres_en_sym >= 3: continue
            if nombre == "KRAKEN" and kraken_en_sym >= 1: continue
            if nombre == "TIBURON" and tib_en_sym >= 1: continue
            if nombre == "TIBURON" and total_tib_global >= 2: continue
            if nombre=="RATA": ok,motivo,wr = detectar_RATA_sym(sym, "RATA")
            elif nombre=="RATITA": ok,motivo,wr = detectar_RATA_sym(sym, "RATITA")
            elif nombre=="MOJARRA": ok,motivo,wr = detectar_RATA_sym(sym, "MOJARRA")
            elif nombre=="MOJARRITA": ok,motivo,wr = detectar_RATA_sym(sym, "MOJARRITA")
            elif nombre in ["PIRANA_BLANCA","PIRANA"]: ok,motivo,wr = detectar_RATA_sym(sym, "PIRANA_BLANCA")
            elif nombre in ["RATA_NEGRA","PIRANA_NEGRA","MOJARRA_NEGRA"]: ok,motivo,wr = detectar_SHORT_sym(sym, nombre)
            elif nombre=="LOBO": ok,motivo,wr = detectar_LOBO_sym(sym)
            elif nombre=="LOBO_NEGRO": ok,motivo,wr = detectar_LOBO_NEGRO_sym(sym)
            elif nombre=="TIBURON": ok,motivo,wr = detectar_TIBURON_sym(sym)
            else: ok,motivo,wr = detectar_KRAKEN_sym(sym)
            tp_a = tp_adaptativo(sym, nombre if nombre in ESTRATEGIAS_V45 else "RATA")
            if ok and wr > mejor_fuerza and es_rentable(tp_a, nombre)[0]:
                mejor_fuerza=wr; mejor_est=nombre; mejor_motivo=f"[{sym} {reg_sym} {cambio_24h:.1f}%] {motivo} TP{tp_a:.1f}% V51 Nv{EVOLUCION_NIVEL.get(sym,{}).get(reg_sym,1)}"; mejor_sym=sym
    if mejor_est: return True, mejor_motivo, mejor_sym, mejor_est, mejor_fuerza
    if rojo: return False, f"CANDADO 3-NIVELES {motivo_rojo}", MONEDAS_ACTIVAS[0], None, 0
    return False, f"V51 BLINDADA MANADA LIBRE x6", MONEDAS_ACTIVAS[0], None, 0
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
            USUARIOS[uid]={"user_id":uid,"prendido":False,"balance":BALANCE_INICIAL,"capital_inicial":BALANCE_INICIAL,"neto_hoy":0.0,"ops_hoy":0,"ganadas":0,"perdidas":0,"modo":"ESPERANDO","mercado":"Toca PRENDER","ultima_op":{}, "historial":[],"estrategias":{k:{"ops":0,"ganadas":0,"neto":0.0} for k in ESTRATEGIAS_V45},"fecha_hoy":ahora_art().strftime("%Y-%m-%d")}
        u = USUARIOS[uid]
        if u.get("balance",0) < 100: u["balance"] = BALANCE_INICIAL
        if u.get("capital_inicial",0) < 100: u["capital_inicial"] = BALANCE_INICIAL
        if "estrategias" not in u or not isinstance(u.get("estrategias"), dict): u["estrategias"] = {}
        for k in ESTRATEGIAS_V45:
            if k not in u["estrategias"]: u["estrategias"][k] = {"ops":0,"ganadas":0,"neto":0.0}
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
            with open(os.path.join(DATA_DIR,"pirana_v50.json"),"w") as f: json.dump({"estado": ESTADO_PIRANA, "estado_negra": ESTADO_PIRANA_NEGRA, "cache": CANDIDATAS_CACHE, "bandas_tiempo": BANDAS_TIEMPO_FUERA, "kraken": {"sl_count": KRAKEN_SL_COUNT, "bloqueo_hasta": KRAKEN_BLOQUEO_HASTA}, "v51_reg_ant": REG_ANT, "v51_contadores": CONTADOR_POR_REGIMEN, "v51_niveles": EVOLUCION_NIVEL},f,indent=2)
    except: pass
def cargar_datos():
    global MONEDAS_ACTIVAS, POSICIONES_ABIERTAS, BANDAS_ACTIVAS, ESTADO_PIRANA, ESTADO_PIRANA_NEGRA, CANDIDATAS_CACHE, BANDAS_TIEMPO_FUERA, CONTADOR_TP_EXPANSION, TANQUE_BNB_USDT, KRAKEN_SL_COUNT, KRAKEN_BLOQUEO_HASTA, REG_ANT, CONTADOR_POR_REGIMEN, EVOLUCION_NIVEL
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,"r") as f:
                data=json.load(f)
                for k,v in data.items():
                    if isinstance(v, dict):
                        if v.get("balance",0) < 100: v["balance"] = BALANCE_INICIAL
                        if v.get("capital_inicial",0) < 100: v["capital_inicial"] = BALANCE_INICIAL
                        if "estrategias" not in v or not isinstance(v.get("estrategias"), dict): v["estrategias"] = {}
                        for ek in ESTRATEGIAS_V45:
                            if ek not in v["estrategias"]: v["estrategias"][ek] = {"ops":0,"ganadas":0,"neto":0.0}
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
        if os.path.exists(os.path.join(DATA_DIR,"pirana_v50.json")):
            with open(os.path.join(DATA_DIR,"pirana_v50.json"),"r") as f:
                pj=json.load(f)
                ESTADO_PIRANA=pj.get("estado",{})
                ESTADO_PIRANA_NEGRA=pj.get("estado_negra",{})
                BANDAS_TIEMPO_FUERA=pj.get("bandas_tiempo",{})
                kr = pj.get("kraken",{})
                KRAKEN_SL_COUNT = kr.get("sl_count",0)
                KRAKEN_BLOQUEO_HASTA = kr.get("bloqueo_hasta",0)
                c = pj.get("cache")
                if c: CANDIDATAS_CACHE.update(c)
                if pj.get("v51_reg_ant"): REG_ANT.update(pj.get("v51_reg_ant"))
                if pj.get("v51_contadores"): CONTADOR_POR_REGIMEN.update(pj.get("v51_contadores"))
                if pj.get("v51_niveles"): EVOLUCION_NIVEL.update(pj.get("v51_niveles"))
    except Exception as e: print(f"cargar error {e}")
def limpiar_pos_viejas(): pass
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
            if not vender_mojarra_vieja_en_profit_y_recargar():
                ejecutar_orden_real("BNBUSDT","BUY", TANQUE_BNB_RECARGA)
            return False
        return True
    except: return True
def ejecutar_orden_real(symbol, side, usdt_amount):
    try:
        if not client: return True, {"simulado": True}, get_precio_robusto(symbol)
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
        if IS_TESTNET: return True, {"simulado": True, "error": str(e)}, get_precio_robusto(symbol)
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
            if wr_total > mejor_wr: mejor_wr = wr_total; mejor = sym
        except: continue
    return mejor, mejor_wr
def intentar_expandir(user_id_notify=None):
    global CONTADOR_TP_EXPANSION, MONEDAS_ACTIVAS
    if CONTADOR_TP_EXPANSION < META_TP_PARA_EXPANDIR: return False
    if len(MONEDAS_ACTIVAS) >= MAX_MONEDAS: return False
    mejor_sym, wr = detectar_mejor_candidata()
    if not mejor_sym: return False
    msg = f"META {META_TP_PARA_EXPANDIR:.0f} TPs\nCandidata: {mejor_sym} WR {wr:.2f}\nActual {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} -> {len(MONEDAS_ACTIVAS)+1}/{MAX_MONEDAS}\nAutorizas sumar {mejor_sym}?"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"AUTORIZAR {mejor_sym}", callback_data=f"AUTH_ADD_{mejor_sym}"), types.InlineKeyboardButton(f"RECHAZAR", callback_data=f"REJECT_{mejor_sym}"))
    try:
        targets = ADMINS_IDS if not user_id_notify else [user_id_notify]
        for uid in targets: bot.send_message(uid, msg, reply_markup=kb)
    except: pass
        CANDIDATAS_CACHE["_aviso_meta"] = time.time()
    guardar_datos()
    return True
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global MONEDAS_ACTIVAS, CONTADOR_TP_EXPANSION
    data = call.data
    try:
        if data.startswith("AUTH_ADD_"):
            nueva = data.replace("AUTH_ADD_", "")
            if nueva not in MONEDAS_ACTIVAS and len(MONEDAS_ACTIVAS) < MAX_MONEDAS:
                MONEDAS_ACTIVAS.append(nueva)
                CONTADOR_TP_EXPANSION = 0
                CANDIDATAS_CACHE["proxima"] = None
                CANDIDATAS_CACHE["_aviso_meta"] = 0
                guardar_datos()
                bot.answer_callback_query(call.id, f"{nueva} AUTORIZADA!")
                bot.send_message(call.message.chat.id, 
                    f"✅ {nueva} AUTORIZADO\n"
                    f"Monedas: {len(MONEDAS_ACTIVAS)}/20 ({','.join([m.replace('USDT','') for m in MONEDAS_ACTIVAS])})\n"
                    f"Tanque: {len(MONEDAS_ACTIVAS)}/20 activo\n"
                    f"📊 Dashboard: {WEB_URL}")
            else:
                bot.answer_callback_query(call.id, "Ya agregada")
        elif data.startswith("REJECT_"):
            rechazada = data.replace("REJECT_", "")
            bot.answer_callback_query(call.id, f"{rechazada} Rechazada")
            bot.send_message(call.message.chat.id, f"❌ {rechazada} rechazada. Sigue con {len(MONEDAS_ACTIVAS)}/20")
            CANDIDATAS_CACHE["proxima"] = None
            guardar_datos()
    except Exception as e:
        print(f"Error callback: {e}")
        bot.answer_callback_query(call.id, "Error")
def escanear_candidatas_y_proponer():
    ahora = time.time()
    if ahora - CANDIDATAS_CACHE.get("_ultimo_scan",0) < TIEMPO_ESCANEO_CANDIDATAS: return
    CANDIDATAS_CACHE["_ultimo_scan"] = ahora
    if CONTADOR_TP_EXPANSION < META_TP_PARA_EXPANDIR * 0.8: return
    mejor, wr = detectar_mejor_candidata()
    if mejor: CANDIDATAS_CACHE["proxima"] = mejor
def motor_v45():
    global CONTADOR_TP_EXPANSION
    print(f">>> MOTOR V51 BLINDADA x6 MOJARRA 0.2 vs 0.3 + EVOLUCION {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}")
    time.sleep(5)
    while True:
        try:
            for sym in list(MONEDAS_ACTIVAS):
                reg, det = detectar_regimen_sym(sym)
                reset_si_cambio_regimen(sym, reg)
                ESTADO["regimenes"][sym] = f"{reg} {det}"
                if sym=="BTCUSDT": ESTADO["btc"]=get_precio_robusto(sym); ESTADO["regimen"]=reg
                cierre_market_cambio(sym, reg)
                if sym=="BNBUSDT": ESTADO["bnb"]=get_precio_robusto(sym)
        except: pass
        gestionar_bandas_moviles()
        verificar_tanque_bnb()
        mandar_pensamiento_telegram()
        escanear_candidatas_y_proponer()
        for user_id in list(USUARIOS.keys()):
            u=USUARIOS[user_id]
            if user_id not in POSICIONES_ABIERTAS: POSICIONES_ABIERTAS[user_id] = []
            for pos in POSICIONES_ABIERTAS[user_id][:]:
                try:
                    precio_actual = get_precio_robusto(pos["symbol"])
                    if precio_actual == 0: continue
                    tp_price = pos["entrada"] * (1 + pos["tp"]/100)
                    sl_price = pos["entrada"] * (1 + pos["sl"]/100)
                    cerrar = None
                    if precio_actual >= tp_price: cerrar = "TP"
                    elif precio_actual <= sl_price: cerrar = "SL"
                    if cerrar:
                        exito = True
                        if client:
                            try: exito, res, _ = ejecutar_orden_real(pos["symbol"], "SELL", pos["usdt"])
                            except: exito = True
                        pnl_bruto = (precio_actual - pos["entrada"]) / pos["entrada"] * pos["usdt"]
                        comision = pos["usdt"] * COMISION_TOTAL/100
                        pnl = pnl_bruto - comision
                        pnl_pct = (precio_actual - pos["entrada"])/pos["entrada"]*100 if pos["entrada"]!=0 else 0
                        es_tp = cerrar == "TP"
                        if es_tp:
                            if pos.get("estrategia") == "KRAKEN": kraken_reset_si_tp()
                            u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["ganadas"]+=1
                            CONTADOR_TP_EXPANSION += 1
                            if CONTADOR_TP_EXPANSION >= META_TP_PARA_EXPANDIR: intentar_expandir(user_id)
                        else:
                            if pos.get("estrategia") == "KRAKEN": kraken_registrar_sl()
                            u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["perdidas"]+=1
                        estr = pos.get("estrategia", "MOJARRA")
                        if estr not in u.get("estrategias", {}): u["estrategias"][estr] = {"ops":0,"ganadas":0,"neto":0.0}
                        u["estrategias"][estr]["ops"]+=1; u["estrategias"][estr]["neto"]+=pnl
                        u["ops_hoy"]+=1
                        u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} {estr} {pos['symbol']} {cerrar} ${pnl:+.2f} TP:{pos['tp']:.1f}% V51")
                        notificar_cierre(pos["symbol"], estr, pos["entrada"], precio_actual, pnl, pnl_pct, es_tp, pos.get("subtipo",""))
                        POSICIONES_ABIERTAS[user_id].remove(pos)
                        guardar_datos()
                except Exception as e: print(f"Error cierre V51 {e}")
            if not u.get("prendido", False): continue
            ok,motivo,symbol_elegido,estrategia_elegida,fuerza = detectar_BI_CEREBRO(ESTADO.get("regimen","LINEAL"))
            if ok and estrategia_elegida:
                existentes = [p for p in POSICIONES_ABIERTAS.get(user_id,[]) if p.get('symbol')==symbol_elegido and p.get('estrategia')==estrategia_elegida]
                key_lock = f"{symbol_elegido}_{estrategia_elegida}"
                if key_lock in ULTIMO_TRADE and (time.time() - ULTIMO_TRADE[key_lock]) < ESTRATEGIAS_V45[estrategia_elegida]["cooldown"]: continue
                if estrategia_elegida in ["MOJARRA"]: max_permitido = MAX_MOJARRA_POR_MONEDA; dist_requerida = DISTANCIA_MOJARRA_PCT
                elif estrategia_elegida in ["MOJARRA_NEGRA"]: max_permitido = MAX_MOJARRA_POR_MONEDA; dist_requerida = DISTANCIA_MOJARRA_NEGRA_PCT
                elif estrategia_elegida in ["PIRANA_BLANCA","PIRANA","MOJARRITA","RATITA"]:
                    if estrategia_elegida == "MOJARRITA": max_permitido = MAX_MOJARRITA_POR_MONEDA; dist_requerida = DISTANCIA_MOJARRA_PCT
                    else: max_permitido = MAX_PIRANA_POR_MONEDA; dist_requerida = DISTANCIA_PIRANA_PCT
                elif estrategia_elegida in ["PIRANA_NEGRA"]: max_permitido = MAX_PIRANA_POR_MONEDA; dist_requerida = DISTANCIA_PIRANA_NEGRA_PCT
                else: max_permitido = 1; dist_requerida = 0.10
                if len(existentes) >= max_permitido: continue
                precio_actual_tmp = get_precio_robusto(symbol_elegido)
                muy_cerca = False
                for ex in existentes:
                    dist = abs(precio_actual_tmp - ex['entrada']) / ex['entrada'] * 100 if ex['entrada']!=0 else 0
                    if dist < dist_requerida: muy_cerca = True; break
                if muy_cerca: continue
                if key_lock not in ULTIMO_CAZANDO or (time.time() - ULTIMO_CAZANDO.get(key_lock,0)) > 300: notificar_cazando(symbol_elegido, motivo[:80])
                usdt_a_usar = max(10, u["balance"]*0.035)
                reg_actual_sym = ESTADO.get("regimenes",{}).get(symbol_elegido,"LINEAL")
                if estrategia_elegida == "LOBO" and "ALCISTA" in reg_actual_sym: usdt_a_usar = max(200, min(500, u["balance"]*0.50))
                elif estrategia_elegida == "LOBO_NEGRO" and ("BAJISTA" in reg_actual_sym or "CRASH" in reg_actual_sym): usdt_a_usar = max(200, min(500, u["balance"]*0.50))
                elif estrategia_elegida == "RATA" and "ALCISTA" in reg_actual_sym: usdt_a_usar = max(80, u["balance"]*0.15)
                elif estrategia_elegida == "RATA_NEGRA" and ("BAJISTA" in reg_actual_sym or "CRASH" in reg_actual_sym): usdt_a_usar = max(80, u["balance"]*0.15)
                if estrategia_elegida == "KRAKEN": usdt_a_usar = max(200, min(300, u["balance"]*0.20))
                exito, res, precio = ejecutar_orden_real(symbol_elegido,"BUY",usdt_a_usar)
                if exito:
                    ULTIMO_TRADE[key_lock]=time.time(); ULTIMO_CAZANDO[key_lock]=time.time()
                    pos = {"symbol": symbol_elegido, "estrategia": estrategia_elegida, "entrada": precio, "tp": tp_adaptativo(symbol_elegido, estrategia_elegida), "sl": ESTRATEGIAS_V45[estrategia_elegida]["sl_neto"], "usdt": usdt_a_usar, "hora": ahora_art().isoformat()}
                    POSICIONES_ABIERTAS[user_id].append(pos)
                    reg_simple = ESTADO.get("regimenes",{}).get(symbol_elegido,"LINEAL").split()[0]
                    registrar_caza_V51(symbol_elegido, estrategia_elegida, reg_simple)
                    u["modo"]=f"{estrategia_elegida} {symbol_elegido} TP{pos['tp']:.1f}%"; u["mercado"]=motivo
                    if estrategia_elegida=="TIBURON": BANDAS_ACTIVAS[symbol_elegido] = {"entrada_tiburon": precio, "tope": precio*1.10, "tipo": "NORMAL", "activa": True, "creada_en": time.time()}
                    if estrategia_elegida=="KRAKEN": BANDAS_ACTIVAS[symbol_elegido] = {"entrada_tiburon": precio*0.97, "tope": precio*0.995, "tipo": "BAJISTA", "activa": True, "creada_en": time.time()}
                    b = BANDAS_ACTIVAS.get(symbol_elegido,{})
                    banda_txt = f"{b.get('entrada_tiburon',precio*0.97):.0f}->{b.get('tope',precio*1.10):.0f} {b.get('tipo','')}"
                    notificar_caza(symbol_elegido, estrategia_elegida, precio, pos['tp'], ESTRATEGIAS_V45[estrategia_elegida]["sl_neto"], banda_txt, usdt_a_usar, motivo)
        guardar_datos()
        time.sleep(60)
def get_menu():
    m=types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("PRENDER","EVOLUCIONAR")
    m.add("BALANCE","HISTORIAL")
    m.add("RETIRAR GANANCIAS","RETIRAR TODO")
    m.add("ORDENES")
    return m
@bot.message_handler(commands=['start'])
def start(m):
    u=get_user_data(m.chat.id)
    estado_txt = f"V51 BLINDADA {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}" if u["prendido"] else "APAGADO"
    regs="\n".join([f"{k}:{v.split()[0]}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO['regimen'].split()[0]
    bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    ganancia = u["balance"] - u["capital_inicial"]
    bot.send_message(m.chat.id,f"V51 BLINDADA CEREBRO {estado_txt}\n{regs}\n{bandas_txt}\n{'+'.join(MONEDAS_ACTIVAS)}\nBal ${u['balance']:.2f}\nGan ${ganancia:.2f}\n{WEB_URL}",reply_markup=get_menu())
@bot.message_handler(func=lambda m: m.text=="BALANCE")
def balance(m):
    u=get_user_data(m.chat.id)
    ganancia_historica = u["balance"]-u["capital_inicial"]
    regs="\n".join([f"{k}: {v.split()[0]} ({get_cambio_24h(k):+.1f}%)" for k,v in ESTADO.get("regimenes",{}).items()])
    pos_txt = "\n".join([f"{p['symbol']} {p['estrategia']} Ent {p['entrada']:.2f} TP{p['tp']:.1f}%" for p in POSICIONES_ABIERTAS.get(m.chat.id,[])]) or "Sin pos"
    kraken_estado = f"KRAKEN BLOQ hasta {int((KRAKEN_BLOQUEO_HASTA-time.time())/3600)}h SL:{KRAKEN_SL_COUNT}" if time.time() < KRAKEN_BLOQUEO_HASTA else f"KRAKEN OK SL:{KRAKEN_SL_COUNT}"
    v51_txt = "\n".join([f"{sym} {reg}: {cnt}" for sym, d in CONTADOR_POR_REGIMEN.items() for reg, cnt in d.items()]) or "V51 contadores vacios"
    nivel_txt = "\n".join([f"{sym} {reg}: Nv{lv}" for sym, d in EVOLUCION_NIVEL.items() for reg, lv in d.items()]) or ""
    bot.send_message(m.chat.id,f"V51 {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} Tanque 20\n{regs}\n{pos_txt}\n{kraken_estado}\n{v51_txt}\n{nivel_txt}\nBal ${u['balance']:.2f} Hist ${ganancia_historica:+.2f}\nHoy ${u['neto_hoy']:+.2f}",reply_markup=get_menu())
@bot.message_handler(func=lambda m: m.text=="PRENDER")
def prender(m):
    u=get_user_data(m.chat.id); u["prendido"]=True; u["modo"]="CAZANDO V51 BLINDADA"; guardar_datos()
    bot.send_message(m.chat.id,f"MANADA PRENDIDA V51 BLINDADA x6 TANQUE 20\nBolsa Unica ${u['balance']:.2f}",reply_markup=get_menu())
@bot.message_handler(func=lambda m: m.text=="EVOLUCIONAR")
def evolucionar(m):
    u=get_user_data(m.chat.id)
    regs="\n".join([f"{k}: {v} {get_cambio_24h(k):+.1f}%" for k,v in ESTADO.get("regimenes",{}).items()])
    bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas V51"
    rojo, motivo = mercado_esta_rojo()
    clima = f"CLIMA BTC {ESTADO.get('regimen','LINEAL')} CANDADO:{rojo} {motivo} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} TPs {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} V51 BLINDADA KRAKEN:{KRAKEN_SL_COUNT}"
    bot.send_message(m.chat.id,f"{clima}\n{regs}\n{bandas_txt}\n{'+'.join(MONEDAS_ACTIVAS)}",reply_markup=get_menu())
@bot.message_handler(func=lambda m: m.text=="HISTORIAL")
def historial(m):
    u=get_user_data(m.chat.id); hist = u.get("historial",[])[-15:]; txt = "\n".join(hist) or "Sin historial"
    bot.send_message(m.chat.id,f"HISTORIAL V51\n{txt}",reply_markup=get_menu())
@bot.message_handler(func=lambda m: m.text=="ORDENES")
def ordenes(m):
    lista = POSICIONES_ABIERTAS.get(m.chat.id,[])
    if not lista: bot.send_message(m.chat.id,"Sin ordenes abiertas V51",reply_markup=get_menu()); return
    txt="".join([f"{p['symbol']} {p['estrategia']} ${p['entrada']:.2f} TP{p['tp']:.1f}% SL{p['sl']:.1f}% ${p['usdt']:.0f}\n" for p in lista])
    bot.send_message(m.chat.id,f"ORDENES V51 {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n{txt}",reply_markup=get_menu())
@bot.message_handler(func=lambda m: m.text=="RETIRAR GANANCIAS")
def retirar_gan(m):
    u=get_user_data(m.chat.id); gan = u["balance"]-u["capital_inicial"]
    if gan <= 0: bot.send_message(m.chat.id,f"Sin ganancias para retirar. Gan ${gan:.2f}",reply_markup=get_menu()); return
    u["balance"]=BALANCE_INICIAL; u["capital_inicial"]=BALANCE_INICIAL; u["neto_hoy"]=0; guardar_datos()
    bot.send_message(m.chat.id,f"GANANCIAS RETIRADAS V51 ${gan:.2f}\nBolsa unica vuelve a ${u['capital_inicial']:.2f}",reply_markup=get_menu())
@bot.message_handler(func=lambda m: m.text=="RETIRAR TODO")
def retirar_todo(m):
    u=get_user_data(m.chat.id); total=u["balance"]; gan = total - u["capital_inicial"]
    u["balance"]=BALANCE_INICIAL; u["capital_inicial"]=BALANCE_INICIAL; u["neto_hoy"]=0; u["ganadas"]=0; u["perdidas"]=0; u["ops_hoy"]=0
    u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} RETIRO TOTAL ${total:.2f} Gan ${gan:.2f} -> RESET 10k")
    POSICIONES_ABIERTAS[m.chat.id]=[]; guardar_datos()
    bot.send_message(m.chat.id,f"TODO RETIRADO V51 ${total:.2f} (Gan ${gan:.2f})\nReseteada a ${BALANCE_INICIAL:.2f}",reply_markup=get_menu())
@bot.message_handler(func=lambda m: True)
def fallback(m):
    try:
        txt=m.text.upper()
        if "BNB" in txt or "BTC" in txt:
            sym = txt.replace(" ","").replace("$","")
            if "USDT" not in sym: sym+="USDT"
            precio=get_precio_robusto(sym)
            bot.send_message(m.chat.id,f"{sym} ${precio:.2f} V51",reply_markup=get_menu())
        else: bot.send_message(m.chat.id,f"V51 BLINDADA Comandos: PRENDER, BALANCE, EVOLUCIONAR\n{len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} TPs {CONTADOR_TP_EXPANSION:.0f}/{META_TP_PARA_EXPANDIR:.0f} Tanque 20\n{WEB_URL}",reply_markup=get_menu())
    except: bot.send_message(m.chat.id,"V51",reply_markup=get_menu())
@app.route('/api/detalles_mercado')
def detalles_mercado():
    def info_sym(sym):
        try:
            d5 = get_velas(sym,"5m",100); d1h = get_velas(sym,"1h",100)
            precio = get_precio_robusto(sym); rsi = rsi_calc(d5["closes"],7) if d5 else 50
            adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 15
            atr = atr_calc(d1h,14) if d1h else 0; atr_pct = (atr/precio*100) if precio else 0
            ema9 = ema_calc(d5["closes"][-20:],9) if d5 else 0; ema20 = ema_calc(d5["closes"][-20:],20) if d5 else 0
            vol_ratio = (d5["vols"][-1] / (sum(d5["vols"][-20:])/20)) if d5 and len(d5["vols"])>=20 else 1.0
            reg_full = ESTADO.get("regimenes",{}).get(sym,"LINEAL"); reg = reg_full.split()[0] if reg_full else "LINEAL"
            cont = CONTADOR_POR_REGIMEN.get(sym,{}).get(reg,{})
            nivel = EVOLUCION_NIVEL.get(sym,{}).get(reg,1)
            mapa_mejor = {"LINEAL_MUERTO": "V51 MANADA LIBRE x6","LINEAL": "V51 MOJARRA 0.2% + RATA","ALCISTA": "V51 LOBO 1.7% JEFE","ALCISTA_FUERTE": "V51 LOBO+TIBURON","BAJISTA": "V51 LOBO_NEGRO SHORT","CRASH": "V51 LOBO_NEGRO+KRAKEN"}
            mejor = mapa_mejor.get(reg, "V51 MANADA LIBRE")
            banda = BANDAS_ACTIVAS.get(sym,{}); madre = banda.get("tipo","NORMAL") if banda.get("activa") else "NORMAL"
            return {"regimen": reg, "reg_detalle": reg_full,"adx": round(adx,1), "rsi": round(rsi,1),"ema": "9>20" if ema9>ema20 else "9<20","atr": round(atr_pct,2), "vol": round(vol_ratio,1),"precio": round(precio,2), "madre": madre,"mejor_estrategia": mejor, "cambio24": round(get_cambio_24h(sym),2), "v51_contador": cont, "v51_nivel": nivel}
        except Exception as e: return {"regimen":"LINEAL","adx":15,"rsi":50,"ema":"9=20","atr":0,"vol":1,"precio":0,"madre":"NORMAL","mejor_estrategia":"V51","error":str(e)[:80]}
    return jsonify({ "BTCUSDT": info_sym("BTCUSDT"), "BNBUSDT": info_sym("BNBUSDT"), "BTC": info_sym("BTCUSDT"), "BNB": info_sym("BNBUSDT") })
@app.route('/')
def home():
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>V51 BLINDADA</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}.top{padding:10px;background:#1e222d;position:sticky;top:0;z-index:20;font-size:13px;border-bottom:2px solid #00ff88}.card{background:#1e222d;border-radius:8px;overflow:hidden;border:1px solid #2a2e39;margin-bottom:6px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px}.detalle-box{background:#0e1a15;border-top:1px solid #1e3d2f;color:#a7f3d0;font-family:monospace;font-size:11px;padding:8px 10px;line-height:1.4;min-height:62px}</style></head><body><div class="top" id="info">Cargando V51 BLINDADA...</div><div class="grid" id="charts_grid"></div><script>const MONEDAS={{ monedas | tojson }};function createChart(sym){let id='tv_'+sym;let card=document.createElement('div');card.className='card';card.innerHTML=`<div id="${id}" style="height:350px"></div><div class="detalle-box" id="detalle-${sym}">Cargando ${sym}...</div>`;document.getElementById('charts_grid').appendChild(card);new TradingView.widget({autosize:true,symbol:'BINANCE:'+sym,interval:'5',container_id:id,theme:'dark',style:'1',locale:'es'});}MONEDAS.forEach(s=>createChart(s));async function load(){let a=await (await fetch('/api/data')).json();document.getElementById('info').innerHTML='<b>V51 BLINDADA x6 | Bal $'+a.balance.toFixed(2)+' Gan $'+a.ganancia_total.toFixed(2)+'</b> | '+Object.entries(a.regimenes).map(e=>e[0].replace('USDT','')+':'+e[1].split(' ')[0]).join(' | ')+' | '+a.bandas_txt;}async function loadDetalles(){try{let d=await (await fetch('/api/detalles_mercado')).json();for(let sym of MONEDAS){let info=d[sym];if(!info) continue;document.getElementById('detalle-'+sym).innerHTML=`REGIMEN: ${info.regimen} (${info.cambio24}%) (ADX ${info.adx}) | Madre: ${info.madre} | RSI ${info.rsi} | EMA ${info.ema} | ATR ${info.atr}% | Vol ${info.vol}x<br><b>Mejor: ${info.mejor_estrategia}</b> | Nv${info.v51_nivel} ${JSON.stringify(info.v51_contador)} | $${info.precio}`;}}catch(e){}}setInterval(load,3000);load();setInterval(loadDetalles,3000);loadDetalles();</script></body></html>"""
    return render_template_string(html)
@app.route('/api/data')
def api_data():
    target=ADMINS_IDS[0]
    if target not in USUARIOS: get_user_data(target)
    u=USUARIOS[target]
    bandas_txt = " | ".join([banda_txt_api(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    precios = {}
    for sym in MONEDAS_ACTIVAS: precios[sym] = get_precio_robusto(sym)
    posiciones = POSICIONES_ABIERTAS.get(target, [])
    ganancia_total = u["balance"]-u["capital_inicial"]
    return jsonify({"balance":u["balance"],"capital_inicial":u["capital_inicial"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"regimen_btc":ESTADO.get("regimen","LINEAL"),"regimenes":ESTADO.get("regimenes",{}),"estrategias":u["estrategias"],"monedas":MONEDAS_ACTIVAS,"ganancia_total": ganancia_total,"bandas": BANDAS_ACTIVAS, "bandas_txt": bandas_txt, "posiciones": posiciones, "precios": precios, "meta_proxima": META_TP_PARA_EXPANDIR, "tps_actual": CONTADOR_TP_EXPANSION, "v51_contadores": CONTADOR_POR_REGIMEN, "v51_niveles": EVOLUCION_NIVEL})

# ARRANQUE V51 BLINDADA
if True:
    cargar_datos()
    t = threading.Thread(target=motor_v45, daemon=True); t.start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), debug=False, use_reloader=False), daemon=True).start()
    print("V51 BLINDADA lista - MOJARRA 0.2 vs 0.3 + EVOLUCION BLINDADA")
    try:
        bot.delete_webhook(drop_pending_updates=True)
        print("V51 Webhook borrado - polling unico")
        time.sleep(2)
    except: pass
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        print(f"Bot polling error V51 {e}")
        time.sleep(10)
