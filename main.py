import os
import json
import threading
import random
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request
import telebot
from telebot import types
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Argentina/Buenos_Aires")
except:
    import pytz
    TZ = pytz.timezone('America/Argentina/Buenos_Aires')

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

BALANCE_INICIAL = 200.0
BALANCE_BTC_INICIAL = 100.0
BALANCE_BNB_INICIAL = 100.0
CACHORRO_PORC = 0.20
ADMINS_IDS = [6530209116]
WEB_URL = "https://bot-v22-1.onrender.com"
DATA_FILE = "/data/manada.json"
os.makedirs("/data", exist_ok=True)

ALIAS_MP_DEMO = "manada.lobo.demo.mp"
DOLAR_CRIPTO = {"valor": 1480, "actualizado": "inicio", "fuente": "DEMO"}
PLANES = {"RATA":20,"LOBO":40,"TIBURON":60}

print(f"### V26.8.6 B-200 SIN TABLA - ADMIN VE SOCIOS / SOCIO VE INVERSION + TOTAL DIA ###")

ESTADO = {"btc": 78287.4, "bnb": 739.68, "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)], "socios": {}, "admins": ADMINS_IDS}
USUARIOS = {}
LOCK = threading.Lock()
MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

try:
    bot.delete_my_commands()
    bot.set_my_commands([])
    print("Menu 3 lineas borrado OK")
except Exception as e:
    print(f"No se pudo borrar menu: {e}")

def ahora_art():
    return datetime.now(TZ)

def reset_diario_si_corresponde(user_data):
    ahora = ahora_art()
    hoy_str = ahora.strftime('%d/%m/%Y')
    ultimo = user_data.get('ultimo_reset', '')
    if ultimo!= hoy_str:
        if user_data.get('ops_hoy', 0) > 0:
            if 'historial_diario' not in user_data:
                user_data['historial_diario'] = []
            user_data['historial_diario'].append({
                'fecha': ultimo or hoy_str,
                'ops': user_data.get('ops_hoy', 0),
                'ganadas': user_data.get('ganadas', 0),
                'perdidas': user_data.get('perdidas', 0),
                'neto': user_data.get('neto_hoy', 0.0),
                'neto_btc': user_data.get('neto_hoy_btc', 0.0),
                'neto_bnb': user_data.get('neto_hoy_bnb', 0.0)
            })
            user_data['historial_diario'] = user_data['historial_diario'][-30:]
        user_data['ops_hoy'] = 0
        user_data['ganadas'] = 0
        user_data['perdidas'] = 0
        user_data['neto_hoy'] = 0.0
        user_data['neto_hoy_btc'] = 0.0
        user_data['neto_hoy_bnb'] = 0.0
        user_data['ops_hoy_btc'] = 0
        user_data['ops_hoy_bnb'] = 0
        user_data['ganadas_btc'] = 0
        user_data['ganadas_bnb'] = 0
        user_data['perdidas_btc'] = 0
        user_data['perdidas_bnb'] = 0
        user_data['ultimo_reset'] = hoy_str
        print(f"[RESET DIARIO] {hoy_str} para {user_data.get('user_id')}")
    return user_data

def actualizar_dolar():
    while True:
        try:
            r = requests.get("https://criptoya.com/api/dolar", timeout=10).json()
            if r and 'cripto' in r and 'ccb' in r['cripto']:
                DOLAR_CRIPTO["valor"] = int(float(r['cripto']['ccb']))
                DOLAR_CRIPTO["actualizado"] = ahora_art().strftime("%H:%M")
            else:
                DOLAR_CRIPTO["actualizado"] = ahora_art().strftime("%H:%M")
        except:
            DOLAR_CRIPTO["valor"] += random.randint(-5,5)
            DOLAR_CRIPTO["actualizado"] = ahora_art().strftime("%H:%M")
        time.sleep(1800)

BIENVENIDA = """👋 MANADA V26.8.6 B-200 SIN TABLA - MP PURO + API SEGURA 🐺

Hola Lobo, bienvenido a la manada.

V26.8.6 B-200 arranca en $200 DEMO limpio.
$100 BTC + $100 BNB SEPARADOS.
Tocá BALANCE y PRENDER para probar.

Si querés cargar API real: /setapi TU_API_KEY TU_SECRET_KEY
Para borrar API: /clearapi
Para reset total a $200: /resetdemo
"""

def get_menu_botones(admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if admin:
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("👥 SOCIOS"), types.KeyboardButton("📈 ESTRATEGIAS"))
        markup.add(types.KeyboardButton("📜 HISTORIAL"), types.KeyboardButton("🆔 ID"))
        markup.add(types.KeyboardButton("🔄 RESET DEMO"), types.KeyboardButton("🧹 CLEAR API"))
    else:
        markup.add(types.KeyboardButton("💰 PAGAR"), types.KeyboardButton("🐺 QUIERO LOBO"))
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("📈 ESTRATEGIAS"), types.KeyboardButton("📜 HISTORIAL"))
        markup.add(types.KeyboardButton("🆔 ID"))
    return markup

def guardar_datos():
    try:
        with LOCK:
            socios_ser = {str(k): {"alta": v["alta"].isoformat(), "vence": v["vence"].isoformat(), "plan": v["plan"]} for k,v in ESTADO["socios"].items()}
            usuarios_ser = {}
            for k,v in USUARIOS.items():
                vd = v.copy()
                if vd.get("pausa_hasta") and isinstance(vd["pausa_hasta"], datetime): vd["pausa_hasta"] = vd["pausa_hasta"].isoformat()
                vd["historial"] = vd.get("historial", [])[-200:]
                usuarios_ser[str(k)] = vd
            with open(DATA_FILE+".tmp", "w", encoding="utf-8") as f: json.dump({"socios": socios_ser, "usuarios": usuarios_ser}, f)
            os.replace(DATA_FILE+".tmp", DATA_FILE)
    except Exception as e: print(f"Error guardando: {e}")

def cargar_datos():
    try:
        if not os.path.exists(DATA_FILE): return
        with open(DATA_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        for k,v in data.get("usuarios", {}).items():
            if v.get("balance",0) > 1000 or v.get("balance",0) < 0:
                print(f"BALANCE TRUCHO DETECTADO {v.get('balance')} -> RESET $200")
                try: os.remove(DATA_FILE)
                except: pass
                return
        for k,v in data.get("socios", {}).items():
            try: ESTADO["socios"][int(k)] = {"alta": datetime.fromisoformat(v["alta"]), "vence": datetime.fromisoformat(v["vence"]), "plan": v["plan"]}
            except: pass
        for k,v in data.get("usuarios", {}).items():
            try:
                if v.get("pausa_hasta"):
                    try: v["pausa_hasta"] = datetime.fromisoformat(v["pausa_hasta"])
                    except: v["pausa_hasta"] = None
                if "ultimo_reset" not in v: v["ultimo_reset"] = ""
                if "historial_diario" not in v: v["historial_diario"] = []
                if "user_id" not in v: v["user_id"] = int(k)
                v["estrategias"].pop("ORCA", None); v["estrategias"].pop("MEGALODON", None)
                USUARIOS[int(k)] = v
            except: pass
    except FileNotFoundError:
        pass
    except:
        try: os.remove(DATA_FILE)
        except: pass

cargar_datos()

def get_user_data(user_id):
    user_id = int(user_id); es_admin_id = user_id in ADMINS_IDS
    if user_id not in USUARIOS:
        USUARIOS[user_id] = {
            "user_id": user_id, "prendido": False, "balance": BALANCE_INICIAL, "capital_inicial": BALANCE_INICIAL,
            "balance_btc": BALANCE_BTC_INICIAL, "balance_bnb": BALANCE_BNB_INICIAL,
            "capital_btc": BALANCE_BTC_INICIAL, "capital_bnb": BALANCE_BNB_INICIAL,
            "neto_hoy_btc": 0.0, "neto_hoy_bnb": 0.0,
            "ops_hoy_btc": 0, "ops_hoy_bnb": 0,
            "ganadas_btc": 0, "ganadas_bnb": 0,
            "perdidas_btc": 0, "perdidas_bnb": 0,
            "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO" if es_admin_id else "CACHORRO", "mercado": "BASE SOLIDA BTC+BNB" if es_admin_id else "CACHORRO GRATIS 7 DIAS (20%)", "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA" if es_admin_id else "SOCIO", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False}
        guardar_datos()
    if USUARIOS[user_id].get("balance",0) > 1000:
        USUARIOS[user_id]["balance"]=BALANCE_INICIAL
        USUARIOS[user_id]["capital_inicial"]=BALANCE_INICIAL
        USUARIOS[user_id]["neto_hoy"]=0.0
        USUARIOS[user_id]["ops_hoy"]=0
        USUARIOS[user_id]["ganadas"]=0
        USUARIOS[user_id]["perdidas"]=0
        USUARIOS[user_id]["historial"]=[]
        USUARIOS[user_id]["api_key"]=None
        USUARIOS[user_id]["api_secret"]=None
        USUARIOS[user_id]["api_cargada"]=False
        USUARIOS[user_id]["balance_btc"]=BALANCE_BTC_INICIAL
        USUARIOS[user_id]["balance_bnb"]=BALANCE_BNB_INICIAL
        USUARIOS[user_id]["capital_btc"]=BALANCE_BTC_INICIAL
        USUARIOS[user_id]["capital_bnb"]=BALANCE_BNB_INICIAL
        USUARIOS[user_id]["neto_hoy_btc"]=0.0
        USUARIOS[user_id]["neto_hoy_bnb"]=0.0
        USUARIOS[user_id]["ops_hoy_btc"]=0
        USUARIOS[user_id]["ops_hoy_bnb"]=0
        USUARIOS[user_id]["ganadas_btc"]=0
        USUARIOS[user_id]["ganadas_bnb"]=0
        USUARIOS[user_id]["perdidas_btc"]=0
        USUARIOS[user_id]["perdidas_bnb"]=0
        guardar_datos()
    USUARIOS[user_id]["estrategias"].pop("ORCA", None); USUARIOS[user_id]["estrategias"].pop("MEGALODON", None)
    for k in ["RATA","LOBO","TIBURON"]:
        if k not in USUARIOS[user_id]["estrategias"]: USUARIOS[user_id]["estrategias"][k] = {"ops":0,"ganadas":0,"neto":0.0}
    if "capital_inicial" not in USUARIOS[user_id]: USUARIOS[user_id]["capital_inicial"] = BALANCE_INICIAL
    if "api_key" not in USUARIOS[user_id]: USUARIOS[user_id]["api_key"] = None
    if "api_secret" not in USUARIOS[user_id]: USUARIOS[user_id]["api_secret"] = None
    if "api_cargada" not in USUARIOS[user_id]: USUARIOS[user_id]["api_cargada"] = False
    if "ultimo_reset" not in USUARIOS[user_id]: USUARIOS[user_id]["ultimo_reset"] = ahora_art().strftime('%d/%m/%Y')
    if "historial_diario" not in USUARIOS[user_id]: USUARIOS[user_id]["historial_diario"] = []
    if "user_id" not in USUARIOS[user_id]: USUARIOS[user_id]["user_id"] = user_id
    if "balance_btc" not in USUARIOS[user_id]:
        bal = USUARIOS[user_id].get("balance", BALANCE_INICIAL)
        mitad = round(bal/2,2)
        USUARIOS[user_id]["balance_btc"] = mitad
        USUARIOS[user_id]["balance_bnb"] = bal - mitad
        USUARIOS[user_id]["capital_btc"] = BALANCE_BTC_INICIAL
        USUARIOS[user_id]["capital_bnb"] = BALANCE_BNB_INICIAL
        USUARIOS[user_id]["neto_hoy_btc"] = 0.0
        USUARIOS[user_id]["neto_hoy_bnb"] = 0.0
        USUARIOS[user_id]["ops_hoy_btc"] = 0
        USUARIOS[user_id]["ops_hoy_bnb"] = 0
        USUARIOS[user_id]["ganadas_btc"] = 0
        USUARIOS[user_id]["ganadas_bnb"] = 0
        USUARIOS[user_id]["perdidas_btc"] = 0
        USUARIOS[user_id]["perdidas_bnb"] = 0
    USUARIOS[user_id] = reset_diario_si_corresponde(USUARIOS[user_id])
    return USUARIOS[user_id]

def es_admin(chat_id): return int(chat_id) in ESTADO["admins"]
def tiene_acceso(chat_id):
    chat_id=int(chat_id)
    if es_admin(chat_id): return True, 999
    socio=ESTADO["socios"].get(chat_id)
    if not socio: return False, 0
    if datetime.now() > socio["vence"]: return False, 0
    return True, (socio["vence"]-datetime.now()).days+1
def calcular_winrate(u): total=u["ganadas"]+u["perdidas"]; return round((u["ganadas"]/total)*100) if total else 0
def calcular_winrate_estrategia(e): return round((e["ganadas"]/e["ops"])*100) if e["ops"] else 0
def get_estado_texto(u):
    if not u["prendido"]: return "🔴 APAGADO"
    if u["pausa_hasta"] and isinstance(u["pausa_hasta"], datetime) and datetime.now() < u["pausa_hasta"]: return f"⏸️ Pausa"
    return "🟢 PRENDIDO"
def analizar_mercado_y_elegir_modo(u):
    try:
        ultimos=ESTADO["btc_history"][-10:]; atr=round((max(ultimos)-min(ultimos))/ESTADO["btc"]*100,2)
        if atr<0.25: atr=round(random.uniform(0.28,0.48),2)
    except: atr=0.40
    if atr<0.35: u["modo"]="RATA"; u["mercado"]=f"LATERAL BTC+BNB ({atr:.2f}%)"
    elif atr>0.70: u["modo"]="TIBURON"; u["mercado"]=f"VOLATIL BTC+BNB ({atr:.2f}%)"
    else: u["modo"]="LOBO"; u["mercado"]=f"NORMAL BTC+BNB ({atr:.2f}%)"
    return atr

def motor_demo():
    contador=0
    while True:
        time.sleep(random.randint(3,6))
        ESTADO["btc"]=round(78287.4+random.uniform(-350,350),2); ESTADO["bnb"]=round(739.68+random.uniform(-5,5),2)
        ESTADO["btc_history"].append(ESTADO["btc"])
        if len(ESTADO["btc_history"])>30: ESTADO["btc_history"]=ESTADO["btc_history"][-30:]
        for user_id, user_data in list(USUARIOS.items()):
            if not user_data["prendido"]: continue
            es_admin_id = int(user_id) in ADMINS_IDS
            user_data = reset_diario_si_corresponde(user_data)
            if not es_admin_id and user_data["pausa_hasta"] and isinstance(user_data["pausa_hasta"], datetime) and datetime.now()<user_data["pausa_hasta"]: continue
            if es_admin_id:
                analizar_mercado_y_elegir_modo(user_data); modo_elegido = user_data["modo"]; activo_base = random.choice(["BTC","BNB"])
                if modo_elegido == "RATA": es_ganada,gan,perd=random.random()<0.72,0.80,0.50; tp,sl=f"+0.2% {activo_base}",f"-0.4% {activo_base}"
                elif modo_elegido == "LOBO": es_ganada,gan,perd=random.random()<0.68,1.80,1.00; tp,sl=f"+0.5% {activo_base}",f"-0.8% {activo_base}"
                else: es_ganada,gan,perd=random.random()<0.60,3.20,1.50; tp,sl=f"+1.2% {activo_base}",f"-1.0% {activo_base}"
                user_data["estrategias"][modo_elegido]["ops"]+=1
                if es_ganada: user_data["estrategias"][modo_elegido]["ganadas"]+=1; user_data["estrategias"][modo_elegido]["neto"]=round(user_data["estrategias"][modo_elegido]["neto"]+gan,2)
                else: user_data["estrategias"][modo_elegido]["neto"]=round(user_data["estrategias"][modo_elegido]["neto"]-perd,2)
            else:
                factor=CACHORRO_PORC; activo_base=random.choice(["BTC","BNB"]); es_ganada,gan,perd=random.random()<0.66,0.60*factor,0.80*factor; tp,sl=f"+0.3% {activo_base}",f"-0.7% {activo_base}"
                user_data["estrategias"]["LOBO"]["ops"]+=1
                if es_ganada: user_data["estrategias"]["LOBO"]["ganadas"]+=1; user_data["estrategias"]["LOBO"]["neto"]=round(user_data["estrategias"]["LOBO"]["neto"]+gan,2)
                else: user_data["estrategias"]["LOBO"]["neto"]=round(user_data["estrategias"]["LOBO"]["neto"]-perd,2)
            modo_log = modo_elegido if es_admin_id else "CACHORRO"
            ahora = ahora_art()
            tipo = f"TP {tp}" if es_ganada else f"SL {sl}"
            monto = gan if es_ganada else -perd
            linea = f"{ahora.strftime('%d/%m/%Y %H:%M:%S')} - {activo_base} - {modo_log} - {tipo} = ${monto:+.2f}"
            user_data["historial"].append(linea)
            if es_ganada:
                user_data["ganadas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]+gan,2); user_data["balance"]=round(user_data["balance"]+gan,2)
                if activo_base == "BTC":
                    user_data["ganadas_btc"]+=1; user_data["ops_hoy_btc"]+=1; user_data["neto_hoy_btc"]=round(user_data["neto_hoy_btc"]+gan,2); user_data["balance_btc"]=round(user_data["balance_btc"]+gan,2)
                else:
                    user_data["ganadas_bnb"]+=1; user_data["ops_hoy_bnb"]+=1; user_data["neto_hoy_bnb"]=round(user_data["neto_hoy_bnb"]+gan,2); user_data["balance_bnb"]=round(user_data["balance_bnb"]+gan,2)
            else:
                user_data["perdidas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]-perd,2); user_data["balance"]=round(user_data["balance"]-perd,2)
                if activo_base == "BTC":
                    user_data["perdidas_btc"]+=1; user_data["ops_hoy_btc"]+=1; user_data["neto_hoy_btc"]=round(user_data["neto_hoy_btc"]-perd,2); user_data["balance_btc"]=round(user_data["balance_btc"]-perd,2)
                else:
                    user_data["perdidas_bnb"]+=1; user_data["ops_hoy_bnb"]+=1; user_data["neto_hoy_bnb"]=round(user_data["neto_hoy_bnb"]-perd,2); user_data["balance_bnb"]=round(user_data["balance_bnb"]-perd,2)
            if not es_admin_id and not es_ganada: user_data["pausa_hasta"]=datetime.now()+timedelta(minutes=10)
            if len(user_data["historial"])>200: user_data["historial"]=user_data["historial"][-200:]
        contador+=1
        if contador>=10: guardar_datos(); contador=0

@bot.message_handler(commands=['clearapi','delapi','resetdemo','reset','borrar'])
def comandos_limpieza(message):
    if not es_admin(message.chat.id):
        bot.reply_to(message, "⛔ Solo admin"); return
    txt = message.text.lower()
    if 'clearapi' in txt or 'delapi' in txt or 'borrar' in txt:
        ud=get_user_data(message.chat.id); ud["api_key"]=None; ud["api_secret"]=None; ud["api_cargada"]=False; guardar_datos()
        bot.reply_to(message, f"🧹 API BORRADA OK - Ahora DEMO ❌\nBalance ${ud['balance']:.2f} (BTC ${ud['balance_btc']:.2f} + BNB ${ud['balance_bnb']:.2f})", reply_markup=get_menu_botones(True))
    if 'resetdemo' in txt or txt.startswith('/reset'):
        USUARIOS[message.chat.id] = {"user_id": message.chat.id, "prendido": False, "balance": BALANCE_INICIAL, "capital_inicial": BALANCE_INICIAL,
            "balance_btc": BALANCE_BTC_INICIAL, "balance_bnb": BALANCE_BNB_INICIAL, "capital_btc": BALANCE_BTC_INICIAL, "capital_bnb": BALANCE_BNB_INICIAL,
            "neto_hoy_btc": 0.0, "neto_hoy_bnb": 0.0, "ops_hoy_btc": 0, "ops_hoy_bnb": 0, "ganadas_btc": 0, "ganadas_bnb": 0, "perdidas_btc": 0, "perdidas_bnb": 0,
            "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO", "mercado": "NORMAL BTC+BNB", "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False}
        try:
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        except: pass
        guardar_datos()
        bot.reply_to(message, f"🔄 RESET DEMO TOTAL OK - $200.00 LIMPIO ($100 BTC + $100 BNB)\nOps 0 - API ❌ DEMO", reply_markup=get_menu_botones(True))

@bot.message_handler(func=lambda m: m.text in ["🔄 RESET DEMO"])
def btn_reset(m):
    if not es_admin(m.chat.id): return
    USUARIOS[m.chat.id] = {"user_id": m.chat.id, "prendido": False, "balance": BALANCE_INICIAL, "capital_inicial": BALANCE_INICIAL,
            "balance_btc": BALANCE_BTC_INICIAL, "balance_bnb": BALANCE_BNB_INICIAL, "capital_btc": BALANCE_BTC_INICIAL, "capital_bnb": BALANCE_BNB_INICIAL,
            "neto_hoy_btc": 0.0, "neto_hoy_bnb": 0.0, "ops_hoy_btc": 0, "ops_hoy_bnb": 0, "ganadas_btc": 0, "ganadas_bnb": 0, "perdidas_btc": 0, "perdidas_bnb": 0,
            "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO", "mercado": "NORMAL BTC+BNB", "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False}
    try:
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
    except: pass
    guardar_datos()
    bot.send_message(m.chat.id, f"✅ DEMO $200 LIMPIO ($100 BTC + $100 BNB)", reply_markup=get_menu_botones(True))

@bot.message_handler(func=lambda m: m.text in ["🧹 CLEAR API"])
def btn_clear(m):
    if not es_admin(m.chat.id): return
    ud=get_user_data(m.chat.id); ud["api_key"]=None; ud["api_secret"]=None; ud["api_cargada"]=False; guardar_datos()
    bot.send_message(m.chat.id, "🧹 API LIMPIA - DEMO $200 ($100 BTC + $100 BNB)", reply_markup=get_menu_botones(True))

@bot.message_handler(commands=['setapi'])
def setapi_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(message.chat.id, "❌ Formato: /setapi TU_API_KEY TU_SECRET_KEY"); return
        api_key = parts[1].strip(); api_secret = parts[2].strip()
        if "TU_API" in api_key or len(api_key) < 20:
            bot.send_message(message.chat.id, "❌ API 'TU_API...' invalida, no cargada. Quedás en DEMO $200. Usa /clearapi"); return
        ud = get_user_data(message.chat.id); ud["api_key"] = api_key; ud["api_secret"] = api_secret; ud["api_cargada"] = True; guardar_datos()
        bot.send_message(message.chat.id, f"✅ API CARGADA {api_key[:6]}...{api_key[-4:]}", reply_markup=get_menu_botones(True))
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error API: {e}")

@bot.message_handler(commands=['id'])
def get_id(message):
    acceso,dias = tiene_acceso(message.chat.id); ud = get_user_data(message.chat.id)
    api_status = "✅ ADMIN VINCULADA" if ud.get("api_cargada") and es_admin(message.chat.id) else ("✅ CARGADA" if ud.get("api_cargada") else "❌ FALTA /setapi - DEMO $200")
    plan = ESTADO["socios"].get(message.chat.id, {}).get("plan","CACHORRO") if not es_admin(message.chat.id) else "ADMIN"
    bot.send_message(message.chat.id,f"🆔 Tu ID es: {message.chat.id}\n📦 Plan: {plan} - ⏳ Quedan {dias} dias\n🔑 API: {api_status}\n💰 $200 DEMO ($100 BTC + $100 BNB)\n🔗 Link: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🆔 ID"])
def btn_id(message): return get_id(message)

@bot.message_handler(func=lambda m: m.text in ["📈 ESTRATEGIAS", "/estrategias"])
def estrategias(message):
    ud=get_user_data(message.chat.id); est=ud["estrategias"]
    txt=f"📈 V26.8.6 B-200 - {ud['caja']}\nModo: {ud['modo']}\nMercado: {ud['mercado']}\n\nRATA: {est['RATA']['ops']} ops Win {calcular_winrate_estrategia(est['RATA'])}% Neto ${est['RATA']['neto']}\nLOBO: {est['LOBO']['ops']} ops Win {calcular_winrate_estrategia(est['LOBO'])}% Neto ${est['LOBO']['neto']}\nTIBURON: {est['TIBURON']['ops']} ops Win {calcular_winrate_estrategia(est['TIBURON'])}% Neto ${est['TIBURON']['neto']}\n\n💰 BTC: ${ud['balance_btc']:.2f} (Neto {ud['neto_hoy_btc']:+.2f} Ops {ud['ops_hoy_btc']})\n💰 BNB: ${ud['balance_bnb']:.2f} (Neto {ud['neto_hoy_bnb']:+.2f} Ops {ud['ops_hoy_bnb']})\n\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id); ud=get_user_data(message.chat.id)
    if es_admin(message.chat.id): bot.send_message(message.chat.id,f"👋 V26.8.6 B-200 SIN TABLA 🐺\nBalance ${ud['balance']:.2f} (BTC ${ud['balance_btc']:.2f} + BNB ${ud['balance_bnb']:.2f}) - {ud['modo']}\n{ud['mercado']}\nTu web: {WEB_URL}", reply_markup=get_menu_botones(True))
    else:
        if not acceso: bot.send_message(message.chat.id, BIENVENIDA + f"\n\nTu ID: {message.chat.id}\nTocá 🐺 QUIERO LOBO", reply_markup=get_menu_botones(False))
        else: bot.send_message(message.chat.id,f"👋 MANADA V26.8.6 B-200\n📦 Plan: {ESTADO['socios'][message.chat.id]['plan']} - ⏳ {dias_rest} dias\n⚙️ Modo: {ud['modo']}\nWeb: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(False))

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/prender"])
def prender(message):
    acceso,_=tiene_acceso(message.chat.id)
    if not acceso and not es_admin(message.chat.id): bot.send_message(message.chat.id,"⛔ Vencido - Tocá 💰 PAGAR", reply_markup=get_menu_botones(False)); return
    user_data = get_user_data(message.chat.id)
    user_data["prendido"]=True; user_data["pausa_hasta"]=None
    analizar_mercado_y_elegir_modo(user_data); guardar_datos()
    bot.send_message(message.chat.id,f"🚀 {user_data['caja']} ACTIVADA - ${user_data['balance']} (BTC ${user_data['balance_btc']:.2f} + BNB ${user_data['balance_bnb']:.2f})\nModo {user_data['modo']} - {user_data['mercado']}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance", "/miplan"])
def balance(message):
    acceso,dias = tiene_acceso(message.chat.id)
    if not acceso and not es_admin(message.chat.id):
        bot.send_message(message.chat.id,"⛔ Plan vencido. Tocá 💰 PAGAR", reply_markup=get_menu_botones(False)); return
    ud = get_user_data(message.chat.id); win=calcular_winrate(ud)
    capital_inicial = ud.get("capital_inicial", BALANCE_INICIAL)
    ganancia_hoy = ud["neto_hoy"]; balance_total = ud["balance"]; ganancia_total = balance_total - capital_inicial
    capital_btc = ud.get("capital_btc", BALANCE_BTC_INICIAL)
    capital_bnb = ud.get("capital_bnb", BALANCE_BNB_INICIAL)
    balance_btc = ud.get("balance_btc", BALANCE_BTC_INICIAL)
    balance_bnb = ud.get("balance_bnb", BALANCE_BNB_INICIAL)
    neto_btc = ud.get("neto_hoy_btc", 0.0)
    neto_bnb = ud.get("neto_hoy_bnb", 0.0)
    ganancia_btc_total = balance_btc - capital_btc
    ganancia_bnb_total = balance_bnb - capital_bnb
    plan_actual = ESTADO["socios"].get(message.chat.id, {}).get("plan","ADMIN BASE SOLIDA - DEMO $200") if not es_admin(message.chat.id) else "ADMIN BASE SOLIDA - DEMO $200"
    vence_txt = ESTADO["socios"].get(message.chat.id, {}).get("vence"); vence_str = vence_txt.strftime("%d/%m/%Y") if vence_txt else "Ilimitado"
    api_status = "✅ ADMIN" if ud.get("api_cargada") and es_admin(message.chat.id) else ("✅" if ud.get("api_cargada") else "❌ DEMO $200")
    texto = f"""💰 {ud['caja']} - BALANCE DETALLADO V26.8.6

💵 Capital Inicial: ${capital_inicial:.2f} ($100 BTC + $100 BNB)
📈 Ganancia Hoy: ${ganancia_hoy:+.2f}
💼 Ganancia Total: ${ganancia_total:+.2f}
💰 Balance Total Actual: ${balance_total:.2f}

--- 🔶 DETALLE BNB SEPARADO ---
₿ BTC Capital: ${capital_btc:.2f} | Balance: ${balance_btc:.2f} | Hoy: ${neto_btc:+.2f} | Total: ${ganancia_btc_total:+.2f}
🔶 BNB Capital: ${capital_bnb:.2f} | Balance: ${balance_bnb:.2f} | Hoy: ${neto_bnb:+.2f} | Total: ${ganancia_bnb_total:+.2f}

✅ Ops Ganadas Hoy: {ud['ganadas']} (BTC {ud.get('ganadas_btc',0)} / BNB {ud.get('ganadas_bnb',0)})
❌ Ops Perdidas Hoy: {ud['perdidas']} (BTC {ud.get('perdidas_btc',0)} / BNB {ud.get('perdidas_bnb',0)})
🔄 Total Ops Hoy: {ud['ops_hoy']} (BTC {ud.get('ops_hoy_btc',0)} + BNB {ud.get('ops_hoy_bnb',0)})
🎯 Winrate Hoy: {win}%

⚙️ Modo: {ud['modo']}
📊 Mercado: {ud['mercado']}
📦 Plan: {plan_actual}
⏳ Te quedan: {dias} dias - Vence {vence_str}
🔑 API: {api_status} - Requisito $100 BTC + $100 BNB

₿ BTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}
💵 Dolar: ${DOLAR_CRIPTO['valor']} ({DOLAR_CRIPTO['actualizado']})
🕒 Actualizado: {ahora_art().strftime('%d/%m/%Y %H:%M:%S')} ART
V26.8.6 SIN TABLA"""
    bot.send_message(message.chat.id, texto, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL", "/historial"])
def historial(message):
    ud = get_user_data(message.chat.id); ahora = ahora_art(); hoy = ahora.date()
    hist_hoy = [h for h in ud["historial"] if hoy.strftime('%d/%m/%Y') in h]
    txt = f"📜 {ud['caja']} - HISTORIAL\n\n📅 HOY {hoy.strftime('%d/%m/%Y')} - {len(hist_hoy)} ops\nBTC {ud.get('ops_hoy_btc',0)} ops / BNB {ud.get('ops_hoy_bnb',0)} ops\n"
    txt += "\n".join(hist_hoy[-15:]) if hist_hoy else "Sin ops hoy"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["💰 PAGAR", "/pagar"])
def pagar(message):
    dolar = DOLAR_CRIPTO['valor']; ud = get_user_data(message.chat.id)
    api_status = "✅ CARGADA" if ud.get("api_cargada") else "❌ FALTA - DEMO $200"
    txt = f"""💰 PAGAR V26.8.6\nDolar: ${dolar} - API: {api_status}\nAlias MP: {ALIAS_MP_DEMO}\nDEMO $200 limpio ($100 BTC + $100 BNB) - Tocá PRENDER para probar"""
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🐺 QUIERO LOBO", "/quierolobo", "/planes"])
def quiero_lobo(message):
    dolar = DOLAR_CRIPTO['valor']
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"🐀 RATA $20/mes", callback_data="plan_RATA"), types.InlineKeyboardButton(f"🐺 LOBO $40/mes", callback_data="plan_LOBO"), types.InlineKeyboardButton(f"🦈 TIBURON $60/mes", callback_data="plan_TIBURON"))
    bot.send_message(message.chat.id, f"🐺 ELEGÍ TU MODO - DEMO $200 ($100 BTC + $100 BNB)\nDolar ${dolar}\nAlias {ALIAS_MP_DEMO}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("plan_"))
def callback_plan(call):
    plan = call.data.split("_")[1]; bot.answer_callback_query(call.id, f"Elegiste {plan}")
    bot.send_message(call.message.chat.id, f"✅ Elegiste {plan}\nAlias MP: {ALIAS_MP_DEMO}", reply_markup=get_menu_botones(False))

def enviar_lista_socios(chat_id):
    if not ESTADO["socios"]:
        bot.send_message(chat_id, "👥 Sin socios", reply_markup=get_menu_botones(True)); return
    bot.send_message(chat_id, f"👥 SOCIOS - {len(ESTADO['socios'])} activos", reply_markup=get_menu_botones(True))
    for cid,d in list(ESTADO["socios"].items()):
        dias=(d["vence"]-datetime.now()).days; u = USUARIOS.get(cid, {"balance":200,"ops_hoy":0,"neto_hoy":0,"ganadas":0,"perdidas":0}); win = calcular_winrate(u)
        txt = f"👤 {cid}\n📦 {d['plan']} - ⏳ {dias}d\n💰 ${u['balance']} | 📈 ${u['neto_hoy']} (BTC ${u.get('balance_btc',100):.2f} + BNB ${u.get('balance_bnb',100):.2f}) | {u.get('modo','-')} | {u.get('mercado','-')}"
        bot.send_message(chat_id, txt)

@bot.message_handler(commands=['alta','socios'])
def admin_cmds(message):
    if not es_admin(message.chat.id): return
    if message.text.startswith('/alta'):
        try:
            parts=message.text.split(); id_cliente=int(parts[1]); dias=int(parts[2]); plan=parts[3].upper() if len(parts)>3 else "CACHORRO"
            vence=datetime.now()+timedelta(days=dias); ESTADO["socios"][id_cliente]={"alta":datetime.now(),"vence":vence,"plan":plan}
            ud = get_user_data(id_cliente); ud["balance"]=200.0; ud["capital_inicial"]=200.0; ud["balance_btc"]=100.0; ud["balance_bnb"]=100.0; ud["capital_btc"]=100.0; ud["capital_bnb"]=100.0; ud["neto_hoy"]=0; ud["neto_hoy_btc"]=0; ud["neto_hoy_bnb"]=0; ud["ops_hoy"]=0; ud["ops_hoy_btc"]=0; ud["ops_hoy_bnb"]=0; ud["ganadas"]=0; ud["ganadas_btc"]=0; ud["ganadas_bnb"]=0; ud["perdidas"]=0; ud["perdidas_btc"]=0; ud["perdidas_bnb"]=0; ud["historial"]=[]; ud["prendido"]=False
            guardar_datos(); bot.send_message(message.chat.id,f"✅ Alta {id_cliente} {plan} {dias}d ($100 BTC + $100 BNB)")
        except Exception as e: bot.send_message(message.chat.id,f"Error: {e}")
    elif message.text.startswith('/socios'):
        enviar_lista_socios(message.chat.id)

@bot.message_handler(func=lambda m: m.text in ["👥 SOCIOS"])
def btn_socios(message):
    if not es_admin(message.chat.id): bot.send_message(message.chat.id,"⛔ Solo admin", reply_markup=get_menu_botones(False)); return
    enviar_lista_socios(message.chat.id)

# --- HTML FINAL SIN TABLA + ADMIN VE SOCIOS / SOCIO VE INVERSION+TOTAL DIA ---
HTML="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>V26.8.6 B-200 SIN TABLA</title><script src="https://s3.tradingview.com/tv.js"></script><style>
body{margin:0;background:#0f1115;color:#d1d4dc;font-family:Arial}
.header{background:#1e222d;padding:15px;border-bottom:2px solid #00ffea}
.box{padding:14px;margin:10px;border-radius:12px;font-size:13px;line-height:1.9}
.admin{background:#0d2a4a;border-left:5px solid #00ffea}
.kpi{display:inline-block;background:#1e222d;padding:10px 14px;border-radius:10px;margin:5px;font-size:13px;border:1px solid #2a2e39;min-width:120px;text-align:center}
.kpi.btc{border-color:#26a69a}.kpi.bnb{border-color:#f3ba2f}.kpi.total{border-color:#00ffea;font-weight:bold;min-width:170px;font-size:14px}.kpi.modo{border-color:#ff5252}
#chart_btc{height:45vh;margin:10px;border-radius:12px;overflow:hidden;border:1px solid #2a2e39}
#chart_bnb{height:35vh;margin:10px;border-radius:12px;overflow:hidden;border:1px solid #2a2e39}
.socios{margin:10px;background:#1e222d;padding:12px;border-radius:12px}
.socio-card{background:#131722;padding:10px;margin:6px 0;border-radius:8px;border-left:3px solid #00ffea;display:flex;justify-content:space-between;flex-wrap:wrap}
h3{margin:15px 10px 5px 10px;color:#00ffea}
</style></head><body>
<div class="header"><b id="titulo">V26.8.6 B-200</b><div id="admin" class="box admin">Cargando...</div></div>
<div id="chart_btc"></div><div id="chart_bnb"></div>
<div id="bloqueSocios"><h3>👥 Socios - Cómo les va (Solo Admin)</h3><div id="socios" class="socios">Cargando socios...</div></div>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"1","theme":"dark","container_id":"chart_btc"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"1","theme":"dark","container_id":"chart_bnb"});
function getId(){return new URLSearchParams(window.location.search).get('id');}
async function load(){
  let idParam=getId();
  let url=idParam?`/api/data?id=${idParam}`:'/api/data';
  let a=await (await fetch(url)).json();
  if(idParam){
    document.getElementById('titulo').innerText=`💼 TU PLATA CRECIENDO - ${a.modo}`;
    document.getElementById('admin').innerHTML=`
      <span class="kpi total">💵 Inversión<br>$${a.capital_inicial.toFixed(2)}<br><small>$100 BTC + $100 BNB</small></span>
      <span class="kpi total">📈 Total del Día<br>$${a.neto_hoy>=0?'+':''}${a.neto_hoy.toFixed(2)}<br><small>${a.ops_hoy} ops | ${a.winrate}%</small></span>
      <span class="kpi total">💰 Balance<br>$${a.balance.toFixed(2)}</span><br>
      <span class="kpi btc">₿ BTC $${a.balance_btc.toFixed(2)}<br><small>Hoy ${a.neto_hoy_btc>=0?'+':''}${a.neto_hoy_btc.toFixed(2)}</small></span>
      <span class="kpi bnb">🔶 BNB $${a.balance_bnb.toFixed(2)}<br><small>Hoy ${a.neto_hoy_bnb.toFixed(2)}</small></span>
      <span class="kpi modo">🐺 ${a.modo}<br><small>${a.mercado}</small></span>
    `;
    document.getElementById('bloqueSocios').style.display='none';
  } else {
    document.getElementById('titulo').innerText=`V26.8.6 ADMIN - $100 BTC + $100 BNB + SOCIOS`;
    document.getElementById('admin').innerHTML=`
      <b>🔵 ADMIN $200 (BTC $${a.balance_btc.toFixed(2)} + BNB $${a.balance_bnb.toFixed(2)}) - ${a.modo}</b><br>
      <span class="kpi total">Total $${a.balance.toFixed(2)} | Hoy $${a.neto_hoy>=0?'+':''}${a.neto_hoy.toFixed(2)}</span>
      <span class="kpi btc">BTC $${a.balance_btc.toFixed(2)} Hoy ${a.neto_hoy_btc.toFixed(2)} Ops ${a.ops_hoy_btc}</span>
      <span class="kpi bnb">BNB $${a.balance_bnb.toFixed(2)} Hoy ${a.neto_hoy_bnb.toFixed(2)} Ops ${a.ops_hoy_bnb}</span>
      <span class="kpi">🎯 ${a.winrate}% | ${a.ops_hoy} ops</span>
      <span class="kpi modo">${a.modo}<br>${a.mercado}</span><br>
      <span class="kpi">₿ BTC $${a.btc} | 🔶 BNB $${a.bnb} | Gan ${a.ganadas} Per ${a.perdidas}</span>
    `;
    document.getElementById('bloqueSocios').style.display='block';
    try{
      let s=await (await fetch('/api/socios')).json();let h='';
      if(Object.keys(s.socios).length==0)h='Sin socios - usa /alta ID DIAS PLAN';
      else{for(let id in s.socios){let u=s.socios[id];h+=`<div class="socio-card"><div><b>👤 ${id}</b> 📦 ${u.plan} ⏳ ${u.vence_dias}d<br>💰 Total $${u.balance.toFixed(2)} (BTC $${u.balance_btc.toFixed(2)} + BNB $${u.balance_bnb.toFixed(2)}) | 📈 Día $${u.neto_hoy.toFixed(2)} | 🎯 ${u.winrate}% | ${u.modo}<br><small>${u.mercado}</small></div><div><a href="/?id=${id}" style="color:#00ffea">Ver</a></div></div>`;}}
      document.getElementById('socios').innerHTML=h;
    }catch(e){document.getElementById('socios').innerHTML='Error cargando socios';}
  }
}
setInterval(load,2500);load();
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    id_q = request.args.get('id', None)
    if id_q and id_q.isdigit():
        target_id = int(id_q)
        a = get_user_data(target_id)
        es_admin_req = target_id in ADMINS_IDS
    else:
        target_id = ADMINS_IDS[0]
        a = get_user_data(target_id)
        es_admin_req = True
    est_out={k:{"ops":v["ops"],"winrate":calcular_winrate_estrategia(v),"neto":v["neto"]} for k,v in a["estrategias"].items()}
    return jsonify({
        "balance":a["balance"],"balance_btc":a.get("balance_btc",100),"balance_bnb":a.get("balance_bnb",100),
        "capital_inicial":a.get("capital_inicial",200),
        "neto_hoy":a["neto_hoy"],"neto_hoy_btc":a.get("neto_hoy_btc",0),"neto_hoy_bnb":a.get("neto_hoy_bnb",0),
        "ops_hoy":a["ops_hoy"],"ops_hoy_btc":a.get("ops_hoy_btc",0),"ops_hoy_bnb":a.get("ops_hoy_bnb",0),
        "ganadas":a.get("ganadas",0),"ganadas_btc":a.get("ganadas_btc",0),"ganadas_bnb":a.get("ganadas_bnb",0),
        "perdidas":a.get("perdidas",0),"perdidas_btc":a.get("perdidas_btc",0),"perdidas_bnb":a.get("perdidas_bnb",0),
        "winrate":calcular_winrate(a),"modo":a["modo"],"mercado":a["mercado"],
        "btc":ESTADO["btc"],"bnb":ESTADO["bnb"],"estrategias":est_out,"dolar":DOLAR_CRIPTO,"es_admin":es_admin_req
    })

@app.route('/api/socios')
def api_socios():
    out={}
    for cid,d in ESTADO["socios"].items():
        u=USUARIOS.get(cid,{"balance":200,"balance_btc":100,"balance_bnb":100,"ops_hoy":0,"neto_hoy":0,"ganadas":0,"perdidas":0,"modo":"CACHORRO","mercado":"CACHORRO","ops_hoy_btc":0,"ops_hoy_bnb":0})
        out[cid]={"balance":u["balance"],"balance_btc":u.get("balance_btc",100),"balance_bnb":u.get("balance_bnb",100),"ops":u["ops_hoy"],"ops_btc":u.get("ops_hoy_btc",0),"ops_bnb":u.get("ops_hoy_bnb",0),"plan":d["plan"],"neto_hoy":u["neto_hoy"],"winrate":calcular_winrate(u),"modo":u["modo"],"mercado":u["mercado"],"vence_dias":(d["vence"]-datetime.now()).days if (d["vence"]-datetime.now()).total_seconds()>0 else 0}
    return jsonify({"socios":out})

def run_bot(): bot.infinity_polling(skip_pending=True)
threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()
threading.Thread(target=actualizar_dolar, daemon=True).start()
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
