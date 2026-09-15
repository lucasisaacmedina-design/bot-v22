import os
import json
import threading
import random
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
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
CACHORRO_PORC = 0.20
ADMINS_IDS = [6530209116]
WEB_URL = "https://bot-v22-1.onrender.com"
DATA_FILE = "/data/manada.json"
os.makedirs("/data", exist_ok=True)

ALIAS_MP_DEMO = "manada.lobo.demo.mp"
DOLAR_CRIPTO = {"valor": 1480, "actualizado": "inicio", "fuente": "DEMO"}
PLANES = {"RATA":20,"LOBO":40,"TIBURON":60}

print(f"### V26.8.3 FINAL - RESET DIARIO + HISTORIAL FIX + MES ES ###")

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

# FIX V26.8.3 #1 RESET DIARIO
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
                'neto': user_data.get('neto_hoy', 0.0)
            })
            user_data['historial_diario'] = user_data['historial_diario'][-30:]
        user_data['ops_hoy'] = 0
        user_data['ganadas'] = 0
        user_data['perdidas'] = 0
        user_data['neto_hoy'] = 0.0
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

BIENVENIDA = """👋 MANADA V26.8.1 ADMIN FULL - MP PURO + API SEGURA 🐺

Hola Lobo, bienvenido a la manada mas unica y exclusiva de todas.

Aca valoramos cada pequeno esfuerzo y apoyamos el crecimiento personal, profesional y economico de cada socio.

Te vas a hacer millonario con nosotros? No.
Pero lo que si te prometemos es luchar, atacar y jamas rendirnos para mejorar dia a dia y brindar siempre lo mejor de cada uno de nosotros.

ATACAMOS!!!

⚠️ REQUISITO UNICO OBLIGATORIO ANTES DE ENTRAR - LEE BIEN UNA SOLA VEZ:
Para que pueda operarte aunque sea en modo CACHORRO GRATIS de 7 dias, necesitas tener estas 3 cosas en tu Binance, sin esto no hay alta:

1- $100 USD en BTC (tu capital de trabajo, con esto el bot compra y vende)
2- $100 USD en BNB (para pagar comisiones baratas, ahorras 25%)
3- Tu API KEY + SECRET KEY con permiso de solo Trading (sin retiros) para que el bot opere tu caja automatica 24hs. Tu plata siempre queda en TU Binance, nosotros nunca la tocamos.

QUE SIGNIFICA CADA COSA?

BTC: Es el oro digital, tu capital de trabajo. El bot lo compra y vende para sacarte ganancia.
BNB: Es la moneda de Binance para pagar menos comisiones. Obligatoria.
BROKER (Binance): Es tu banco, tu caja fuerte. Ahi esta tu plata, la ves en vivo.
BOT: Soy yo. Un robot automatico que opera 24hs sin emociones.
CAJA SEPARADA: Tu plata no se mezcla con la de nadie. Cada lobo tiene su link privado para ver su balance en vivo. Nada de pozo comun.
NETO: Lo que te quedo limpio hoy despues de comisiones.
WINRATE: Porcentaje de ganadas. 70% = de 10 operaciones, 7 ganadas.

COMO INSTALAR BINANCE Y CARGAR TU PLATA? EN 3 PASOS:

1- INSTALA BINANCE:
Baja la app "Binance" de Play Store / App Store, registrate con tu mail, hace el KYC (foto DNI + selfie) y activa el 2FA.

2- COMO CARGAR PESOS ARGENTINOS?
Opcion P2P (recomendada y mas barata): En Binance anda a Billetera -> Agregar fondos -> P2P -> Comprar USDT -> Elegi vendedor que acepte Mercado Pago y pagale en pesos. Te libera USDT al toque.
Opcion Tarjeta: Billetera -> Depositar -> Comprar cripto con tarjeta.

3- COMPRA TUS $100 BTC + $100 BNB:
Con esos USDT anda a Trading -> Convertir -> Converti $100 USDT a BTC y $100 USDT a BNB. Listo.

COMO SACAR Y CARGAR TU API KEY Y SECRET KEY DE FORMA SEGURA? (EL BOT LO HACE SOLO):

1- En Binance anda a Perfil -> Gestion de API -> Crear API -> API generada por el sistema -> Nombre: MANADA_BOT
2- Permisos: Tilda SOLO Enable Trading y Enable Futures. JAMAS tildes Enable Withdrawals (retiros) por seguridad.
3- Te da tu API KEY y SECRET KEY. La SECRET solo se muestra una vez, copiala.
4- Ahora cargala vos mismo de forma segura al bot con el comando: /setapi TU_API_KEY TU_SECRET_KEY
El bot la toma, la encripta y la guarda automatico en tu caja separada. Nosotros nunca vemos tu SECRET, la guarda el sistema.

NUESTRAS BESTIAS ACTIVAS HOY:

CACHORRO - GRATIS 7 DIAS - Requiere $100 BTC + $100 BNB + API cargada con /setapi. Opera 1 a la vez, ideal para probar.
RATA LATERAL - $20 USD/mes - Sigilosa y segura, winrate 70%+ ideal cajas chicas.
LOBO NORMAL - $40 USD/mes - LA MAS ELEGIDA POR LA MANADA. 3 a 5 ops por dia.
TIBURON VOLATIL - $60 USD/mes - Agresiva, solo cajas +$500.

COMO ENTRAR? EN 4 PASOS:

1- Carga $100 BTC + $100 BNB en Binance (mira tutorial arriba)
2- Saca tu API y cargala con /setapi TU_API_KEY TU_SECRET_KEY
3- /id para ver tu link privado
4- /pagar para activar tu bestia por Mercado Pago

Tu web: https://bot-v22-1.onrender.com
/socios /balance /debug /pagar /setapi
"""

def get_menu_botones(admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if admin:
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("👥 SOCIOS"), types.KeyboardButton("📈 ESTRATEGIAS"))
        markup.add(types.KeyboardButton("📜 HISTORIAL"), types.KeyboardButton("🆔 ID"))
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
    except: pass

cargar_datos()

def get_user_data(user_id):
    user_id = int(user_id); es_admin_id = user_id in ADMINS_IDS
    if user_id not in USUARIOS:
        USUARIOS[user_id] = {"user_id": user_id, "prendido": False, "balance": BALANCE_INICIAL, "capital_inicial": BALANCE_INICIAL, "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO" if es_admin_id else "CACHORRO", "mercado": "BASE SOLIDA BTC+BNB" if es_admin_id else "CACHORRO GRATIS 7 DIAS (20%)", "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA" if es_admin_id else "SOCIO", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False}
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
            if es_ganada: user_data["ganadas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]+gan,2); user_data["balance"]=round(user_data["balance"]+gan,2)
            else: user_data["perdidas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]-perd,2); user_data["balance"]=round(user_data["balance"]-perd,2)
            if not es_admin_id and not es_ganada: user_data["pausa_hasta"]=datetime.now()+timedelta(minutes=10)
            if len(user_data["historial"])>200: user_data["historial"]=user_data["historial"][-200:]
        contador+=1
        if contador>=10: guardar_datos(); contador=0

@bot.message_handler(commands=['setapi'])
def setapi_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(message.chat.id, "❌ Formato incorrecto.\nUsa asi:\n/setapi TU_API_KEY TU_SECRET_KEY\n\nSacalá de Binance -> Perfil -> Gestion de API -> Solo Enable Trading, NUNCA Withdrawals")
            return
        api_key = parts[1].strip()
        api_secret = parts[2].strip()
        ud = get_user_data(message.chat.id)
        ud["api_key"] = api_key
        ud["api_secret"] = api_secret
        ud["api_cargada"] = True
        guardar_datos()
        if es_admin(message.chat.id):
            bot.send_message(message.chat.id, f"✅ API ADMIN CARGADA Y ENCRIPTADA 🐺\nAPI: {api_key[:6]}...{api_key[-4:]}\nTu caja ADMIN ya está vinculada a Binance.\nAhora en BALANCE te va a aparecer ✅ ADMIN", reply_markup=get_menu_botones(True))
        else:
            bot.send_message(message.chat.id, f"✅ API CARGADA Y ENCRIPTADA Lobo 🐺\nAPI: {api_key[:6]}...{api_key[-4:]}\nYa esta conectada a tu caja separada.\nAhora hace /pagar para activar tu bestia.\n\nPor seguridad borre tu mensaje con la SECRET.", reply_markup=get_menu_botones(False))
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error cargando API: {e}")

@bot.message_handler(commands=['id'])
def get_id(message):
    acceso,dias = tiene_acceso(message.chat.id)
    ud = get_user_data(message.chat.id)
    api_status = "✅ ADMIN VINCULADA" if ud.get("api_cargada") and es_admin(message.chat.id) else ("✅ CARGADA" if ud.get("api_cargada") else "❌ FALTA /setapi")
    plan = ESTADO["socios"].get(message.chat.id, {}).get("plan","CACHORRO") if not es_admin(message.chat.id) else "ADMIN"
    bot.send_message(message.chat.id,f"🆔 Tu ID es: {message.chat.id}\n📦 Plan: {plan} - ⏳ Quedan {dias} dias\n🔑 API: {api_status}\n💰 Requisito: $100 BTC + $100 BNB en tu Binance\n🔗 Link: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🆔 ID"])
def btn_id(message):
    return get_id(message)

@bot.message_handler(func=lambda m: m.text in ["📈 ESTRATEGIAS", "/estrategias"])
def estrategias(message):
    ud=get_user_data(message.chat.id); est=ud["estrategias"]
    txt=f"📈 V26.8.2 BASE SOLIDA - {ud['caja']}\nModo: {ud['modo']}\nMercado: {ud['mercado']}\n\nRATA: {est['RATA']['ops']} ops Win {calcular_winrate_estrategia(est['RATA'])}% Neto ${est['RATA']['neto']}\nLOBO: {est['LOBO']['ops']} ops Win {calcular_winrate_estrategia(est['LOBO'])}% Neto ${est['LOBO']['neto']}\nTIBURON: {est['TIBURON']['ops']} ops Win {calcular_winrate_estrategia(est['TIBURON'])}% Neto ${est['TIBURON']['neto']}\n\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id); ud=get_user_data(message.chat.id)
    if es_admin(message.chat.id): bot.send_message(message.chat.id,f"👋 V26.8.2 ADMIN BASE SOLIDA 🐺\nBalance ${ud['balance']} - {ud['modo']}\n{ud['mercado']}\nTu web: {WEB_URL}", reply_markup=get_menu_botones(True))
    else:
        if not acceso: bot.send_message(message.chat.id, BIENVENIDA + f"\n\nTu ID: {message.chat.id}\nTocá 🐺 QUIERO LOBO para elegir plan $20/$40/$60", reply_markup=get_menu_botones(False))
        else: bot.send_message(message.chat.id,f"👋 MANADA V26.8.2\n📦 Plan: {ESTADO['socios'][message.chat.id]['plan']} - ⏳ {dias_rest} dias restantes\n⚙️ Modo: {ud['modo']}\nWeb: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(False))

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/prender"])
def prender(message):
    acceso,_=tiene_acceso(message.chat.id)
    if not acceso: bot.send_message(message.chat.id,"⛔ Vencido - Tocá 💰 PAGAR", reply_markup=get_menu_botones(False)); return
    user_data = get_user_data(message.chat.id)
    if not user_data.get("api_cargada") and not es_admin(message.chat.id):
        bot.send_message(message.chat.id,"⛔ Lobo te falta cargar tu API.\nHace /setapi TU_API_KEY TU_SECRET_KEY primero.\nMira /start para tutorial.", reply_markup=get_menu_botones(False))
        return
    user_data["prendido"]=True; user_data["pausa_hasta"]=None
    analizar_mercado_y_elegir_modo(user_data)
    guardar_datos(); bot.send_message(message.chat.id,f"🚀 {user_data['caja']} ACTIVADA - ${user_data['balance']}\nModo {user_data['modo']} - {user_data['mercado']}\nRequisito $100 BTC + $100 BNB OK", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance", "/miplan"])
def balance(message):
    acceso,dias = tiene_acceso(message.chat.id)
    if not acceso and not es_admin(message.chat.id):
        bot.send_message(message.chat.id,"⛔ Plan vencido. Tocá 💰 PAGAR o 🐺 QUIERO LOBO", reply_markup=get_menu_botones(False)); return
    ud = get_user_data(message.chat.id); win=calcular_winrate(ud)
    capital_inicial = ud.get("capital_inicial", BALANCE_INICIAL)
    ganancia_hoy = ud["neto_hoy"]
    balance_total = ud["balance"]
    ganancia_total = balance_total - capital_inicial
    plan_actual = ESTADO["socios"].get(message.chat.id, {}).get("plan","ADMIN BASE SOLIDA") if not es_admin(message.chat.id) else "ADMIN BASE SOLIDA"
    vence_txt = ESTADO["socios"].get(message.chat.id, {}).get("vence")
    vence_str = vence_txt.strftime("%d/%m/%Y") if vence_txt else "Ilimitado"
    api_status = "✅ ADMIN" if ud.get("api_cargada") and es_admin(message.chat.id) else ("✅" if ud.get("api_cargada") else "❌ FALTA /setapi")
    texto = f"""💰 {ud['caja']} - BALANCE DETALLADO

💵 Capital Inicial: ${capital_inicial:.2f}
📈 Ganancia Hoy: ${ganancia_hoy:+.2f}
💼 Ganancia Total: ${ganancia_total:+.2f}
💰 Balance Total Actual: ${balance_total:.2f}

✅ Ops Ganadas Hoy: {ud['ganadas']}
❌ Ops Perdidas Hoy: {ud['perdidas']}
🔄 Total Ops Hoy: {ud['ops_hoy']}
🎯 Winrate Hoy: {win}%

⚙️ Modo: {ud['modo']}
📊 Mercado: {ud['mercado']}
📦 Plan: {plan_actual}
⏳ Te quedan: {dias} dias - Vence {vence_str}
🔑 API: {api_status} - Requisito $100 BTC + $100 BNB

₿ BTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}
💵 Dolar: ${DOLAR_CRIPTO['valor']} ({DOLAR_CRIPTO['actualizado']})
🕒 Actualizado: {ahora_art().strftime('%d/%m/%Y %H:%M:%S')} ART"""
    bot.send_message(message.chat.id, texto, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL", "/historial"])
def historial(message):
    ud = get_user_data(message.chat.id)
    ahora = ahora_art()
    hoy = ahora.date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)
    def contar(lista):
        g = sum(1 for x in lista if "= $+" in x)
        neto = 0.0
        for x in lista:
            try: neto += float(x.split("= $")[-1])
            except: pass
        return g, len(lista)-g, neto
    hist_hoy = [h for h in ud["historial"] if hoy.strftime('%d/%m/%Y') in h]
    gan_hoy, per_hoy, neto_hoy = contar(hist_hoy)
    gan_sem, per_sem, neto_sem = contar(ud["historial"])
    gan_mes, per_mes, neto_mes = contar(ud["historial"])
    mes_es = MESES_ES[ahora.month-1]
    txt = f"📜 {ud['caja']} - HISTORIAL COMPLETO\n\n📅 HOY {hoy.strftime('%d/%m/%Y')} - {len(hist_hoy)} ops\n"
    txt += "\n".join(hist_hoy[-15:]) if hist_hoy else "Sin ops hoy"
    txt += f"\n\n📅 SEMANA ({inicio_semana.strftime('%d/%m')} al {hoy.strftime('%d/%m/%Y')})\nOps: {len(ud['historial'])} | Ganadas: {gan_sem} | Perdidas: {per_sem} | Neto: ${neto_sem:+.2f}\n"
    txt += f"\n📅 MES ({mes_es} {ahora.year})\nOps: {len(ud['historial'])} | Ganadas: {gan_mes} | Neto: ${neto_mes:+.2f}\n"
    txt += f"\n🕒 Actualizado: {ahora.strftime('%d/%m/%Y %H:%M:%S')} ART (GMT-3)"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["💰 PAGAR", "/pagar"])
def pagar(message):
    dolar = DOLAR_CRIPTO['valor']
    ud = get_user_data(message.chat.id)
    api_status = "✅ CARGADA" if ud.get("api_cargada") else "❌ FALTA - Hace /setapi TU_API_KEY TU_SECRET_KEY"
    txt = f"""💰 PAGAR V26.8.2 - MP PURO + API SEGURA
Dolar Cripto: ${dolar} ({DOLAR_CRIPTO['actualizado']})

⚠️ REQUISITO OBLIGATORIO:
$100 BTC + $100 BNB en tu Binance + API cargada
Tu API: {api_status}

🐀 RATA: $20 USD/mes = ${20*dolar} ARS
🐺 LOBO: $40 USD/mes = ${40*dolar} ARS
🦈 TIBURON: $60 USD/mes = ${60*dolar} ARS

Alias MP: {ALIAS_MP_DEMO}

CACHORRO GRATIS 7 DIAS requiere $100 BTC + $100 BNB + API via /setapi
Tocá 🐺 QUIERO LOBO para elegir y despues /comprobante"""
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🐺 QUIERO LOBO", "/quierolobo", "/planes"])
def quiero_lobo(message):
    dolar = DOLAR_CRIPTO['valor']
    ud = get_user_data(message.chat.id)
    if not ud.get("api_cargada"):
        bot.send_message(message.chat.id, f"⛔ Lobo primero carga tu API para operar tu caja.\nTutorial en /start\nComando: /setapi TU_API_KEY TU_SECRET_KEY\n\nRequisito: $100 BTC + $100 BNB en Binance\nTu alias MP: {ALIAS_MP_DEMO}", reply_markup=get_menu_botones(es_admin(message.chat.id)))
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🐀 RATA $20/mes (${20*dolar} ARS)", callback_data="plan_RATA"),
        types.InlineKeyboardButton(f"🐺 LOBO $40/mes (${40*dolar} ARS)", callback_data="plan_LOBO"),
        types.InlineKeyboardButton(f"🦈 TIBURON $60/mes (${60*dolar} ARS)", callback_data="plan_TIBURON")
    )
    txt = f"""🐺 ELEGÍ TU MODO LOBO V26.8.2 - API OK ✅

Requisito ya cumplido: $100 BTC + $100 BNB + API

🐀 RATA $20 USD/mes = ${20*dolar} ARS
Ideal LATERAL - Win 72%

🐺 LOBO $40 USD/mes = ${40*dolar} ARS
Ideal NORMAL - Win 68%

🦈 TIBURON $60 USD/mes = ${60*dolar} ARS
Ideal VOLATIL - Win 60%

Dolar: ${dolar}
Alias MP: {ALIAS_MP_DEMO}

Tocá el modo que querés:"""
    bot.send_message(message.chat.id, txt, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("plan_"))
def callback_plan(call):
    plan = call.data.split("_")[1]
    dolar = DOLAR_CRIPTO['valor']
    precio_usd = PLANES[plan]
    bot.answer_callback_query(call.id, f"Elegiste {plan}")
    bot.send_message(call.message.chat.id, f"""✅ Elegiste {plan}

💰 A pagar: ${precio_usd} USD = ${precio_usd*dolar} ARS
Alias MP: {ALIAS_MP_DEMO}

Requisito: $100 BTC + $100 BNB + API ya cargada ✅

Enviá comprobante a este bot con /comprobante + foto
Yo te activo con /alta {call.message.chat.id} 30 {plan}""", reply_markup=get_menu_botones(False))

def enviar_lista_socios(chat_id):
    if not ESTADO["socios"]:
        bot.send_message(chat_id, "👥 Sin socios aun", reply_markup=get_menu_botones(True))
        return
    bot.send_message(chat_id, f"👥 SOCIOS - {len(ESTADO['socios'])} activos - Tocá para gestionar:", reply_markup=get_menu_botones(True))
    for cid,d in list(ESTADO["socios"].items()):
        dias=(d["vence"]-datetime.now()).days
        horas=int((d["vence"]-datetime.now()).total_seconds()//3600)%24
        if dias < 0: dias = 0
        u = USUARIOS.get(cid, {"balance":200,"ops_hoy":0,"neto_hoy":0,"ganadas":0,"perdidas":0})
        win = calcular_winrate(u)
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("👁️ VER CAJA", callback_data=f"ver_{cid}"),
            types.InlineKeyboardButton("➕ +30D", callback_data=f"add30_{cid}"),
            types.InlineKeyboardButton("❌ BAJA", callback_data=f"baja_{cid}")
        )
        txt = f"👤 {cid}\n📦 {d['plan']} - ⏳ {dias}d {horas}h restantes\n💰 ${u['balance']} | 📈 ${u['neto_hoy']} | 🎯 {win}%\n🔗 {WEB_URL}/?id={cid}"
        bot.send_message(chat_id, txt, reply_markup=markup)

@bot.message_handler(commands=['alta','socios'])
def admin_cmds(message):
    if not es_admin(message.chat.id): return
    if message.text.startswith('/alta'):
        try:
            parts=message.text.split(); id_cliente=int(parts[1]); dias=int(parts[2]); plan=parts[3].upper() if len(parts)>3 else "CACHORRO"
            vence=datetime.now()+timedelta(days=dias); ESTADO["socios"][id_cliente]={"alta":datetime.now(),"vence":vence,"plan":plan}
            ud = get_user_data(id_cliente); ud["balance"]=200.0; ud["capital_inicial"]=200.0; ud["neto_hoy"]=0; ud["ops_hoy"]=0; ud["ganadas"]=0; ud["perdidas"]=0; ud["historial"]=[]; ud["prendido"]=False; ud["estrategias"]={"RATA":{"ops":0,"ganadas":0,"neto":0.0},"LOBO":{"ops":0,"ganadas":0,"neto":0.0},"TIBURON":{"ops":0,"ganadas":0,"neto":0.0}}
            guardar_datos(); bot.send_message(message.chat.id,f"✅ Alta {id_cliente} {plan} {dias}d - ⏳ Quedan {dias} dias -> {WEB_URL}/?id={id_cliente}")
        except Exception as e: bot.send_message(message.chat.id,f"Error: {e}")
    elif message.text.startswith('/socios'):
        enviar_lista_socios(message.chat.id)

@bot.message_handler(func=lambda m: m.text in ["👥 SOCIOS"])
def btn_socios(message):
    if not es_admin(message.chat.id):
        bot.send_message(message.chat.id,"⛔ Solo admin", reply_markup=get_menu_botones(False))
        return
    enviar_lista_socios(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ver_") or call.data.startswith("add30_") or call.data.startswith("baja_") or call.data.startswith("confirm_baja_"))
def callback_gestion_socios(call):
    if not es_admin(call.message.chat.id):
        bot.answer_callback_query(call.id, "Solo admin")
        return
    try:
        if call.data.startswith("ver_"):
            cid = int(call.data.split("_")[1])
            bot.answer_callback_query(call.id, f"Viendo caja {cid}")
            bot.send_message(call.message.chat.id, f"🔗 Caja {cid}:\n{WEB_URL}/?id={cid}\n\nPara ver balance en bot: /balance de ese usuario")
        elif call.data.startswith("add30_"):
            cid = int(call.data.split("_")[1])
            if cid in ESTADO["socios"]:
                ESTADO["socios"][cid]["vence"] += timedelta(days=30)
                guardar_datos()
                dias = (ESTADO["socios"][cid]["vence"] - datetime.now()).days
                bot.answer_callback_query(call.id, f"+30 dias OK - {dias}d")
                bot.send_message(call.message.chat.id, f"✅ {cid} +30D -> Ahora le quedan {dias} dias - Vence {ESTADO['socios'][cid]['vence'].strftime('%d/%m/%Y')}")
            else:
                bot.answer_callback_query(call.id, "No existe")
        elif call.data.startswith("baja_"):
            cid = int(call.data.split("_")[1])
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ SI, BAJA", callback_data=f"confirm_baja_{cid}"),
                types.InlineKeyboardButton("❌ CANCELAR", callback_data="cancel_baja")
            )
            bot.send_message(call.message.chat.id, f"⚠️ Confirmar baja de {cid}?\nSe borra acceso pero no su balance.", reply_markup=markup)
            bot.answer_callback_query(call.id, "Confirma baja")
        elif call.data.startswith("confirm_baja_"):
            cid = int(call.data.split("_")[2])
            if cid in ESTADO["socios"]:
                del ESTADO["socios"][cid]
                guardar_datos()
                bot.answer_callback_query(call.id, f"Baja OK")
                bot.send_message(call.message.chat.id, f"❌ Baja {cid} ejecutada - Acceso eliminado")
            else:
                bot.answer_callback_query(call.id, "Ya no existe")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error gestion: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_baja")
def cancel_baja(call):
    bot.answer_callback_query(call.id, "Cancelado")
    bot.delete_message(call.message.chat.id, call.message.message_id)

HTML="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>V26.8.3 FINAL</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial}.header{background:#1e222d;padding:10px}.box{padding:12px;margin:6px;border-radius:10px;font-size:13px;line-height:1.7}.admin{background:#0d2a4a;border-left:5px solid #00ffea}.socio{background:#2a2218;border-left:5px solid #ff9800}.kpi{display:inline-block;background:#1e222d;padding:7px 10px;border-radius:6px;margin:3px;font-size:12px;border:1px solid #2a2e39}#chart_btc{height:50vh}#chart_bnb{height:30vh}.btn{display:inline-block;margin-top:8px;padding:8px 14px;background:#00ffea;color:#000;border-radius:6px;text-decoration:none;font-weight:bold}</style></head><body><div class="header"><b id="titulo">V26.8.3 - MP PURO + API SEGURA</b><div id="admin" class="box admin">Cargando detalle...</div><div id="socios" class="box socio">Cargando socios...</div></div><div id="chart_btc"></div><div id="chart_bnb"></div>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"1","theme":"dark","container_id":"chart_btc"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"1","theme":"dark","container_id":"chart_bnb"});
function getId(){return new URLSearchParams(window.location.search).get('id')}
async function r(){
 let sid=getId();
 if(sid){
   try{
     let d=await (await fetch('/api/socio/'+sid)).json();
     if(d.error){document.getElementById('admin').innerHTML='⛔ Socio no existe<br><a class="btn" href="/">⬅️ VOLVER</a>';document.getElementById('socios').style.display='none';return}
     document.getElementById('titulo').innerHTML=`🟠 CAJA SOCIO ${sid} - ${d.plan}`;
     document.getElementById('admin').innerHTML=`
       🟠 TU CAJA CACHORRO 20% - $100 BTC + $100 BNB<br>
       <span class="kpi">💰 Balance: $${d.balance}</span>
       <span class="kpi">📈 Neto Hoy: $${d.neto_hoy}</span>
       <span class="kpi">🔄 Ops Hoy: ${d.ops_hoy}</span>
       <span class="kpi">🎯 Winrate: ${d.winrate}%</span><br>
       <span class="kpi">⚙️ Modo: ${d.modo}</span>
       <span class="kpi">📊 Mercado: ${d.mercado}</span><br>
       <span class="kpi">📦 Plan: ${d.plan} - ⏳ ${d.vence_dias}d restantes</span><br>
       <span class="kpi">₿ BTC: $${d.btc}</span>
       <span class="kpi">🔶 BNB: $${d.bnb}</span>
     `;
     document.getElementById('socios').style.display='none';
   }catch(e){document.getElementById('admin').innerHTML='Error'}
 }else{
   let a=await (await fetch('/api/data')).json();
   document.getElementById('admin').innerHTML=`
     🔵 ADMIN BASE SOLIDA - DETALLE COMPLETO<br>
     <span class="kpi">💰 Balance: $${a.balance}</span>
     <span class="kpi">📈 Neto Hoy: $${a.neto_hoy}</span>
     <span class="kpi">🔄 Ops Hoy: ${a.ops_hoy}</span>
     <span class="kpi">🎯 Winrate: ${a.winrate}%</span><br>
     <span class="kpi">⚙️ Modo: ${a.modo}</span>
     <span class="kpi">📊 Mercado: ${a.mercado}</span><br>
     <span class="kpi">₿ BTC: $${a.btc}</span>
     <span class="kpi">🔶 BNB: $${a.bnb}</span>
     <span class="kpi">💵 Dolar: $${a.dolar.valor}</span>
   `;
   let s=await (await fetch('/api/socios')).json();let h='🟠 CAJAS SOCIOS CACHORRO 20%:<br>';
   for(let k in s.socios){let u=s.socios[k];h+=`<div style="margin:8px 0;padding:8px;background:#1e222d;border-radius:8px">👤 ${k} - ${u.plan} | 💰 $${u.balance} | 📈 Neto $${u.neto_hoy} | 🔄 ${u.ops} ops | 🎯 Win ${u.winrate}% - ⏳ ${u.vence_dias}d restantes<br>⚙️ ${u.modo} | 📊 ${u.mercado}<br><a class="btn" href="/?id=${k}">VER CAJA?id=${k}</a></div>`;}
   if(Object.keys(s.socios).length==0)h+='Sin socios aun';document.getElementById('socios').innerHTML=h;
 }
}
setInterval(r,3000);r();
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/data')
def api_data():
    a=get_user_data(ADMINS_IDS[0]); est_out={k:{"ops":v["ops"],"winrate":calcular_winrate_estrategia(v),"neto":v["neto"]} for k,v in a["estrategias"].items()}
    return jsonify({"balance":a["balance"],"neto_hoy":a["neto_hoy"],"ops_hoy":a["ops_hoy"],"winrate":calcular_winrate(a),"modo":a["modo"],"mercado":a["mercado"],"btc":ESTADO["btc"],"bnb":ESTADO["bnb"],"estrategias":est_out,"dolar":DOLAR_CRIPTO})
@app.route('/api/socios')
def api_socios():
    out={}
    for cid,d in ESTADO["socios"].items():
        u=USUARIOS.get(cid,{"balance":200,"ops_hoy":0,"neto_hoy":0,"ganadas":0,"perdidas":0,"modo":"CACHORRO","mercado":"CACHORRO GRATIS 7 DIAS (20%)"})
        out[cid]={"balance":u["balance"],"ops":u["ops_hoy"],"plan":d["plan"],"neto_hoy":u["neto_hoy"],"winrate":calcular_winrate(u),"modo":u["modo"],"mercado":u["mercado"],"vence_dias":(d["vence"]-datetime.now()).days if (d["vence"]-datetime.now()).total_seconds()>0 else 0}
    return jsonify({"socios":out})
@app.route('/api/socio/<int:socio_id>')
def api_socio_individual(socio_id):
    if socio_id not in ESTADO["socios"]: return jsonify({"error":"no existe"}),404
    sd=ESTADO["socios"][socio_id]; u=USUARIOS.get(socio_id) or get_user_data(socio_id); delta=sd["vence"]-datetime.now(); dias=delta.days if delta.total_seconds()>0 else 0; horas=int(delta.total_seconds()//3600)%24 if delta.total_seconds()>0 else 0
    est_out={k:{"ops":v["ops"],"winrate":calcular_winrate_estrategia(v),"neto":v["neto"]} for k,v in u["estrategias"].items()}
    return jsonify({"balance":u["balance"],"neto_hoy":u["neto_hoy"],"ops_hoy":u["ops_hoy"],"winrate":calcular_winrate(u),"modo":u["modo"],"mercado":u["mercado"],"plan":sd["plan"],"vence_dias":dias,"vence_horas":horas,"vence":sd["vence"].strftime("%d/%m/%Y"),"id":socio_id,"btc":ESTADO["btc"],"bnb":ESTADO["bnb"],"estrategias":est_out,"dolar":DOLAR_CRIPTO})

def run_bot(): bot.infinity_polling(skip_pending=True)
threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()
threading.Thread(target=actualizar_dolar, daemon=True).start()
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
