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
IS_TESTNET = (os.getenv("BINANCE_TESTNET", "False") or "False").lower().strip() == "true"
WEB_URL = os.getenv("WEB_URL", "https://bot-v22.onrender.com").strip().rstrip("/")

# V57.1 FIX 4/20 - SIN CANDADO GLOBAL - 5 REGIMENES ESPEJADOS
MONEDAS_ACTIVAS = ["BTCUSDT", "BNBUSDT", "AVAXUSDT", "XRPUSDT"]
CANDIDATAS = ["ETHUSDT","SOLUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","DOTUSDT","LTCUSDT","TRXUSDT","MATICUSDT","SHIBUSDT","PEPEUSDT","SUIUSDT","APTUSDT","ARBUSDT","OPUSDT","NEARUSDT","FILUSDT","INJUSDT"]
MAX_MONEDAS = 20
META_PROFIT_PARA_EXPANDIR = 120.0
META_TP_PARA_EXPANDIR = META_PROFIT_PARA_EXPANDIR
CONTADOR_TP_EXPANSION = 0.0
TANQUE_POR_MONEDA = 2.0
TANQUE_BNB_USDT = 50.0
TANQUE_BNB_MIN = 5.0
TANQUE_BNB_RECARGA = 8.0
TANQUE = TANQUE_BNB_USDT
TRAILING_CONFIG = {
    "TIBURON": {"activacion": 2.5, "trailing": 1.5, "activo": False},
    "TIBURON_NEGRO": {"activacion": 2.5, "trailing": 1.5, "activo": False},
    "LOBO": {"activacion": 1.0, "trailing": 0.8, "activo": False},
    "LOBO_NEGRO": {"activacion": 1.0, "trailing": 0.8, "activo": False},
    "RATA": {"activacion": 1.0, "trailing": 0.8, "activo": False},
    "RATA_NEGRA": {"activacion": 1.0, "trailing": 0.8, "activo": False},
    "RATITA": {"activacion": 0.8, "trailing": 0.6, "activo": False},
    "RATITA_BLANCA": {"activacion": 0.8, "trailing": 0.6, "activo": False},
    "RATITA_NEGRA": {"activacion": 0.8, "trailing": 0.6, "activo": False},
    "PIRANA_BLANCA":{"activacion": 0.6, "trailing": 0.5, "activo": False},
    "PIRANA_NEGRA": {"activacion": 0.6, "trailing": 0.5, "activo": False},
    "MOJARRA": {"activo": False},
    "MOJARRITA": {"activo": False},
    "MOJARRA_NEGRA":{"activo": False},
    "KRAKEN": {"activo": False},
}
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
ESCAPE_BLOCK = {}
ESCAPES_TIMELINE = []
PAUSA_GLOBAL_HASTA = 0
BTC_PRECIOS_15M = []
TIEMPO_BLOQUEO_MONEDA = 7200
TIEMPO_PAUSA_PANICO = 1800
MAX_ESCAPES_POR_HORA = 3
EVOLUCION_NIVEL_NEGRA = {}
CONTADOR_NEGRA_POR_REGIMEN = {}
BAJISTA_PROFUNDO_HASTA = 0
BLOQUEO_LONG_TOTAL_HASTA = 0
BAJISTA_PROFUNDO_POR_MONEDA = {}
BLOQUEO_LONG_POR_MONEDA = {}
CONTADOR_SL_NEGRA_SEGUIDOS = 0

def is_moneda_bloqueada(sym):
    if sym in ESCAPE_BLOCK:
        if time.time() < ESCAPE_BLOCK[sym]:
            return True
        else:
            del ESCAPE_BLOCK[sym]
    return False

def registrar_escape(sym):
    global ESCAPES_TIMELINE, PAUSA_GLOBAL_HASTA
    ahora = time.time()
    ESCAPE_BLOCK[sym] = ahora + TIEMPO_BLOQUEO_MONEDA
    ESCAPES_TIMELINE.append(ahora)
    ESCAPES_TIMELINE = [t for t in ESCAPES_TIMELINE if ahora - t < 3600]
    if len(ESCAPES_TIMELINE) >= MAX_ESCAPES_POR_HORA:
        PAUSA_GLOBAL_HASTA = ahora + TIEMPO_PAUSA_PANICO
        print(f"V57 PANICO {len(ESCAPES_TIMELINE)} escapes/h -> PAUSA 30MIN")
        return True
    return True

def hay_pausa_global():
    return False

def es_bajista_profundo_activo(sym=None):
    return False

def es_bloqueo_long_total(sym=None):
    return False

def btc_crash_15m(umbral=-2.5):
    try:
        if len(BTC_PRECIOS_15M) < 2: return False
        ahora = time.time()
        recientes = [(p,t) for p,t in BTC_PRECIOS_15M if ahora - t < 900]
        if len(recientes) < 2: return False
        p_viejo = recientes[0][0]
        p_nuevo = recientes[-1][0]
        if p_viejo == 0: return False
        caida = (p_nuevo - p_viejo)/p_viejo*100
        return caida <= umbral
    except: return False

TIEMPO_FUERA_NORMAL = 720
TIEMPO_FUERA_BAJISTA = 360
CANDIDATAS_CACHE = {"_ultimo_scan": 0, "_aviso_meta": 0, "proxima": None}
TIEMPO_ESCANEO_CANDIDATAS = 600
KRAKEN_SL_COUNT = 0
KRAKEN_BLOQUEO_HASTA = 0
CONTADOR_POR_REGIMEN = {}
EVOLUCION_NIVEL = {}
REG_ANT = {}
ESTRATEGIAS_V45 = {
    "MOJARRA": {"tf": "1m", "desc": "MOJARRA 0.3-0.5% LONG - PARTE ALTA LINEAL_MUERTO RSI40 V57 FIX","rango_tp": (0.3, 0.5), "sl_neto": -2.5, "max_dia": 300,"cooldown": 45, "cooldown_rec": 45,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.3},
    "MOJARRITA": {"tf": "5m", "desc": "MOJARRITA 0.3-0.5% FONDO RSI30 V57 FIX","rango_tp": (0.3, 0.5), "sl_neto": -1.5, "max_dia": 200,"cooldown": 45, "cooldown_rec": 45,"mercado_ideal": "LINEAL_MUERTO", "tp_fijo_banda": 0.3},
    "PIRANA_BLANCA": {"tf": "3m", "desc": "PIRANA BLANCA 0.5-0.8% LONG V57","rango_tp": (0.5, 0.8), "sl_neto": -2.8, "max_dia": 150,"cooldown": 90, "cooldown_rec": 90,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.5},
    "RATITA": {"tf": "5m", "desc": "RATITA 0.6-1.0% LONG V57","rango_tp": (0.6, 1.0), "sl_neto": -3.0, "max_dia": 40,"cooldown": 120, "cooldown_rec": 120,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "RATITA_BLANCA": {"tf": "5m", "desc": "RATITA BLANCA 0.8% LONG RSI32 8% cap V57 FINAL","rango_tp": (0.8, 0.8), "sl_neto": -3.0, "max_dia": 40,"cooldown": 120, "cooldown_rec": 120,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "RATA": {"tf": "5m", "desc": "Madre RATA 0.8-1.2% LONG V57","rango_tp": (0.8, 1.2), "sl_neto": -3.0, "max_dia": 30,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "LINEAL", "tp_fijo_banda": 1.0},
    "LOBO": {"tf": "1h", "desc": "Madre LOBO 1.2% LONG JEFE V57","rango_tp": (1.2, 2.2), "sl_neto": -5.0, "max_dia": 100,"cooldown": 300, "cooldown_rec": 300,"mercado_ideal": "ALCISTA", "tp_fijo_banda": 1.2},
    "TIBURON": {"tf": "1d", "desc": "Madre TIBURON 5-10% LONG JEFE FUERTE V57","rango_tp": (5.0, 10.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 14400, "cooldown_rec": 14400,"mercado_ideal": "ALCISTA_FUERTE"},
    "TIBURON_NEGRO": {"tf": "1d", "desc": "TIBURON NEGRO 5-10% SHORT JEFE FUERTE V57 STRADIVARIUS","rango_tp": (5.0, 10.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 14400, "cooldown_rec": 14400,"mercado_ideal": "CRASH"},
    "KRAKEN": {"tf": "1h", "desc": "Madre KRAKEN 3-5% LONG REBOTE CRASH V57","rango_tp": (3.0, 5.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 3600, "cooldown_rec": 3600,"mercado_ideal": "CRASH"},
    "MOJARRA_NEGRA": {"tf": "5m", "desc": "MOJARRA NEGRA 0.3-0.5% SHORT REBOTE V57","rango_tp": (0.3, 0.5), "sl_neto": -1.5, "max_dia": 200,"cooldown": 60, "cooldown_rec": 60,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.3},
    "PIRANA_NEGRA": {"tf": "5m", "desc": "PIRANA NEGRA 0.5-0.8% SHORT REBOTE V57","rango_tp": (0.5, 0.8), "sl_neto": -3.5, "max_dia": 100,"cooldown": 600, "cooldown_rec": 600,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.5},
    "RATA_NEGRA": {"tf": "5m", "desc": "RATA NEGRA 0.8-1.5% SHORT REBOTE V57","rango_tp": (0.8, 1.5), "sl_neto": -4.0, "max_dia": 100,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.8},
    "RATITA_NEGRA": {"tf": "5m", "desc": "RATITA NEGRA 0.8% SHORT RSI68 8% cap V57 FINAL","rango_tp": (0.8, 0.8), "sl_neto": -4.0, "max_dia": 100,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.8},
    "LOBO_NEGRO": {"tf": "1h", "desc": "LOBO NEGRO 1.2% JEFE SHORT V57","rango_tp": (1.2, 2.2), "sl_neto": -8.0, "max_dia": 100,"cooldown": 300, "cooldown_rec": 300,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 1.2},
}
ESTRATEGIAS_V45["PIRANA"] = ESTRATEGIAS_V45["PIRANA_BLANCA"]
ESTRATEGIAS_V45["PIRAÑA_NEGRA"] = ESTRATEGIAS_V45["PIRANA_NEGRA"]
BLANCAS = {"MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATITA","RATITA_BLANCA","RATA","LOBO","TIBURON"}
NEGRAS = {"MOJARRA_NEGRA","PIRANA_NEGRA","PIRAÑA_NEGRA","RATITA_NEGRA","RATA_NEGRA","LOBO_NEGRO","KRAKEN","TIBURON_NEGRO"}
MADRES_LIBRES_V52 = {"LOBO","TIBURON","KRAKEN","LOBO_NEGRO","TIBURON_NEGRO"}

def candado(est, regimen, sym=None):
    r = regimen.split()[0] if regimen else "LINEAL"
    if r == "LINEAL_MUERTO":
        return est in ["MOJARRA","MOJARRITA"]
    if r == "LINEAL":
        return est in ["MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATITA","RATITA_BLANCA","RATA"]
    if r == "ALCISTA":
        return est in ["MOJARRA","PIRANA_BLANCA","RATITA_BLANCA","RATITA","RATA","LOBO"]
    if r == "ALCISTA_FUERTE":
        return est in ["MOJARRA","PIRANA_BLANCA","RATITA_BLANCA","RATITA","RATA","LOBO","TIBURON"]
    if r in ["BAJISTA","CRASH"]:
        if est in ["MOJARRA","MOJARRITA"]:
            return True
        return est in ["MOJARRA_NEGRA","PIRANA_NEGRA","PIRAÑA_NEGRA","RATITA_NEGRA","RATA_NEGRA","LOBO_NEGRO","TIBURON_NEGRO","KRAKEN"]
    return True

def cierre_market_cambio(sym, reg_nuevo, reg_viejo_override=None):
    return

def cierre_forzado_por_candado():
    return

def reset_si_cambio_regimen(sym, reg_nuevo):
    global CONTADOR_POR_REGIMEN, EVOLUCION_NIVEL, REG_ANT
    reg_nuevo_simple = reg_nuevo.split()[0]
    reg_ant = REG_ANT.get(sym, "")
    if reg_ant and reg_ant!= reg_nuevo_simple:
       if {reg_ant, reg_nuevo_simple} <= {"LINEAL", "LINEAL_MUERTO"}:
           EVOLUCION_NIVEL.setdefault(sym, {})[reg_nuevo_simple] = EVOLUCION_NIVEL.get(sym, {}).get(reg_ant, 1)
       EVOLUCION_NIVEL.setdefault(sym, {})[reg_nuevo_simple] = EVOLUCION_NIVEL.get(sym, {}).get(reg_nuevo_simple, 1)
    REG_ANT[sym] = reg_nuevo_simple

def registrar_caza_V51(sym, estrategia, regimen):
    global CONTADOR_POR_REGIMEN, EVOLUCION_NIVEL
    if sym not in CONTADOR_POR_REGIMEN: CONTADOR_POR_REGIMEN[sym] = {}
    if regimen not in CONTADOR_POR_REGIMEN[sym]: CONTADOR_POR_REGIMEN[sym][regimen] = {}
    if sym not in EVOLUCION_NIVEL: EVOLUCION_NIVEL[sym] = {}
    if regimen not in EVOLUCION_NIVEL[sym]: EVOLUCION_NIVEL[sym][regimen] = 1
    CONTADOR_POR_REGIMEN[sym][regimen][estrategia] = CONTADOR_POR_REGIMEN[sym][regimen].get(estrategia, 0) + 1

def candado_evolucion_V51(sym, estrategia, regimen):
    if estrategia in MADRES_LIBRES_V52: return False
    if estrategia in ["MOJARRA","MOJARRITA"]: return False
    return False

def registrar_caza_negra_V56_4(sym, estrategia, regimen):
    global CONTADOR_NEGRA_POR_REGIMEN, EVOLUCION_NIVEL_NEGRA
    reg_simple = regimen.split()[0]
    if reg_simple not in ["BAJISTA", "CRASH"]: return
    if sym not in CONTADOR_NEGRA_POR_REGIMEN: CONTADOR_NEGRA_POR_REGIMEN[sym] = {}
    if reg_simple not in CONTADOR_NEGRA_POR_REGIMEN[sym]: CONTADOR_NEGRA_POR_REGIMEN[sym][reg_simple] = {}
    if sym not in EVOLUCION_NIVEL_NEGRA: EVOLUCION_NIVEL_NEGRA[sym] = {}
    if reg_simple not in EVOLUCION_NIVEL_NEGRA[sym]: EVOLUCION_NIVEL_NEGRA[sym][reg_simple] = 1
    CONTADOR_NEGRA_POR_REGIMEN[sym][reg_simple][estrategia] = CONTADOR_NEGRA_POR_REGIMEN[sym][reg_simple].get(estrategia, 0) + 1

def candado_evolucion_negra_V56_4(sym, estrategia, regimen):
    reg_simple = regimen.split()[0]
    if reg_simple not in ["BAJISTA", "CRASH"]: return True
    if estrategia in ["MOJARRA_NEGRA","MOJARRA","MOJARRITA"]: return False
    return False

def activar_kraken_stradivarius_V56_4(motivo="2 SL", sym=None):
    print(f"V57.1 {sym or 'GLOBAL'} {motivo} - Sin bloqueo global")

MAPA_ANIDADO_V50_9 = {
    "LINEAL_MUERTO": ["MOJARRA", "MOJARRITA"],
    "LINEAL": ["MOJARRA", "PIRANA_BLANCA", "RATITA", "RATA"],
    "ALCISTA": ["MOJARRA", "PIRANA_BLANCA","RATITA_BLANCA","RATITA", "RATA", "LOBO"],
    "ALCISTA_FUERTE": ["MOJARRA", "PIRANA_BLANCA","RATITA_BLANCA","RATITA", "RATA", "LOBO", "TIBURON"],
    "BAJISTA": ["MOJARRA_NEGRA", "PIRANA_NEGRA", "RATITA_NEGRA", "RATA_NEGRA", "LOBO_NEGRO"],
    "CRASH": ["MOJARRA_NEGRA", "PIRANA_NEGRA", "RATITA_NEGRA", "RATA_NEGRA", "LOBO_NEGRO", "TIBURON_NEGRO", "KRAKEN"],
    "SUPERVIVENCIA": ["MOJARRITA_SUPERVIVENCIA"]
}
MAPA_ESTRATEGIA = {"LINEAL_MUERTO": "MANADA LIBRE MOJARRA+MOJARRITA x6 FONDO V57", "LINEAL": "MOJARRA 0.3% + RATITA_BLANCA RSI32 V57", "ALCISTA": "REGIMEN 3 LOBO 1.2% JEFE V57", "ALCISTA_FUERTE": "REGIMEN 4 LOBO 1.2% + TIBURON 5-10% V57", "BAJISTA": "REGIMEN 5 LOBO_NEGRO 1.2% JEFE V57 + RATITA_NEGRA RSI68 V57", "CRASH": "REGIMEN 6 CRASH TIBURON_NEGRO 5-10% + KRAKEN V57"}

# ==================== 06 SUPERVIVENCIA ADAPTATIVA - V58.1 FINAL ====================
# BLOQUE 06 - MOJARRITA SUPERVIVENCIA + SCANNER TOP1/TOP2 ROTATIVO ADAPTATIVO
# Se adapta a cualquier moneda nueva que agregues al TOP

ESTRATEGIAS_V45["MOJARRITA_SUPERVIVENCIA"] = {
    "nombre": "MOJARRITA_SUPERVIVENCIA",
    "riesgo": 0.05,
    "tp": 0.008,
    "sl": 0.015,
    "rsi_compra": 25,
    "rsi_venta": 60,
    "tipo": "SCALP_SUPERVIVENCIA"
}

def es_mercado_supervivencia(symbol="BTCUSDT"):
    """V58.1 ADAPTATIVO - Detecta si SYMBOL está en lateral muerto"""
    try:
        velas = get_velas(symbol, "1h", 50)
        if not velas or len(velas) < 30:
            return False
        if isinstance(velas, dict):
            closes = velas.get("closes", [])
        else:
            closes = [float(v[4]) for v in velas]
        if len(closes) < 24:
            return False
        var_24h = abs(closes[-1] - closes[-24]) / closes[-24] if closes[-24]!= 0 else 0
        rsi_val = rsi_calc(closes, 14)
        return var_24h < 0.015 and 38 < rsi_val < 62
    except:
        return False

def scanner_06_mejor_oportunidad(symbols_top20):
    """Scanner rotativo TOP1/TOP2 que busca la mejor mojarrita en modo supervivencia"""
    mejor = None
    mejor_score = -999
    try:
        for sym in symbols_top20[:12]:
            velas = get_velas(sym, "5m", 100)
            if not velas or len(velas) < 50:
                continue
            if isinstance(velas, dict):
                closes = velas.get("closes", [])
            else:
                closes = [float(v[4]) for v in velas]
            rsi = rsi_calc(closes, 14)
            if rsi < 30:
                vol = float(velas[-1][5]) if not isinstance(velas, dict) else 0
                score = (30 - rsi) + (vol / 1000000)
                if score > mejor_score:
                    mejor_score = score
                    mejor = (sym, rsi, closes[-1])
    except Exception as e:
        print(f"[06] error scanner: {e}")
    return mejor

def ejecutar_mojarrita_supervivencia(sym, precio, rsi):
    """Lanza la caza de supervivencia con notificacion especial"""
    try:
        estrategia = ESTRATEGIAS_V45["MOJARRITA_SUPERVIVENCIA"]
        notificar_caza(
            simbolo=sym,
            estrategia="MOJARRITA_SUPERVIVENCIA",
            precio=precio,
            rsi=rsi,
            regimen="SUPERVIVENCIA",
            extra=f"SCANNER TOP1 SCORE RSI:{rsi:.1f} V58.1"
        )
        return True
    except Exception as e:
        print(f"[06] error ejecutar: {e}")
        return False

print("[OK] BLOQUE 06 V58.1 CARGADO - SUPERVIVENCIA ADAPTATIVA")
# ==================== FIN BLOQUE 06 ====================#

def estrategia_prevista(regimen_txt):
    reg = regimen_txt.split()[0] if regimen_txt else "LINEAL"
    return MAPA_ESTRATEGIA.get(reg, "MANADA LIBRE")
BLANCAS_SET = {"MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATITA","RATITA_BLANCA","RATA","LOBO","TIBURON"}

def mercado_esta_rojo(sym=None):
    if sym:
        reg = ESTADO.get("regimenes",{}).get(sym,"")
        rs = reg.split()[0] if reg else ""
        if rs in ("BAJISTA","CRASH"):
            return True, f"REGIMEN {sym} {reg}"
        banda = BANDAS_ACTIVAS.get(sym,{})
        if banda.get("activa"):
            tipo = str(banda.get("tipo","")).upper()
            if "BAJISTA" in tipo or "CRASH" in tipo:
                return True, f"BANDA {sym} {tipo}"
        return False, ""
    for s, reg in ESTADO.get("regimenes", {}).items():
        rs = reg.split()[0] if reg else ""
        if rs in ("BAJISTA","CRASH"):
            return True, f"{s} {reg}"
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
for _f in [os.path.join(DATA_DIR, "pirana_v50.json"), os.path.join(DATA_DIR, "bandas_v45.json"), os.path.join(DATA_DIR, "contador_expansion.json")]:
    try:
        if os.path.exists(_f):
            os.remove(_f)
            print(f"V57 FIX AUTO BORRADO {_f}")
    except Exception as _e:
        print(f"Error borrando {_f}: {_e}")
CONTADOR_POR_REGIMEN = {}
EVOLUCION_NIVEL = {sym: {"LINEAL":1,"LINEAL_MUERTO":1,"ALCISTA":1,"ALCISTA_FUERTE":1,"BAJISTA":1,"CRASH":1} for sym in MONEDAS_ACTIVAS}
CONTADOR_NEGRA_POR_REGIMEN = {}
EVOLUCION_NIVEL_NEGRA = {sym: {"BAJISTA":1,"CRASH":1} for sym in MONEDAS_ACTIVAS}
ESCAPE_BLOCK = {}
ESCAPES_TIMELINE = []

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
        reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
        reg_simple = reg.split()[0] if reg else "LINEAL"
        if reg_simple == "LINEAL_MUERTO":
            if estrategia in ["MOJARRA", "MOJARRITA", "PIRANA_BLANCA", "PIRANA", "MOJARRA_NEGRA"]:
                return rango[0]
            return 0.5
        if reg_simple == "LINEAL":
            if estrategia in ["RATITA", "RATA"]:
                return 0.8
            if estrategia in ["MOJARRA", "MOJARRITA", "PIRANA_BLANCA", "PIRANA", "MOJARRA_NEGRA"]:
                return rango[0]
            return 0.8
        if estrategia in ["MOJARRA", "MOJARRITA", "PIRANA_BLANCA", "PIRANA", "MOJARRA_NEGRA"]: return rango[0]
        if estrategia == "LOBO" or estrategia == "LOBO_NEGRO": return 1.2
        d1h = get_velas(symbol,"1h",100)
        if not d1h: return rango[0]
        adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
        atr = atr_calc(d1h, 14)
        precio = d1h["closes"][-1]
        atr_pct = (atr/precio*100) if precio!=0 else 0
        if estrategia in ["RATA","RATA_NEGRA","RATITA"]:
            if adx > 30 and atr_pct > 1.0: return rango[1]
            return rango[0]
        if estrategia in ["TIBURON","TIBURON_NEGRO"]:
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
    if cambio > -2.5: return False
    d1h = get_velas(symbol,"1h",60)
    if not d1h: return False
    rsi = rsi_calc(d1h["closes"],14)
    vol_prom = sum(d1h["vols"][-20:])/20 if len(d1h["vols"])>=20 else 1
    vol_x = d1h["vols"][-1]/vol_prom if vol_prom else 0
    if rsi > 32 or vol_x < 1.15: return False
    return False
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
            return False
    except: pass
    return False
def get_umbral_adaptativo(regimen):
    # === V58.2 KRAKEN 2.0 ADAPTATIVO POR MONEDA - SIN FRENO GLOBAL ===
    reg = regimen.split()[0] if regimen else "LINEAL"
    btc_delta = 0.0
    try:
        if 'BTC_PRECIOS' in globals() and len(BTC_PRECIOS) > 4:
            btc_delta = ((BTC_PRECIOS[-1] - BTC_PRECIOS[-5]) / BTC_PRECIOS[-5]) * 100
    except: btc_delta = 0.0

    ajuste = 0.0
    if btc_delta <= -1.2: ajuste = -4.0
    elif btc_delta <= -0.6: ajuste = -2.0
    elif btc_delta >= 1.0: ajuste = 1.0

    if reg == "ALCISTA_FUERTE": return {"rsi_kraken": max(20, 30.5 + ajuste), "rsi_pirana": 35, "rsi_pirana_negra": 30, "vsa_kraken_base": 1.3}
    elif reg == "ALCISTA": return {"rsi_kraken": max(20, 29.5 + ajuste), "rsi_pirana": 33, "rsi_pirana_negra": 29, "vsa_kraken_base": 1.4}
    elif reg == "BAJISTA": return {"rsi_kraken": max(18, 27.5 + ajuste), "rsi_pirana": 30, "rsi_pirana_negra": 35, "vsa_kraken_base": 1.6}
    elif reg == "CRASH": return {"rsi_kraken": max(18, 30.0 + ajuste), "rsi_pirana": 28, "rsi_pirana_negra": 40, "vsa_kraken_base": 1.3}
    elif reg == "LINEAL": return {"rsi_kraken": max(20, 29.0 + ajuste), "rsi_pirana": 38, "rsi_pirana_negra": 28, "vsa_kraken_base": 1.3}
    else: return {"rsi_kraken": max(18, 27.5 + ajuste), "rsi_pirana": 30, "rsi_pirana_negra": 28, "vsa_kraken_base": 1.6}

# === V58.1 TOP3 MEJORES MOJARRITAS ===
def scanner_06_top3_mejores_oportunidades(symbols):
    ops = []
    for sym in symbols:
        try:
            try: rsi = obtener_rsi(sym)
            except:
                try: rsi = get_rsi(sym)
                except: rsi = 50
            precio = get_precio_robusto(sym)
            score = 100 - rsi
            ops.append((score, sym, rsi, precio))
        except: pass
    ops.sort(reverse=True, key=lambda x: x[0])
    return [(sym, rsi, precio) for score, sym, rsi, precio in ops[:3]]

def ejecutar_mojarrita_supervivencia(sym, precio, rsi):
    try:
        print(f"[06] MOJARRITA TOP3 -> {sym} RSI:{rsi:.1f}")
        intentar_comprar(sym, motivo=f"SUPERVIVENCIA TOP3 RSI {rsi:.1f}")
    except Exception as e:
        print(f"[06] Error mojarrita {sym}: {e}")
# === FIN V58.1 TOP3 ===

def detectar_regimen_sym(symbol):
    # === V58.2 KRAKEN 2.0 ADAPTATIVO POR MONEDA ===
    btc_delta_15m = 0.0
    try:
        # intenta sacar delta BTC 15m de tu lista, si no existe deja 0
        if 'BTC_PRECIOS' in globals() and len(BTC_PRECIOS) > 4:
            btc_delta_15m = ((BTC_PRECIOS[-1] - BTC_PRECIOS[-5]) / BTC_PRECIOS[-5]) * 100
    except: btc_delta_15m = 0.0

    # === V58.1 ADAPTATIVO A TODA MONEDA ===
    try:
        if es_mercado_supervivencia(symbol):
            return "SUPERVIVENCIA", f"V58 {symbol} lateral <1.5% 24h - SUPERVIVENCIA"
    except: pass
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
    if precio < ema200 and 15 <= adx_1h <= 80 and -0.12 <= rent_14d <= -0.01 and -0.08 <= dist_ema200 <= -0.01 and 22 <= rsi_1h <= 60: return "BAJISTA", f"BAJISTA ADX{adx_1h:.0f} {rent_14d*100:.1f}% V57"
    if precio > ema200 and precio > ema50 and adx_1h >= 28 and rent_14d > 0.06 and dist_ema200 > 0.02 and rsi_1h >= 50: return "ALCISTA_FUERTE", f"FUERTE ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
    if precio > ema200 and 18 <= adx_1h <= 35 and 0.01 <= rent_14d <= 0.12 and 0.01 <= dist_ema200 <= 0.08 and 40 <= rsi_1h <= 78: return "ALCISTA", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
    if precio < ema200 and adx_1h > 15 and rent_14d < -0.01: return "BAJISTA", f"BAJISTA ADX{adx_1h:.0f} {rent_14d*100:.1f}% V57"
    return "LINEAL", f"ADX{adx_1h:.0f} {rent_14d*100:+.1f}%"
def get_vol_requerido_auto(estrategia, reg_simple, adx, atr_pct=0):
    if IS_TESTNET: return 0.0
    if estrategia == "MOJARRA": return 0.10
    if estrategia in ["PIRANA_BLANCA", "PIRANA", "MOJARRA", "MOJARRITA", "RATITA"]: return 0.25
    return 1.2

def detectar_RATA_sym(symbol, estrategia_nombre="RATA"):
    d5=get_velas(symbol,"5m",100); d1h=get_velas(symbol,"1h",50)
    if not d5: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    # V57.1 FIX RAIZ - fallback si falta rsi_rata_max
    if not isinstance(umb, dict):
        umb = {}
    rsi_max = umb.get("rsi_rata_max", umb.get("rsi_max", 40))
    rsi_min = umb.get("rsi_rata_min", 20)

    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    if estrategia_nombre in ["MOJARRA","MOJARRITA"] and rsi < 20:
        return True,f"[{symbol}] {estrategia_nombre} EMERGENCIA RSI{int(rsi)}<20 {reg.split()[0]} CAZA FORZADA V57", 0.99
    sma20=sum(closes[-20:])/20; var=sum((x-sma20)**2 for x in closes[-20:])/20; std=var**0.5; lower=sma20-2*std
    precio=closes[-1]
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if estrategia_nombre in ["MOJARRA", "MOJARRITA", "PIRANA_BLANCA", "PIRANA", "RATITA", "RATITA_BLANCA"]:
        if estrategia_nombre == "MOJARRA":
            if reg_simple == "LINEAL_MUERTO":
                if rsi <= 40: return True,f"[{symbol}] MOJARRA ALTA V57 RSI{int(rsi)}<=40 {reg_simple} SIN VOL", 0.85
                return False,f"[{symbol}] MOJARRA ALTA RSI{int(rsi)}/40 {reg_simple}", 0.30
            if rsi <= 40: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}<=40 ALTA {reg_simple} V57", 0.85
            return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/40 {reg_simple}", 0.30
        if estrategia_nombre == "MOJARRITA":
            if rsi <= 32: return True,f"[{symbol}] MOJARRITA DESTRABE V57 RSI{int(rsi)}<=32 FONDO {reg_simple}", 0.80
            return False,f"[{symbol}] MOJARRITA RSI{int(rsi)}/32 {reg_simple}", 0.30
        if rsi <= 40: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}<=40 {reg_simple} V57", 0.85
        return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/40 {reg_simple}", 0.30
    # V57.1 FIX - uso rsi_max con fallback
    if precio<=lower and rsi < rsi_max:
        return True,f"[{symbol}] {estrategia_nombre} V57 {reg_simple} RSI{int(rsi)}<{rsi_max}", 0.68
    return False,f"[{symbol}] {estrategia_nombre} {reg_simple} RSI{int(rsi)}/{rsi_max}", 0.30
    
def detectar_SHORT_sym(symbol, estrategia_nombre="MOJARRA_NEGRA"):
    d5=get_velas(symbol,"5m",100)
    if not d5: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    reg_simple = reg.split()[0] if reg else "LINEAL"

    # V58.2 FIX BAJISTA - en BAJISTA/CRASH cazamos SHORT con RSI mucho más bajo
    if reg_simple in ["BAJISTA", "CRASH", "BAJISTA_FUERTE"]:
        if rsi >= 42:
            return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}>=42 SHORT {reg_simple} V58.2 CAZA BAJISTA", 0.85
        if rsi >= 35: # continuidad bajista
            return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)} BAJISTA CONTINUIDAD SHORT {reg_simple} V58.2", 0.75
        return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/35 {reg_simple}", 0.30

    if estrategia_nombre == "MOJARRA_NEGRA":
        if rsi >= 52: # antes 58, muy alto, lo bajamos a 52 para LINEAL/ALCISTA agotado
            return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}>=52 SHORT {reg_simple} V58.2", 0.85
        return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/52 {reg_simple}", 0.30

    if rsi >= 55: # antes 60
        return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}>=55 SHORT {reg_simple} V58.2", 0.75
    return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/55 {reg_simple}", 0.30
    
def detectar_LOBO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if reg_simple not in ["ALCISTA","ALCISTA_FUERTE"]: return False,f"[{symbol}] LOBO BLOQUEADO Solo ALCISTA {reg_simple}",0.10
    closes=d["closes"]; ema20=sum(closes[-20:])/20
    adx = adx_calc(d["highs"], d["lows"], d["closes"], 14); rsi = rsi_calc(closes,14)
    if closes[-1] > ema20 and rsi >= 48 and adx >= 15: return True,f"[{symbol}] LOBO V57 {reg_simple} ADX{adx:.0f} RSI{int(rsi)} TP1.2%", 0.75
    return False,f"[{symbol}] LOBO {reg_simple} ADX{adx:.0f} RSI{int(rsi)} esperando",0.35

def detectar_LOBO_NEGRO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if reg_simple not in ["BAJISTA","CRASH"]: return False,f"[{symbol}] LOBO_NEGRO BLOQUEADO Solo BAJISTA {reg_simple}",0.10
    closes=d["closes"]; ema20=sum(closes[-20:])/20
    adx = adx_calc(d["highs"], d["lows"], d["closes"], 14); rsi = rsi_calc(closes,14)
    if closes[-1] < ema20 and rsi <= 52 and adx >= 15: return True,f"[{symbol}] LOBO_NEGRO V57 {reg_simple} ADX{adx:.0f} RSI{int(rsi)} TP1.2%", 0.75
    return False,f"[{symbol}] LOBO_NEGRO {reg_simple} ADX{adx:.0f} RSI{int(rsi)} esperando",0.35

def detectar_TIBURON_sym(symbol):
    d=get_velas(symbol,"1d",210); d1h=get_velas(symbol,"1h",50)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d["closes"]; ema50=sum(closes[-50:])/50; rsi14=rsi_calc(closes,14)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 20
    if closes[-1] > ema50 and rsi14 > 45 and adx_1h > umb["adx_tiburon"]: return True,f"[{symbol}] TIBURON V57 {reg.split()[0]} ADX{adx_1h:.0f}>{umb['adx_tiburon']} RSI{int(rsi14)}", 0.85
    return False,f"[{symbol}] TIBU {reg.split()[0]} ADX{adx_1h:.0f}/{umb['adx_tiburon']} esperando", 0.25

def detectar_TIBURON_NEGRO_sym(symbol):
    d=get_velas(symbol,"1d",210); d1h=get_velas(symbol,"1h",50)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d["closes"]; ema50=sum(closes[-50:])/50; rsi14=rsi_calc(closes,14)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 20
    if closes[-1] < ema50 and rsi14 < 55 and adx_1h > umb["adx_tiburon"]: return True,f"[{symbol}] TIBURON_NEGRO V57 {reg.split()[0]} ADX{adx_1h:.0f}>{umb['adx_tiburon']} RSI{int(rsi14)} SHORT 5-10%", 0.85
    return False,f"[{symbol}] TIBURON_NEGRO {reg.split()[0]} ADX{adx_1h:.0f}/{umb['adx_tiburon']} esperando", 0.25

def detectar_KRAKEN_sym(symbol):
    d1h=get_velas(symbol,"1h",210)
    if not d1h: return False,f"{symbol} Sin velas",0
    closes_1h=d1h["closes"]; vols_1h=d1h["vols"]
    rsi_1h=rsi_calc(closes_1h,14); adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
    ema200 = ema_calc(closes_1h, 200); precio = closes_1h[-1]
    vol_prom_1h=sum(vols_1h[-21:-1])/20 if len(vols_1h)>=22 else sum(vols_1h)/len(vols_1h) if vols_1h else 1
    vsa_mult = vols_1h[-1]/vol_prom_1h if vol_prom_1h!=0 else 0
    panico_real = rsi_1h < 32 and vsa_mult > 1.15 and precio < ema200 and adx_1h > 20
    if panico_real: return True,f"[{symbol}] KRAKEN V57 PANICO REAL RSI{int(rsi_1h)}<32 VSA{vsa_mult:.1f}>1.15 <EMA200 ADX{adx_1h:.0f}",0.99
    return False,f"[{symbol}] KRAKEN ESPERA PANICO RSI{int(rsi_1h)}/32 VSA{vsa_mult:.1f}/1.15",0.05

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
                BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio*0.995, "tope": precio*1.08, "tipo": "NORMAL", "activa": False, "origen_mov": f"ESCLAVA V57 {reg} BAJISTA->NORMAL", "creada_en": ahora}
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
            BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio*0.97, "tope": precio*0.995, "tipo": "BAJISTA", "activa": False, "origen_mov": f"AUTO PANICO {entrada:.0f}->{tiempo_fuera/3600:.1f}h", "creada_en": ahora}
            BANDAS_TIEMPO_FUERA.pop(sym, None)
        elif tipo=="BAJISTA" and fuera_tipo=="ARRIBA" and tiempo_fuera > tiempo_optimo:
            BANDAS_ACTIVAS[sym] = {"entrada_tiburon": precio, "tope": precio*1.10, "tipo": "NORMAL", "activa": False, "origen_mov": f"AUTO CAZA {tiempo_fuera/3600:.1f}h", "creada_en": ahora}
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
            if p.get("estrategia") in ["TIBURON","TIBURON_NEGRO"]: total_tib += 1
    return counts, total_tib
def banda_txt_display(k,v):
    base = f"BANDA {k} {v['entrada_tiburon']:.0f}->{v['tope']:.0f} {v['tipo']}"
    if v.get("origen_mov"): base += f" MOVIL"
    return base
def banda_txt_api(k,v): return f"{k.replace('USDT','')} {v.get('tipo','')}"
def notificar_caza(sym, tipo, precio, tp, sl, banda_txt, usdt, motivo=""):
    try:
        msg = f"V57 AUTO {tipo} CAZADA!\nPar: {sym}\nEntrada: ${precio:.2f}\nMonto: ${usdt:.2f}\nTP: {tp:.1f}% | SL: {sl:.1f}%\nBanda: {banda_txt}\n{motivo[:100]}\nExp: PROFIT ${CONTADOR_TP_EXPANSION:.2f}/${META_PROFIT_PARA_EXPANDIR:.0f} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n{WEB_URL}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except: pass
        
# --- V57.1 FIX CAZA REAL - 4 MONEDAS - SIN CANDADO GLOBAL - GRAFICOS ON ---
def obtener_top_20_rentables_binance():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=8)
        data = r.json()
        out = []
        for t in data:
            s = t["symbol"]
            if not s.endswith("USDT"): continue
            if s in MONEDAS_ACTIVAS or s in ["USDTUSDT","USDCUSDT","FDUSDUSDT","BUSDUSDT"]: continue
            if is_moneda_bloqueada(s): continue
            if float(t.get("quoteVolume",0)) < 10000000: continue
            out.append((s, float(t.get("priceChangePercent",0))))
        out.sort(key=lambda x: x[1], reverse=False)
        top = [x[0] for x in out[:20]]
        print(f"V57 TOP20 REAL BINANCE: {top}")
        return top
    except Exception as e:
        print(f"V57 TOP20 error {e} -> fallback CANDIDATAS")
        return CANDIDATAS

def detectar_mejor_candidata():
    mejor = None; mejor_wr = 0
    for sym in obtener_top_20_rentables_binance():
        if sym in MONEDAS_ACTIVAS: continue
        if is_moneda_bloqueada(sym): continue
        try:
            _,_,wr1 = detectar_RATA_sym(sym)
            _,_,wr2 = detectar_LOBO_sym(sym)
            _,_,wr3 = detectar_TIBURON_sym(sym)
            _,_,wr4 = detectar_KRAKEN_sym(sym)
            _,_,wr5 = detectar_TIBURON_NEGRO_sym(sym)
            wr_total = wr1+wr2+wr3+wr4+wr5
            if wr_total > mejor_wr: mejor_wr = wr_total; mejor = sym
        except: continue
    return mejor, mejor_wr

def notificar_cierre(sym, tipo, entrada, salida, ganancia_usdt, ganancia_pct, es_tp, subtipo=""):
    try:
        u = USUARIOS.get(ADMINS_IDS[0], {})
        hoy = u.get("neto_hoy",0); total = (u.get("balance",0)-u.get("capital_inicial",0))
        if es_tp: msg = f"V57 PRESA DEVORADA\n{tipo} {sym}\n${entrada:.2f} -> ${salida:.2f}\n+${ganancia_usdt:.2f} ({ganancia_pct:+.2f}%)\nHoy: ${hoy:+.2f} Total: ${total:+.2f}"
        else: msg = f"V57 ESCAPO!\n{tipo} {sym}\n${entrada:.2f} -> ${salida:.2f}\n${ganancia_usdt:.2f} ({ganancia_pct:+.2f}%)\nHoy: ${hoy:+.2f} Total: ${total:+.2f}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except: pass

def notificar_cazando(sym, regimen):
    try:
        ahora = time.time(); key = f"caz_{sym}"
        if key in ULTIMO_CAZANDO and ahora - ULTIMO_CAZANDO[key] < 300: return
        ULTIMO_CAZANDO[key] = ahora
    except: pass

def mandar_pensamiento_telegram():
    global ULTIMO_PENSAMIENTO
    try:
        ahora = time.time()
        if ahora - ULTIMO_PENSAMIENTO < 1800: return
        ULTIMO_PENSAMIENTO = ahora
        regs_txt = "\n".join([f"{k}: {v}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO.get("regimen","LINEAL")
        bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
        try:
            ok, motivo, sym, est, fuerza = detectar_BI_CEREBRO(ESTADO.get("regimen","LINEAL"))
        except Exception as e_cerebro:
            print(f"Error cerebro interno V57 (no critico): {e_cerebro}")
            ok = False
            motivo = f"Recalibrando: {e_cerebro}"
            sym, est, fuerza = "", "", 0.0
        monedas_txt = f"{len(MONEDAS_ACTIVAS)}/20 ({','.join([m.replace('USDT','') for m in MONEDAS_ACTIVAS])})"
        tanque_txt = f"PROFIT ${CONTADOR_TP_EXPANSION:.2f}/${META_PROFIT_PARA_EXPANDIR:.0f} Tanque {monedas_txt}"
        if ok:
            texto = f"PENSAMIENTO LOBO V57.1 CAZA\n{regs_txt}\n{bandas_txt}\nEstrategia: {est} en {sym} ({fuerza:.2f})\n{motivo[:120]}\n{tanque_txt}\nDashboard: {WEB_URL}"
        else:
            texto = f"MERCADO EN LECTURA V57.1\n{regs_txt}\n{bandas_txt}\nAcechando... {motivo[:100]}\n{tanque_txt}\nDashboard: {WEB_URL}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, texto)
                except: pass
    except Exception as e:
        print(f"Error pensamiento V57: {e}")
        
# V57.1 - CEREBRO SIN CANDADO GLOBAL - SOLO POR REGIMEN
def detectar_BI_CEREBRO(regimen):
    counts_global, total_tib_global = contar_posiciones_globales()
    tib_por_moneda = {}; tib_negro_por_moneda = {}; kraken_por_moneda = {}
    for uid, lista in POSICIONES_ABIERTAS.items():
        if not isinstance(lista, list): continue
        for p in lista:
            sym = p.get("symbol")
            if p.get("estrategia") == "TIBURON": tib_por_moneda[sym] = tib_por_moneda.get(sym,0)+1
            if p.get("estrategia") == "TIBURON_NEGRO": tib_negro_por_moneda[sym] = tib_negro_por_moneda.get(sym,0)+1
            if p.get("estrategia") == "KRAKEN": kraken_por_moneda[sym] = kraken_por_moneda.get(sym,0)+1
    mejor_motivo=""; mejor_sym=""; mejor_fuerza=0; mejor_est=None
    for sym in MONEDAS_ACTIVAS:
        if is_moneda_bloqueada(sym): continue
        total_madres_en_sym = sum(1 for uid2, lista2 in POSICIONES_ABIERTAS.items() for p in (lista2 if isinstance(lista2,list) else []) if p.get("symbol")==sym and p.get("estrategia") in ["RATA","RATITA","LOBO","TIBURON","KRAKEN","RATA_NEGRA","LOBO_NEGRO","TIBURON_NEGRO","RATITA_BLANCA","RATITA_NEGRA"])
        tib_en_sym = tib_por_moneda.get(sym,0)
        tib_negro_en_sym = tib_negro_por_moneda.get(sym,0)
        kraken_en_sym = kraken_por_moneda.get(sym,0)
        reg_sym = ESTADO.get("regimenes",{}).get(sym,"LINEAL").split()[0]
        cambio_24h = get_cambio_24h(sym)

        if reg_sym in ("BAJISTA","CRASH"):
            if cambio_24h > -3: orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","RATA_NEGRA","RATITA_NEGRA","MOJARRITA"]
            elif cambio_24h > -5: orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","RATA_NEGRA","RATITA_NEGRA","LOBO_NEGRO","MOJARRITA"]
            else: orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","RATA_NEGRA","RATITA_NEGRA","LOBO_NEGRO","TIBURON_NEGRO","KRAKEN","MOJARRITA"]
        else:
            if reg_sym == "ALCISTA_FUERTE": orden = ["TIBURON","LOBO","RATA","RATITA","RATITA_BLANCA","PIRANA_BLANCA","MOJARRA","MOJARRITA"]
            elif reg_sym == "ALCISTA": orden = ["LOBO","RATA","RATITA","RATITA_BLANCA","PIRANA_BLANCA","MOJARRA","MOJARRITA"]
            elif reg_sym == "LINEAL_MUERTO": orden = ["MOJARRA", "MOJARRITA"]
            else: orden = ["MOJARRA","MOJARRITA","PIRANA_BLANCA","RATITA","RATITA_BLANCA","RATA"]

        for nombre in orden:
            try:
                if not candado(nombre, reg_sym, sym=sym): continue
                MADRES = ["RATA","RATITA","LOBO","TIBURON","KRAKEN","RATA_NEGRA","LOBO_NEGRO","TIBURON_NEGRO","RATITA_BLANCA","RATITA_NEGRA"]
                if nombre in MADRES and total_madres_en_sym >= 3: continue
                if nombre == "KRAKEN" and kraken_en_sym >= 1: continue
                if nombre == "TIBURON" and tib_en_sym >= 1: continue
                if nombre == "TIBURON_NEGRO" and tib_negro_en_sym >= 1: continue
                if nombre == "TIBURON" and total_tib_global >= 2: continue
                if nombre == "TIBURON_NEGRO" and total_tib_global >= 2: continue

                ok=False; motivo=""; wr=0
                if nombre=="RATA": ok,motivo,wr = detectar_RATA_sym(sym, "RATA")
                elif nombre=="RATITA": ok,motivo,wr = detectar_RATA_sym(sym, "RATITA")
                elif nombre=="RATITA_BLANCA": ok,motivo,wr = detectar_RATA_sym(sym, "RATITA_BLANCA")
                elif nombre=="MOJARRA": ok,motivo,wr = detectar_RATA_sym(sym, "MOJARRA")
                elif nombre=="MOJARRITA": ok,motivo,wr = detectar_RATA_sym(sym, "MOJARRITA")
                elif nombre in ["PIRANA_BLANCA","PIRANA"]: ok,motivo,wr = detectar_RATA_sym(sym, "PIRANA_BLANCA")
                elif nombre in ["RATA_NEGRA","PIRANA_NEGRA","MOJARRA_NEGRA","RATITA_NEGRA"]: ok,motivo,wr = detectar_SHORT_sym(sym, nombre)
                elif nombre=="LOBO": ok,motivo,wr = detectar_LOBO_sym(sym)
                elif nombre=="LOBO_NEGRO": ok,motivo,wr = detectar_LOBO_NEGRO_sym(sym)
                elif nombre=="TIBURON": ok,motivo,wr = detectar_TIBURON_sym(sym)
                elif nombre=="TIBURON_NEGRO": ok,motivo,wr = detectar_TIBURON_NEGRO_sym(sym)
                else: ok,motivo,wr = detectar_KRAKEN_sym(sym)

                tp_a = tp_adaptativo(sym, nombre if nombre in ESTRATEGIAS_V45 else "RATA")
                if tp_a == 0: tp_a = 0.3
                if ok and wr > mejor_fuerza and es_rentable(tp_a, nombre)[0]:
                    mejor_fuerza=wr; mejor_est=nombre; mejor_motivo=f"[{sym} {reg_sym} {cambio_24h:.1f}%] {motivo} TP{tp_a:.1f}% V58.2 Nv{EVOLUCION_NIVEL.get(sym,{}).get(reg_sym,1)}"; mejor_sym=sym
            except Exception as e_interno:
                print(f"Skip {nombre} {sym}: {e_interno}")
                continue

    if mejor_est: return True, mejor_motivo, mejor_sym, mejor_est, mejor_fuerza
    # V58.2 - Mensaje real de por qué no cazó, ya no más "SIN GLOBAL" ciego
    return False, f"V58.2 BAJISTA BUSCANDO - RSI 35-42 revisado, esperando gatillo V58.2", MONEDAS_ACTIVAS[0], None, 0    
    
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
            try:
                pf = os.path.join(DATA_DIR,"pirana_v50.json")
                if os.path.exists(pf): os.remove(pf)
            except: pass
    except: pass

def cargar_datos():
    global MONEDAS_ACTIVAS, POSICIONES_ABIERTAS, BANDAS_ACTIVAS, ESTADO_PIRANA, ESTADO_PIRANA_NEGRA, CANDIDATAS_CACHE, BANDAS_TIEMPO_FUERA, CONTADOR_TP_EXPANSION, TANQUE_BNB_USDT, KRAKEN_SL_COUNT, KRAKEN_BLOQUEO_HASTA, REG_ANT, CONTADOR_POR_REGIMEN, EVOLUCION_NIVEL, ESCAPE_BLOCK, ESCAPES_TIMELINE, PAUSA_GLOBAL_HASTA, BAJISTA_PROFUNDO_HASTA, BLOQUEO_LONG_TOTAL_HASTA, BAJISTA_PROFUNDO_POR_MONEDA, BLOQUEO_LONG_POR_MONEDA, EVOLUCION_NIVEL_NEGRA, CONTADOR_NEGRA_POR_REGIMEN, CONTADOR_SL_NEGRA_SEGUIDOS
    try:
        try:
            for _fn in ["pirana_v50.json","manada_v40.json","bandas_v45.json","contador_expansion.json","posiciones_abiertas.json"]:
                _p = os.path.join(DATA_DIR, _fn)
                if os.path.exists(_p): os.remove(_p)
                print(f"V57 FIX DEFINITIVO BORRADO {_p}")
        except: pass
        EVOLUCION_NIVEL = {sym: {"LINEAL":1,"LINEAL_MUERTO":1,"ALCISTA":1,"ALCISTA_FUERTE":1,"BAJISTA":1,"CRASH":1} for sym in MONEDAS_ACTIVAS}
        CONTADOR_POR_REGIMEN = {}
        EVOLUCION_NIVEL_NEGRA = {sym: {"BAJISTA":1,"CRASH":1} for sym in MONEDAS_ACTIVAS}
        CONTADOR_NEGRA_POR_REGIMEN = {}
        CONTADOR_TP_EXPANSION = 0.0
        ESCAPE_BLOCK = {}
        ESCAPES_TIMELINE = []
        PAUSA_GLOBAL_HASTA = 0
        print("V57.1 FIX CAZA - EVOLUCION FORZADA Nv1 TODAS - SIN GLOBAL")
        return
    except Exception as e: print(f"V57 cargar error {e}")

def limpiar_pos_viejas(): pass

def verificar_tanque_bnb():
    global REAL_BALANCE_BNB
    try:
        if not client: return False
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
        return False
    except: return False

def ejecutar_orden_real(symbol, side, usdt_amount):
    try:
        if not client: return False, {"simulado": False}, get_precio_robusto(symbol)
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

def inicializar_moneda_nueva_AUTO(sym):
    try:
        precio = get_precio_robusto(sym)
        if precio == 0: precio = 100
        d1h = get_velas(sym, "1h", 50)
        atr = atr_calc(d1h, 14) if d1h else precio * 0.02
        atr_pct = (atr/precio*100) if precio else 2.0
        if atr_pct > 2.5:
            inf = precio * 0.94
            sup = precio * 1.06
        else:
            inf = precio * 0.97
            sup = precio * 1.03
        BANDAS_ACTIVAS[sym] = {
            "entrada_tiburon": inf,
            "tope": sup,
            "tipo": "NORMAL",
            "activa": False,
            "origen_mov": f"V57 AUTO ATR{atr_pct:.2f}%",
            "creada_en": time.time()
        }
        REG_ANT[sym] = "LINEAL"
        EVOLUCION_NIVEL[sym] = {"LINEAL": 1, "LINEAL_MUERTO": 1, "ALCISTA": 1, "ALCISTA_FUERTE": 1, "BAJISTA": 1, "CRASH": 1}
        CONTADOR_POR_REGIMEN[sym] = {}
        EVOLUCION_NIVEL_NEGRA[sym] = {"BAJISTA": 1, "CRASH": 1}
        CONTADOR_NEGRA_POR_REGIMEN[sym] = {}
        print(f"V57 AUTO INICIADA {sym} ${precio:.2f} ATR{atr_pct:.2f}% Banda {inf:.2f}->{sup:.2f}")
        return True
    except Exception as e:
        print(f"V57 AUTO ERROR {sym}: {e}")
        BANDAS_ACTIVAS[sym] = {"entrada_tiburon": get_precio_robusto(sym)*0.97, "tope": get_precio_robusto(sym)*1.03, "tipo": "NORMAL", "activa": False, "creada_en": time.time()}
        REG_ANT[sym] = "LINEAL"
        EVOLUCION_NIVEL[sym] = {"LINEAL": 1}
        return False

def intentar_expandir(user_id_notify=None):
    global CONTADOR_TP_EXPANSION, MONEDAS_ACTIVAS
    if CONTADOR_TP_EXPANSION < META_PROFIT_PARA_EXPANDIR: return False
    if len(MONEDAS_ACTIVAS) >= MAX_MONEDAS: return False
    mejor_sym, wr = detectar_mejor_candidata()
    if not mejor_sym: return False
    msg = f"META PROFIT ${META_PROFIT_PARA_EXPANDIR:.0f} ALCANZADA V57 AUTO\nProfit: ${CONTADOR_TP_EXPANSION:.2f}\nCandidata: {mejor_sym} WR {wr:.2f}\nActual {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} -> {len(MONEDAS_ACTIVAS)+1}/{MAX_MONEDAS}\nAutorizas sumar {mejor_sym}?"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"AUTORIZAR {mejor_sym} AUTO", callback_data=f"AUTH_ADD_{mejor_sym}"), types.InlineKeyboardButton(f"RECHAZAR", callback_data=f"REJECT_{mejor_sym}"))
    try:
        targets = ADMINS_IDS if not user_id_notify else [user_id_notify]
        for uid in targets: bot.send_message(uid, msg, reply_markup=kb)
    except: pass
    CANDIDATAS_CACHE["_aviso_meta"] = time.time()
    guardar_datos()
    return False

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global MONEDAS_ACTIVAS, CONTADOR_TP_EXPANSION
    data = call.data
    try:
        if data.startswith("AUTH_ADD_"):
            nueva = data.replace("AUTH_ADD_", "")
            if nueva not in MONEDAS_ACTIVAS and len(MONEDAS_ACTIVAS) < MAX_MONEDAS:
                MONEDAS_ACTIVAS.append(nueva)
                inicializar_moneda_nueva_AUTO(nueva)
                ESTADO["regimenes"].setdefault(nueva, "LINEAL Iniciada por evolucion AUTO V57")
                CONTADOR_TP_EXPANSION = 0
                CANDIDATAS_CACHE["proxima"] = None
                CANDIDATAS_CACHE["_aviso_meta"] = 0
                guardar_datos()
                bot.answer_callback_query(call.id, f"{nueva} AUTORIZADA V57!")
                bot.send_message(call.message.chat.id, f"V57 {nueva} AUTORIZADO\nMonedas: {len(MONEDAS_ACTIVAS)}/20 ({','.join([m.replace('USDT','') for m in MONEDAS_ACTIVAS])})\nDashboard: {WEB_URL}")
            else:
                bot.answer_callback_query(call.id, "Ya agregada")
        elif data.startswith("REJECT_"):
            rechazada = data.replace("REJECT_", "")
            bot.answer_callback_query(call.id, f"{rechazada} Rechazada")
            bot.send_message(call.message.chat.id, f"V57 {rechazada} rechazada. Sigue con {len(MONEDAS_ACTIVAS)}/20")
            CANDIDATAS_CACHE["proxima"] = None
            guardar_datos()
    except Exception as e:
        print(f"Error callback V57: {e}")
        bot.answer_callback_query(call.id, "Error")

def escanear_candidatas_y_proponer():
    ahora = time.time()
    if ahora - CANDIDATAS_CACHE.get("_ultimo_scan",0) < TIEMPO_ESCANEO_CANDIDATAS: return
    CANDIDATAS_CACHE["_ultimo_scan"] = ahora
    if CONTADOR_TP_EXPANSION < META_PROFIT_PARA_EXPANDIR * 0.8: return
    mejor, wr = detectar_mejor_candidata()
    if mejor: CANDIDATAS_CACHE["proxima"] = mejor

def motor_v45():
    global CONTADOR_TP_EXPANSION, BTC_PRECIOS_15M, CONTADOR_SL_NEGRA_SEGUIDOS
    print(f">>> MOTOR V57.1 FIX CAZA REAL 4 MONEDAS {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} - SIN GLOBAL - GRAFICOS ON")
    time.sleep(5)
    while True:
        try:
            btc_price = get_precio_robusto("BTCUSDT")
            if btc_price>0:
                BTC_PRECIOS_15M.append((btc_price, time.time()))
                if len(BTC_PRECIOS_15M)>20: BTC_PRECIOS_15M = BTC_PRECIOS_15M[-20:]

            # === V58.1 FILTRO TOP3 SUPERVIVENCIA ===
            try:
                temp_sup = []
                for _s in list(MONEDAS_ACTIVAS)[:15]:
                    try:
                        _reg, _ = detectar_regimen_sym(_s)
                        if _reg == "SUPERVIVENCIA":
                            temp_sup.append(_s)
                    except: pass
            except: pass

            if len(temp_sup) >= 3:
                try:
                    top3 = scanner_06_top3_mejores_oportunidades(temp_sup)
                    if top3:
                        print(f"[06] SUPERVIVENCIA {len(temp_sup)} muertas. TOP3: {[x[0] for x in top3]}")
                        for sym_m, rsi_m, prec_m in top3:
                            ejecutar_mojarrita_supervivencia(sym_m, prec_m, rsi_m)
                        time.sleep(300)
                        continue
                except: pass
            # === FIN FILTRO TOP3 ===

            for sym in list(MONEDAS_ACTIVAS):
                reg, det = detectar_regimen_sym(sym)
                reset_si_cambio_regimen(sym, reg)
                ESTADO["regimenes"][sym] = f"{reg} {det}"
                if sym=="BTCUSDT": ESTADO["btc"]=btc_price; ESTADO["regimen"]=reg
                if sym=="BNBUSDT": ESTADO["bnb"]=get_precio_robusto(sym)

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
                        es_short = pos.get("estrategia") in NEGRAS
                        if not es_short:
                            pnl_pct_actual = (precio_actual - pos["entrada"]) / pos["entrada"] * 100 if pos["entrada"]!=0 else 0
                        else:
                            pnl_pct_actual = (pos["entrada"] - precio_actual) / pos["entrada"] * 100 if pos["entrada"]!=0 else 0
                        if pnl_pct_actual <= -3.5:
                            try:
                                lado_cierre = "BUY" if es_short else "SELL"
                                ejecutar_orden_real(pos["symbol"], lado_cierre, pos["usdt"])
                                pnl_bruto = (precio_actual - pos["entrada"]) / pos["entrada"] * pos["usdt"] if not es_short else (pos["entrada"] - precio_actual) / pos["entrada"] * pos["usdt"]
                                comision = pos["usdt"] * COMISION_TOTAL/100
                                pnl = pnl_bruto - comision
                                u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["perdidas"]+=1
                                if es_short:
                                    CONTADOR_SL_NEGRA_SEGUIDOS+=1
                                POSICIONES_ABIERTAS[user_id].remove(pos)
                                guardar_datos()
                                continue
                            except: pass
                        if "max_pnl" not in pos:
                            pos["max_pnl"] = pnl_pct_actual
                            pos["max_precio"] = precio_actual
                        if pnl_pct_actual > pos["max_pnl"]:
                            pos["max_pnl"] = pnl_pct_actual
                            pos["max_precio"] = precio_actual
                        tp_price = pos["entrada"] * (1 + pos["tp"]/100) if not es_short else pos["entrada"] * (1 - pos["tp"]/100)
                        sl_price = pos["entrada"] * (1 + pos["sl"]/100) if not es_short else pos["entrada"] * (1 - pos["sl"]/100)
                        cerrar = None
                        motivo_cierre = ""
                        cfg = TRAILING_CONFIG.get(pos["estrategia"], {"activo": False})
                        if cfg.get("activo") and pos["max_pnl"] >= cfg["activacion"]:
                            if pnl_pct_actual <= (pos["max_pnl"] - cfg["trailing"]):
                                cerrar = "TP"
                                motivo_cierre = f"TRAILING V57 {pos['estrategia']} Max{pos['max_pnl']:.2f}% -> Actual{pnl_pct_actual:.2f}% Trail{cfg['trailing']}%"
                        if not cerrar:
                            if not es_short:
                                if precio_actual >= tp_price: cerrar = "TP"
                                elif precio_actual <= sl_price: cerrar = "SL"
                            else:
                                if precio_actual <= tp_price: cerrar = "TP"
                                elif precio_actual >= sl_price: cerrar = "SL"
                        if cerrar:
                            lado_cierre = "BUY" if es_short else "SELL"
                            try: ejecutar_orden_real(pos["symbol"], lado_cierre, pos["usdt"])
                            except: pass
                            pnl_bruto = (precio_actual - pos["entrada"]) / pos["entrada"] * pos["usdt"] if not es_short else (pos["entrada"] - precio_actual) / pos["entrada"] * pos["usdt"]
                            comision = pos["usdt"] * COMISION_TOTAL/100
                            pnl = pnl_bruto - comision
                            pnl_pct = pnl_pct_actual
                            es_tp = cerrar == "TP"
                            if es_tp:
                                if pos.get("estrategia") == "KRAKEN": kraken_reset_si_tp()
                                u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["ganadas"]+=1
                                if es_short: CONTADOR_SL_NEGRA_SEGUIDOS=0
                                ganancia_real_total = u["balance"] - BALANCE_INICIAL
                                CONTADOR_TP_EXPANSION = max(0.0, ganancia_real_total)
                                if CONTADOR_TP_EXPANSION >= META_PROFIT_PARA_EXPANDIR: intentar_expandir(user_id)
                            else:
                                if pos.get("estrategia") == "KRAKEN": kraken_registrar_sl()
                                u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["perdidas"]+=1
                                if es_short:
                                    CONTADOR_SL_NEGRA_SEGUIDOS+=1
                                if pnl <= -1.0: registrar_escape(pos["symbol"])
                            estr = pos.get("estrategia", "MOJARRA")
                            if estr not in u.get("estrategias", {}): u["estrategias"][estr] = {"ops":0,"ganadas":0,"neto":0.0}
                            u["estrategias"][estr]["ops"]+=1; u["estrategias"][estr]["neto"]+=pnl
                            u["ops_hoy"]+=1
                            extra = f" {motivo_cierre}" if motivo_cierre else ""
                            u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} {estr} {pos['symbol']} {cerrar}{extra} ${pnl:+.2f} TP:{pos['tp']:.1f}% V57.1")
                            notificar_cierre(pos["symbol"], estr, pos["entrada"], precio_actual, pnl, pnl_pct, es_tp, pos.get("subtipo","")+extra)
                            POSICIONES_ABIERTAS[user_id].remove(pos)
                            guardar_datos()
                    except Exception as e: print(f"Error cierre V57 {e}")
                if not u.get("prendido", False): continue
                ok,motivo,symbol_elegido,estrategia_elegida,fuerza = detectar_BI_CEREBRO(ESTADO.get("regimen","LINEAL"))
                if ok and estrategia_elegida:
                    counts_global, _ = contar_posiciones_globales()
                    key_global = (symbol_elegido, estrategia_elegida)
                    existentes = [p for p in POSICIONES_ABIERTAS.get(user_id,[]) if p.get('symbol')==symbol_elegido and p.get('estrategia')==estrategia_elegida]
                    key_lock = f"{symbol_elegido}_{estrategia_elegida}"
                    if key_lock in ULTIMO_TRADE and (time.time() - ULTIMO_TRADE[key_lock]) < ESTRATEGIAS_V45[estrategia_elegida]["cooldown"]: continue
                    if estrategia_elegida in ["MOJARRA"]: max_permitido = MAX_MOJARRA_POR_MONEDA; dist_requerida = DISTANCIA_MOJARRA_PCT
                    elif estrategia_elegida in ["MOJARRA_NEGRA"]: max_permitido = MAX_MOJARRA_POR_MONEDA; dist_requerida = DISTANCIA_MOJARRA_NEGRA_PCT
                    elif estrategia_elegida in ["PIRANA_BLANCA","PIRANA","MOJARRA","MOJARRITA","RATITA","RATITA_BLANCA"]:
                        if estrategia_elegida == "MOJARRITA": max_permitido = MAX_MOJARRITA_POR_MONEDA; dist_requerida = DISTANCIA_MOJARRA_PCT
                        else: max_permitido = MAX_PIRANA_POR_MONEDA; dist_requerida = DISTANCIA_PIRANA_PCT
                    elif estrategia_elegida in ["PIRANA_NEGRA","RATITA_NEGRA"]: max_permitido = MAX_PIRANA_POR_MONEDA; dist_requerida = DISTANCIA_PIRANA_NEGRA_PCT
                    else: max_permitido = 1; dist_requerida = 0.10
                    if counts_global.get(key_global, 0) >= max_permitido: continue
                    if len(existentes) >= max_permitido: continue
                    precio_actual_tmp = get_precio_robusto(symbol_elegido)
                    usdt_a_usar = max(10, u["balance"]*0.035)
                    reg_actual_sym = ESTADO.get("regimenes",{}).get(symbol_elegido,"LINEAL")
                    if estrategia_elegida == "LOBO" and "ALCISTA" in reg_actual_sym: usdt_a_usar = max(200, min(500, u["balance"]*0.50))
                    elif estrategia_elegida in ["LOBO_NEGRO","TIBURON_NEGRO"] and ("BAJISTA" in reg_actual_sym or "CRASH" in reg_actual_sym): usdt_a_usar = max(200, min(500, u["balance"]*0.50))
                    elif estrategia_elegida == "RATA" and "ALCISTA" in reg_actual_sym: usdt_a_usar = max(80, u["balance"]*0.15)
                    elif estrategia_elegida in ["RATA_NEGRA","RATITA_NEGRA"] and ("BAJISTA" in reg_actual_sym or "CRASH" in reg_actual_sym): usdt_a_usar = max(80, u["balance"]*0.15)
                    elif estrategia_elegida == "RATITA_BLANCA" and "ALCISTA" in reg_actual_sym: usdt_a_usar = max(80, u["balance"]*0.15)
                    if estrategia_elegida == "KRAKEN": usdt_a_usar = max(200, min(300, u["balance"]*0.20))
                    if estrategia_elegida == "TIBURON_NEGRO": usdt_a_usar = max(200, min(500, u["balance"]*0.40))
                    tp_final = tp_adaptativo(symbol_elegido, estrategia_elegida)
                    if tp_final == 0: tp_final = 0.3
                    exito, res, precio = ejecutar_orden_real(symbol_elegido,"BUY",usdt_a_usar)
                    if exito:
                        ULTIMO_TRADE[key_lock]=time.time(); ULTIMO_CAZANDO[key_lock]=time.time()
                        pos = {"symbol": symbol_elegido, "estrategia": estrategia_elegida, "entrada": precio, "tp": tp_final, "sl": ESTRATEGIAS_V45[estrategia_elegida]["sl_neto"], "usdt": usdt_a_usar, "hora": ahora_art().isoformat(), "max_pnl": 0.0, "max_precio": precio}
                        POSICIONES_ABIERTAS[user_id].append(pos)
                        reg_simple = ESTADO.get("regimenes",{}).get(symbol_elegido,"LINEAL").split()[0]
                        if estrategia_elegida in BLANCAS: registrar_caza_V51(symbol_elegido, estrategia_elegida, reg_simple)
                        else: registrar_caza_negra_V56_4(symbol_elegido, estrategia_elegida, reg_simple)
                        u["modo"]=f"{estrategia_elegida} {symbol_elegido} TP{pos['tp']:.1f}%"; u["mercado"]=motivo
                        b = BANDAS_ACTIVAS.get(symbol_elegido,{})
                        banda_txt = f"{b.get('entrada_tiburon',precio*0.97):.0f}->{b.get('tope',precio*1.10):.0f} {b.get('tipo','')}"
                        notificar_caza(symbol_elegido, estrategia_elegida, precio, pos['tp'], ESTRATEGIAS_V45[estrategia_elegida]["sl_neto"], banda_txt, usdt_a_usar, motivo)
            guardar_datos()
            time.sleep(60)
        except Exception as e:
            print(f"Error motor V57.1 {e}")
            time.sleep(10)
            
def get_menu():
    m=types.ReplyKeyboardMarkup(resize_keyboard=False)
    m.add("PRENDER","EVOLUCIONAR")
    m.add("BALANCE","HISTORIAL")
    m.add("RETIRAR GANANCIAS","RETIRAR TODO")
    m.add("ORDENES")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    u=get_user_data(m.chat.id)
    estado_txt = f"V57 {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}" if u["prendido"] else "APAGADO"
    regs="\n".join([f"{k}:{v.split()[0]}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO['regimen'].split()[0]
    bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
    ganancia = u["balance"] - u["capital_inicial"]
    bot.send_message(m.chat.id,f"V57 CEREBRO {estado_txt}\n{regs}\n{bandas_txt}\n{'+'.join(MONEDAS_ACTIVAS)}\nBal ${u['balance']:.2f}\nGan ${ganancia:.2f}\n{WEB_URL}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="BALANCE")
def balance(m):
    u=get_user_data(m.chat.id)
    ganancia_historica = u["balance"]-u["capital_inicial"]
    regs="\n".join([f"{k}: {v.split()[0]} ({get_cambio_24h(k):+.1f}%)" for k,v in ESTADO.get("regimenes",{}).items()])
    pos_txt = "\n".join([f"{p['symbol']} {p['estrategia']} Ent {p['entrada']:.2f} TP{p['tp']:.1f}% Max{p.get('max_pnl',0):.1f}%" for p in POSICIONES_ABIERTAS.get(m.chat.id,[])]) or "Sin pos"
    bot.send_message(m.chat.id,f"V57.1 FIX CAZA {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} SIN GLOBAL\n{regs}\n{pos_txt}\nBal ${u['balance']:.2f} Hist ${ganancia_historica:+.2f}\nHoy ${u['neto_hoy']:+.2f}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="PRENDER")
def prender(m):
    u=get_user_data(m.chat.id); u["prendido"]=True; u["modo"]="CAZANDO V57.1"; guardar_datos()
    bot.send_message(m.chat.id,f"MANADA PRENDIDA V57.1 SIN GLOBAL\nBolsa Unica ${u['balance']:.2f}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="EVOLUCIONAR")
def evolucionar(m):
    u=get_user_data(m.chat.id)
    regs="\n".join([f"{k}: {v} {get_cambio_24h(k):+.1f}%" for k,v in ESTADO.get("regimenes",{}).items()])
    bandas_txt = "\n".join([banda_txt_display(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas V57"
    clima = f"V57.1 SIN GLOBAL CLIMA BTC {ESTADO.get('regimen','LINEAL')} {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} PROFIT ${CONTADOR_TP_EXPANSION:.2f}/${META_PROFIT_PARA_EXPANDIR:.0f}"
    bot.send_message(m.chat.id,f"{clima}\n{regs}\n{bandas_txt}\n{'+'.join(MONEDAS_ACTIVAS)}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="HISTORIAL")
def historial(m):
    u=get_user_data(m.chat.id); hist = u.get("historial",[])[-15:]; txt = "\n".join(hist) or "Sin historial"
    bot.send_message(m.chat.id,f"HISTORIAL V57\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="ORDENES")
def ordenes(m):
    lista = POSICIONES_ABIERTAS.get(m.chat.id,[])
    if not lista: bot.send_message(m.chat.id,"Sin ordenes abiertas V57",reply_markup=get_menu()); return
    txt="".join([f"{p['symbol']} {p['estrategia']} ${p['entrada']:.2f} TP{p['tp']:.1f}% SL{p['sl']:.1f}% Max{p.get('max_pnl',0):.1f}% ${p['usdt']:.0f}\n" for p in lista])
    bot.send_message(m.chat.id,f"ORDENES V57 {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\n{txt}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="RETIRAR GANANCIAS")
def retirar_gan(m):
    u=get_user_data(m.chat.id); gan = u["balance"]-u["capital_inicial"]
    if gan <= 0: bot.send_message(m.chat.id,f"Sin ganancias para retirar. Gan ${gan:.2f}",reply_markup=get_menu()); return
    u["balance"]=BALANCE_INICIAL; u["capital_inicial"]=BALANCE_INICIAL; u["neto_hoy"]=0; guardar_datos()
    bot.send_message(m.chat.id,f"GANANCIAS RETIRADAS V57 ${gan:.2f}\nBolsa unica vuelve a ${u['capital_inicial']:.2f}",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="RETIRAR TODO")
def retirar_todo(m):
    global CONTADOR_POR_REGIMEN, EVOLUCION_NIVEL, CONTADOR_NEGRA_POR_REGIMEN, EVOLUCION_NIVEL_NEGRA, CONTADOR_TP_EXPANSION, ESCAPE_BLOCK, ESCAPES_TIMELINE, PAUSA_GLOBAL_HASTA
    u=get_user_data(m.chat.id); total=u["balance"]; gan = total - u["capital_inicial"]
    u["balance"]=BALANCE_INICIAL; u["capital_inicial"]=BALANCE_INICIAL; u["neto_hoy"]=0; u["ganadas"]=0; u["perdidas"]=0; u["ops_hoy"]=0
    u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} RETIRO TOTAL ${total:.2f} Gan ${gan:.2f} -> RESET 10k V57")
    POSICIONES_ABIERTAS[m.chat.id]=[]
    CONTADOR_POR_REGIMEN = {}
    EVOLUCION_NIVEL = {sym: {"LINEAL":1,"LINEAL_MUERTO":1,"ALCISTA":1,"ALCISTA_FUERTE":1,"BAJISTA":1,"CRASH":1} for sym in MONEDAS_ACTIVAS}
    CONTADOR_NEGRA_POR_REGIMEN = {}
    EVOLUCION_NIVEL_NEGRA = {sym: {"BAJISTA":1,"CRASH":1} for sym in MONEDAS_ACTIVAS}
    CONTADOR_TP_EXPANSION = 0.0
    ESCAPE_BLOCK = {}
    ESCAPES_TIMELINE = []
    PAUSA_GLOBAL_HASTA = 0
    try:
        for _fn in ["pirana_v50.json","manada_v40.json","bandas_v45.json","contador_expansion.json","posiciones_abiertas.json","monedas_activas.json"]:
            _p = os.path.join(DATA_DIR, _fn)
            if os.path.exists(_p): os.remove(_p)
    except: pass
    guardar_datos()
    bot.send_message(m.chat.id,f"TODO RETIRADO V57 ${total:.2f} (Gan ${gan:.2f})\nReseteada a ${BALANCE_INICIAL:.2f} + EVOLUCION Nv1",reply_markup=get_menu())

@bot.message_handler(func=lambda m: True)
def fallback(m):
    try:
        txt=m.text.upper()
        if "BNB" in txt or "BTC" in txt:
            sym = txt.replace(" ","").replace("$","")
            if "USDT" not in sym: sym+="USDT"
            precio=get_precio_robusto(sym)
            bot.send_message(m.chat.id,f"{sym} ${precio:.2f} V57",reply_markup=get_menu())
        else: bot.send_message(m.chat.id,f"V57.1 SIN GLOBAL 4 MONEDAS Comandos: PRENDER, BALANCE, EVOLUCIONAR\n{len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} PROFIT ${CONTADOR_TP_EXPANSION:.2f}/${META_PROFIT_PARA_EXPANDIR:.0f} Tanque 50\n{WEB_URL}",reply_markup=get_menu())
    except: bot.send_message(m.chat.id,"V57",reply_markup=get_menu())

def info_sym(sym):
    try:
        precio = get_precio_robusto(sym)
        if precio==0: precio = ESTADO.get("btc",0) or 100.0
        cambio24 = get_cambio_24h(sym)
        d1h = get_velas(sym, "1h", 50)
        d5 = get_velas(sym, "5m", 50)
        adx_real = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 15.0
        rsi_real = rsi_calc(d5["closes"], 7) if d5 else 50.0
        atr_val = atr_calc(d1h, 14) if d1h else 0
        atr_pct = (atr_val/precio*100) if precio!=0 else 0
        vol_txt = 1.0
        if d1h and len(d1h["vols"])>=20:
            prom = sum(d1h["vols"][-20:])/20
            vol_txt = d1h["vols"][-1]/prom if prom else 1.0
        reg_full = ESTADO.get("regimenes",{}).get(sym,"LINEAL")
        reg = reg_full.split()[0] if reg_full else "LINEAL"
        cont = CONTADOR_POR_REGIMEN.get(sym,{}).get(reg,{})
        cont_negra = CONTADOR_NEGRA_POR_REGIMEN.get(sym,{}).get(reg,{})
        nivel = EVOLUCION_NIVEL.get(sym,{}).get(reg,1)
        nivel_negra = EVOLUCION_NIVEL_NEGRA.get(sym,{}).get(reg,1)
        banda = BANDAS_ACTIVAS.get(sym,{})
        madre = banda.get("tipo","NORMAL")
        ema_txt = "9>20"
        if d1h:
            ema20 = sum(d1h["closes"][-20:])/20
            ema50 = sum(d1h["closes"][-50:])/50 if len(d1h["closes"])>=50 else ema20
            ema_txt = "20>50" if ema20>ema50 else "20<50"
        return {
            "regimen": str(reg),
            "reg_detalle": str(reg_full),
            "cambio24": float(cambio24),
            "adx": float(adx_real),
            "rsi": float(rsi_real),
            "ema": str(ema_txt),
            "atr": float(atr_pct),
            "vol": float(vol_txt),
            "precio": float(precio),
            "madre": str(madre),
            "mejor_estrategia": f"V57 Nv{nivel}/NvNegra{nivel_negra} {cont} {cont_negra}",
            "banda_inf": float(banda.get("entrada_tiburon",precio*0.97)),
            "banda_sup": float(banda.get("tope",precio*1.03)),
            "v51_nivel": int(nivel),
            "v51_contador": cont,
            "v56_nivel_negra": int(nivel_negra),
            "v56_contador_negra": cont_negra
        }
    except Exception as e:
        print(f"info_sym V57 error {sym}: {e}")
        return {"regimen":"LINEAL","cambio24":0.0,"adx":15.0,"rsi":50.0,"ema":"9>20","atr":0.0,"vol":1.0,"precio":0.0,"madre":"NORMAL","mejor_estrategia":"V57","banda_inf":1.0,"banda_sup":2.0,"v51_nivel":1,"v51_contador":{},"v56_nivel_negra":1,"v56_contador_negra":{}}
@app.route('/api/mercado')
def api_mercado():
    try: return jsonify({sym: info_sym(sym) for sym in MONEDAS_ACTIVAS})
    except: return jsonify({}), 200
@app.route('/api/detalles_mercado')
def api_detalles_mercado():
    try:
        res = {}
        for sym in MONEDAS_ACTIVAS:
            inf = info_sym(sym)
            res[sym] = {
                "regimen": str(inf.get("regimen","LINEAL")),
                "cambio24": float(inf.get("cambio24",0.0)),
                "adx": float(inf.get("adx",15.0)),
                "madre": str(inf.get("madre","NORMAL")),
                "rsi": float(inf.get("rsi",50.0)),
                "ema": str(inf.get("ema","9>20")),
                "atr": float(inf.get("atr",0.0)),
                "vol": float(inf.get("vol",1.0)),
                "mejor_estrategia": str(inf.get("mejor_estrategia","V57")),
                "v51_nivel": int(inf.get("v51_nivel",1)),
                "v51_contador": inf.get("v51_contador",{}),
                "v56_nivel_negra": int(inf.get("v56_nivel_negra",1)),
                "v56_contador_negra": inf.get("v56_contador_negra",{}),
                "precio": float(inf.get("precio",0.0)),
                "banda_inf": float(inf.get("banda_inf",1.0)),
                "banda_sup": float(inf.get("banda_sup",2.0))
            }
        return jsonify(res)
    except: return jsonify({}), 200

# V57.1 GRAFICOS RESTAURADOS
@app.route('/api/graficos')
def api_graficos():
    try:
        res = {}
        for sym in MONEDAS_ACTIVAS:
            d = get_velas(sym, "5m", 100)
            if d:
                res[sym] = {"closes": d["closes"][-50:], "rsi": rsi_calc(d["closes"],7)}
        return jsonify(res)
    except: return jsonify({}), 200

@app.route('/')
def home():
    html = '''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>V57.1 SIN GLOBAL 4/20 GRAFICOS ON</title><script src="https://s3.tradingview.com/tv.js"></script>
    <style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}.top{padding:12px;background:#1e222d;position:sticky;top:0;z-index:20;border-bottom:2px solid #44ff88;font-size:12px;white-space:nowrap;overflow:auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px}.card{background:#1e222d;border-radius:8px;overflow:hidden;border:1px solid #2a2e39}.det{font-family:monospace;font-size:11px;padding:6px;background:#0e1a0e;color:#a5fca5}</style>
    </head><body><div class="top" id="info">V57.1 SIN GLOBAL 4/20 GRAFICOS ON - Cargando...</div><div class="grid" id="grid"></div>
    <script>
    async function init(){
      let a = await (await fetch('/api/data')).json();
      let MONEDAS = a.monedas || ["BTCUSDT","BNBUSDT","AVAXUSDT","XRPUSDT"];
      document.getElementById('grid').innerHTML = "";
      MONEDAS.forEach(sym=>{
        let id='tv_'+sym;let c=document.createElement('div');c.className='card';
        c.innerHTML=`<div id="${id}" style="height:340px"></div><div class="det" id="det-${sym}">${sym}...</div>`;
        document.getElementById('grid').appendChild(c);
        new TradingView.widget({autosize:true,symbol:"BINANCE:"+sym,interval:"5",container_id:id,theme:"dark",style:"1",locale:"es"});
      });
      load();
    }
    async function load(){
      try{let a=await (await fetch('/api/data')).json();
        document.getElementById('info').innerHTML=`V57.1 SIN GLOBAL ${a.monedas.length}/20 | $${a.balance?.toFixed(2)||''} | ${a.bandas_txt||''} | ${Object.entries(a.regimenes||{}).map(e=>e[0].replace('USDT','')+':'+e[1]).join(' | ')} | PROFIT $${a.tps_actual?.toFixed(2)}/$${a.meta_proxima}`;
      }catch(e){}
      try{
        let d=await (await fetch('/api/detalles_mercado')).json();
        for(let k in d){
          let el=document.getElementById('det-'+k);
          if(el&&d[k]){
            let x=d[k];
            let cambio=(x.cambio24>=0?'+':'')+Number(x.cambio24).toFixed(2)+'%';
            el.innerHTML=`REGIMEN: ${x.regimen} (${cambio}) (ADX ${Number(x.adx).toFixed(1)}) | Madre: ${x.madre} | RSI ${Number(x.rsi).toFixed(1)} | ${x.ema} | ATR ${Number(x.atr).toFixed(2)}% | Vol ${Number(x.vol).toFixed(2)}x<br>Mejor: ${x.mejor_estrategia} | Nv ${x.v51_nivel} Negra Nv${x.v56_nivel_negra} | $${Number(x.precio).toFixed(2)} | <a href='/api/graficos' style='color:#44ff88'>Graficos ON</a>`;
          }
        }
      }catch(e){}
    }
    init();setInterval(load,5000);
    </script></body></html>'''
    return render_template_string(html, monedas=MONEDAS_ACTIVAS)

@app.route('/api/data')
def api_data():
    try:
        target=ADMINS_IDS[0]
        if target not in USUARIOS: get_user_data(target)
        u=USUARIOS[target]
        bandas_txt = " | ".join([banda_txt_api(k,v) for k,v in BANDAS_ACTIVAS.items() if v.get("activa")]) or "Sin bandas"
        ganancia_total = u["balance"]-u["capital_inicial"]
        return jsonify({"balance":u["balance"],"capital_inicial":u["capital_inicial"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"regimen_btc":ESTADO.get("regimen","LINEAL"),"regimenes":ESTADO.get("regimenes",{}),"estrategias":u["estrategias"],"monedas":MONEDAS_ACTIVAS,"ganancia_total":ganancia_total,"bandas":BANDAS_ACTIVAS,"bandas_txt":bandas_txt,"posiciones":POSICIONES_ABIERTAS.get(target,[]),"precios":{},"meta_proxima":META_PROFIT_PARA_EXPANDIR,"tps_actual":CONTADOR_TP_EXPANSION,"v51_contadores":CONTADOR_POR_REGIMEN,"v51_niveles":EVOLUCION_NIVEL,"v56_contadores_negra":CONTADOR_NEGRA_POR_REGIMEN,"v56_niveles_negra":EVOLUCION_NIVEL_NEGRA,"bajista_profundo":BAJISTA_PROFUNDO_HASTA,"bloqueo_long":BLOQUEO_LONG_TOTAL_HASTA,"bajista_por_moneda":BAJISTA_PROFUNDO_POR_MONEDA,"bloqueo_por_moneda":BLOQUEO_LONG_POR_MONEDA})
    except Exception as e:
        return jsonify({"balance":10000,"capital_inicial":10000,"neto_hoy":0,"modo":"OK","mercado":"OK","regimen_btc":"LINEAL","regimenes":ESTADO.get("regimenes",{}),"estrategias":{},"monedas":MONEDAS_ACTIVAS,"ganancia_total":0,"bandas":BANDAS_ACTIVAS,"bandas_txt":"OK","posiciones":[],"precios":{},"meta_proxima":120,"tps_actual":CONTADOR_TP_EXPANSION,"v51_contadores":CONTADOR_POR_REGIMEN,"v51_niveles":EVOLUCION_NIVEL}),200

if True:
    cargar_datos()
    for sym in MONEDAS_ACTIVAS:
        ESTADO["regimenes"].setdefault(sym, "LINEAL Inicializado")
        REG_ANT.setdefault(sym, "LINEAL")
    t = threading.Thread(target=motor_v45, daemon=False); t.start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), debug=False, use_reloader=False), daemon=False).start()
    print("V57.1 FIX CAZA REAL 4 MONEDAS - SIN GLOBAL - GRAFICOS ON")
    try:
        bot.delete_webhook(drop_pending_updates=False)
        print("V57.1 Webhook borrado - polling unico")
        time.sleep(2)
    except: pass
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        print(f"Bot polling error V57.1 {e}")
        time.sleep(10)
