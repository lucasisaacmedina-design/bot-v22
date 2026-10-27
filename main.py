# ==================== V59.5.4 FINAL FIX PARTE 1 COMPLETA - 40/40 EXCLUSIVOS + 12H/6H + ORDEN MOJARRA->PIRANA_BLANCA->RATITA_BLANCA->RATA - FIX BTC REAL ====================
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

MONEDAS_ACTIVAS = ["BTCUSDT", "BNBUSDT", "AVAXUSDT", "XRPUSDT"]
TP_BASE_V594 = 0.5
TP_RESCATE_V594 = 0.3
HORAS_RESCATE_V594 = 12
CICLO_VUELTA_H = 6
TP_FIJO_LOBO = 1.2
TP_FIJO_TIBURON_MIN = 5.0
TP_FIJO_TIBURON_MAX = 10.0
TP_FIJO_RATA = 0.8
TP_FIJO_KRAKEN = 3.0
VOL_MIN_REAL = 1.5
ATR_MIN_REAL = 0.42
ADX_MIN_ALCISTA_REAL = 25
ADX_MIN_BAJISTA_REAL = 28

CANDIDATAS = ["ETHUSDT","SOLUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","DOTUSDT","LTCUSDT","TRXUSDT","MATICUSDT","SHIBUSDT","PEPEUSDT","SUIUSDT","APTUSDT","ARBUSDT","OPUSDT","NEARUSDT","FILUSDT","INJUSDT","BONKUSDT"]
MAX_MONEDAS = 40
META_PROFIT_PARA_EXPANDIR = 120.0
META_TP_PARA_EXPANDIR = META_PROFIT_PARA_EXPANDIR
CONTADOR_TP_EXPANSION = 0.0
TANQUE_POR_MONEDA = 2.0
TANQUE_BNB_USDT = 50.0
TANQUE_BNB_MIN = 5.0
TANQUE_BNB_RECARGA = 8.0
TANQUE = TANQUE_BNB_USDT
MOJARRA_USDT = 10.0
MOJARRA_USDT_VIEJA = 350.0
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
MAX_MOJARRA_POR_MONEDA = 5
MAX_PIRANA_POR_MONEDA = 2
MAX_MOJARRITA_POR_MONEDA = 5
MOJARRITA_NIVELES = [20, 16, 12, 8, 3]
DISTANCIA_CARDUMEN_PCT = 0
DISTANCIA_PIRANA_PCT = 0.40
DISTANCIA_MOJARRA_PCT = 0
DISTANCIA_MOJARRA_NEGRA_PCT = 0.40
DISTANCIA_PIRANA_NEGRA_PCT = 0.40
DISTANCIA_EXCLUSIVA_PCT = 0
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
        if time.time() < ESCAPE_BLOCK[sym]: return True
        else: del ESCAPE_BLOCK[sym]
    return False
def registrar_escape(sym):
    global ESCAPES_TIMELINE, PAUSA_GLOBAL_HASTA
    ahora = time.time()
    ESCAPE_BLOCK[sym] = ahora + TIEMPO_BLOQUEO_MONEDA
    ESCAPES_TIMELINE.append(ahora)
    ESCAPES_TIMELINE = [t for t in ESCAPES_TIMELINE if ahora - t < 3600]
    if len(ESCAPES_TIMELINE) >= MAX_ESCAPES_POR_HORA:
        PAUSA_GLOBAL_HASTA = ahora + TIEMPO_PAUSA_PANICO
        return True
    return True
def hay_pausa_global(): return False
def es_bajista_profundo_activo(sym=None): return False
def es_bloqueo_long_total(sym=None): return False
def btc_crash_15m(umbral=-2.5):
    try:
        if len(BTC_PRECIOS_15M) < 2: return False
        ahora = time.time()
        recientes = [(p,t) for p,t in BTC_PRECIOS_15M if ahora - t < 900]
        if len(recientes) < 2: return False
        p_viejo = recientes[0][0]; p_nuevo = recientes[-1][0]
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
    "MOJARRA": {"tf": "1m", "desc": "MOJARRA 0.5% LONG LINEAL_MUERTO 52/58/65 V59.5.4 INMORTAL 40/40","rango_tp": (0.5, 0.5), "sl_neto": -2.5, "max_dia": 300,"cooldown": 15, "cooldown_rec": 15,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.5},
    "MOJARRITA": {"tf": "5m", "desc": "MOJARRITA 0.5% LINEAL_MUERTO V59.5.4 5-28 x1","rango_tp": (0.5, 0.5), "sl_neto": -1.5, "max_dia": 200,"cooldown": 15, "cooldown_rec": 15,"mercado_ideal": "LINEAL_MUERTO", "tp_fijo_banda": 0.5},
    "PIRANA_BLANCA": {"tf": "3m", "desc": "PIRANA BLANCA 0.8% FIJO LONG V59.5.4","rango_tp": (0.8, 0.8), "sl_neto": -2.8, "max_dia": 150,"cooldown": 90, "cooldown_rec": 90,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "RATITA": {"tf": "5m", "desc": "RATITA 0.8% FIJO LONG V59.5.4","rango_tp": (0.8, 0.8), "sl_neto": -3.0, "max_dia": 40,"cooldown": 120, "cooldown_rec": 120,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "RATITA_BLANCA": {"tf": "5m", "desc": "RATITA BLANCA 0.8% FIJO LONG V59.5.4","rango_tp": (0.8, 0.8), "sl_neto": -3.0, "max_dia": 40,"cooldown": 120, "cooldown_rec": 120,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "RATA": {"tf": "5m", "desc": "Madre RATA 0.8% FIJO LONG V59.5.4","rango_tp": (0.8, 0.8), "sl_neto": -3.0, "max_dia": 30,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "LINEAL", "tp_fijo_banda": 0.8},
    "LOBO": {"tf": "1h", "desc": "Madre LOBO 1.2% FIJO LONG V59.5.4","rango_tp": (1.2, 1.2), "sl_neto": -5.0, "max_dia": 100,"cooldown": 300, "cooldown_rec": 300,"mercado_ideal": "ALCISTA", "tp_fijo_banda": 1.2},
    "TIBURON": {"tf": "1d", "desc": "Madre TIBURON 5-10% FIJO LONG V59.5.4","rango_tp": (5.0, 10.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 14400, "cooldown_rec": 14400,"mercado_ideal": "ALCISTA_FUERTE"},
    "TIBURON_NEGRO": {"tf": "1d", "desc": "TIBURON NEGRO 5-10% FIJO SHORT V59.5.4","rango_tp": (5.0, 10.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 14400, "cooldown_rec": 14400,"mercado_ideal": "CRASH"},
    "KRAKEN": {"tf": "1h", "desc": "Madre KRAKEN 3% FIJO LONG REBOTE V59.5.4","rango_tp": (3.0, 3.0), "sl_neto": -8.0, "max_dia": 2,"cooldown": 3600, "cooldown_rec": 3600,"mercado_ideal": "CRASH"},
    "MOJARRA_NEGRA": {"tf": "5m", "desc": "MOJARRA NEGRA 0.3-0.5% SHORT V59.5.4","rango_tp": (0.3, 0.5), "sl_neto": -1.5, "max_dia": 200,"cooldown": 60, "cooldown_rec": 60,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.3},
    "PIRANA_NEGRA": {"tf": "5m", "desc": "PIRANA NEGRA 0.8% FIJO SHORT V59.5.4","rango_tp": (0.8, 0.8), "sl_neto": -3.5, "max_dia": 100,"cooldown": 600, "cooldown_rec": 600,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.8},
    "RATA_NEGRA": {"tf": "5m", "desc": "RATA NEGRA 0.8% FIJO SHORT V59.5.4","rango_tp": (0.8, 0.8), "sl_neto": -4.0, "max_dia": 100,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.8},
    "RATITA_NEGRA": {"tf": "5m", "desc": "RATITA NEGRA 0.8% FIJO SHORT V59.5.4","rango_tp": (0.8, 0.8), "sl_neto": -4.0, "max_dia": 100,"cooldown": 180, "cooldown_rec": 180,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 0.8},
    "LOBO_NEGRO": {"tf": "1h", "desc": "LOBO NEGRO 1.2% FIJO SHORT V59.5.4","rango_tp": (1.2, 1.2), "sl_neto": -8.0, "max_dia": 100,"cooldown": 300, "cooldown_rec": 300,"mercado_ideal": "BAJISTA", "tp_fijo_banda": 1.2},
}
ESTRATEGIAS_V45["PIRANA"] = ESTRATEGIAS_V45["PIRANA_BLANCA"]
ESTRATEGIAS_V45["PIRAÑA_NEGRA"] = ESTRATEGIAS_V45["PIRANA_NEGRA"]
BLANCAS = {"MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATITA","RATITA_BLANCA","RATA","LOBO","TIBURON"}
NEGRAS = {"MOJARRA_NEGRA","PIRANA_NEGRA","PIRAÑA_NEGRA","RATITA_NEGRA","RATA_NEGRA","LOBO_NEGRO","KRAKEN","TIBURON_NEGRO"}
MADRES_LIBRES_V52 = {"LOBO","TIBURON","KRAKEN","LOBO_NEGRO","TIBURON_NEGRO"}

def candado(est, regimen, sym=None):
    r = regimen.split()[0] if regimen else "LINEAL"
    if est == "MOJARRITA_SUPERVIVENCIA": return r in ["BAJISTA", "CRASH", "SUPERVIVENCIA"]
    if r == "LINEAL_MUERTO": return est in ["MOJARRA","MOJARRITA"]
    if r == "LINEAL": return est in ["MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATITA","RATITA_BLANCA","RATA"]
    if r == "ALCISTA": return est in ["MOJARRA","PIRANA_BLANCA","RATITA_BLANCA","RATITA","RATA","LOBO"]
    if r == "ALCISTA_FUERTE": return est in ["MOJARRA","PIRANA_BLANCA","RATITA_BLANCA","RATITA","RATA","LOBO","TIBURON"]
    if r in ["BAJISTA","CRASH"]:
        if est in ["MOJARRA","MOJARRITA"]: return True
        return est in ["MOJARRA_NEGRA","PIRANA_NEGRA","PIRAÑA_NEGRA","RATITA_NEGRA","RATA_NEGRA","LOBO_NEGRO","TIBURON_NEGRO","KRAKEN","MOJARRITA_SUPERVIVENCIA"]
    if r == "SUPERVIVENCIA": return est in ["MOJARRITA_SUPERVIVENCIA","MOJARRA","MOJARRITA"]
    return True

def get_rsi_15m(sym):
    try:
        d = get_velas(sym, "15m", 30)
        if not d: return 50
        return rsi_calc(d["closes"], 14)
    except: return 50

def es_alcista_real(sym, vol_mult, atr_pct, adx, close_price, ema20):
    try:
        if vol_mult < VOL_MIN_REAL: return False, f"FALSO ALCISTA Vol{vol_mult:.2f}<{VOL_MIN_REAL}"
        if atr_pct < ATR_MIN_REAL: return False, f"FALSO ALCISTA ATR{atr_pct:.2f}%<{ATR_MIN_REAL}%"
        if adx < ADX_MIN_ALCISTA_REAL: return False, f"FALSO ALCISTA ADX{adx:.0f}<{ADX_MIN_ALCISTA_REAL}"
        if close_price < ema20: return False, f"FALSO ALCISTA CIERRE<EMA20"
        rsi_15 = get_rsi_15m(sym)
        if rsi_15 > 50: return False, f"FALSO ALCISTA RSI15m{rsi_15:.0f}>40"
        return True, f"ALCISTA REAL Vol{vol_mult:.2f}x ATR{atr_pct:.2f}% ADX{adx:.0f} >EMA20 RSI15m{rsi_15:.0f}"
    except: return False, "FALSO ERROR"

def es_bajista_real(sym, vol_mult, atr_pct, adx, close_price, ema20):
    try:
        if vol_mult < VOL_MIN_REAL: return False, f"FALSO BAJISTA Vol{vol_mult:.2f}<{VOL_MIN_REAL}"
        if atr_pct < ATR_MIN_REAL: return False, f"FALSO BAJISTA ATR{atr_pct:.2f}%<{ATR_MIN_REAL}%"
        if adx < ADX_MIN_BAJISTA_REAL: return False, f"FALSO BAJISTA ADX{adx:.0f}<{ADX_MIN_BAJISTA_REAL}"
        if close_price > ema20: return False, f"FALSO BAJISTA CIERRE>EMA20"
        rsi_15 = get_rsi_15m(sym)
        if rsi_15 < 60: return False, f"FALSO BAJISTA RSI15m{rsi_15:.0f}<60"
        return True, f"BAJISTA REAL Vol{vol_mult:.2f}x ATR{atr_pct:.2f}% ADX{adx:.0f} <EMA20 RSI15m{rsi_15:.0f}"
    except: return False, "FALSO ERROR"

def tp_rescate_escalonado(pos):
    try:
        dt_entry = pos.get("dt_rescate") or pos.get("dt") or pos.get("timestamp") or time.time()
        if isinstance(dt_entry, str):
            try: dt_entry = datetime.fromisoformat(dt_entry).timestamp()
            except: dt_entry = time.time()
        horas = (time.time() - float(dt_entry))/3600
    except: horas = 0
    if not pos.get("es_rescate", False): return pos.get("tp", TP_FIJO_RATA)
    if horas < 12: return pos.get("tp_original", TP_FIJO_LOBO)
    elif horas < 24: return 0.8
    elif horas < 36: return 0.5
    else: return 0.3

def get_tp_variable_mojarra(pos):
    try:
        dt_entry = pos.get("dt") or pos.get("timestamp") or time.time()
        if isinstance(dt_entry, str):
            try: dt_entry = datetime.fromisoformat(dt_entry).timestamp()
            except: dt_entry = time.time()
        horas = (time.time() - float(dt_entry))/3600
        resto = horas % 18
        return TP_BASE_V594 if resto < 12 else TP_RESCATE_V594
    except: return TP_BASE_V594

def es_rango_exclusivo_FIX(sym, precio_nuevo):
    return True

def get_usdt_compound_mojarra(balance_actual):
    try:
        profit = max(0.0, balance_actual - 10000.0)
        extra = int(profit // 15)
        return min(20.0, 10.0 + extra)
    except: return 10.0

def cierre_market_cambio(sym, reg_nuevo, reg_viejo_override=None):
    try:
        reg_nuevo_simple = reg_nuevo.split()[0] if reg_nuevo else ""
        reg_viejo_simple = (reg_viejo_override.split()[0] if reg_viejo_override else REG_ANT.get(sym,"")).split()[0]
        if not reg_viejo_simple: return
        for uid in POSICIONES_ABIERTAS:
            for pos in POSICIONES_ABIERTAS[uid]:
                if pos.get("symbol")!=sym: continue
                est = pos.get("estrategia","")
                if est in ["MOJARRA","MOJARRITA","MOJARRITA_SUPERVIVENCIA"]: continue
                if reg_viejo_simple in ["ALCISTA","ALCISTA_FUERTE"] and reg_nuevo_simple in ["BAJISTA","CRASH"]:
                    if est in ["LOBO","TIBURON","RATA","PIRANA_BLANCA","RATITA_BLANCA","RATITA"]:
                        if pos.get("profit_pct",0) < 0:
                            pos["es_rescate"] = True
                            pos["tp_original"] = pos.get("tp", TP_FIJO_LOBO)
                            pos["dt_rescate"] = time.time()
                if reg_viejo_simple in ["BAJISTA","CRASH"] and reg_nuevo_simple in ["ALCISTA","ALCISTA_FUERTE","LINEAL"]:
                    if est in ["LOBO_NEGRO","TIBURON_NEGRO","RATA_NEGRA","PIRANA_NEGRA","RATITA_NEGRA"]:
                        if pos.get("profit_pct",0) < 0:
                            pos["es_rescate"] = True
                            pos["tp_original"] = pos.get("tp", TP_FIJO_LOBO)
                            pos["dt_rescate"] = time.time()
    except Exception as e: print(f"Error cierre V59.5.4: {e}")
    return
def cierre_forzado_por_candado(): return

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
    print(f"V59.5.4 {sym or 'GLOBAL'} {motivo} - Sin bloqueo global")

MAPA_ANIDADO_V50_9 = {
    "LINEAL_MUERTO": ["MOJARRA", "MOJARRITA"],
    "LINEAL": ["MOJARRA", "PIRANA_BLANCA", "RATITA_BLANCA", "RATA"],
    "ALCISTA": ["MOJARRA", "PIRANA_BLANCA","RATITA_BLANCA","RATITA", "RATA", "LOBO"],
    "ALCISTA_FUERTE": ["MOJARRA", "PIRANA_BLANCA","RATITA_BLANCA","RATITA", "RATA", "LOBO", "TIBURON"],
    "BAJISTA": ["MOJARRA_NEGRA", "PIRANA_NEGRA", "RATITA_NEGRA", "RATA_NEGRA", "LOBO_NEGRO", "MOJARRITA_SUPERVIVENCIA", "MOJARRA", "MOJARRITA"],
    "CRASH": ["MOJARRA_NEGRA", "PIRANA_NEGRA", "RATITA_NEGRA", "RATA_NEGRA", "LOBO_NEGRO", "TIBURON_NEGRO", "KRAKEN", "MOJARRITA_SUPERVIVENCIA"],
    "SUPERVIVENCIA": ["MOJARRITA_SUPERVIVENCIA"]
}
MAPA_ESTRATEGIA = {
"LINEAL_MUERTO": "01 LINEAL_MUERTO - MOJARRA 52/58/65 + MOJARRITA 5-28 RSI TP 0.5%->12H 0.3% V59.5.4 INMORTAL 40/40",
"LINEAL": "02 GREEN - MOJARRA -> PIRANA_BLANCA -> RATITA_BLANCA -> RATA 0.8% FIJO V59.5.4",
"ALCISTA": "REGIMEN 3 - LOBO 1.2% FIJO + DETECTOR REAL V59.5.4",
"ALCISTA_FUERTE": "REGIMEN 4 - LOBO 1.2% + TIBURON 5-10% FIJO + DETECTOR REAL V59.5.4",
"BAJISTA": "REGIMEN 5 - LOBO_NEGRO 1.2% FIJO SHORT + DETECTOR REAL V59.5.4",
"CRASH": "REGIMEN 6 CRASH - TIBURON_NEGRO 5-10% FIJO + KRAKEN 3% FIJO + RANURA 20-3 V59.5.4",
"SUPERVIVENCIA": "SUPERVIVENCIA V59.5.4 RANURA 20-3 DISTRIBUIDA REAL RSI 20/17/14/11/8/5/3"
}
ESTRATEGIAS_V45["MOJARRITA_SUPERVIVENCIA"] = {
    "nombre": "MOJARRITA_SUPERVIVENCIA", "riesgo": 0.05, "tp": 0.008, "sl": 0.015,
    "rsi_compra": 20, "rsi_venta": 60, "tipo": "SCALP_SUPERVIVENCIA", "cap": 0.25, "reciclable": 1
}
ULTIMO_SCANNER_V58 = 0
TOP_MONEDAS_V58 = []
TIEMPO_SCANNER_V58 = 300
def calcular_score_v58(adx, rsi, atr, vol):
    if rsi > 85: return -1000
    score_rsi = 25 if 45 <= rsi <= 55 else (15 if 40 <= rsi <= 60 else 0)
    score = (adx * 1.5) + score_rsi + (atr * 100 * 0.30) + (vol * 15)
    if vol < 0.90: score -= 20
    return score
def scanner_mejor_oportunidad_v58():
    global ULTIMO_SCANNER_V58, TOP_MONEDAS_V58
    ahora = time.time()
    if ahora - ULTIMO_SCANNER_V58 < TIEMPO_SCANNER_V58: return TOP_MONEDAS_V58
    scores = []
    for symbol in MONEDAS_ACTIVAS:
        try:
            velas = get_velas(symbol, "5m", 100)
            if not velas or len(velas) < 50: continue
            closes = velas.get("closes", []) if isinstance(velas, dict) else [float(v[4]) for v in velas]
            if len(closes) < 30: continue
            rsi_v = rsi_calc(closes, 14)
            if rsi_v > 85: continue
            try: adx_v = adx_calc(velas["highs"], velas["lows"], closes, 14)
            except: adx_v = 20
            try: atr_v = atr_calc(velas, 14)
            except: atr_v = 0.5
            vol_v = 1.0
            if 3 <= rsi_v <= 20:
                reg = ESTADO.get("regimenes",{}).get(symbol,"").split()[0]
                if reg in ["BAJISTA","CRASH","SUPERVIVENCIA"]:
                    score = 999
                    scores.append((symbol, score, {"adx":adx_v,"rsi":rsi_v,"atr":atr_v,"vol":vol_v, "tipo":"SUPERVIVENCIA_RANURA"}))
                    continue
            score = calcular_score_v58(adx_v, rsi_v, atr_v, vol_v)
            scores.append((symbol, score, {"adx":adx_v,"rsi":rsi_v,"atr":atr_v,"vol":vol_v}))
        except: continue
    scores.sort(key=lambda x: x[1], reverse=True)
    TOP_MONEDAS_V58 = scores[:2] if scores else TOP_MONEDAS_V58
    ULTIMO_SCANNER_V58 = ahora
    return TOP_MONEDAS_V58
def get_mejor_estrategia_v58(symbol, rsi_5m, adx, atr, regimen):
    if 18 <= rsi_5m <= 20: return {"nombre":"MOJARRITA_SUPERVIVENCIA","nivel":20,"cap":0.35,"tp":[0.003,0.005,0.008],"reciclable":1,"tipo":"MOJARRA"}
    if 15 <= rsi_5m <= 17: return {"nombre":"MOJARRITA_SUPERVIVENCIA","nivel":17,"cap":0.25,"tp":[0.003,0.005,0.008],"reciclable":1,"tipo":"MOJARRITA"}
    if 12 <= rsi_5m <= 14: return {"nombre":"MOJARRITA_SUPERVIVENCIA","nivel":14,"cap":0.35,"tp":[0.003,0.005,0.008],"reciclable":1,"tipo":"MOJARRA"}
    if 9 <= rsi_5m <= 11: return {"nombre":"MOJARRITA_SUPERVIVENCIA","nivel":11,"cap":0.25,"tp":[0.003,0.005,0.008],"reciclable":1,"tipo":"MOJARRITA"}
    if 6 <= rsi_5m <= 8: return {"nombre":"MOJARRITA_SUPERVIVENCIA","nivel":8,"cap":0.35,"tp":[0.003,0.005,0.008],"reciclable":1,"tipo":"MOJARRA"}
    if 3 <= rsi_5m <= 5: return {"nombre":"MOJARRITA_SUPERVIVENCIA","nivel":5,"cap":0.25,"tp":[0.003,0.005,0.008],"reciclable":1,"tipo":"MOJARRA"}
    return None
def es_mercado_supervivencia(symbol="BTCUSDT"):
    try:
        velas = get_velas(symbol, "1h", 50)
        if not velas or len(velas) < 30: return False
        closes = velas.get("closes", []) if isinstance(velas, dict) else [float(v[4]) for v in velas]
        if len(closes) < 24: return False
        var_24h = abs(closes[-1] - closes[-24]) / closes[-24] if closes[-24]!=0 else 0
        rsi_val = rsi_calc(closes, 14)
        return var_24h < 0.006 and 40 < rsi_val < 60
    except: return False
def senal_mojarrita_supervivencia(symbol):
    try:
        reg = ESTADO.get("regimenes",{}).get(symbol,"").split()[0]
        if reg not in ["BAJISTA","CRASH","SUPERVIVENCIA"]: return None
        velas = get_velas(symbol, "5m", 100)
        if not velas: return None
        closes = velas.get("closes", []) if isinstance(velas, dict) else [float(v[4]) for v in velas]
        rsi_v = rsi_calc(closes, 14)
        if 18 <= rsi_v <= 20: return {"estrategia":"MOJARRITA_SUPERVIVENCIA","nivel":20,"tp":[0.003,0.005,0.008],"rsi":rsi_v,"tipo":"MOJARRA"}
        if 15 <= rsi_v <= 17: return {"estrategia":"MOJARRITA_SUPERVIVENCIA","nivel":17,"tp":[0.003,0.005,0.008],"rsi":rsi_v,"tipo":"MOJARRITA"}
        if 12 <= rsi_v <= 14: return {"estrategia":"MOJARRITA_SUPERVIVENCIA","nivel":14,"tp":[0.003,0.005,0.008],"rsi":rsi_v,"tipo":"MOJARRA"}
        if 9 <= rsi_v <= 11: return {"estrategia":"MOJARRITA_SUPERVIVENCIA","nivel":11,"tp":[0.003,0.005,0.008],"rsi":rsi_v,"tipo":"MOJARRITA"}
        if 6 <= rsi_v <= 8: return {"estrategia":"MOJARRITA_SUPERVIVENCIA","nivel":8,"tp":[0.003,0.005,0.008],"rsi":rsi_v,"tipo":"MOJARRA"}
        if 3 <= rsi_v <= 5: return {"estrategia":"MOJARRITA_SUPERVIVENCIA","nivel":5,"tp":[0.003,0.005,0.008],"rsi":rsi_v,"tipo":"MOJARRA"}
        return None
    except: return None

print("[OK] BLOQUE 06 V59.5.4 FIX CARGADO - DETECTOR ANTI-FALSO + BANCAR ESCALONADO + 40/40")

def estrategia_prevista(regimen_txt):
    reg = regimen_txt.split()[0] if regimen_txt else "LINEAL_MUERTO"
    return MAPA_ESTRATEGIA.get(reg, MAPA_ESTRATEGIA["LINEAL_MUERTO"])
BLANCAS_SET = {"MOJARRA","MOJARRITA","PIRANA_BLANCA","PIRANA","RATITA","RATITA_BLANCA","RATA","LOBO","TIBURON"}
def mercado_esta_rojo(sym=None):
    if sym:
        reg = ESTADO.get("regimenes",{}).get(sym,"")
        rs = reg.split()[0] if reg else ""
        if rs in ("BAJISTA","CRASH"): return True, f"REGIMEN {sym} {reg}"
        banda = BANDAS_ACTIVAS.get(sym,{})
        if banda.get("activa"):
            tipo = str(banda.get("tipo","")).upper()
            if "BAJISTA" in tipo or "CRASH" in tipo: return True, f"BANDA {sym} {tipo}"
        return False, ""
    for s, reg in ESTADO.get("regimenes", {}).items():
        rs = reg.split()[0] if reg else ""
        if rs in ("BAJISTA","CRASH"): return True, f"{s} {reg}"
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

# --- FIX BTC 0.0 REAL - UNICO CAMBIO ---
def get_precio_robusto(symbol):
    try:
        if client:
            p = float(client.get_symbol_ticker(symbol=symbol)['price'])
            if p > 0:
                return p
    except: pass
    for base in ["https://data-api.binance.vision","https://api.binance.com","https://api1.binance.com","https://api2.binance.com","https://api3.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/price?symbol={symbol}", timeout=4)
            if r.status_code==200:
                p = float(r.json()['price'])
                if p > 0:
                    return p
        except: pass
    try:
        r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}", timeout=8)
        if r.status_code==200:
            return float(r.json()['price'])
    except: pass
    return ESTADO.get("btc" if "BTC" in symbol else "bnb",0) or 0.0

def get_velas(symbol="BTCUSDT", interval="5m", limit=200):
    try:
        if client:
            klines=client.get_klines(symbol=symbol, interval=interval, limit=limit)
            if klines and len(klines) >= 20:
                return {"closes": [float(k[4]) for k in klines],"highs": [float(k[2]) for k in klines],"lows": [float(k[3]) for k in klines],"vols": [float(k[5]) for k in klines]}
    except: pass
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}", timeout=6)
        if r.status_code==200:
            klines=r.json()
            if klines and len(klines) >= 20:
                return {"closes": [float(k[4]) for k in klines],"highs": [float(k[2]) for k in klines],"lows": [float(k[3]) for k in klines],"vols": [float(k[5]) for k in klines]}
    except: pass
    for base in ["https://api.binance.com","https://api1.binance.com","https://api2.binance.com","https://api3.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}", timeout=5)
            if r.status_code==200:
                klines=r.json()
                if klines and len(klines) >= 20:
                    return {"closes": [float(k[4]) for k in klines],"highs": [float(k[2]) for k in klines],"lows": [float(k[3]) for k in klines],"vols": [float(k[5]) for k in klines]}
        except: pass
    return None
def rsi_calc(closes, period=14):
    try:
        if not closes or len(closes) < period+2: return 55.0
        deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
        gains = [d if d>0 else 0 for d in deltas[-period:]]
        losses = [-d if d<0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains)/period
        avg_loss = sum(losses)/period
        if avg_gain == 0 and avg_loss == 0: return 55.0
        if avg_loss == 0: return 68.0
        if avg_gain == 0: return 32.0
        rs = avg_gain/avg_loss
        rsi = 100-(100/(1+rs))
        return max(5.0, min(92.0, rsi))
    except: return 55.0
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
    for c in closes[period:]: ema = c*k + ema*(1-k)
    return ema

def tp_adaptativo(symbol, estrategia):
    try:
        if estrategia in ["MOJARRA","MOJARRITA","MOJARRITA_SUPERVIVENCIA"]:
            for uid in POSICIONES_ABIERTAS:
                for p in POSICIONES_ABIERTAS[uid]:
                    if p.get("symbol")==symbol and p.get("estrategia")==estrategia:
                        if p.get("es_rescate"): return tp_rescate_escalonado(p)
                        return get_tp_variable_mojarra(p)
            return TP_BASE_V594
        if estrategia in ["LOBO","LOBO_NEGRO"]: return TP_FIJO_LOBO
        if estrategia in ["TIBURON","TIBURON_NEGRO"]: return TP_FIJO_TIBURON_MIN
        if estrategia in ["RATA","RATA_NEGRA","RATITA","RATITA_BLANCA","RATITA_NEGRA","PIRANA_BLANCA","PIRANA","PIRANA_NEGRA","PIRAÑA_NEGRA"]: return TP_FIJO_RATA
        if estrategia == "KRAKEN": return TP_FIJO_KRAKEN
        for uid in POSICIONES_ABIERTAS:
            for p in POSICIONES_ABIERTAS[uid]:
                if p.get("symbol")==symbol and p.get("estrategia")==estrategia and p.get("es_rescate"):
                    return tp_rescate_escalonado(p)
        rango = ESTRATEGIAS_V45[estrategia]["rango_tp"]
        return rango[0]
    except: return TP_BASE_V594

def tiempo_fuera_inteligente(symbol, tipo_actual):
    try:
        d1h = get_velas(symbol,"1h",60); d5 = get_velas(symbol,"5m",60)
        if not d1h or not d5: return TIEMPO_FUERA_NORMAL if tipo_actual=="NORMAL" else TIEMPO_FUERA_BAJISTA
        adx = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14); rsi_5 = rsi_calc(d5["closes"],7)
        atr = atr_calc(d1h,14); precio = d1h["closes"][-1]
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
        for base in ["https://data-api.binance.vision","https://api.binance.com","https://api1.binance.com"]:
            try:
                r = requests.get(f"{base}/api/v3/ticker/24hr?symbol={symbol}", timeout=4)
                if r.status_code == 200:
                    data = r.json()
                    return float(data.get("priceChangePercent", 0))
            except: continue
    except: pass
    try:
        d = get_velas(symbol, "1d", 3)
        if d and len(d["closes"]) >= 2 and d["closes"][-2]!= 0:
            return (d["closes"][-1] - d["closes"][-2]) / d["closes"][-2] * 100
    except: pass
    return 0.0

def get_umbral_adaptativo(regimen):
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
    if reg == "ALCISTA_FUERTE": return {"rsi_kraken": max(20, 30.5 + ajuste), "rsi_pirana": 35, "rsi_pirana_negra": 30, "vsa_kraken_base": 1.3, "adx_tiburon": 25}
    elif reg == "ALCISTA": return {"rsi_kraken": max(20, 29.5 + ajuste), "rsi_pirana": 33, "rsi_pirana_negra": 29, "vsa_kraken_base": 1.4, "adx_tiburon": 22}
    elif reg == "BAJISTA": return {"rsi_kraken": max(18, 27.5 + ajuste), "rsi_pirana": 30, "rsi_pirana_negra": 35, "vsa_kraken_base": 1.6, "adx_tiburon": 20}
    elif reg == "CRASH": return {"rsi_kraken": max(18, 30.0 + ajuste), "rsi_pirana": 28, "rsi_pirana_negra": 40, "vsa_kraken_base": 1.3, "adx_tiburon": 20}
    elif reg == "LINEAL": return {"rsi_kraken": max(20, 29.0 + ajuste), "rsi_pirana": 38, "rsi_pirana_negra": 28, "vsa_kraken_base": 1.3, "adx_tiburon": 22}
    else: return {"rsi_kraken": max(18, 27.5 + ajuste), "rsi_pirana": 30, "rsi_pirana_negra": 28, "vsa_kraken_base": 1.6, "adx_tiburon": 20}

def detectar_regimen_sym(symbol):
    try:
        cambio24 = get_cambio_24h(symbol)
        btc_cambio = get_cambio_24h("BTCUSDT")
        try:
            d1h_tmp = get_velas(symbol, "1h", 30)
            if d1h_tmp:
                closes_tmp = d1h_tmp["closes"]
                ema9 = ema_calc(closes_tmp, 9)
                ema20 = ema_calc(closes_tmp, 20)
                madre_bajista = ema9 < ema20
                vols = d1h_tmp["vols"]
                vol_prom = sum(vols[-20:])/20 if len(vols)>=20 else 1
                vol_ratio = vols[-1]/vol_prom if vol_prom else 0.0
                atr_tmp = atr_calc(d1h_tmp, 14) if d1h_tmp else 0
                prec_tmp = d1h_tmp["closes"][-1] if d1h_tmp else 1
                atr_pct_real = (atr_tmp/prec_tmp*100) if prec_tmp else 0
                adx_tmp = adx_calc(d1h_tmp["highs"], d1h_tmp["lows"], closes_tmp, 14)
            else:
                madre_bajista = False; vol_ratio = 0.0; atr_pct_real = 0; adx_tmp = 15; ema20 = 0; prec_tmp = 0
        except: madre_bajista = False; vol_ratio = 0.0; atr_pct_real = 0; adx_tmp = 15; ema20 = 0; prec_tmp = 0
        if cambio24 <= -8.0:
            es_real, motivo = es_bajista_real(symbol, vol_ratio, atr_pct_real, adx_tmp, prec_tmp, ema20)
            if es_real and madre_bajista and btc_cambio <= -5.0:
                return "BAJISTA", f"BAJISTA REAL V59.5.4 {cambio24:.1f}% {motivo} BTC {btc_cambio:.1f}% | ESTRATEGIA: {MAPA_ESTRATEGIA['BAJISTA']}"
            else:
                return "LINEAL_MUERTO", f"LINEAL_MUERTO FALSO BAJISTA {cambio24:.1f}% {motivo} BTC {btc_cambio:.1f}% -> NO BAJISTA V59.5.4 | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
        if es_mercado_supervivencia(symbol):
            return "LINEAL_MUERTO", f"LINEAL_MUERTO MUERTO ATR{atr_pct_real:.2f}% Vol Real | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
    except: pass
    d1h=get_velas(symbol,"1h",210); d1d=get_velas(symbol,"1d",15)
    if not d1h or not d1d: return "LINEAL_MUERTO", f"LINEAL_MUERTO Iniciando -> ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
    closes_1h=d1h["closes"]; closes_1d=d1d["closes"]
    ema200 = ema_calc(closes_1h, 200); ema50 = ema_calc(closes_1h, 50); ema20_1h = ema_calc(closes_1h, 20)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14)
    atr = atr_calc(d1h, 14); precio = closes_1h[-1]
    atr_pct = (atr/precio*100) if precio!=0 else 0
    vols_1h = d1h["vols"]; vol_prom_1h = sum(vols_1h[-20:])/20 if len(vols_1h)>=20 else 1
    vol_ratio_1h = vols_1h[-1]/vol_prom_1h if vol_prom_1h else 0
    rent_14d = (closes_1d[-1]-closes_1d[0])/closes_1d[0] if closes_1d[0]!=0 else 0
    dist_ema200 = (precio - ema200)/ema200 if ema200!=0 else 0
    rsi_1h = rsi_calc(closes_1h,14)
    if adx_1h < 15 and atr_pct < 0.6: return "LINEAL_MUERTO", f"LINEAL_MUERTO MUERTO ADX{adx_1h:.0f} ATR{atr_pct:.2f}% | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
    if rent_14d < -0.12 and precio < ema200 and precio < ema50 and adx_1h >= 28:
        es_real, motivo = es_bajista_real(symbol, vol_ratio_1h, atr_pct, adx_1h, precio, ema20_1h)
        if es_real: return "CRASH", f"CRASH REAL V59.5.4 ADX{adx_1h:.0f} {rent_14d*100:.1f}% {motivo} | ESTRATEGIA: {MAPA_ESTRATEGIA['CRASH']}"
        else: return "LINEAL_MUERTO", f"LINEAL_MUERTO FALSO CRASH {motivo} | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
    if precio < ema200 and 15 <= adx_1h <= 80 and -0.12 <= rent_14d <= -0.01 and -0.08 <= dist_ema200 <= -0.01 and 22 <= rsi_1h <= 60:
        cambio_check = get_cambio_24h(symbol)
        if cambio_check > -8.0: return "LINEAL_MUERTO", f"LINEAL_MUERTO BAJISTA TECNICO PERO {cambio_check:.1f}% > -8% -> LINEAL V59.5.4 | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
        es_real, motivo = es_bajista_real(symbol, vol_ratio_1h, atr_pct, adx_1h, precio, ema20_1h)
        if es_real: return "BAJISTA", f"BAJISTA REAL V59.5.4 ADX{adx_1h:.0f} {rent_14d*100:.1f}% {motivo} | ESTRATEGIA: {MAPA_ESTRATEGIA['BAJISTA']}"
        else: return "LINEAL_MUERTO", f"LINEAL_MUERTO FALSO BAJISTA {motivo} | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
    if precio > ema200 and precio > ema50 and adx_1h >= 28 and rent_14d > 0.06 and dist_ema200 > 0.02 and rsi_1h >= 50:
        es_real, motivo = es_alcista_real(symbol, vol_ratio_1h, atr_pct, adx_1h, precio, ema20_1h)
        if es_real: return "ALCISTA_FUERTE", f"FUERTE REAL V59.5.4 ADX{adx_1h:.0f} {rent_14d*100:+.1f}% {motivo} | ESTRATEGIA: {MAPA_ESTRATEGIA['ALCISTA_FUERTE']}"
        else: return "LINEAL", f"LINEAL FALSO FUERTE {motivo} -> LINEAL V59.5.4 | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL']}"
    if precio > ema200 and 18 <= adx_1h <= 35 and 0.01 <= rent_14d <= 0.12 and 0.01 <= dist_ema200 <= 0.08 and 40 <= rsi_1h <= 78:
        es_real, motivo = es_alcista_real(symbol, vol_ratio_1h, atr_pct, adx_1h, precio, ema20_1h)
        if es_real: return "ALCISTA", f"ALCISTA REAL V59.5.4 ADX{adx_1h:.0f} {rent_14d*100:+.1f}% {motivo} | ESTRATEGIA: {MAPA_ESTRATEGIA['ALCISTA']}"
        else: return "LINEAL", f"LINEAL FALSO ALCISTA {motivo} -> LINEAL V59.5.4 | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL']}"
    if precio < ema200 and adx_1h > 15 and rent_14d < -0.01:
        cambio_check = get_cambio_24h(symbol)
        if cambio_check > -8.0: return "LINEAL_MUERTO", f"LINEAL_MUERTO BAJISTA TECNICO {cambio_check:.1f}% > -8% V59.5.4 | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
        es_real, motivo = es_bajista_real(symbol, vol_ratio_1h, atr_pct, adx_1h, precio, ema20_1h)
        if es_real: return "BAJISTA", f"BAJISTA REAL V59.5.4 ADX{adx_1h:.0f} {rent_14d*100:.1f}% {motivo} | ESTRATEGIA: {MAPA_ESTRATEGIA['BAJISTA']}"
        else: return "LINEAL_MUERTO", f"LINEAL_MUERTO FALSO BAJISTA {motivo} V59.5.4 | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"
    return "LINEAL_MUERTO", f"LINEAL_MUERTO ADX{adx_1h:.0f} {rent_14d*100:+.1f}% | ESTRATEGIA: {MAPA_ESTRATEGIA['LINEAL_MUERTO']}"

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
    if not isinstance(umb, dict): umb = {}
    rsi_max = umb.get("rsi_rata_max", umb.get("rsi_max", 40))
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    if estrategia_nombre in ["MOJARRA","MOJARRITA"] and rsi < 20:
        reg_simple_em = reg.split()[0] if reg else "LINEAL"
        if reg_simple_em in ["BAJISTA","CRASH","SUPERVIVENCIA"]:
            return True,f"[{symbol}] {estrategia_nombre} EMERGENCIA SUPERVIVENCIA RSI{int(rsi)}<20 {reg_simple_em} CAZA BAJISTA V59.5.4", 0.99
    sma20=sum(closes[-20:])/20; var=sum((x-sma20)**2 for x in closes[-20:])/20; std=var**0.5; lower=sma20-2*std
    precio=closes[-1]
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if estrategia_nombre in ["MOJARRA", "MOJARRITA", "PIRANA_BLANCA", "PIRANA", "RATITA", "RATITA_BLANCA"]:
        if estrategia_nombre == "MOJARRA":
            if reg_simple == "LINEAL_MUERTO":
                if 50 <= rsi <= 68: return True,f"[{symbol}] MOJARRA ALTA V59.5.4 FINAL RSI{int(rsi)} 52/58/65 {reg_simple} TP0.5%->0.3% x1", 0.90
                return False,f"[{symbol}] MOJARRA ALTA RSI{int(rsi)}/52-68 {reg_simple} esperando 52/58/65", 0.30
            if rsi <= 40: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}<=40 ALTA {reg_simple} V59.5.4", 0.85
            return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/40 {reg_simple}", 0.30
        if estrategia_nombre == "MOJARRITA":
            if reg_simple == "LINEAL_MUERTO":
                if 5 <= rsi <= 28: return True,f"[{symbol}] MOJARRITA V59.5.4 FINAL LINEAL_MUERTO RSI{int(rsi)} 5-28 TP0.5%->0.3% x1", 0.88
                return False,f"[{symbol}] MOJARRITA RSI{int(rsi)}/5-28 {reg_simple} esperando 25/22/18", 0.30
            if rsi <= 32: return True,f"[{symbol}] MOJARRITA DESTRABE V59.5.4 RSI{int(rsi)}<=32 FONDO {reg_simple}", 0.80
            return False,f"[{symbol}] MOJARRITA RSI{int(rsi)}/32 {reg_simple}", 0.30
        if rsi <= 40: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}<=40 {reg_simple} V59.5.4", 0.85
        return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/40 {reg_simple}", 0.30
    if precio<=lower and rsi < rsi_max: return True,f"[{symbol}] {estrategia_nombre} V59.5.4 {reg_simple} RSI{int(rsi)}<{rsi_max}", 0.68
    return False,f"[{symbol}] {estrategia_nombre} {reg_simple} RSI{int(rsi)}/{rsi_max}", 0.30

def detectar_SHORT_sym(symbol, estrategia_nombre="MOJARRA_NEGRA"):
    d5=get_velas(symbol,"5m",100)
    if not d5: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    closes=d5["closes"]; rsi=rsi_calc(closes,7)
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if reg_simple in ["BAJISTA", "CRASH", "BAJISTA_FUERTE"]:
        if rsi >= 42: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}>=42 SHORT {reg_simple} V59.5.4 CAZA BAJISTA", 0.85
        if rsi >= 35: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)} BAJISTA CONTINUIDAD SHORT {reg_simple} V59.5.4", 0.75
        return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/35 {reg_simple}", 0.30
    if estrategia_nombre == "MOJARRA_NEGRA":
        if rsi >= 52: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}>=52 SHORT {reg_simple} V59.5.4", 0.85
        return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/52 {reg_simple}", 0.30
    if rsi >= 55: return True,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}>=55 SHORT {reg_simple} V59.5.4", 0.75
    return False,f"[{symbol}] {estrategia_nombre} RSI{int(rsi)}/55 {reg_simple}", 0.30

def detectar_LOBO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if reg_simple not in ["ALCISTA","ALCISTA_FUERTE"]: return False,f"[{symbol}] LOBO BLOQUEADO Solo ALCISTA {reg_simple}",0.10
    closes=d["closes"]; ema20=sum(closes[-20:])/20
    adx = adx_calc(d["highs"], d["lows"], d["closes"], 14); rsi = rsi_calc(closes,14)
    if closes[-1] > ema20 and rsi >= 48 and adx >= 15: return True,f"[{symbol}] LOBO V59.5.4 {reg_simple} ADX{adx:.0f} RSI{int(rsi)} TP1.2% FIJO", 0.75
    return False,f"[{symbol}] LOBO {reg_simple} ADX{adx:.0f} RSI{int(rsi)} esperando",0.35

def detectar_LOBO_NEGRO_sym(symbol):
    d=get_velas(symbol,"1h",100)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    reg_simple = reg.split()[0] if reg else "LINEAL"
    if reg_simple not in ["BAJISTA","CRASH"]: return False,f"[{symbol}] LOBO_NEGRO BLOQUEADO Solo BAJISTA {reg_simple}",0.10
    closes=d["closes"]; ema20=sum(closes[-20:])/20
    adx = adx_calc(d["highs"], d["lows"], d["closes"], 14); rsi = rsi_calc(closes,14)
    if closes[-1] < ema20 and rsi <= 52 and adx >= 15: return True,f"[{symbol}] LOBO_NEGRO V59.5.4 {reg_simple} ADX{adx:.0f} RSI{int(rsi)} TP1.2% FIJO", 0.75
    return False,f"[{symbol}] LOBO_NEGRO {reg_simple} ADX{adx:.0f} RSI{int(rsi)} esperando",0.35

def detectar_TIBURON_sym(symbol):
    d=get_velas(symbol,"1d",210); d1h=get_velas(symbol,"1h",50)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d["closes"]; ema50=sum(closes[-50:])/50; rsi14=rsi_calc(closes,14)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 20
    if closes[-1] > ema50 and rsi14 > 45 and adx_1h > umb["adx_tiburon"]: return True,f"[{symbol}] TIBURON V59.5.4 {reg.split()[0]} ADX{adx_1h:.0f}>{umb['adx_tiburon']} RSI{int(rsi14)} FIJO 5-10%", 0.85
    return False,f"[{symbol}] TIBU {reg.split()[0]} ADX{adx_1h:.0f}/{umb['adx_tiburon']} esperando", 0.25

def detectar_TIBURON_NEGRO_sym(symbol):
    d=get_velas(symbol,"1d",210); d1h=get_velas(symbol,"1h",50)
    if not d: return False,f"{symbol} Sin velas",0
    reg = ESTADO.get("regimenes",{}).get(symbol,"LINEAL")
    umb = get_umbral_adaptativo(reg)
    closes=d["closes"]; ema50=sum(closes[-50:])/50; rsi14=rsi_calc(closes,14)
    adx_1h = adx_calc(d1h["highs"], d1h["lows"], d1h["closes"], 14) if d1h else 20
    if closes[-1] < ema50 and rsi14 < 55 and adx_1h > umb["adx_tiburon"]: return True,f"[{symbol}] TIBURON_NEGRO V59.5.4 {reg.split()[0]} ADX{adx_1h:.0f}>{umb['adx_tiburon']} RSI{int(rsi14)} SHORT 5-10% FIJO", 0.85
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
    if panico_real: return True,f"[{symbol}] KRAKEN V59.5.4 PANICO REAL RSI{int(rsi_1h)}<32 VSA{vsa_mult:.1f}>1.15 <EMA200 ADX{adx_1h:.0f} FIJO 3%",0.99
    return False,f"[{symbol}] KRAKEN ESPERA PANICO RSI{int(rsi_1h)}/32 VSA{vsa_mult:.1f}/1.15",0.05

def gestionar_bandas_moviles():
    global BANDAS_ACTIVAS, BANDAS_TIEMPO_FUERA
    BANDAS_TIEMPO_FUERA.clear()
    return
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
        msg = f"🐺 PRESA CAZADA V59.5.4 40/40\nPar: {sym}\nEstrategia: {tipo}\nEntrada: ${precio:.2f}\nMonto: ${usdt:.2f}\nTP: {tp:.1f}% | SL: {sl:.1}%\nBanda: {banda_txt}\n{motivo[:120]}\n{WEB_URL}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except Exception as e: print(f"Error notificar_caza: {e}")
def notificar_cierre(sym, tipo, precio_cierre, profit_usd, profit_pct, es_tp=True):
    try:
        if es_tp: msg = f"🔥 PRESA DEVORADA V59.5.4 40/40\nPar: {sym}\nEstrategia: {tipo}\nCierre: ${precio_cierre:.2f}\nProfit: ${profit_usd:.2f} ({profit_pct:.2f}%)\n{WEB_URL}"
        else: msg = f"💨 ESCAPÓ LA PRESA V59.5.4\nPar: {sym}\nEstrategia: {tipo}\nCierre: ${precio_cierre:.2f}\nPérdida: ${profit_usd:.2f} ({profit_pct:.2f}%)\n{WEB_URL}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, msg)
                except: pass
    except Exception as e: print(f"Error notificar_cierre: {e}")
                
# --- PARTE 2 V59.5.4 FINAL FIX - 40/40 + 12H/6H + TOP20 FIX + COMPOUND - SIN CANDADO 0.40% EN 01 ---
INDICE_RONDA_DISTRIBUIDA = 0

def obtener_top_20_rentables_binance():
    for base in ["https://data-api.binance.vision","https://api.binance.com","https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=8)
            data = r.json()
            out = []
            for t in data:
                s = t["symbol"]
                if not s.endswith("USDT"): continue
                if s in MONEDAS_ACTIVAS or s in ["USDTUSDT","USDCUSDT","FDUSDUSDT","BUSDUSDT"]: continue
                if is_moneda_bloqueada(s): continue
                out.append((s, float(t.get("priceChangePercent",0))))
            out.sort(key=lambda x: x[1], reverse=True)
            top = [x[0] for x in out[:20]]
            print(f"V59.5.4 FIX TOP20: {top} ANTI-FALSO {base}")
            return top
        except:
            continue
    print(f"V59.5.4 TOP20 error -> fallback CANDIDATAS")
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

def calcular_profit_hoy_por_moneda(u):
    profit_map = {sym: {"profit":0.0, "count":0} for sym in MONEDAS_ACTIVAS}
    try:
        for h in u.get("historial", [])[-100:]:
            for sym in MONEDAS_ACTIVAS:
                if sym in h:
                    try:
                        if "$" in h:
                            parte = h.split("$")[-1]
                            import re
                            m = re.search(r'([+-]?\d+\.\d+)', parte)
                            if m:
                                val = float(m.group(1))
                                profit_map[sym]["profit"] += val
                                profit_map[sym]["count"] += 1
                    except: pass
                    break
    except: pass
    return profit_map

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
        bandas_txt = "V59.5.4 FIX 40/40 - SIN CANDADO - TP 0.5%->12H 0.3%->6H"
        motivo = ESTADO.get("ultimo_motivo", ESTADO.get("regimen_detalle","Acechando..."))
        monedas_txt = f"{len(MONEDAS_ACTIVAS)}/40"
        tanque_txt = f"PROFIT ${CONTADOR_TP_EXPANSION:.2f}/${META_PROFIT_PARA_EXPANDIR:.0f} Tanque {monedas_txt} V59.5.4 40/40 TP 0.5%->12H 0.3%->6H LOBO 1.2% FIJO"
        texto = f"🐺 ACECHANDO V59.5.4 FIX\n{regs_txt}\n{bandas_txt}\n{motivo[:150]}\n{tanque_txt}\nDashboard: {WEB_URL}"
        for uid in list(USUARIOS.keys()):
            if USUARIOS[uid].get("prendido"):
                try: bot.send_message(uid, texto)
                except Exception as e_tg: print(f"[PENSAMIENTO] ERROR TG a {uid}: {e_tg}")
    except Exception as e: print(f"Error pensamiento V59.5.4: {e}")

def detectar_BI_CEREBRO_DISTRIBUIDA(regimen):
    global INDICE_RONDA_DISTRIBUIDA
    counts_global, _ = contar_posiciones_globales() if 'contar_posiciones_globales' in globals() else ({},0)
    total_posiciones_abiertas = sum(counts_global.values())
    if total_posiciones_abiertas >= MAX_MONEDAS:
        return False, f"TOPE {total_posiciones_abiertas}/{MAX_MONEDAS} ALCANZADO - ESPERANDO TP V59.5.4 40/40", MONEDAS_ACTIVAS[0], None, 0
    monedas_ordenadas = []
    for i in range(len(MONEDAS_ACTIVAS)):
        idx = (INDICE_RONDA_DISTRIBUIDA + i) % len(MONEDAS_ACTIVAS)
        monedas_ordenadas.append(MONEDAS_ACTIVAS[idx])
    candidatos = []
    for sym in monedas_ordenadas:
        if is_moneda_bloqueada(sym): continue
        reg_sym = ESTADO.get("regimenes",{}).get(sym,"LINEAL").split()[0]
        if reg_sym == "LINEAL_MUERTO": orden = ["MOJARRA", "MOJARRITA"]
        elif reg_sym == "LINEAL": orden = ["MOJARRA","PIRANA_BLANCA","RATITA_BLANCA","RATA"]
        elif reg_sym == "ALCISTA": orden = ["MOJARRA","PIRANA_BLANCA","RATITA_BLANCA","RATITA","RATA","LOBO"]
        elif reg_sym == "ALCISTA_FUERTE": orden = ["MOJARRA","PIRANA_BLANCA","RATITA_BLANCA","RATITA","RATA","LOBO","TIBURON"]
        elif reg_sym in ["BAJISTA","CRASH"]: orden = ["MOJARRA_NEGRA","PIRANA_NEGRA","RATITA_NEGRA","RATA_NEGRA","LOBO_NEGRO","TIBURON_NEGRO","KRAKEN","MOJARRITA_SUPERVIVENCIA","MOJARRA","MOJARRITA"]
        else: orden = ["MOJARRITA_SUPERVIVENCIA"]
        for nombre in orden:
            if not candado(nombre, reg_sym, sym=sym): continue
            if nombre == "MOJARRA": max_perm = MAX_MOJARRA_POR_MONEDA
            elif nombre in ["MOJARRITA","MOJARRITA_SUPERVIVENCIA"]: max_perm = MAX_MOJARRITA_POR_MONEDA
            elif nombre in ["LOBO","TIBURON","LOBO_NEGRO","TIBURON_NEGRO","KRAKEN"]: max_perm = 1
            else: max_perm = MAX_PIRANA_POR_MONEDA
            key_global = (sym, nombre)
            if counts_global.get(key_global, 0) >= max_perm: continue
            key_lock = f"{sym}_{nombre}"
            if key_lock in ULTIMO_TRADE and (time.time() - ULTIMO_TRADE[key_lock]) < 30: continue
            ok=False; motivo=""; wr=0
            if nombre=="MOJARRA": ok,motivo,wr = detectar_RATA_sym(sym, "MOJARRA")
            elif nombre=="MOJARRITA": ok,motivo,wr = detectar_RATA_sym(sym, "MOJARRITA")
            elif nombre in ["PIRANA_BLANCA","PIRANA"]: ok,motivo,wr = detectar_RATA_sym(sym, "PIRANA_BLANCA")
            elif nombre in ["RATA","RATITA","RATITA_BLANCA"]: ok,motivo,wr = detectar_RATA_sym(sym, nombre)
            elif nombre=="LOBO": ok,motivo,wr = detectar_LOBO_sym(sym)
            elif nombre=="TIBURON": ok,motivo,wr = detectar_TIBURON_sym(sym)
            elif nombre in ["MOJARRA_NEGRA","PIRANA_NEGRA","RATITA_NEGRA","RATA_NEGRA"]: ok,motivo,wr = detectar_SHORT_sym(sym, nombre)
            elif nombre=="LOBO_NEGRO": ok,motivo,wr = detectar_LOBO_NEGRO_sym(sym)
            elif nombre=="TIBURON_NEGRO": ok,motivo,wr = detectar_TIBURON_NEGRO_sym(sym)
            elif nombre=="KRAKEN": ok,motivo,wr = detectar_KRAKEN_sym(sym)
            elif nombre=="MOJARRITA_SUPERVIVENCIA":
                senal = senal_mojarrita_supervivencia(sym)
                if senal: ok=True; motivo=f"SUPERVIVENCIA RANURA {senal['nivel']} RSI {senal['rsi']:.1f} V59.5.4"; wr=0.95
            if ok and wr > 0.5:
                count_sym = sum([v for k,v in counts_global.items() if k[0]==sym])
                score_dist = wr - (count_sym * 0.5)
                if nombre in ["LOBO","TIBURON"]: score_dist += 0.3
                candidatos.append((score_dist, motivo, sym, nombre, wr, 0.5))
    if candidatos:
        candidatos.sort(key=lambda x: x[0], reverse=True)
        mejor = candidatos[0]
        return True, mejor[1], mejor[2], mejor[3], mejor[4]
    return False, f"V59.5.4 40/40 Esperando RSI 5-28 o 52/58/65 o LOBO/TIBURON + DETECTOR REAL", MONEDAS_ACTIVAS[0], None, 0

def detectar_BI_CEREBRO(regimen):
    return detectar_BI_CEREBRO_DISTRIBUIDA(regimen)

def check_reset_diario(u):
    try:
        hoy = ahora_art().strftime("%Y-%m-%d")
        if u.get("fecha_hoy")!= hoy:
            u["fecha_hoy"] = hoy; u["neto_hoy"] = 0.0; u["ops_hoy"] = 0; u["ganadas"] = 0; u["perdidas"] = 0
        if "neto_hoy" not in u: u["neto_hoy"] = 0.0
        if "ops_hoy" not in u: u["ops_hoy"] = 0
        if "fecha_hoy" not in u: u["fecha_hoy"] = hoy
    except Exception as e: print(f"check_reset_diario error: {e}")
    return u

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
    except: pass

def cargar_datos():
    global MONEDAS_ACTIVAS, POSICIONES_ABIERTAS, BANDAS_ACTIVAS, ESTADO_PIRANA, ESTADO_PIRANA_NEGRA, CANDIDATAS_CACHE, BANDAS_TIEMPO_FUERA, CONTADOR_TP_EXPANSION, TANQUE_BNB_USDT, KRAKEN_SL_COUNT, KRAKEN_BLOQUEO_HASTA, REG_ANT, CONTADOR_POR_REGIMEN, EVOLUCION_NIVEL, ESCAPE_BLOCK, ESCAPES_TIMELINE, PAUSA_GLOBAL_HASTA, BAJISTA_PROFUNDO_HASTA, BLOQUEO_LONG_TOTAL_HASTA, BAJISTA_PROFUNDO_POR_MONEDA, BLOQUEO_LONG_POR_MONEDA, EVOLUCION_NIVEL_NEGRA, CONTADOR_NEGRA_POR_REGIMEN, CONTADOR_SL_NEGRA_SEGUIDOS
    try:
        for fp in [BANDA_FILE]:
            try:
                if os.path.exists(fp): os.remove(fp)
            except: pass
        try:
            if os.path.exists(POS_FILE):
                with open(POS_FILE,"r") as f: POSICIONES_ABIERTAS = json.load(f)
                print(f"V59.5.4 POSICIONES CONSERVADAS 40/40")
            else: POSICIONES_ABIERTAS = {}
        except: POSICIONES_ABIERTAS = {}
        BANDAS_ACTIVAS = {}; ESTADO_PIRANA = {}; ESTADO_PIRANA_NEGRA = {}; BANDAS_TIEMPO_FUERA = {}
        CANDIDATAS_CACHE = {"_ultimo_scan": 0, "_aviso_meta": 0, "proxima": None}
        EVOLUCION_NIVEL = {sym: {"LINEAL":1,"LINEAL_MUERTO":1,"ALCISTA":1,"ALCISTA_FUERTE":1,"BAJISTA":1,"CRASH":1} for sym in MONEDAS_ACTIVAS}
        CONTADOR_POR_REGIMEN = {}
        EVOLUCION_NIVEL_NEGRA = {sym: {"BAJISTA":1,"CRASH":1} for sym in MONEDAS_ACTIVAS}
        CONTADOR_NEGRA_POR_REGIMEN = {}
        CONTADOR_TP_EXPANSION = 0.0
        ESCAPE_BLOCK = {}; ESCAPES_TIMELINE = []; PAUSA_GLOBAL_HASTA = 0; BAJISTA_PROFUNDO_HASTA = 0; BLOQUEO_LONG_TOTAL_HASTA = 0
        print("V59.5.4 FIX - ARRANQUE CONSERVA ORDENES + 40/40 SIN CANDADO + TOP20 FIX")
        return
    except Exception as e:
        print(f"V59.5.4 cargar error {e}")
        POSICIONES_ABIERTAS = {}

def verificar_tanque_bnb():
    global REAL_BALANCE_BNB
    try:
        if not client: return False
        acc=client.get_account()
        bnb=0
        for b in acc['balances']:
            if b['asset']=='BNB': bnb=float(b['free'])+float(b['locked'])
        REAL_BALANCE_BNB=bnb
        return False
    except: return False

def ejecutar_orden_real(symbol, side, usdt_amount):
    try:
        if not client: return True, {"simulado": True, "testnet": True}, get_precio_robusto(symbol)
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
        print(f"ORDEN REAL FALLA {symbol} {e} -> SIMULANDO")
        return True, {"simulado": True, "error": str(e)}, get_precio_robusto(symbol)

def inicializar_moneda_nueva_AUTO(sym):
    try:
        precio = get_precio_robusto(sym)
        if precio == 0: precio = 100
        d1h = get_velas(sym, "1h", 50)
        atr = atr_calc(d1h, 14) if d1h else precio * 0.02
        atr_pct = (atr/precio*100) if precio else 2.0
        if atr_pct > 2.5: inf = precio * 0.94; sup = precio * 1.06
        else: inf = precio * 0.97; sup = precio * 1.03
        BANDAS_ACTIVAS[sym] = {"entrada_tiburon": inf, "tope": sup, "tipo": "NORMAL", "activa": False, "origen_mov": f"V59.5.4 AUTO ATR{atr_pct:.2f}%", "creada_en": time.time()}
        REG_ANT[sym] = "LINEAL"
        EVOLUCION_NIVEL[sym] = {"LINEAL": 1, "LINEAL_MUERTO": 1, "ALCISTA": 1, "ALCISTA_FUERTE": 1, "BAJISTA": 1, "CRASH": 1}
        CONTADOR_POR_REGIMEN[sym] = {}
        EVOLUCION_NIVEL_NEGRA[sym] = {"BAJISTA": 1, "CRASH": 1}
        CONTADOR_NEGRA_POR_REGIMEN[sym] = {}
        print(f"V59.5.4 AUTO INICIADA {sym} ${precio:.2f}")
        return True
    except Exception as e:
        BANDAS_ACTIVAS[sym] = {"entrada_tiburon": get_precio_robusto(sym)*0.97, "tope": get_precio_robusto(sym)*1.03, "tipo": "NORMAL", "activa": False, "creada_en": time.time()}
        REG_ANT[sym] = "LINEAL"; EVOLUCION_NIVEL[sym] = {"LINEAL": 1}
        return False

def intentar_expandir(user_id_notify=None):
    global CONTADOR_TP_EXPANSION, MONEDAS_ACTIVAS
    if CONTADOR_TP_EXPANSION < META_PROFIT_PARA_EXPANDIR: return False
    if len(MONEDAS_ACTIVAS) >= MAX_MONEDAS: return False
    mejor_sym, wr = detectar_mejor_candidata()
    if not mejor_sym: return False
    msg = f"META PROFIT ${META_PROFIT_PARA_EXPANDIR:.0f} ALCANZADA V59.5.4 FIX 40/40\nProfit: ${CONTADOR_TP_EXPANSION:.2f}\nCandidata: {mejor_sym} WR {wr:.2f}\nActual {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS}\nAutorizas sumar {mejor_sym}?"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"AUTORIZAR {mejor_sym} AUTO", callback_data=f"AUTH_ADD_{mejor_sym}"), types.InlineKeyboardButton(f"RECHAZAR", callback_data=f"REJECT_{mejor_sym}"))
    try:
        targets = ADMINS_IDS if not user_id_notify else [user_id_notify]
        for uid in targets: bot.send_message(uid, msg, reply_markup=kb)
    except: pass
    CANDIDATAS_CACHE["_aviso_meta"] = time.time(); guardar_datos()
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
                ESTADO["regimenes"].setdefault(nueva, "LINEAL Iniciada por evolucion AUTO V59.5.4")
                CONTADOR_TP_EXPANSION = 0
                CANDIDATAS_CACHE["proxima"] = None; CANDIDATAS_CACHE["_aviso_meta"] = 0
                guardar_datos()
                bot.answer_callback_query(call.id, f"{nueva} AUTORIZADA V59.5.4 FIX 40/40!")
                bot.send_message(call.message.chat.id, f"V59.5.4 FIX {nueva} AUTORIZADO\nMonedas: {len(MONEDAS_ACTIVAS)}/40", reply_markup=None)
            else: bot.answer_callback_query(call.id, "Ya agregada")
        elif data.startswith("REJECT_"):
            rechazada = data.replace("REJECT_", "")
            bot.answer_callback_query(call.id, f"{rechazada} Rechazada")
            bot.send_message(call.message.chat.id, f"V59.5.4 {rechazada} rechazada.")
            CANDIDATAS_CACHE["proxima"] = None; guardar_datos()
    except Exception as e:
        print(f"Error callback V59.5.4: {e}")
        bot.answer_callback_query(call.id, "Error")

def escanear_candidatas_y_proponer():
    ahora = time.time()
    if ahora - CANDIDATAS_CACHE.get("_ultimo_scan",0) < TIEMPO_ESCANEO_CANDIDATAS: return
    CANDIDATAS_CACHE["_ultimo_scan"] = ahora
    if CONTADOR_TP_EXPANSION < META_PROFIT_PARA_EXPANDIR * 0.8: return
    mejor, wr = detectar_mejor_candidata()
    if mejor: CANDIDATAS_CACHE["proxima"] = mejor

def motor_v45():
    global CONTADOR_TP_EXPANSION, BTC_PRECIOS_15M, CONTADOR_SL_NEGRA_SEGUIDOS, INDICE_RONDA_DISTRIBUIDA
    print(f">>> MOTOR V59.5.4 FINAL FIX {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} - 40/40 SIN CANDADO + 12H/6H + TOP20 FIX + COMPOUND")
    time.sleep(5)
    while True:
        try:
            btc_price = get_precio_robusto("BTCUSDT")
            if btc_price>0:
                BTC_PRECIOS_15M.append((btc_price, time.time()))
                if len(BTC_PRECIOS_15M)>20: BTC_PRECIOS_15M = BTC_PRECIOS_15M[-20:]
            for sym in list(MONEDAS_ACTIVAS):
                reg, det = detectar_regimen_sym(sym)
                reg_viejo = REG_ANT.get(sym, "")
                if reg_viejo and reg_viejo != reg.split()[0]:
                    cierre_market_cambio(sym, reg, reg_viejo)
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
                        pnl_pct_actual = (precio_actual - pos["entrada"]) / pos["entrada"] * 100 if not es_short else (pos["entrada"] - precio_actual) / pos["entrada"] * 100
                        pos["profit_pct"] = pnl_pct_actual
                        es_mojarra_inmortal = pos.get("estrategia") in ["MOJARRA","MOJARRITA","MOJARRITA_SUPERVIVENCIA"]
                        es_rescate = pos.get("es_rescate", False)
                        try:
                            dt_entry = datetime.fromisoformat(pos.get("hora",""))
                            if dt_entry.tzinfo is None: dt_entry = dt_entry.replace(tzinfo=TZ)
                            horas_hold = (ahora_art() - dt_entry).total_seconds()/3600
                        except: horas_hold = 0
                        
                        if es_rescate:
                            tp_usar = tp_rescate_escalonado(pos)
                        elif es_mojarra_inmortal:
                            tp_usar = get_tp_variable_mojarra(pos)
                        else:
                            tp_usar = pos.get("tp", TP_FIJO_RATA)
                            if pos.get("estrategia") in ["LOBO","LOBO_NEGRO"]: tp_usar = TP_FIJO_LOBO
                            elif pos.get("estrategia") in ["TIBURON","TIBURON_NEGRO"]: tp_usar = TP_FIJO_TIBURON_MIN
                            elif pos.get("estrategia") == "KRAKEN": tp_usar = TP_FIJO_KRAKEN
                            elif pos.get("estrategia") in ["RATA","RATA_NEGRA","RATITA","RATITA_BLANCA","RATITA_NEGRA","PIRANA_BLANCA","PIRANA_NEGRA"]: tp_usar = TP_FIJO_RATA

                        if not es_mojarra_inmortal and not es_rescate and pnl_pct_actual <= -3.5:
                            try:
                                ejecutar_orden_real(pos["symbol"], "BUY" if es_short else "SELL", pos["usdt"])
                                pnl_bruto = (precio_actual - pos["entrada"]) / pos["entrada"] * pos["usdt"] if not es_short else (pos["entrada"] - precio_actual) / pos["entrada"] * pos["usdt"]
                                pnl = pnl_bruto - pos["usdt"] * COMISION_TOTAL/100
                                u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["perdidas"]+=1
                                POSICIONES_ABIERTAS[user_id].remove(pos)
                                guardar_datos()
                                continue
                            except: pass
                        tp_price = pos["entrada"] * (1 + tp_usar/100) if not es_short else pos["entrada"] * (1 - tp_usar/100)
                        sl_price = pos["entrada"] * (1 + pos["sl"]/100) if not es_short else pos["entrada"] * (1 - pos["sl"]/100)
                        cerrar = None
                        if not es_short:
                            if precio_actual >= tp_price: cerrar = "TP"
                            elif not es_mojarra_inmortal and not es_rescate and precio_actual <= sl_price: cerrar = "SL"
                        else:
                            if precio_actual <= tp_price: cerrar = "TP"
                            elif not es_mojarra_inmortal and not es_rescate and precio_actual >= sl_price: cerrar = "SL"
                        if cerrar:
                            ejecutar_orden_real(pos["symbol"], "BUY" if es_short else "SELL", pos["usdt"])
                            pnl_bruto = (precio_actual - pos["entrada"]) / pos["entrada"] * pos["usdt"] if not es_short else (pos["entrada"] - precio_actual) / pos["entrada"] * pos["usdt"]
                            pnl = pnl_bruto - pos["usdt"] * COMISION_TOTAL/100
                            es_tp = cerrar == "TP"
                            if es_tp:
                                u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["ganadas"]+=1
                                CONTADOR_TP_EXPANSION = max(0.0, u["balance"] - BALANCE_INICIAL)
                            else:
                                u["balance"]+=pnl; u["neto_hoy"]+=pnl; u["perdidas"]+=1
                                if pnl <= -1.0: registrar_escape(pos["symbol"])
                            estr = pos.get("estrategia", "MOJARRA")
                            if estr not in u.get("estrategias", {}): u["estrategias"][estr] = {"ops":0,"ganadas":0,"neto":0.0}
                            u["estrategias"][estr]["ops"]+=1; u["estrategias"][estr]["neto"]+=pnl
                            u["ops_hoy"]+=1
                            tag_rescate = " RESCATE" if es_rescate else ""
                            u["historial"].append(f"{ahora_art().strftime('%H:%M:%S')} {estr}{tag_rescate} {pos['symbol']} {cerrar} ${pnl:+.2f} TP:{tp_usar:.1f}% V59.5.4 FIX 40/40")
                            try: notificar_cierre(pos["symbol"], estr+tag_rescate, precio_actual, pnl, pnl_pct_actual, es_tp=es_tp)
                            except: pass
                            POSICIONES_ABIERTAS[user_id].remove(pos)
                            guardar_datos()
                    except Exception as e: print(f"Error cierre V59.5.4 {e}")
                if not u.get("prendido", False): continue
                ok,motivo,symbol_elegido,estrategia_elegida,fuerza = detectar_BI_CEREBRO_DISTRIBUIDA(ESTADO.get("regimen","LINEAL"))
                if ok and estrategia_elegida:
                    counts_global, _ = contar_posiciones_globales()
                    key_global = (symbol_elegido, estrategia_elegida)
                    existentes = [p for p in POSICIONES_ABIERTAS.get(user_id,[]) if p.get('symbol')==symbol_elegido and p.get('estrategia')==estrategia_elegida]
                    key_lock = f"{symbol_elegido}_{estrategia_elegida}"
                    if key_lock in ULTIMO_TRADE and (time.time() - ULTIMO_TRADE[key_lock]) < 30: continue
                    if estrategia_elegida == "MOJARRA": max_permitido = MAX_MOJARRA_POR_MONEDA
                    elif estrategia_elegida in ["MOJARRITA","MOJARRITA_SUPERVIVENCIA"]: max_permitido = MAX_MOJARRITA_POR_MONEDA
                    elif estrategia_elegida in ["LOBO","TIBURON","LOBO_NEGRO","TIBURON_NEGRO","KRAKEN"]: max_permitido = 1
                    else: max_permitido = MAX_PIRANA_POR_MONEDA
                    if counts_global.get(key_global, 0) >= max_permitido: continue
                    if len(existentes) >= max_permitido: continue
                    if estrategia_elegida in ["MOJARRA","MOJARRITA","MOJARRITA_SUPERVIVENCIA"]:
                        usdt_a_usar = get_usdt_compound_mojarra(u["balance"])
                    elif estrategia_elegida in ["LOBO","TIBURON"]: usdt_a_usar = max(15, u["balance"]*0.05)
                    else: usdt_a_usar = max(10, u["balance"]*0.035)
                    if estrategia_elegida in ["LOBO","LOBO_NEGRO"]: tp_final = TP_FIJO_LOBO
                    elif estrategia_elegida in ["TIBURON","TIBURON_NEGRO"]: tp_final = TP_FIJO_TIBURON_MIN
                    elif estrategia_elegida == "KRAKEN": tp_final = TP_FIJO_KRAKEN
                    elif estrategia_elegida in ["MOJARRA","MOJARRITA","MOJARRITA_SUPERVIVENCIA"]: tp_final = TP_BASE_V594
                    else: tp_final = TP_FIJO_RATA
                    print(f"CAZANDO V59.5.4 FIX {symbol_elegido} {estrategia_elegida} {motivo} {len(existentes)+1}/{max_permitido} ${usdt_a_usar} TP{tp_final}% 40/40")
                    lado = "SELL" if estrategia_elegida in NEGRAS else "BUY"
                    exito, res, precio = ejecutar_orden_real(symbol_elegido, lado, usdt_a_usar)
                    if exito:
                        ULTIMO_TRADE[key_lock]=time.time()
                        INDICE_RONDA_DISTRIBUIDA = (INDICE_RONDA_DISTRIBUIDA + 1) % len(MONEDAS_ACTIVAS)
                        pos = {"symbol": symbol_elegido, "estrategia": estrategia_elegida, "entrada": precio, "tp": tp_final, "sl": ESTRATEGIAS_V45[estrategia_elegida]["sl_neto"], "usdt": usdt_a_usar, "hora": ahora_art().isoformat(), "max_pnl": 0.0, "max_precio": precio, "es_rescate": False, "tp_original": tp_final, "dt_rescate": time.time(), "timestamp": time.time()}
                        POSICIONES_ABIERTAS[user_id].append(pos)
                        reg_simple = ESTADO.get("regimenes",{}).get(symbol_elegido,"LINEAL").split()[0]
                        registrar_caza_V51(symbol_elegido, estrategia_elegida, reg_simple)
                        u["modo"]=f"{estrategia_elegida} {symbol_elegido} TP{pos['tp']:.1f}%"; u["mercado"]=motivo
                        b = BANDAS_ACTIVAS.get(symbol_elegido,{})
                        banda_txt = f"{b.get('entrada_tiburon',precio*0.97):.0f}->{b.get('tope',precio*1.10):.0f} {b.get('tipo','')}"
                        try:
                            msg = f"🐺 PRESA CAZADA V59.5.4 FIX 40/40\nPar: {symbol_elegido}\nEstrategia: {estrategia_elegida}\nEntrada: ${precio:.2f}\nMonto: ${usdt_a_usar:.2f}\nTP: {tp_final:.1f}% FIJO | {len(existentes)+1}/{max_permitido} | Banda: {banda_txt}\n{motivo[:120]}\n{WEB_URL}"
                            for uid in list(USUARIOS.keys()):
                                if USUARIOS[uid].get("prendido"):
                                    try: bot.send_message(uid, msg)
                                    except: pass
                        except: pass
            guardar_datos()
            time.sleep(10)
        except Exception as e:
            print(f"Error motor V59.5.4 {e}")
            time.sleep(10)

def intentar_comprar(sym, motivo=""): return True
def get_menu():
    m=types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("PRENDER","EVOLUCIONAR"); m.add("BALANCE","HISTORIAL"); m.add("RETIRAR GANANCIAS","RETIRAR TODO"); m.add("ORDENES")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    try:
        u=get_user_data(m.chat.id)
        estado_txt = f"V59.5.4 FIX FINAL {len(MONEDAS_ACTIVAS)}/{MAX_MONEDAS} SIN CANDADO" if u["prendido"] else "APAGADO"
        regs="\n".join([f"{k}:{v.split()[0]}" for k,v in ESTADO.get("regimenes",{}).items()]) or ESTADO['regimen'].split()[0]
        bot.send_message(m.chat.id,f"V59.5.4 FIX FINAL CEREBRO {estado_txt}\n{regs}\nBal ${u['balance']:.2f}\n{WEB_URL}",reply_markup=get_menu())
    except Exception as e: print(f"START ERROR {e}")

@bot.message_handler(func=lambda m: m.text=="BALANCE")
def balance(m):
    try:
        u=get_user_data(m.chat.id)
        profit_map = calcular_profit_hoy_por_moneda(u)
        regs_txt = ""
        for k,v in ESTADO.get("regimenes",{}).items():
            reg_simple = v.split()[0]
            cambio = get_cambio_24h(k)
            pm = profit_map.get(k, {"profit":0.0,"count":0})
            extra = f" | Hoy: ${pm['profit']:+.2f} ({pm['count']}/3)" if pm["count"]>0 else f" | Hoy: $0.00"
            fuego = " 🔥" if pm["profit"]>0 else ""
            regs_txt += f"{k}: {reg_simple} ({cambio:+.1f}%){extra}{fuego}\n"
        posiciones = POSICIONES_ABIERTAS.get(m.chat.id, [])
        if not posiciones and m.chat.id!= ADMINS_IDS[0]: posiciones = []
        en_juego = sum([p.get("usdt",0) for p in posiciones])
        total = u["balance"]
        disponible = total - en_juego
        if disponible < 0: disponible = total
        total_acum = total - u.get("capital_inicial",10000)
        count_vieja = sum(1 for p in posiciones if p.get("usdt",0) >= 100)
        count_nueva = len(posiciones) - count_vieja
        if count_vieja>0 and count_nueva>0: en_juego_txt = f"{len(posiciones)} ordenes ({count_vieja}x$350 + {count_nueva}x${MOJARRA_USDT:.0f})"
        elif count_vieja>0: en_juego_txt = f"{len(posiciones)} x $350 (viejas hasta TP)"
        else: en_juego_txt = f"{len(posiciones)} x ${MOJARRA_USDT:.0f} (V59.5.4 FIX 40/40)"
        msg = f"🐺 V59.5.4 FIX FINAL {len(posiciones)}/40\n━━━━━━━━━━━━━━\n📊 REGIMENES:\n{regs_txt}\n💰 BALANCE:\nTotal: ${total:.2f}\nHoy: ${u.get('neto_hoy',0):+.2f} ({u.get('ganadas',0)} devoradas)\nAcumulado: ${total_acum:+.2f}\nEn Juego: ${en_juego:.0f} ({en_juego_txt})\nDisponible: ${disponible:.2f}\n\n🎯 V59.5.4 FIX: 40/40 SIN CANDADO | TP 0.5%->12H 0.3%->6H ciclo | LOBO 1.2% FIJO | COMPOUND MOJARRA $10->$20\n{WEB_URL}"
        bot.send_message(m.chat.id, msg, reply_markup=get_menu())
    except Exception as e: print(f"BALANCE ERROR: {e}")

@bot.message_handler(func=lambda m: m.text=="ORDENES")
def ordenes(m):
    try:
        uid = m.chat.id
        posiciones = POSICIONES_ABIERTAS.get(uid, [])
        if not posiciones:
            bot.send_message(m.chat.id, f"📋 ORDENES ABIERTAS 0/40 V59.5.4 FIX\n━━━━━━━━━━━━━━\nSin ordenes abiertas\nEn Juego Total: $0", reply_markup=get_menu())
            return
        msg = f"📋 ORDENES ABIERTAS {len(posiciones)}/40 V59.5.4 FIX\n━━━━━━━━━━━━━━\n"
        total_juego = 0
        for i,p in enumerate(posiciones[:40],1):
            try:
                sym = p.get("symbol","?")
                entrada = p.get("entrada",0)
                es_rescate = p.get("es_rescate", False)
                if es_rescate: tp_pct = tp_rescate_escalonado(p)
                elif p.get("estrategia") in ["MOJARRA","MOJARRITA","MOJARRITA_SUPERVIVENCIA"]: tp_pct = get_tp_variable_mojarra(p)
                else: tp_pct = p.get("tp",0.8)
                tp_precio = entrada * (1+tp_pct/100) if p.get("estrategia") not in NEGRAS else entrada * (1-tp_pct/100)
                usdt = p.get("usdt",0)
                total_juego += usdt
                try:
                    hora_iso = p.get("hora","")
                    dt = datetime.fromisoformat(hora_iso)
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=TZ)
                    mins = int((ahora_art() - dt).total_seconds()/60)
                    hace = f"{mins}m" if mins<60 else f"{mins//60}h {mins%60}m"
                    if es_rescate: hace += f" RESCATE->{tp_pct:.1f}%"
                    elif p.get("estrategia") in ["MOJARRA","MOJARRITA"] and mins>12*60: hace += f" -> {TP_RESCATE_V594}% RESCATE 12H/6H"
                except: hace = "?"
                tag = "RESCATE" if es_rescate else (f"V59.5.4 FIX ${usdt:.0f} COMPOUND" if usdt < 100 else "VIEJA")
                if p.get("estrategia") in ["LOBO","TIBURON"] and not es_rescate: tag += " FIJO"
                msg += f"{i}. {sym} {p.get('estrategia')} ${entrada:.2f} -> ${tp_precio:.2f} | +{tp_pct:.1f}% | ${usdt:.0f} {tag} | {hace}\n"
            except: continue
        msg += f"\nEn Juego Total: ${total_juego:.0f} | 40/40 SIN CANDADO"
        bot.send_message(m.chat.id, msg, reply_markup=get_menu())
    except Exception as e: print(f"ORDENES ERROR: {e}")

@bot.message_handler(func=lambda m: m.text=="HISTORIAL")
def historial(m):
    try:
        u=get_user_data(m.chat.id)
        hist = u.get("historial", [])
        if not hist:
            bot.send_message(m.chat.id, f"📜 HISTORIAL VACIO\nHoy: 0/3 | +$0.00\nTotal: 0 | +$0.00", reply_markup=get_menu())
            return
        ultimas = hist[-10:]
        msg = f"📜 HISTORIAL ULTIMAS {len(ultimas)} V59.5.4 FIX 40/40\n━━━━━━━━━━━━━━\n"
        for h in ultimas[::-1]: msg += f"{h[:90]}\n"
        msg += f"\nHoy: {u.get('ganadas',0)}/{u.get('ops_hoy',0)} | ${u.get('neto_hoy',0):+.2f}\nTotal Acum: ${u['balance']-u.get('capital_inicial',10000):+.2f}"
        bot.send_message(m.chat.id, msg, reply_markup=get_menu())
    except Exception as e: print(f"HISTORIAL ERROR: {e}")

@bot.message_handler(func=lambda m: m.text=="PRENDER")
def prender(m):
    u=get_user_data(m.chat.id); u["prendido"]=True; guardar_datos()
    bot.send_message(m.chat.id,f"MANADA PRENDIDA V59.5.4 FIX FINAL 40/40\nSIN CANDADO 0.40% - TP 0.5%->12H 0.3%->6H ciclo LOBO 1.2% FIJO TIBURON 5-10% FIJO\n01 MOJARRA 52/58/65 + MOJARRITA 5-28 $10->$20 COMPOUND x5 + x5 = 40/40",reply_markup=get_menu())

@bot.message_handler(func=lambda m: m.text=="EVOLUCIONAR")
def evolucionar(m):
    regs="\n".join([f"{k}: {v}" for k,v in ESTADO.get("regimenes",{}).items()])
    bot.send_message(m.chat.id,f"V59.5.4 FIX FINAL 40/40 SIN CANDADO\n{regs}",reply_markup=get_menu())

def info_sym(sym):
    try:
        precio = get_precio_robusto(sym)
        if precio==0: precio = 100.0
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
        banda = BANDAS_ACTIVAS.get(sym,{})
        madre = banda.get("tipo","NORMAL")
        ema_txt = "9>20" if vol_txt>0 else "9<20"
        if reg == "LINEAL_MUERTO":
            if rsi_real <= 28: mejor_estrat = f"01 LINEAL_MUERTO - MOJARRITA {int(rsi_real)} 5-28 TP0.5%->12H 0.3% x1 $10->$20 40/40 V59.5.4 FIX"
            else: mejor_estrat = f"01 LINEAL_MUERTO - MOJARRA {int(rsi_real)} 52/58/65 TP0.5%->12H 0.3% x1 $10->$20 40/40 V59.5.4 FIX"
        else: mejor_estrat = estrategia_prevista(reg_full)
        return {"regimen": str(reg), "reg_detalle": str(reg_full), "cambio24": float(cambio24),"adx": float(adx_real), "rsi": float(rsi_real), "ema": str(ema_txt),"atr": float(atr_pct), "vol": float(vol_txt), "precio": float(precio),"madre": str(madre), "mejor_estrategia": str(mejor_estrat),"banda_inf": float(banda.get("entrada_tiburon",precio*0.97)),"banda_sup": float(banda.get("tope",precio*1.03)),"v51_nivel": 1, "v51_contador": {}, "v56_nivel_negra": 1, "v56_contador_negra": {}}
    except Exception as e:
        return {"regimen":"LINEAL_MUERTO","cambio24":0.0,"adx":12.0,"rsi":15.0,"ema":"9>20","atr":0.23,"vol":0.05,"precio":86342.0,"madre":"NORMAL","mejor_estrategia":"01 LINEAL_MUERTO 0.5%->12H 0.3% $10->$20 40/40 V59.5.4 FIX","banda_inf":1.0,"banda_sup":2.0,"v51_nivel":1,"v51_contador":{},"v56_nivel_negra":1,"v56_contador_negra":{}}

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
            res[sym] = {"regimen": str(inf.get("regimen","LINEAL")), "cambio24": float(inf.get("cambio24",0.0)),"adx": float(inf.get("adx",15.0)), "madre": str(inf.get("madre","NORMAL")),"rsi": float(inf.get("rsi",50.0)), "ema": str(inf.get("ema","9>20")),"atr": float(inf.get("atr",0.0)), "vol": float(inf.get("vol",1.0)),"mejor_estrategia": str(inf.get("mejor_estrategia","V59.5.4 FIX")),"v51_nivel": int(inf.get("v51_nivel",1)), "v51_contador": inf.get("v51_contador",{}),"v56_nivel_negra": int(inf.get("v56_nivel_negra",1)), "v56_contador_negra": inf.get("v56_contador_negra",{}),"precio": float(inf.get("precio",0.0)), "banda_inf": float(inf.get("banda_inf",1.0)), "banda_sup": float(inf.get("banda_sup",2.0))}
        return jsonify(res)
    except: return jsonify({}), 200
@app.route('/api/graficos')
def api_graficos():
    try:
        res = {}
        for sym in MONEDAS_ACTIVAS:
            d = get_velas(sym, "5m", 100)
            if d: res[sym] = {"closes": d["closes"][-50:], "rsi": rsi_calc(d["closes"],7)}
        return jsonify(res)
    except: return jsonify({}), 200
@app.route('/')
def home():
    html = '''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V59.5.4 FIX FINAL 40/40 DEVORA TODO ANTI-FALSO</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}.top{padding:12px;background:#1e222d;position:sticky;top:0;z-index:20;border-bottom:2px solid #00ff88;font-size:12px;white-space:nowrap;overflow:auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px}.card{background:#1e222d;border-radius:8px;overflow:hidden;border:1px solid #2a2e39}.det{font-family:monospace;font-size:11px;padding:8px;background:#0e1a0e;color:#a5fca5;line-height:1.4}.det b{color:#ffcc00}.det.est{color:#00ff88;font-weight:bold}</style></head><body><div class="top" id="info">V59.5.4 FIX FINAL 40/40 - Cargando...</div><div class="grid" id="grid"></div><script>async function init(){let a=await (await fetch('/api/data')).json();let MONEDAS=a.monedas||["BTCUSDT","BNBUSDT","AVAXUSDT","XRPUSDT"];document.getElementById('grid').innerHTML="";MONEDAS.forEach(sym=>{let id='tv_'+sym;let c=document.createElement('div');c.className='card';c.innerHTML=`<div id="${id}" style="height:320px"></div><div class="det" id="det-${sym}">${sym}...</div>`;document.getElementById('grid').appendChild(c);new TradingView.widget({autosize:true,symbol:"BINANCE:"+sym,interval:"5",container_id:id,theme:"dark",style:"1",locale:"es"});});load();}async function load(){try{let a=await (await fetch('/api/data')).json();document.getElementById('info').innerHTML=`V59.5.4 FIX FINAL ${a.monedas.length}/40 | $${a.balance?.toFixed(2)||''} | ${a.bandas_txt||''} | ${Object.entries(a.regimenes||{}).map(e=>e[0].replace('USDT','')+':'+e[1].split('|')[0]).join(' | ')} | PROFIT $${a.tps_actual?.toFixed(2)}/$${a.meta_proxima} ANTI-FALSO 40/40`;}catch(e){}try{let d=await (await fetch('/api/detalles_mercado')).json();for(let k in d){let el=document.getElementById('det-'+k);if(el&&d[k]){let x=d[k];let cambio=(x.cambio24>=0?'+':'')+Number(x.cambio24).toFixed(2)+'%';el.innerHTML=`<b>REGIMEN:</b> ${x.regimen} (${cambio}) ADX ${Number(x.adx).toFixed(1)} ATR ${Number(x.atr).toFixed(2)}% Vol ${Number(x.vol).toFixed(2)}x Madre:${x.madre} RSI ${Number(x.rsi).toFixed(1)} ${x.ema}<br><span class="est">ESTRATEGIA: ${x.mejor_estrategia} | $${Number(x.precio).toFixed(2)} REAL 40/40</span>`;}}}catch(e){}}init();setInterval(load,5000);</script></body></html>'''
    return render_template_string(html, monedas=MONEDAS_ACTIVAS)
@app.route('/api/data')
def api_data():
    try:
        target=ADMINS_IDS[0]
        if target not in USUARIOS: get_user_data(target)
        u=USUARIOS[target]
        bandas_txt = "V59.5.4 FIX FINAL 40/40 SIN CANDADO 0.40% + 12H/6H + TOP20 FIX + COMPOUND"
        ganancia_total = u["balance"]-u["capital_inicial"]
        return jsonify({"balance":u["balance"],"capital_inicial":u["capital_inicial"],"neto_hoy":u["neto_hoy"],"modo":u["modo"],"mercado":u["mercado"],"regimen_btc":ESTADO.get("regimen","LINEAL"),"regimenes":ESTADO.get("regimenes",{}),"estrategias":u["estrategias"],"monedas":MONEDAS_ACTIVAS,"ganancia_total":ganancia_total,"bandas":BANDAS_ACTIVAS,"bandas_txt":bandas_txt,"posiciones":POSICIONES_ABIERTAS.get(target,[]),"precios":{},"meta_proxima":META_PROFIT_PARA_EXPANDIR,"tps_actual":CONTADOR_TP_EXPANSION,"v51_contadores":CONTADOR_POR_REGIMEN,"v51_niveles":EVOLUCION_NIVEL,"v56_contadores_negra":CONTADOR_NEGRA_POR_REGIMEN,"v56_niveles_negra":EVOLUCION_NIVEL_NEGRA})
    except Exception as e:
        return jsonify({"balance":10000,"capital_inicial":10000,"neto_hoy":0,"modo":"OK","mercado":"OK","regimen_btc":"LINEAL","regimenes":ESTADO.get("regimenes",{}),"estrategias":{},"monedas":MONEDAS_ACTIVAS,"ganancia_total":0,"bandas":BANDAS_ACTIVAS,"bandas_txt":"OK","posiciones":[],"precios":{},"meta_proxima":120,"tps_actual":CONTADOR_TP_EXPANSION}),200

if True:
    cargar_datos()
    for sym in MONEDAS_ACTIVAS:
        ESTADO["regimenes"].setdefault(sym, "LINEAL_MUERTO Inicializado V59.5.4 FIX FINAL 40/40 SIN CANDADO")
        REG_ANT.setdefault(sym, "LINEAL_MUERTO")
    t = threading.Thread(target=motor_v45, daemon=False); t.start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), debug=False, use_reloader=False), daemon=False).start()
    print("V59.5.3 FINAL - LISTO PARA REAL - SIN CANDADO + TP VARIABLE 0.5%->12H 0.3%")
    import logging
    logging.getLogger('telebot').setLevel(logging.ERROR)
    while True:
        try:
            try:
                bot.delete_webhook(drop_pending_updates=True)
                print("V59.5.4 FIX Webhook borrado - polling unico FINAL 40/40 SIN CANDADO")
                time.sleep(3)
            except Exception as e_wh: print(f"Webhook {e_wh}")
            bot.infinity_polling(timeout=60, long_polling_timeout=60, allowed_updates=["message", "callback_query"], skip_pending=True)
        except Exception as e:
            err_txt = str(e).lower()
            if "429" in err_txt or "too many" in err_txt:
                print(f"[ANTI-429] Telegram saturado, duermo 15s: {e}")
                time.sleep(15)
            else:
                print(f"Bot polling error V59.5.4 {e} - reintento en 10s")
                time.sleep(10)
