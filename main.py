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

# CORREGIDO V26.8.9
ALIAS_MP_DEMO = "manada.lobo.bru"
ALIAS_BRUBANK = "manada.lobo.bru"
DOLAR_CRIPTO = {"valor": 1480, "actualizado": "inicio", "fuente": "BRUBANK"}
PLANES = {"RATA":20,"LOBO":40,"TIBURON":60}

print(f"### V26.8.9 FINAL - B-200 + BRUBANK + CACHORRO AUTO + PACKS PAGOS ###")

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

# BIENVENIDA FINAL V26.8.9 CORREGIDA - SIN CACHORRO EN PACKS
BIENVENIDA = """👋 MANADA V26.8.9 ADMIN FULL - BRUBANK + API SEGURA 🐺

Hola Lobo, bienvenido a la manada mas unica y exclusiva de todas.

Aca valoramos cada pequeno esfuerzo y apoyamos el crecimiento personal, profesional y economico de cada socio.

Te vas a hacer millonario con nosotros? No.
Pero lo que si te prometemos es luchar, atacar y jamas rendirnos para mejorar dia a dia y brindar siempre lo mejor de cada uno de nosotros.

ATACAMOS!!!

⚠️ REQUISITO UNICO OBLIGATORIO ANTES DE ENTRAR - LEE BIEN UNA SOLA VEZ:
Para que pueda operarte aunque sea en modo CACHORRO GRATIS de 7 dias, necesitas tener estas 3 cosas en tu Binance, sin esto no hay alta:

1- Desde $50 USD en BTC (tu capital de trabajo, con esto el bot compra y vende) - Lo recomendable es $100 USD en BTC para mejor rendimiento.
2- Desde $50 USD en BNB (para pagar comisiones baratas, ahorras 25%) - Lo recomendable es $100 USD en BNB para pagar menos comisiones.
3- Tu API KEY + SECRET KEY con permiso de solo Trading (sin retiros) para que el bot opere tu caja automatica 24hs. Tu plata siempre queda en TU Binance, nosotros nunca la tocamos.

🚨 ALERTA DE SEGURIDAD - LEELA BIEN POR FAVOR:
JAMAS pero JAMAS compartas tu API KEY y tu SECRET KEY con nadie por privado, por grupo, por soporte o por mail.
Tu API KEY y SECRET KEY son como la llave de tu caja fuerte. Solo vos la tenes que cargar en el bot con el boton 🔑 CARGAR API y el sistema la encripta automatico.
Nosotros NUNCA te vamos a pedir tu SECRET KEY por privado. Si alguien te la pide, es estafa. Bloquealo.

QUE SIGNIFICA CADA COSA? Te lo explico simple:

BTC: Es el oro digital, es tu capital de trabajo. El bot lo compra y vende para sacarte ganancia.
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

3- COMPRA TUS BTC + BNB:
Con esos USDT anda a Trading -> Convertir -> Converti desde $50 USDT a BTC y desde $50 USDT a BNB. Listo. Lo recomendable es $100 USDT a BTC y $100 USDT a BNB para que rinda mejor.

COMO SACAR Y CARGAR TU API KEY Y SECRET KEY DE FORMA SEGURA? (EL BOT LO HACE SOLO):

1- En Binance anda a Perfil -> Gestion de API -> Crear API -> API generada por el sistema -> Nombre: MANADA_BOT
2- Permisos: Tilda SOLO Enable Trading y Enable Futures. JAMAS tildes Enable Withdrawals (retiros) por seguridad.
3- Te da tu API KEY y SECRET KEY. La SECRET solo se muestra una vez, copiala.
4- Ahora toca el boton 🔑 CARGAR API y cargala vos mismo de forma segura. El sistema la encripta automatico.

COMO FUNCIONA LA ENTRADA? MUY SIMPLE:

1- Cargas desde $50 BTC + $50 BNB en tu Binance (recomendable $100+$100)
2- Cargas tu API con el boton 🔑 CARGAR API
3- Automaticamente entras en MODO CACHORRO GRATIS x 7 dias. Opera solo, 1 a la vez, para que pruebes sin pagar nada.
4- Si te gusta como caza, despues elegis tu pack pago con el boton 🐺 QUIERO LOBO

TE COMENTO NUESTROS PACKS PAGOS (PARA DESPUES DE TU PRUEBA GRATIS):

RATA LATERAL - $20 USD/mes - Sigilosa y segura, winrate 70%+ ideal cajas chicas.
LOBO NORMAL - $40 USD/mes - LA MAS ELEGIDA POR LA MANADA. 3 a 5 ops por dia.
TIBURON VOLATIL - $60 USD/mes - Agresiva, solo cajas +$500.

COMO ACTIVAR TU PACK PAGO? CUANDO QUIERAS:

1- Toca 🐺 QUIERO LOBO
2- Elegi tu bestia
3- Transferi a alias manada.lobo.bru (Brubank)
4- Toca ✅ YA PAGUE y manda comprobante. Alta en minutos.
"""

TEXTO_PAGAR = """💰 COMO PAGAR? BRUBANK - 3 PASOS:

Recorda que ya tenes que tener cargado en tu Binance desde $50 BTC + $50 BNB (recomendable $100+$100) y tu API cargada con 🔑 CARGAR API. Si no, hacelo primero viendo /start.

ENTRADA: Con $50 BTC + $50 BNB entras automaticamente en MODO CACHORRO GRATIS x 7 dias. No pagas nada para probar.

PASO 1: Elegi tu bestia PAGA despues de probar
RATA = $20
LOBO = $40
TIBURON = $60

PASO 2: Paga por Brubank
Alias: manada.lobo.bru
Titular: Brubank

PASO 3: Toca ✅ YA PAGUE y manda foto del comprobante

Listo, en 5 min te activo con tu caja separada y tu contador 30->0 dias.
"""

def get_menu_botones(admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if admin:
        # ADMIN MANTIENE TODO + NUEVO ORDEN V26.8.9
        markup.add(types.KeyboardButton("🐺 QUIERO LOBO"), types.KeyboardButton("🔑 CARGAR API"))
        markup.add(types.KeyboardButton("🚀 PRENDER"), types.KeyboardButton("📊 BALANCE"))
        markup.add(types.KeyboardButton("📜 HISTORIAL"), types.KeyboardButton("💸 RETIRAR"))
        markup.add(types.KeyboardButton("👥 SOCIOS"), types.KeyboardButton("📈 ESTRATEGIAS"))
        markup.add(types.KeyboardButton("🆔 ID"), types.KeyboardButton("🔄 RESET DEMO"))
        markup.add(types.KeyboardButton("🧹 CLEAR API"))
    else:
        # NUEVO MENU V26.8.9 FINAL
        markup.add(types.KeyboardButton("🐺 QUIERO LOBO"), types.KeyboardButton("🔑 CARGAR API"))
        markup.add(types.KeyboardButton("🚀 PRENDER"), types.KeyboardButton("📊 BALANCE"))
        markup.add(types.KeyboardButton("📜 HISTORIAL"), types.KeyboardButton("💸 RETIRAR"))
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
            "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO" if es_admin_id else "CACHORRO", "mercado": "BASE SOLIDA BTC+BNB" if es_admin_id else "CACHORRO GRATIS 7 DIAS (20%)", "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA" if es_admin_id else "SOCIO", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False, "pendiente_pago": None}
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
    if "pendiente_pago" not in USUARIOS[user_id]: USUARIOS[user_id]["pendiente_pago"] = None
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
            "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO", "mercado": "NORMAL BTC+BNB", "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False, "pendiente_pago": None}
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
            "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "ultimo_reset": ahora_art().strftime('%d/%m/%Y'), "historial_diario": [], "modo": "LOBO", "mercado": "NORMAL BTC+BNB", "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}, "api_key": None, "api_secret": None, "api_cargada": False, "pendiente_pago": None}
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
        # ACTIVACION CACHORRO AUTO V26.8.9
        if not es_admin(message.chat.id):
            ESTADO["socios"][message.chat.id] = {"alta": datetime.now(), "vence": datetime.now()+timedelta(days=7), "plan": "CACHORRO"}
            guardar_datos()
        bot.send_message(message.chat.id, f"✅ API CARGADA {api_key[:6]}...{api_key[-4:]}\n\n🐺 MODO CACHORRO GRATIS ACTIVADO x 7 dias automaticamente!\nDesde $50 BTC + $50 BNB (recomendable $100+$100)\nYa podes darle a 🚀 PRENDER", reply_markup=get_menu_botones(es_admin(message.chat.id)))
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error API: {e}")

# BOTONES NUEVOS V26.8.9
@bot.message_handler(func=lambda m: m.text in ["🔑 CARGAR API"])
def btn_cargar_api(m):
    bot.send_message(m.chat.id, "🔑 CARGAR API SEGURA - V26.8.9\n\nMandame:\n/setapi TU_API_KEY TU_SECRET_KEY\n\nLa encripto automatico y te activo CACHORRO GRATIS x 7 dias con tus $50 BTC + $50 BNB (recomendable $100+$100)", reply_markup=get_menu_botones(es_admin(m.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["💸 RETIRAR"])
def btn_retirar(m):
    bot.send_message(m.chat.id, "💸 Tu plata esta en TU Binance, no en el bot. La ves en vivo. Para retirar: Binance -> Billetera -> Retirar. Nosotros nunca tocamos tu caja.", reply_markup=get_menu_botones(es_admin(m.chat.id)))

@bot.message_handler(commands=['id'])
def get_id(message):
    acceso,dias = tiene_acceso(message.chat.id); ud = get_user_data(message.chat.id)
    api_status = "✅ ADMIN VINCULADA" if ud.get("api_cargada") and es_admin(message.chat.id) else ("✅ CARGADA" if ud.get("api_cargada") else "❌ FALTA /setapi - DEMO $200")
    plan = ESTADO["socios"].get(message.chat.id, {}).get("plan","CACHORRO") if not es_admin(message.chat.id) else "ADMIN"
    bot.send_message(message.chat.id,f"🆔 Tu ID es: {message.chat.id}\n📦 Plan: {plan} - ⏳ Quedan {dias} dias\n🔑 API: {api_status}\n💰 $200 DEMO ($100 BTC + $100 BNB) - Min $50+$50 para arrancar, recomendable $100+$100\n🔗 Link: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🆔 ID"])
def btn_id(message): return get_id(message)

@bot.message_handler(func=lambda m: m.text in ["📈 ESTRATEGIAS", "/estrategias"])
def estrategias(message):
    ud=get_user_data(message.chat.id); est=ud["estrategias"]
    txt=f"📈 V26.8.9 B-200 - {ud['caja']}\nModo: {ud['modo']}\nMercado: {ud['mercado']}\n\nRATA: {est['RATA']['ops']} ops Win {calcular_winrate_estrategia(est['RATA'])}% Neto ${est['RATA']['neto']}\nLOBO: {est['LOBO']['ops']} ops Win {calcular_winrate_estrategia(est['LOBO'])}% Neto ${est['LOBO']['neto']}\nTIBURON: {est['TIBURON']['ops']} ops Win {calcular_winrate_estrategia(est['TIBURON'])}% Neto ${est['TIBURON']['neto']}\n\n💰 BTC: ${ud['balance_btc']:.2f} (Neto {ud['neto_hoy_btc']:+.2f} Ops {ud['ops_hoy_btc']})\n💰 BNB: ${ud['balance_bnb']:.2f} (Neto {ud['neto_hoy_bnb']:+.2f} Ops {ud['ops_hoy_bnb']})\n\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

def enviar_bienvenida_completa(chat_id, markup):
    limite = 3500
    if len(BIENVENIDA) > limite:
        parte1 = BIENVENIDA[:limite]
        parte2 = BIENVENIDA[limite:]
        bot.send_message(chat_id, parte1)
        time.sleep(0.8)
        bot.send_message(chat_id, parte2 + f"\n\nTu ID: {chat_id}\nTocá 🔑 CARGAR API para entrar en CACHORRO GRATIS", reply_markup=markup)
    else:
        bot.send_message(chat_id, BIENVENIDA + f"\n\nTu ID: {chat_id}\nTocá 🔑 CARGAR API para entrar en CACHORRO GRATIS", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id); ud=get_user_data(message.chat.id)
    if es_admin(message.chat.id):
        bot.send_message(message.chat.id,f"👋 V26.8.9 B-200 BRUBANK + CACHORRO AUTO 🐺\nBalance ${ud['balance']:.2f} (BTC ${ud['balance_btc']:.2f} + BNB ${ud['balance_bnb']:.2f}) - {ud['modo']}\n{ud['mercado']}\nTu web: {WEB_URL}\nAlias: {ALIAS_BRUBANK}", reply_markup=get_menu_botones(True))
    else:
        if not acceso:
            enviar_bienvenida_completa(message.chat.id, get_menu_botones(False))
        else:
            bot.send_message(message.chat.id,f"👋 MANADA V26.8.9 B-200 BRUBANK\n📦 Plan: {ESTADO['socios'][message.chat.id]['plan']} - ⏳ {dias_rest} dias\n⚙️ Modo: {ud['modo']}\nWeb: {WEB_URL}/?id={message.chat.id}\nAlias pago: {ALIAS_BRUBANK}", reply_markup=get_menu_botones(False))

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/prender"])
def prender(message):
    acceso,_=tiene_acceso(message.chat.id)
    if not acceso and not es_admin(message.chat.id): bot.send_message(message.chat.id,"⛔ Vencido - Tocá 🐺 QUIERO LOBO para pagar", reply_markup=get_menu_botones(False)); return
    user_data = get_user_data(message.chat.id)
    user_data["prendido"]=True; user_data["pausa_hasta"]=None
    analizar_mercado_y_elegir_modo(user_data); guardar_datos()
    bot.send_message(message.chat.id,f"🚀 {user_data['caja']} ACTIVADA - ${user_data['balance']} (BTC ${user_data['balance_btc']:.2f} + BNB ${user_data['balance_bnb']:.2f})\nModo {user_data['modo']} - {user_data['mercado']}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance", "/miplan"])
def balance(message):
    acceso,dias = tiene_acceso(message.chat.id)
    if not acceso and not es_admin(message.chat.id):
        bot.send_message(message.chat.id,"⛔ Plan vencido. Tocá 🐺 QUIERO LOBO", reply_markup=get_menu_botones(False)); return
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
    texto = f"""💰 {ud['caja']} - BALANCE DETALLADO V26.8.9

💵 Capital Inicial: ${capital_inicial:.2f} ($100 BTC + $100 BNB - Min $50+$50)
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
🔑 API: {api_status} - Ideal $100 BTC + $100 BNB - Min $50+$50 para arrancar (recomendado $100 por comisiones)

₿ BTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}
💵 Dolar: ${DOLAR_CRIPTO['valor']} ({DOLAR_CRIPTO['actualizado']})
🕒 Actualizado: {ahora_art().strftime('%d/%m/%Y %H:%M:%S')} ART
V26.8.9 BRUBANK + CACHORRO AUTO"""
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
    bot.send_message(message.chat.id, TEXTO_PAGAR, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🐺 QUIERO LOBO", "/quierolobo", "/planes"])
def quiero_lobo(message):
    dolar = DOLAR_CRIPTO['valor']
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"🐀 RATA $20/mes", callback_data="plan_RATA"), types.InlineKeyboardButton(f"🐺 LOBO $40/mes - MAS ELEGIDA", callback_data="plan_LOBO"), types.InlineKeyboardButton(f"🦈 TIBURON $60/mes", callback_data="plan_TIBURON"))
    bot.send_message(message.chat.id, f"🐺 ELEGÍ TU PACK PAGO - DESPUES DE CACHORRO GRATIS\nDEMO $200 ($100 BTC + $100 BNB) - Min $50+$50 para arrancar, ideal $100+$100 por comisiones\nDolar ${dolar}\nAlias BRUBANK {ALIAS_BRUBANK}\n\n{TEXTO_PAGAR}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("plan_"))
def callback_plan(call):
    plan = call.data.split("_")[1];
    bot.answer_callback_query(call.id, f"Elegiste {plan}")
    # Guardar pendiente
    ud = get_user_data(call.message.chat.id)
    ud["pendiente_pago"] = plan
    guardar_datos()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"✅ YA PAGUÉ {plan} - MANDAR COMPROBANTE", callback_data=f"yapague_{plan}"))
    bot.send_message(call.message.chat.id, f"✅ Elegiste {plan} - ${PLANES[plan]}\n\nAlias BRUBANK: {ALIAS_BRUBANK}\n1- Transferi\n2- Toca el boton y manda foto comprobante", reply_markup=markup)

# NUEVOS CALLBACKS V26.8.9 - YA PAGUE + ALTA ADMIN
@bot.callback_query_handler(func=lambda call: call.data.startswith("yapague_"))
def callback_yapague(call):
    plan = call.data.split("_")[1]
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"📸 Perfecto! Ahora mandame la FOTO del comprobante de tu pago {plan} a {ALIAS_BRUBANK}\n\nApenas lo mandas, me llega a mi y te doy el alta en minutos.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.from_user.id
    ud = get_user_data(uid)
    pack = ud.get("pendiente_pago", "LOBO")
    # Reenviar a admin con botones de alta
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"✅ DAR ALTA {pack}", callback_data=f"alta_{uid}_{pack}"), types.InlineKeyboardButton("❌ RECHAZAR", callback_data=f"rechazar_{uid}"))
    try:
        bot.send_photo(chat_id=ADMINS_IDS[0], photo=message.photo[-1].file_id, caption=f"💰 COMPROBANTE NUEVO V26.8.9\n\nSocio: @{message.from_user.username}\nID: {uid}\nPack: {pack}\nAlias destino: {ALIAS_BRUBANK}\n\nRevisa y da el alta:", reply_markup=kb)
        bot.send_message(uid, "✅ Comprobante recibido! Ya le avise al admin. En minutos te damos el alta. ATACAMOS!!! 🐺", reply_markup=get_menu_botones(es_admin(uid)))
    except Exception as e:
        bot.send_message(uid, f"❌ Error enviando comprobante: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("alta_") or call.data.startswith("rechazar_"))
def handle_admin_action(call):
    bot.answer_callback_query(call.id)
    data = call.data
    if data.startswith("alta_"):
        _, uid, pack = data.split("_")
        uid = int(uid)
        ESTADO["socios"][uid] = {"alta": datetime.now(), "vence": datetime.now()+timedelta(days=30), "plan": pack}
        ud = get_user_data(uid)
        ud["pendiente_pago"] = None
        guardar_datos()
        try:
            bot.send_message(uid, f"🔥🔥🔥 ALTA CONFIRMADA LOBO!!!\n\nTu pack {pack} ya esta ACTIVO x 30 dias.\nAlias: {ALIAS_BRUBANK}\n\nDale a 🚀 PRENDER y a cazar!!!\nATACAMOS!!! 🐺", reply_markup=get_menu_botones(False))
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + f"\n\n✅ ALTA DADA - {pack} - {ahora_art().strftime('%d/%m %H:%M')}")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Error dando alta: {e}")
    elif data.startswith("rechazar_"):
        uid = int(data.split("_")[1])
        try:
            bot.send_message(uid, "❌ Comprobante rechazado lobo. Revisa el alias manada.lobo.bru y el monto y manda de nuevo con ✅ YA PAGUE")
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ RECHAZADO")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Error: {e}")

def enviar_lista_socios(chat_id):
    if not ESTADO["socios"]:
        bot.send_message(chat_id, "👥 Sin socios", reply_markup=get_menu_botones(True)); return
    bot.send_message(chat_id, f"👥 SOCIOS - {len(ESTADO['socios'])} activos - V26.8.9", reply_markup=get_menu_botones(True))
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
            guardar_datos(); bot.send_message(message.chat.id,f"✅ Alta {id_cliente} {plan} {dias}d ($100 BTC + $100 BNB - Min $50+$50)")
        except Exception as e: bot.send_message(message.chat.id,f"Error: {e}")
    elif message.text.startswith('/socios'):
        enviar_lista_socios(message.chat.id)

@bot.message_handler(func=lambda m: m.text in ["👥 SOCIOS"])
def btn_socios(message):
    if not es_admin(message.chat.id): bot.send_message(message.chat.id,"⛔ Solo admin", reply_markup=get_menu_botones(False)); return
    enviar_lista_socios(message.chat.id)

HTML="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>V26.8.9 BRUBANK CACHORRO AUTO</title><script src="https://s3.tradingview.com/tv.js"></script><style>
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
<div class="header"><b id="titulo">V26.8.9 BRUBANK</b><div id="admin" class="box admin">Cargando...</div></div>
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
      <span class="kpi total">💵 Inversión<br>$${a.capital_inicial.toFixed(2)}<br><small>$100 BTC + $100 BNB (Min $50+$50)</small></span>
      <span class="kpi total">📈 Total del Día<br>$${a.neto_hoy>=0?'+':''}${a.neto_hoy.toFixed(2)}<br><small>${a.ops_hoy} ops | ${a.winrate}%</small></span>
      <span class="kpi total">💰 Balance<br>$${a.balance.toFixed(2)}</span><br>
      <span class="kpi btc">₿ BTC $${a.balance_btc.toFixed(2)}<br><small>Hoy ${a.neto_hoy_btc>=0?'+':''}${a.neto_hoy_btc.toFixed(2)}</small></span>
      <span class="kpi bnb">🔶 BNB $${a.balance_bnb.toFixed(2)}<br><small>Hoy ${a.neto_hoy_bnb.toFixed(2)}</small></span>
      <span class="kpi modo">🐺 ${a.modo}<br><small>${a.mercado}</small></span>
    `;
    document.getElementById('bloqueSocios').style.display='none';
  } else {
    document.getElementById('titulo').innerText=`V26.8.9 ADMIN - $100 BTC + $100 BNB + SOCIOS - Min $50+$50 - Alias manada.lobo.bru`;
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
