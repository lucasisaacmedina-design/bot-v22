import os
import json
import threading
import random
import time
import requests
import base64
import hashlib
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

def _get_encrypt_key():
    k = os.getenv("ENCRYPT_KEY", "manada-v27-key-segura-lobo-2026")
    return hashlib.sha256(k.encode()).digest()[:32]

def encriptar_api(texto):
    if not texto: return None
    try:
        from cryptography.fernet import Fernet
        f = Fernet(base64.urlsafe_b64encode(_get_encrypt_key()))
        return f.encrypt(texto.encode()).decode()
    except:
        key = _get_encrypt_key()
        enc = bytes([b ^ key[i % len(key)] for i, b in enumerate(texto.encode())])
        return base64.b64encode(enc).decode()

def desencriptar_api(token_enc):
    if not token_enc: return None
    try:
        from cryptography.fernet import Fernet
        f = Fernet(base64.urlsafe_b64encode(_get_encrypt_key()))
        return f.decrypt(token_enc.encode()).decode()
    except:
        try:
            key = _get_encrypt_key()
            enc = base64.b64decode(token_enc.encode())
            dec = bytes([b ^ key[i % len(key)] for i, b in enumerate(enc)])
            return dec.decode()
        except: return None

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN: raise Exception("Falta BOT_TOKEN en Render")
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
ALIAS_BRUBANK = "manada.lobo.bru"
DOLAR_CRIPTO = {"valor": 1480, "actualizado": "inicio", "fuente": "BRUBANK"}
PLANES = {"RATA":20,"LOBO":40,"TIBURON":60}
print(f"### V28 ALQUILER FINAL - SIN BOTON ID - AUTOMATICO ###")
ESTADO = {"btc": 78287.4, "bnb": 739.68, "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)], "socios": {}, "admins": ADMINS_IDS}
USUARIOS = {}
LOCK = threading.Lock()
try: bot.delete_my_commands(); bot.set_my_commands([])
except: pass

def ahora_art(): return datetime.now(TZ)
def reset_diario_si_corresponde(user_data):
    ahora = ahora_art(); hoy_str = ahora.strftime('%d/%m/%Y'); ultimo = user_data.get('ultimo_reset', '')
    if ultimo!= hoy_str:
        if user_data.get('ops_hoy', 0) > 0:
            if 'historial_diario' not in user_data: user_data['historial_diario'] = []
            user_data['historial_diario'].append({'fecha': ultimo or hoy_str,'ops': user_data.get('ops_hoy', 0),'ganadas': user_data.get('ganadas', 0),'perdidas': user_data.get('perdidas', 0),'neto': user_data.get('neto_hoy', 0.0),'neto_btc': user_data.get('neto_hoy_btc', 0.0),'neto_bnb': user_data.get('neto_hoy_bnb', 0.0)})
            user_data['historial_diario'] = user_data['historial_diario'][-30:]
        user_data['ops_hoy']=0; user_data['ganadas']=0; user_data['perdidas']=0; user_data['neto_hoy']=0.0
        user_data['neto_hoy_btc']=0.0; user_data['neto_hoy_bnb']=0.0; user_data['ops_hoy_btc']=0; user_data['ops_hoy_bnb']=0
        user_data['ganadas_btc']=0; user_data['ganadas_bnb']=0; user_data['perdidas_btc']=0; user_data['perdidas_bnb']=0
        user_data['ultimo_reset']=hoy_str
    return user_data

def actualizar_dolar():
    while True:
        try:
            r = requests.get("https://criptoya.com/api/dolar", timeout=10).json()
            if r and 'cripto' in r and 'ccb' in r['cripto']: DOLAR_CRIPTO["valor"]=int(float(r['cripto']['ccb'])); DOLAR_CRIPTO["actualizado"]=ahora_art().strftime("%H:%M")
            else: DOLAR_CRIPTO["actualizado"]=ahora_art().strftime("%H:%M")
        except: DOLAR_CRIPTO["valor"]+=random.randint(-5,5); DOLAR_CRIPTO["actualizado"]=ahora_art().strftime("%H:%M")
        time.sleep(1800)

BIENVENIDA = """👋 MANADA V28 - BRUBANK + API SEGURA + ALQUILER 🐺
Hola Lobo, bienvenido a la manada mas unica y exclusiva.
REQUISITO UNICO: $50 BTC + $50 BNB en TU Binance + API Trading (sin retiros)
Tu plata siempre en TU Binance, cada uno opera SU bot con SU plata.
Cargá API con 🔑 CARGAR API (encriptada) y pedí ALTA CACHORRO 20% x 7 dias
PACKS: RATA $20/mes 40% = solo RATA - LOBO $40/mes 60% = RATA+LOBO - TIBURON $60/mes 100% = RATA+LOBO+TIBURON completo
Alias: manada.lobo.bru (Brubank)
"""
TEXTO_PAGAR = """💰 COMO PAGAR? BRUBANK - V28 ACUMULATIVO
Alias: manada.lobo.bru
RATA $20 = solo RATA 40%
LOBO $40 = RATA+LOBO 60%
TIBURON $60 = RATA+LOBO+TIBURON 100%
CACHORRO = TIBURON completo al 20% x 7 dias GRATIS
"""

def get_menu_botones(admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if admin:
        # ADMIN - SIN ID - 5 LOGICOS
        markup.add(types.KeyboardButton("🔑 CARGAR API"))
        markup.add(types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("📜 HISTORIAL"))
        markup.add(types.KeyboardButton("💸 RETIRAR"))
        markup.add(types.KeyboardButton("👥 SOCIOS"))
    else:
        # SOCIO - SIN ID - 6 LOGICOS
        markup.add(types.KeyboardButton("🔑 CARGAR API"))
        markup.add(types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("📜 HISTORIAL"))
        markup.add(types.KeyboardButton("💸 RETIRAR"))
        markup.add(types.KeyboardButton("🐺 QUIERO LOBO"))
        markup.add(types.KeyboardButton("🔻 SOLICITAR BAJA"))
    return markup

def guardar_datos():
    try:
        with LOCK:
            socios_ser = {str(k): {"alta": v["alta"].isoformat(), "vence": v["vence"].isoformat(), "plan": v["plan"]} for k,v in ESTADO["socios"].items()}
            usuarios_ser = {}
            for k,v in USUARIOS.items():
                vd = v.copy()
                if vd.get("pausa_hasta") and isinstance(vd["pausa_hasta"], datetime): vd["pausa_hasta"] = vd["pausa_hasta"].isoformat()
                vd["historial"] = vd.get("historial", [])[-200:]; usuarios_ser[str(k)] = vd
            with open(DATA_FILE+".tmp", "w", encoding="utf-8") as f: json.dump({"socios": socios_ser, "usuarios": usuarios_ser}, f)
            os.replace(DATA_FILE+".tmp", DATA_FILE)
    except Exception as e: print(f"Error guardando: {e}")

def cargar_datos():
    try:
        if not os.path.exists(DATA_FILE): return
        with open(DATA_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        for k,v in data.get("socios", {}).items():
            try: ESTADO["socios"][int(k)] = {"alta": datetime.fromisoformat(v["alta"]), "vence": datetime.fromisoformat(v["vence"]), "plan": v["plan"]}
            except: pass
        for k,v in data.get("usuarios", {}).items():
            try:
                if v.get("pausa_hasta"):
                    try: v["pausa_hasta"] = datetime.fromisoformat(v["pausa_hasta"])
                    except: v["pausa_hasta"] = None
                USUARIOS[int(k)] = v
            except: pass
    except: pass

cargar_datos()

def get_user_data(user_id):
    user_id = int(user_id); es_admin_id = user_id in ADMINS_IDS
    if user_id not in USUARIOS:
        USUARIOS[user_id] = {"user_id": user_id, "prendido": False, "balance": BALANCE_INICIAL, "capital_inicial": BALANCE_INICIAL,"balance_btc": BALANCE_BTC_INICIAL, "balance_bnb": BALANCE_BNB_INICIAL,"capital_btc": BALANCE_BTC_INICIAL, "capital_bnb": BALANCE_BNB_INICIAL,"neto_hoy_btc": 0.0, "neto_hoy_bnb": 0.0,"ops_hoy_btc": 0, "ops_hoy_bnb": 0,"ganadas_btc": 0, "ganadas_bnb": 0,"perdidas_btc": 0, "perdidas_bnb": 0,"ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO" if es_admin_id else "CACHORRO", "mercado": "BASE SOLIDA BTC+BNB" if es_admin_id else "CACHORRO TIBURON 20% (RATA+LOBO+TIBURON)", "pausa_hasta": None, "historial": [], "caja": "ADMIN TIBURON 100% - TU PLATA" if es_admin_id else "SOCIO ALQUILER - TU PLATA", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False, "api_encriptada": False, "pendiente_pago": None}
        guardar_datos()
    for k in ["RATA","LOBO","TIBURON"]:
        if k not in USUARIOS[user_id]["estrategias"]: USUARIOS[user_id]["estrategias"][k] = {"ops":0,"ganadas":0,"neto":0.0}
    if "api_key" not in USUARIOS[user_id]: USUARIOS[user_id]["api_key"]=None
    if "api_secret" not in USUARIOS[user_id]: USUARIOS[user_id]["api_secret"]=None
    if "api_cargada" not in USUARIOS[user_id]: USUARIOS[user_id]["api_cargada"]=False
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

def calcular_winrate(u):
    total = u["ganadas"] + u["perdidas"]
    return round((u["ganadas"]/total)*100) if total else 0

def calcular_winrate_estrategia(e):
    return round((e["ganadas"]/e["ops"])*100) if e["ops"] else 0

def get_estado_texto(u):
    if not u["prendido"]: return "🔴 APAGADO"
    if u["pausa_hasta"] and isinstance(u["pausa_hasta"], datetime) and datetime.now() < u["pausa_hasta"]: return f"⏸️ Pausa"
    return "🟢 PRENDIDO"

def analizar_mercado_y_elegir_modo(u):
    try: ultimos=ESTADO["btc_history"][-10:]; atr=round((max(ultimos)-min(ultimos))/ESTADO["btc"]*100,2)
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
            if not es_admin_id:
                acceso, _ = tiene_acceso(user_id)
                if not acceso:
                    user_data["prendido"]=False
                    try:
                        generado = round(user_data["balance"] - user_data.get("capital_inicial", BALANCE_INICIAL), 2)
                        kb_pack = types.InlineKeyboardMarkup(row_width=1)
                        kb_pack.add(types.InlineKeyboardButton(f"🐀 RATA $20 40%", callback_data="plan_RATA"),types.InlineKeyboardButton(f"🐺 LOBO $40 60%", callback_data="plan_LOBO"),types.InlineKeyboardButton(f"🦈 TIBURON $60 100%", callback_data="plan_TIBURON"))
                        bot.send_message(user_id, f"🐺 CACHORRO FINALIZADO - TU BOT PAUSADO\nGeneraste: ${generado:.2f} en TU Binance\nElegí pack para seguir al 100%:", reply_markup=kb_pack)
                        kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton(f"➕ ALTA PENDIENTE {user_id}", callback_data=f"espera_{user_id}"))
                        bot.send_message(ADMINS_IDS[0], f"⚠️ CACHORRO {user_id} VENCIDO - Generó ${generado:.2f} - Su bot pausado.", reply_markup=kb)
                    except: pass
                    continue
                if user_data["pausa_hasta"] and isinstance(user_data["pausa_hasta"], datetime) and datetime.now()<user_data["pausa_hasta"]: continue

            if es_admin_id:
                analizar_mercado_y_elegir_modo(user_data); modo_elegido = user_data["modo"]; factor = 1.0
                activo_base = random.choice(["BTC","BNB"])
                if modo_elegido == "RATA": es_ganada,gan,perd=random.random()<0.72,0.80,0.50; tp,sl=f"+0.2% {activo_base}",f"-0.4% {activo_base}"
                elif modo_elegido == "LOBO": es_ganada,gan,perd=random.random()<0.68,1.80,1.00; tp,sl=f"+0.5% {activo_base}",f"-0.8% {activo_base}"
                else: es_ganada,gan,perd=random.random()<0.60,3.20,1.50; tp,sl=f"+1.2% {activo_base}",f"-1.0% {activo_base}"
            else:
                plan_actual = ESTADO["socios"].get(user_id, {}).get("plan","CACHORRO")
                activo_base = random.choice(["BTC","BNB"])
                if plan_actual == "CACHORRO": modo_elegido = random.choice(["RATA","LOBO","TIBURON"]); factor = CACHORRO_PORC
                elif plan_actual == "RATA": modo_elegido = "RATA"; factor = 1.0
                elif plan_actual == "LOBO": modo_elegido = random.choice(["RATA","LOBO"]); factor = 1.0
                else: modo_elegido = random.choice(["RATA","LOBO","TIBURON"]); factor = 1.0
                if modo_elegido == "RATA": es_ganada,gan,perd=random.random()<0.72,0.80,0.50; tp,sl=f"+0.2% {activo_base}",f"-0.4% {activo_base}"
                elif modo_elegido == "LOBO": es_ganada,gan,perd=random.random()<0.68,1.80,1.00; tp,sl=f"+0.5% {activo_base}",f"-0.8% {activo_base}"
                else: es_ganada,gan,perd=random.random()<0.60,3.20,1.50; tp,sl=f"+1.2% {activo_base}",f"-1.0% {activo_base}"
                if plan_actual == "CACHORRO": gan=round(gan*factor,2); perd=round(perd*factor,2)

            user_data["estrategias"][modo_elegido]["ops"]+=1
            if es_ganada: user_data["estrategias"][modo_elegido]["ganadas"]+=1; user_data["estrategias"][modo_elegido]["neto"]=round(user_data["estrategias"][modo_elegido]["neto"]+gan,2)
            else: user_data["estrategias"][modo_elegido]["neto"]=round(user_data["estrategias"][modo_elegido]["neto"]-perd,2)
            modo_log = modo_elegido if es_admin_id else f"{modo_elegido} {ESTADO['socios'].get(user_id,{}).get('plan','CACHORRO')}"
            ahora = ahora_art(); tipo = f"TP {tp}" if es_ganada else f"SL {sl}"; monto = gan if es_ganada else -perd
            linea = f"{ahora.strftime('%d/%m/%Y %H:%M:%S')} - {activo_base} - {modo_log} - {tipo} = ${monto:+.2f}"
            user_data["historial"].append(linea)
            if es_ganada:
                user_data["ganadas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]+gan,2); user_data["balance"]=round(user_data["balance"]+gan,2)
                if activo_base == "BTC": user_data["ganadas_btc"]+=1; user_data["ops_hoy_btc"]+=1; user_data["neto_hoy_btc"]=round(user_data["neto_hoy_btc"]+gan,2); user_data["balance_btc"]=round(user_data["balance_btc"]+gan,2)
                else: user_data["ganadas_bnb"]+=1; user_data["ops_hoy_bnb"]+=1; user_data["neto_hoy_bnb"]=round(user_data["neto_hoy_bnb"]+gan,2); user_data["balance_bnb"]=round(user_data["balance_bnb"]+gan,2)
            else:
                user_data["perdidas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]-perd,2); user_data["balance"]=round(user_data["balance"]-perd,2)
                if activo_base == "BTC": user_data["perdidas_btc"]+=1; user_data["ops_hoy_btc"]+=1; user_data["neto_hoy_btc"]=round(user_data["neto_hoy_btc"]-perd,2); user_data["balance_btc"]=round(user_data["balance_btc"]-perd,2)
                else: user_data["perdidas_bnb"]+=1; user_data["ops_hoy_bnb"]+=1; user_data["neto_hoy_bnb"]=round(user_data["neto_hoy_bnb"]-perd,2); user_data["balance_bnb"]=round(user_data["balance_bnb"]-perd,2)
            if len(user_data["historial"])>200: user_data["historial"]=user_data["historial"][-200:]
        contador+=1
        if contador>=10: guardar_datos(); contador=0

@bot.message_handler(commands=['clearapi','delapi','resetdemo','reset','borrar'])
def comandos_limpieza(message):
    if not es_admin(message.chat.id): bot.reply_to(message, "⛔ Solo admin"); return
    txt = message.text.lower()
    if 'clearapi' in txt or 'delapi' in txt or 'borrar' in txt:
        ud=get_user_data(message.chat.id); ud["api_key"]=None; ud["api_secret"]=None; ud["api_cargada"]=False; ud["api_encriptada"]=False; guardar_datos()
        bot.reply_to(message, f"🧹 API BORRADA OK - Ahora DEMO ❌\nBalance ${ud['balance']:.2f}", reply_markup=get_menu_botones(True))
    if 'resetdemo' in txt or txt.startswith('/reset'):
        USUARIOS[message.chat.id] = {"user_id": message.chat.id, "prendido": False, "balance": BALANCE_INICIAL, "capital_inicial": BALANCE_INICIAL,"balance_btc": BALANCE_BTC_INICIAL, "balance_bnb": BALANCE_BNB_INICIAL, "capital_btc": BALANCE_BTC_INICIAL, "capital_bnb": BALANCE_BNB_INICIAL,"neto_hoy_btc": 0.0, "neto_hoy_bnb": 0.0, "ops_hoy_btc": 0, "ops_hoy_bnb": 0, "ganadas_btc": 0, "ganadas_bnb": 0, "perdidas_btc": 0, "perdidas_bnb": 0,"ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO", "mercado": "NORMAL BTC+BNB", "pausa_hasta": None, "historial": [], "caja": "ADMIN TIBURON 100% - TU PLATA", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False, "api_encriptada": False, "pendiente_pago": None}
        try:
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        except: pass
        guardar_datos()
        bot.reply_to(message, f"🔄 RESET DEMO TOTAL OK - $200.00 LIMPIO", reply_markup=get_menu_botones(True))

@bot.message_handler(commands=['setapi'])
def setapi_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 3: bot.send_message(message.chat.id, "❌ Formato: /setapi TU_API_KEY TU_SECRET_KEY"); return
        api_key = parts[1].strip(); api_secret = parts[2].strip()
        ud = get_user_data(message.chat.id)
        ud["api_key"] = encriptar_api(api_key); ud["api_secret"] = encriptar_api(api_secret); ud["api_cargada"] = True; ud["api_encriptada"] = True; guardar_datos()
        if not es_admin(message.chat.id):
            kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton(f"➕ ALTA CACHORRO 20% - ID {message.chat.id}", callback_data=f"alta_{message.chat.id}_CACHORRO"))
            bot.send_message(ADMINS_IDS[0], f"🐶 NUEVO SOCIO - API ENCRIPTADA 🔒\nID: {message.chat.id}\nUser: @{message.from_user.username}\n🔒 API: ENCRIPTADA\n👉 Tocá ➕ ALTA para CACHORRO 20% x 7 dias", reply_markup=kb)
            bot.send_message(message.chat.id, f"✅ API CARGADA Y ENCRIPTADA 🔒\nTu bot ya puede operar TU plata. Esperando ➕ ALTA del lider", reply_markup=get_menu_botones(False))
        else: bot.send_message(message.chat.id, f"✅ API ADMIN CARGADA Y ENCRIPTADA 🔒 - Tu bot opera tu plata al 100%", reply_markup=get_menu_botones(True))
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
    except Exception as e: bot.send_message(message.chat.id, f"❌ Error API: {e}")

@bot.message_handler(func=lambda m: m.text in ["🔑 CARGAR API"])
def btn_cargar_api(m): bot.send_message(m.chat.id, "🔑 CARGAR API SEGURA - V28 ALQUILER\nMandame:\n/setapi TU_API_KEY TU_SECRET_KEY\nLa encripto automatico - Opera TU plata en TU Binance", reply_markup=get_menu_botones(es_admin(m.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["💸 RETIRAR"])
def btn_retirar(m): bot.send_message(m.chat.id, "💸 Tu plata esta en TU Binance, no en el bot. Binance -> Billetera -> Retirar.", reply_markup=get_menu_botones(es_admin(m.chat.id)))

@bot.message_handler(commands=['id'])
def get_id(message):
    acceso,dias = tiene_acceso(message.chat.id); ud = get_user_data(message.chat.id)
    api_status = "✅ ENCRIPTADA - TU BOT" if ud.get("api_cargada") else "❌ FALTA /setapi"
    plan = ESTADO["socios"].get(message.chat.id, {}).get("plan","-")
    bot.send_message(message.chat.id,f"🆔 Tu ID es: {message.chat.id}\n📦 Plan: {plan} - ⏳ {dias} dias\n🔑 API: {api_status}\n🔗 Link: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

def enviar_bienvenida_completa(chat_id, markup):
    limite = 3500
    if len(BIENVENIDA) > limite:
        parte1 = BIENVENIDA[:limite]; parte2 = BIENVENIDA[limite:]
        bot.send_message(chat_id, parte1); time.sleep(0.8)
        bot.send_message(chat_id, parte2 + f"\n\nTu ID: {chat_id}\nTocá 🔑 CARGAR API", reply_markup=markup)
    else: bot.send_message(chat_id, BIENVENIDA + f"\n\nTu ID: {chat_id}\nTocá 🔑 CARGAR API", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id); ud=get_user_data(message.chat.id)
    if es_admin(message.chat.id): bot.send_message(message.chat.id,f"👋 V28 ADMIN ALQUILER FULL 🐺\nTU BOT: ${ud['balance']:.2f} (BTC ${ud['balance_btc']:.2f} + BNB ${ud['balance_bnb']:.2f}) - {ud['modo']}\n{ud['mercado']}\nOperás solo TU plata. Socios operan la suya.\nTu web: {WEB_URL}\nAlias: {ALIAS_BRUBANK}\nTu ID: {message.chat.id} (auto)", reply_markup=get_menu_botones(True))
    else:
        if not acceso: enviar_bienvenida_completa(message.chat.id, get_menu_botones(False))
        else: bot.send_message(message.chat.id,f"👋 MANADA V28\n📦 Plan: {ESTADO['socios'][message.chat.id]['plan']} - ⏳ {dias_rest} dias\n⚙️ Modo: {ud['modo']}\nTU BOT: ${ud['balance']:.2f}\nWeb: {WEB_URL}/?id={message.chat.id}\nAlias pago: {ALIAS_BRUBANK}\nTu ID: {message.chat.id} (auto)", reply_markup=get_menu_botones(False))

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/prender"])
def prender(message):
    user_id = int(message.chat.id)
    ud = get_user_data(user_id)
    if not ud.get("api_cargada"):
        bot.send_message(message.chat.id,"❌ Primero cargá TU API con 🔑 CARGAR API\nTu Binance debe tener $50 BTC + $50 BNB", reply_markup=get_menu_botones(es_admin(user_id)))
        return
    if not es_admin(user_id):
        acceso,dias = tiene_acceso(user_id)
        if not acceso:
            bot.send_message(message.chat.id,"⛔ Tu alquiler venció - Tocá 🐺 QUIERO LOBO", reply_markup=get_menu_botones(False))
            return
    ud["prendido"]=True; ud["pausa_hasta"]=None; guardar_datos()
    if es_admin(user_id):
        analizar_mercado_y_elegir_modo(ud)
        bot.send_message(message.chat.id,f"🚀 TU BOT TIBURÓN 100% PRENDIDO\nOperás TU plata en TU Binance\n${ud['balance']:.2f} (BTC ${ud['balance_btc']:.2f} + BNB ${ud['balance_bnb']:.2f})\nModo {ud['modo']} - {ud['mercado']}", reply_markup=get_menu_botones(True))
    else:
        plan = ESTADO["socios"].get(user_id,{}).get("plan","CACHORRO"); pot = 20 if plan=="CACHORRO" else PLANES.get(plan,20)
        bot.send_message(message.chat.id,f"🚀 TU BOT {plan} {pot}% PRENDIDO\nOperás TU plata en TU Binance usando estrategia TIBURÓN\nBalance ${ud['balance']:.2f} (BTC ${ud['balance_btc']:.2f} + BNB ${ud['balance_bnb']:.2f})", reply_markup=get_menu_botones(False))

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance", "/miplan"])
def balance(message):
    acceso,dias = tiene_acceso(message.chat.id)
    if not acceso and not es_admin(message.chat.id): bot.send_message(message.chat.id,"⛔ Plan vencido. Tocá 🐺 QUIERO LOBO", reply_markup=get_menu_botones(False)); return
    ud = get_user_data(message.chat.id); win=calcular_winrate(ud)
    capital_inicial = ud.get("capital_inicial", BALANCE_INICIAL); ganancia_hoy = ud["neto_hoy"]; balance_total = ud["balance"]; ganancia_total = balance_total - capital_inicial
    capital_btc = ud.get("capital_btc", BALANCE_BTC_INICIAL); capital_bnb = ud.get("capital_bnb", BALANCE_BNB_INICIAL)
    balance_btc = ud.get("balance_btc", BALANCE_BTC_INICIAL); balance_bnb = ud.get("balance_bnb", BALANCE_BNB_INICIAL)
    neto_btc = ud.get("neto_hoy_btc", 0.0); neto_bnb = ud.get("neto_hoy_bnb", 0.0)
    ganancia_btc_total = balance_btc - capital_btc; ganancia_bnb_total = balance_bnb - capital_bnb
    plan_actual = ESTADO["socios"].get(message.chat.id, {}).get("plan","ADMIN") if not es_admin(message.chat.id) else "ADMIN TIBURON 100%"
    vence_txt = ESTADO["socios"].get(message.chat.id, {}).get("vence"); vence_str = vence_txt.strftime("%d/%m/%Y") if vence_txt else "Ilimitado"
    api_status = "✅ TU BOT - ENCRIPTADA" if ud.get("api_cargada") else "❌ DEMO"
    texto = f"""💰 {ud['caja']} - BALANCE V28 ALQUILER
💵 Capital Inicial: ${capital_inicial:.2f} ($100 BTC + $100 BNB)
📈 Ganancia Hoy: ${ganancia_hoy:+.2f} - Total: ${ganancia_total:+.2f}
💰 Balance Actual: ${balance_total:.2f}
₿ BTC: ${capital_btc:.2f} -> ${balance_btc:.2f} Hoy {neto_btc:+.2f} Total {ganancia_btc_total:+.2f}
🔶 BNB: ${capital_bnb:.2f} -> ${balance_bnb:.2f} Hoy {neto_bnb:+.2f} Total {ganancia_bnb_total:+.2f}
🎯 Winrate Hoy: {win}% - ⚙️ Modo: {ud['modo']} - 📊 {ud['mercado']}
📦 Plan: {plan_actual} - ⏳ {dias} dias - Vence {vence_str}
🔑 API: {api_status} - TU plata en TU Binance
₿ BTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}
💵 Dolar: ${DOLAR_CRIPTO['valor']} ({DOLAR_CRIPTO['actualizado']})
V28 ALQUILER - CADA UNO SU BOT
ID auto: {message.chat.id}
"""
    bot.send_message(message.chat.id, texto, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL", "/historial"])
def historial(message):
    ud = get_user_data(message.chat.id); ahora = ahora_art(); hoy = ahora.date()
    hist_hoy = [h for h in ud["historial"] if hoy.strftime('%d/%m/%Y') in h]
    txt = f"📜 {ud['caja']} - HISTORIAL\n📅 HOY {hoy.strftime('%d/%m/%Y')} - {len(hist_hoy)} ops\n" + "\n".join(hist_hoy[-15:] if hist_hoy else ["Sin ops hoy"])
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🐺 QUIERO LOBO", "/quierolobo", "/planes"])
def quiero_lobo(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"🐀 RATA $20 40%", callback_data="plan_RATA"),types.InlineKeyboardButton(f"🐺 LOBO $40 60%", callback_data="plan_LOBO"),types.InlineKeyboardButton(f"🦈 TIBURON $60 100%", callback_data="plan_TIBURON"))
    bot.send_message(message.chat.id, f"🐺 ELEGÍ TU PACK ALQUILER V28\nAlias BRUBANK {ALIAS_BRUBANK}\n\n{TEXTO_PAGAR}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("plan_"))
def callback_plan(call):
    plan = call.data.split("_")[1]; bot.answer_callback_query(call.id, f"Elegiste {plan}")
    ud = get_user_data(call.message.chat.id); ud["pendiente_pago"] = plan; guardar_datos()
    markup = types.InlineKeyboardMarkup(); markup.add(types.InlineKeyboardButton(f"✅ YA PAGUÉ {plan}", callback_data=f"yapague_{plan}"))
    bot.send_message(call.message.chat.id, f"✅ Elegiste {plan} ${PLANES[plan]}\nAlias {ALIAS_BRUBANK}\n1- Transferi 2- Toca boton y manda foto", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("yapague_"))
def callback_yapague(call): plan = call.data.split("_")[1]; bot.answer_callback_query(call.id); bot.send_message(call.message.chat.id, f"📸 Manda FOTO comprobante {plan} a {ALIAS_BRUBANK}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.from_user.id; ud = get_user_data(uid); pack = ud.get("pendiente_pago", "LOBO")
    kb = types.InlineKeyboardMarkup(); kb.add(types.InlineKeyboardButton(f"✅ DAR ALTA {pack} - ID {uid}", callback_data=f"alta_{uid}_{pack}"),types.InlineKeyboardButton("❌ RECHAZAR", callback_data=f"rechazar_{uid}"))
    try:
        bot.send_photo(chat_id=ADMINS_IDS[0], photo=message.photo[-1].file_id, caption=f"💰 COMPROBANTE NUEVO V28 ALQUILER\nSocio: @{message.from_user.username}\nID: {uid}\nPack: {pack} - Su bot operará su plata\nAlias: {ALIAS_BRUBANK}", reply_markup=kb)
        bot.send_message(uid, "✅ Comprobante recibido! Esperando ➕ ALTA del admin para prender TU bot.", reply_markup=get_menu_botones(es_admin(uid)))
    except Exception as e: bot.send_message(uid, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: m.text in ["🔻 SOLICITAR BAJA"])
def solicitar_baja(m):
    if es_admin(m.chat.id):
        bot.send_message(m.chat.id, "⛔ Sos admin, no necesitas baja.", reply_markup=get_menu_botones(True))
        return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"🔻 BAJA SOCIO {m.chat.id}", callback_data=f"baja_{m.chat.id}"))
    bot.send_message(ADMINS_IDS[0], f"🔔 ID {m.chat.id} (@{m.from_user.username}) pide BAJA\nPlan: {ESTADO['socios'].get(m.chat.id, {}).get('plan','-')}", reply_markup=kb)
    bot.send_message(m.chat.id, "🔻 Solicitud de baja enviada al admin. Tu bot se pausará al confirmar.", reply_markup=get_menu_botones(False))

@bot.callback_query_handler(func=lambda call: call.data.startswith("baja_"))
def handle_baja(call):
    bot.answer_callback_query(call.id)
    uid = int(call.data.split("_")[1])
    if uid in ESTADO["socios"]: del ESTADO["socios"][uid]
    if uid in USUARIOS: USUARIOS[uid]["prendido"] = False
    guardar_datos()
    try:
        bot.send_message(uid, "🔻 BAJA CONFIRMADA - Tu estrategia apagada. Podés retirar tu plata de tu Binance.")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"✅ BAJA DADA {uid} - Bot apagado")
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("alta_") or call.data.startswith("rechazar_") or call.data.startswith("espera_"))
def handle_admin_action(call):
    bot.answer_callback_query(call.id); data = call.data
    if data.startswith("alta_"):
        _, uid, pack = data.split("_"); uid = int(uid); dias = 7 if pack == "CACHORRO" else 30
        ESTADO["socios"][uid] = {"alta": datetime.now(), "vence": datetime.now()+timedelta(days=dias), "plan": pack}
        ud = get_user_data(uid); ud["pendiente_pago"] = None; guardar_datos()
        try:
            if pack == "CACHORRO": bot.send_message(uid, f"🐺 CACHORRO 20% ACTIVADO x 7 días - TU BOT\nTu web: {WEB_URL}/?id={uid}\nDale a 🚀 PRENDER para operar TU plata", reply_markup=get_menu_botones(False))
            else: bot.send_message(uid, f"🔥 ALTA {pack} {PLANES[pack]}% CONFIRMADA x 30 dias! TU BOT\nDale a 🚀 PRENDER", reply_markup=get_menu_botones(False))
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + f"\n\n✅ ALTA DADA {pack} - Su bot opera su plata")
        except:
            try: bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + f"\n\n✅ ALTA DADA {pack}")
            except: pass
    elif data.startswith("rechazar_"): uid = int(data.split("_")[1]); bot.send_message(uid, "❌ Comprobante rechazado. Revisa alias manada.lobo.bru")
    elif data.startswith("espera_"): bot.send_message(call.message.chat.id, "Esperando pago del socio vencido.")

def enviar_lista_socios(chat_id):
    if not ESTADO["socios"]: bot.send_message(chat_id, "👥 Sin socios - Esperando altas", reply_markup=get_menu_botones(True)); return
    bot.send_message(chat_id, f"👥 SOCIOS ALQUILER - {len(ESTADO['socios'])} activos", reply_markup=get_menu_botones(True))
    for cid,d in list(ESTADO["socios"].items()):
        dias=(d["vence"]-datetime.now()).days; u = USUARIOS.get(cid, {"balance":200,"ops_hoy":0,"neto_hoy":0,"ganadas":0,"perdidas":0}); win = calcular_winrate(u)
        txt = f"👤 {cid}\n📦 {d['plan']} - ⏳ {dias}d\n💰 ${u['balance']} | 📈 ${u['neto_hoy']} | {u.get('modo','-')} | TU BOT\nID /alta {cid} 30 {d['plan']} /baja {cid}"
        bot.send_message(chat_id, txt)

@bot.message_handler(commands=['alta','socios','baja'])
def admin_cmds(message):
    if not es_admin(message.chat.id): return
    if message.text.startswith('/alta'):
        try:
            parts=message.text.split(); id_cliente=int(parts[1]); dias=int(parts[2]); plan=parts[3].upper() if len(parts)>3 else "CACHORRO"
            vence=datetime.now()+timedelta(days=dias); ESTADO["socios"][id_cliente]={"alta":datetime.now(),"vence":vence,"plan":plan}
            ud = get_user_data(id_cliente); ud["balance"]=200.0; ud["capital_inicial"]=200.0; ud["balance_btc"]=100.0; ud["balance_bnb"]=100.0; ud["capital_btc"]=100.0; ud["capital_bnb"]=100.0; ud["neto_hoy"]=0; ud["neto_hoy_btc"]=0; ud["neto_hoy_bnb"]=0; ud["ops_hoy"]=0; ud["ops_hoy_btc"]=0; ud["ops_hoy_bnb"]=0; ud["ganadas"]=0; ud["ganadas_btc"]=0; ud["ganadas_bnb"]=0; ud["perdidas"]=0; ud["perdidas_btc"]=0; ud["perdidas_bnb"]=0; ud["historial"]=[]; ud["prendido"]=False
            guardar_datos(); bot.send_message(message.chat.id,f"✅ Alta {id_cliente} {plan} {dias}d - Su bot operará su plata")
        except Exception as e: bot.send_message(message.chat.id,f"Error: {e}")
    elif message.text.startswith('/socios'): enviar_lista_socios(message.chat.id)
    elif message.text.startswith('/baja'):
        try:
            parts=message.text.split(); id_cliente=int(parts[1])
            if id_cliente in ESTADO["socios"]: del ESTADO["socios"][id_cliente]
            if id_cliente in USUARIOS: USUARIOS[id_cliente]["prendido"]=False
            guardar_datos(); bot.send_message(message.chat.id,f"✅ Baja {id_cliente} OK - Bot apagado")
        except Exception as e: bot.send_message(message.chat.id,f"Error baja: {e}")

@bot.message_handler(func=lambda m: m.text in ["👥 SOCIOS"])
def btn_socios(message):
    if not es_admin(message.chat.id): bot.send_message(message.chat.id,"⛔ Solo admin", reply_markup=get_menu_botones(False)); return
    enviar_lista_socios(message.chat.id)

HTML="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>V28 ALQUILER FINAL</title><script src="https://s3.tradingview.com/tv.js"></script><style>
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
<div class="header"><b id="titulo">V28 ALQUILER - CADA UNO SU BOT</b><div id="admin" class="box admin">Cargando...</div></div>
<div id="chart_btc"></div><div id="chart_bnb"></div>
<div id="bloqueSocios"><h3>👥 Socios - Cada uno su bot su plata</h3><div id="socios" class="socios">Cargando...</div></div>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"1","theme":"dark","container_id":"chart_btc"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"1","theme":"dark","container_id":"chart_bnb"});
function getId(){return new URLSearchParams(window.location.search).get('id');}
async function load(){
  let idParam=getId();
  let url=idParam?`/api/data?id=${idParam}`:'/api/data';
  let a=await (await fetch(url)).json();
  if(idParam){
    document.getElementById('titulo').innerText=`💼 TU PLATA - TU BOT - ${a.modo}`;
    document.getElementById('admin').innerHTML=`<span class="kpi total">💵 $${a.capital_inicial.toFixed(2)}</span><span class="kpi total">📈 $${a.neto_hoy.toFixed(2)}</span><span class="kpi total">💰 $${a.balance.toFixed(2)}</span><br><span class="kpi btc">₿ BTC $${a.balance_btc.toFixed(2)}</span><span class="kpi bnb">🔶 BNB $${a.balance_bnb.toFixed(2)}</span><span class="kpi modo">🐺 ${a.modo}</span>`;
    document.getElementById('bloqueSocios').style.display='none';
  } else {
    document.getElementById('admin').innerHTML=`<b>🔵 ADMIN TIBURON 100% - TU PLATA $${a.balance.toFixed(2)} - ${a.modo}</b><br><span class="kpi total">Total $${a.balance.toFixed(2)} | Hoy $${a.neto_hoy.toFixed(2)}</span><span class="kpi btc">BTC $${a.balance_btc.toFixed(2)}</span><span class="kpi bnb">BNB $${a.balance_bnb.toFixed(2)}</span><span class="kpi">🎯 ${a.winrate}%</span>`;
    try{
      let s=await (await fetch('/api/socios')).json();let h='';
      if(Object.keys(s.socios).length==0)h='Sin socios';
      else{for(let id in s.socios){let u=s.socios[id];h+=`<div class="socio-card"><div><b>👤 ${id}</b> 📦 ${u.plan} ⏳ ${u.vence_dias}d<br>💰 $${u.balance.toFixed(2)} | 📈 $${u.neto_hoy.toFixed(2)} | 🎯 ${u.winrate}% | ${u.modo} - SU BOT</div><div><a href="/?id=${id}" style="color:#00ffea">Ver su bot</a></div></div>`;}}
      document.getElementById('socios').innerHTML=h;
    }catch(e){}
  }
}
setInterval(load,2500);load();
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/data')
def api_data():
    id_q = request.args.get('id', None)
    if id_q and id_q.isdigit(): target_id = int(id_q); a = get_user_data(target_id); es_admin_req = target_id in ADMINS_IDS
    else: target_id = ADMINS_IDS[0]; a = get_user_data(target_id); es_admin_req = True
    est_out={k:{"ops":v["ops"],"winrate":calcular_winrate_estrategia(v),"neto":v["neto"]} for k,v in a["estrategias"].items()}
    return jsonify({"balance":a["balance"],"balance_btc":a.get("balance_btc",100),"balance_bnb":a.get("balance_bnb",100),"capital_inicial":a.get("capital_inicial",200),"neto_hoy":a["neto_hoy"],"neto_hoy_btc":a.get("neto_hoy_btc",0),"neto_hoy_bnb":a.get("neto_hoy_bnb",0),"ops_hoy":a["ops_hoy"],"ops_hoy_btc":a.get("ops_hoy_btc",0),"ops_hoy_bnb":a.get("ops_hoy_bnb",0),"ganadas":a.get("ganadas",0),"ganadas_btc":a.get("ganadas_btc",0),"ganadas_bnb":a.get("ganadas_bnb",0),"perdidas":a.get("perdidas",0),"perdidas_btc":a.get("perdidas_btc",0),"perdidas_bnb":a.get("perdidas_bnb",0),"winrate":calcular_winrate(a),"modo":a["modo"],"mercado":a["mercado"],"btc":ESTADO["btc"],"bnb":ESTADO["bnb"],"estrategias":est_out,"dolar":DOLAR_CRIPTO,"es_admin":es_admin_req})
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
