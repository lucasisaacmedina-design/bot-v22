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

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

BALANCE_INICIAL = 200.0
CACHORRO_PORC = 0.20
CACHORRO_DIAS = 7
ADMINS_IDS = [6530209116]
PLANES = {"RATA":15,"LOBO":30,"TIBURON":50,"ORCA":100,"MEGALODON":150}
WEB_URL = "https://bot-v22-1.onrender.com"
DATA_FILE = "/data/manada.json"
os.makedirs("/data", exist_ok=True)

# === CONFIG PAGO DEMO MP SIMPLE + DOLAR AUTO ===
ALIAS_MP_DEMO = "manada.lobo.demo.mp"
DOLAR_CRIPTO_DEMO = 1450
DOLAR_CRIPTO = {"valor": 1480, "actualizado": "inicio", "fuente": "DEMO"}
CEDEARS = {"AAPL": 1200.5, "TSLA": 890.3, "NVDA": 1450.8, "MELI": 2500.0}

print(f"### V26.1 MEGALODON ADMIN 100% + ESTRATEGIAS + CEDEARS + BOTONES + DOLAR AUTO - DISCO: {DATA_FILE} ###")

ESTADO = {
    "btc": 78287.4,
    "bnb": 739.68,
    "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)],
    "socios": {},
    "admins": ADMINS_IDS,
    "cedears_history": {"AAPL": [1200.5], "TSLA": [890.3], "NVDA": [1450.8]}
}
USUARIOS = {}
LOCK = threading.Lock()

# === TEXTOS FINALES V26.1 ===
BIENVENIDA = f"""
Hola Lobo, bienvenido a la manada mas unica y exclusiva de todas.

Aca valoramos cada pequeno esfuerzo y apoyamos el crecimiento personal, profesional y economico de cada socio.

Te vas a hacer millonario con nosotros? No.
Pero lo que si te prometemos es luchar, atacar y jamas rendirnos para mejorar dia a dia y brindar siempre lo mejor de cada uno de nosotros.

ATACAMOS!!!

QUE ES TODO ESTO? Te lo explico simple, sin humo:

BTC: Es el oro digital. La moneda madre.
BNB: La moneda del broker, nos ahorra comisiones.
BROKER (Binance): Es donde esta TU plata. Nosotros nunca la tocamos.
BOT: Soy yo, opero 24hs automatico por vos.
CAJA SEPARADA: Tu plata no se mezcla con nadie. La ves en vivo en tu link privado.
NETO: Lo que te quedo limpio hoy.
WINRATE: % de ganadas reales.

NUESTRAS BESTIAS:
CACHORRO - GRATIS 7 DIAS - Para probar. 1 op a la vez.
RATA - $15 USD/mes - Sigilosa y segura. Win 70%+
LOBO - $30 USD/mes - LA MAS ELEGIDA. Equilibrada. 3-5 ops/dia.
TIBURON - $50 USD/mes - Agresiva. Para cajas +$500.
ORCA - $100 USD/mes - Avanzada.
MEGALODON - $150 USD/mes - El depredador final. ADMIN 100% TODAS LAS BESTIAS.

COMO PAGAR? SUPER SIMPLE EN 3 PASOS (Mercado Pago):
PASO 1: Toca boton 🐺 QUIERO LOBO abajo
PASO 2: Paga por Mercado Pago a este alias (DEMO): {ALIAS_MP_DEMO}
PASO 3: Manda /comprobante + foto del pago.
En 5 min te activo con tu link privado y tu contador 30->0 dias.

Empeza con /id para ver tu ID y tu link.
Para ver como pagar siempre: toca 💰 PAGAR
"""

TEXTO_PAGAR = f"""
COMO PAGAR? EN 3 PASOS - SIMPLE:

PASO 1: Elegi tu bestia (toca boton)
🐺 QUIERO LOBO = $30 USD
/quiero RATA = $15 USD
/quiero TIBURON = $50 USD
/quiero MEGALODON = $150 USD

PASO 2: Paga por Mercado Pago
Alias DEMO: {ALIAS_MP_DEMO}
Dolar Cripto Auto: ${DOLAR_CRIPTO['valor']} (act {DOLAR_CRIPTO['actualizado']})
- Abri Mercado Pago
- Transferir -> Alias
- Pega el alias

PASO 3: Manda el comprobante
Toca 📸 COMPROBANTE y manda la captura.

Listo. Te doy de alta en el momento con tu caja separada.
Usas cripto? Tambien acepto USDT BEP20, pedime la direccion.
"""

def actualizar_dolar_y_cedears():
    while True:
        try:
            r = requests.get("https://criptoya.com/api/dolar", timeout=10).json()
            if r and 'cripto' in r:
                # busca el mejor
                if 'ccb' in r['cripto']:
                    DOLAR_CRIPTO["valor"] = int(float(r['cripto']['ccb']))
                    DOLAR_CRIPTO["actualizado"] = datetime.now().strftime("%H:%M")
                    DOLAR_CRIPTO["fuente"] = "criptoya"
        except:
            DOLAR_CRIPTO["valor"] = DOLAR_CRIPTO["valor"] + random.randint(-5,5)
        # Simula CEDEARs movimiento
        try:
            for k in CEDEARS:
                CEDEARS[k] = round(CEDEARS[k] + random.uniform(-5,5), 2)
                ESTADO["cedears_history"][k].append(CEDEARS[k])
                if len(ESTADO["cedears_history"][k]) > 30:
                    ESTADO["cedears_history"][k] = ESTADO["cedears_history"][k][-30:]
        except:
            pass
        time.sleep(3600)

def get_menu_botones(admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if admin:
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("👥 SOCIOS"), types.KeyboardButton("📈 ESTRATEGIAS"))
        markup.add(types.KeyboardButton("💰 PAGAR"), types.KeyboardButton("🐺 QUIERO LOBO"))
        markup.add(types.KeyboardButton("💾 DEBUG"), types.KeyboardButton("📜 HISTORIAL"))
    else:
        markup.add(types.KeyboardButton("💰 PAGAR"), types.KeyboardButton("🐺 QUIERO LOBO"))
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("📜 HISTORIAL"), types.KeyboardButton("📈 ESTRATEGIAS"))
        markup.add(types.KeyboardButton("📸 COMPROBANTE"), types.KeyboardButton("🆔 ID"))
    return markup

def guardar_datos():
    try:
        with LOCK:
            socios_ser = {}
            for k,v in ESTADO["socios"].items():
                socios_ser[str(k)] = {
                    "alta": v["alta"].isoformat() if isinstance(v["alta"], datetime) else str(v["alta"]),
                    "vence": v["vence"].isoformat() if isinstance(v["vence"], datetime) else str(v["vence"]),
                    "plan": v["plan"]
                }
            usuarios_ser = {}
            for k,v in USUARIOS.items():
                vd = v.copy()
                if vd.get("pausa_hasta") and isinstance(vd["pausa_hasta"], datetime):
                    vd["pausa_hasta"] = vd["pausa_hasta"].isoformat()
                usuarios_ser[str(k)] = vd
            data = {
                "socios": socios_ser,
                "usuarios": usuarios_ser,
                "guardado": datetime.now().isoformat(),
                "dolar": DOLAR_CRIPTO,
                "cedears": CEDEARS
            }
            tmp = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, DATA_FILE)
    except Exception as e:
        print(f"Error guardando: {e}")

def cargar_datos():
    try:
        if not os.path.exists(DATA_FILE):
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k,v in data.get("socios", {}).items():
            try:
                ESTADO["socios"][int(k)] = {
                    "alta": datetime.fromisoformat(v["alta"]),
                    "vence": datetime.fromisoformat(v["vence"]),
                    "plan": v["plan"]
                }
            except:
                pass
        for k,v in data.get("usuarios", {}).items():
            try:
                if v.get("pausa_hasta"):
                    try:
                        v["pausa_hasta"] = datetime.fromisoformat(v["pausa_hasta"])
                    except:
                        v["pausa_hasta"] = None
                # Asegurar estrategias si no existen
                if "estrategias" not in v:
                    v["estrategias"] = {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}, "MEGALODON": {"ops":0,"ganadas":0,"neto":0.0}}
                USUARIOS[int(k)] = v
            except:
                pass
        if "dolar" in data:
            DOLAR_CRIPTO.update(data["dolar"])
        if "cedears" in data:
            CEDEARS.update(data["cedears"])
    except Exception as e:
        print(f"Error cargando: {e}")

cargar_datos()

def get_user_data(user_id):
    user_id = int(user_id)
    es_admin_id = user_id in ADMINS_IDS
    if user_id not in USUARIOS:
        USUARIOS[user_id] = {
            "prendido": False,
            "balance": BALANCE_INICIAL,
            "balance_inicial": BALANCE_INICIAL,
            "btc_inicial": 100.0,
            "bnb_inicial": 100.0,
            "ops_hoy": 0,
            "neto_hoy": 0.0,
            "ganadas": 0,
            "perdidas": 0,
            "modo": "MEGALODON" if es_admin_id else "CACHORRO",
            "mercado": "MEGALODON FULL 100% - TODAS LAS BESTIAS" if es_admin_id else "CACHORRO GRATIS 7 DIAS (20%)",
            "pausa_hasta": None,
            "historial": [],
            "caja": "ADMIN MEGALODON 100%" if es_admin_id else "SOCIO",
            "estrategias": {
                "RATA": {"ops":0,"ganadas":0,"neto":0.0},
                "LOBO": {"ops":0,"ganadas":0,"neto":0.0},
                "TIBURON": {"ops":0,"ganadas":0,"neto":0.0},
                "MEGALODON": {"ops":0,"ganadas":0,"neto":0.0}
            }
        }
        guardar_datos()
    # FIX MEGALODON ADMIN SIEMPRE
    if es_admin_id:
        USUARIOS[user_id]["caja"] = "ADMIN MEGALODON 100%"
        if USUARIOS[user_id]["modo"] == "CACHORRO":
            USUARIOS[user_id]["modo"] = "MEGALODON"
            USUARIOS[user_id]["mercado"] = "MEGALODON FULL 100% - TODAS LAS BESTIAS"
    if "estrategias" not in USUARIOS[user_id]:
        USUARIOS[user_id]["estrategias"] = {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}, "MEGALODON": {"ops":0,"ganadas":0,"neto":0.0}}
    return USUARIOS[user_id]

def es_admin(chat_id):
    try:
        return int(chat_id) in ESTADO["admins"]
    except:
        return False

def tiene_acceso(chat_id):
    chat_id=int(chat_id)
    if es_admin(chat_id):
        return True, 999
    socio=ESTADO["socios"].get(chat_id)
    if not socio:
        return False, 0
    if datetime.now() > socio["vence"]:
        return False, 0
    dias=(socio["vence"]-datetime.now()).days+1
    return True, dias

def calcular_winrate(user_data):
    total=user_data["ganadas"]+user_data["perdidas"]
    return round((user_data["ganadas"]/total)*100) if total else 0

def calcular_winrate_estrategia(est):
    if est["ops"] == 0:
        return 0
    return round((est["ganadas"]/est["ops"])*100)

def get_estado_texto(user_data):
    if not user_data["prendido"]:
        return "🔴 APAGADO"
    if user_data["pausa_hasta"] and isinstance(user_data["pausa_hasta"], datetime) and datetime.now() < user_data["pausa_hasta"]:
        mins=int((user_data["pausa_hasta"]-datetime.now()).total_seconds()/60)+1
        return f"⏸️ Pausa {mins}min (solo esta caja)"
    return "🟢 PRENDIDO"

def analizar_mercado_y_elegir_modo(user_data, user_id=None):
    # ADMIN SIEMPRE MEGALODON
    if user_id and int(user_id) in ADMINS_IDS:
        user_data["modo"]="MEGALODON"
        user_data["mercado"]="MEGALODON FULL 100% - TODAS LAS BESTIAS"
        return 1.5
    if user_data["modo"]=="CACHORRO":
        user_data["mercado"]="CACHORRO GRATIS 7 DIAS (20%)"
        return 0.20
    try:
        ultimos=ESTADO["btc_history"][-10:]
        atr=round((max(ultimos)-min(ultimos))/ESTADO["btc"]*100,2)
        if atr<0.25:
            atr=round(random.uniform(0.28,0.48),2)
    except:
        atr=0.40
    if atr<0.35:
        user_data["modo"]="RATA"
        user_data["mercado"]=f"LATERAL ({atr:.2f}%)"
    elif atr>0.70:
        user_data["modo"]="TIBURON"
        user_data["mercado"]=f"VOLATIL ({atr:.2f}%)"
    else:
        user_data["modo"]="LOBO"
        user_data["mercado"]=f"NORMAL ({atr:.2f}%)"
    return atr

def motor_demo():
    contador=0
    while True:
        time.sleep(random.randint(3,6))
        ESTADO["btc"]=round(78287.4+random.uniform(-350,350),2)
        ESTADO["bnb"]=round(739.68+random.uniform(-5,5),2)
        ESTADO["btc_history"].append(ESTADO["btc"])
        if len(ESTADO["btc_history"])>30:
            ESTADO["btc_history"]=ESTADO["btc_history"][-30:]
        for user_id, user_data in list(USUARIOS.items()):
            if not user_data["prendido"]:
                continue
            if user_data["pausa_hasta"] and isinstance(user_data["pausa_hasta"], datetime) and datetime.now()<user_data["pausa_hasta"]:
                continue
            es_admin_id = int(user_id) in ADMINS_IDS
            if es_admin_id:
                analizar_mercado_y_elegir_modo(user_data, user_id)
                # MEGALODON USA TODAS LAS ESTRATEGIAS
                modo_elegido = random.choice(["RATA","LOBO","TIBURON"])
                if modo_elegido == "RATA":
                    es_ganada,gan,perd=random.random()<0.72,0.80,0.50
                    tp,sl="+0.2%","-0.4%"
                elif modo_elegido == "LOBO":
                    es_ganada,gan,perd=random.random()<0.68,1.80,1.00
                    tp,sl="+0.5%","-0.8%"
                else:
                    es_ganada,gan,perd=random.random()<0.60,3.20,1.50
                    tp,sl="+1.1%","-1.2%"
                # ESTRATEGIA TRACK
                user_data["estrategias"][modo_elegido]["ops"]+=1
                user_data["estrategias"]["MEGALODON"]["ops"]+=1
                if es_ganada:
                    user_data["estrategias"][modo_elegido]["ganadas"]+=1
                    user_data["estrategias"][modo_elegido]["neto"]=round(user_data["estrategias"][modo_elegido]["neto"]+gan,2)
                    user_data["estrategias"]["MEGALODON"]["ganadas"]+=1
                    user_data["estrategias"]["MEGALODON"]["neto"]=round(user_data["estrategias"]["MEGALODON"]["neto"]+gan,2)
                else:
                    user_data["estrategias"][modo_elegido]["neto"]=round(user_data["estrategias"][modo_elegido]["neto"]-perd,2)
                    user_data["estrategias"]["MEGALODON"]["neto"]=round(user_data["estrategias"]["MEGALODON"]["neto"]-perd,2)
            else:
                if user_data["modo"]!="CACHORRO":
                    analizar_mercado_y_elegir_modo(user_data)
                modo=user_data["modo"]
                factor=CACHORRO_PORC
                if modo in ["LOBO","CACHORRO"]:
                    es_ganada,gan,perd=random.random()<0.66,0.60*factor,0.80*factor
                    tp,sl="+0.3%","-0.7%"
                elif modo=="RATA":
                    es_ganada,gan,perd=random.random()<0.70,0.30*factor,0.40*factor
                    tp,sl="+0.15%","-0.4%"
                else:
                    es_ganada,gan,perd=random.random()<0.55,1.20*factor,1.00*factor
                    tp,sl="+0.8%","-1.0%"
                # TRACK SOCIO TAMBIEN
                if modo not in user_data["estrategias"]:
                    user_data["estrategias"][modo]={"ops":0,"ganadas":0,"neto":0.0}
                user_data["estrategias"][modo]["ops"]+=1
                if es_ganada:
                    user_data["estrategias"][modo]["ganadas"]+=1
                    user_data["estrategias"][modo]["neto"]=round(user_data["estrategias"][modo]["neto"]+gan,2)
                else:
                    user_data["estrategias"][modo]["neto"]=round(user_data["estrategias"][modo]["neto"]-perd,2)
            # BALANCE GENERAL
            modo_log = modo_elegido if es_admin_id else user_data["modo"]
            if es_ganada:
                user_data["ganadas"]+=1
                user_data["ops_hoy"]+=1
                user_data["neto_hoy"]=round(user_data["neto_hoy"]+gan,2)
                user_data["balance"]=round(user_data["balance"]+gan,2)
                user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - BTC - {modo_log} - TP {tp} = +${gan} Neto")
            else:
                user_data["perdidas"]+=1
                user_data["ops_hoy"]+=1
                user_data["neto_hoy"]=round(user_data["neto_hoy"]-perd,2)
                user_data["balance"]=round(user_data["balance"]-perd,2)
                user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - BNB - {modo_log} - SL {sl} = -${perd} Neto (Pausa 10min)")
                user_data["pausa_hasta"]=datetime.now()+timedelta(minutes=10)
            if len(user_data["historial"])>20:
                user_data["historial"]=user_data["historial"][-20:]
        contador+=1
        if contador>=10:
            guardar_datos()
            contador=0

@bot.message_handler(commands=['id'])
def get_id(message):
    bot.send_message(message.chat.id,f"Tu ID es: {message.chat.id}\nTu link: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🆔 ID", "ID"])
def id_btn(message):
    get_id(message)

@bot.message_handler(func=lambda m: m.text in ["💰 PAGAR", "/pagar"])
def pagar(message):
    bot.send_message(message.chat.id, TEXTO_PAGAR + f"\nDolar actual: ${DOLAR_CRIPTO['valor']} fuente {DOLAR_CRIPTO['fuente']}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(commands=['quiero'])
def quiero(message):
    try:
        parts=message.text.split()
        plan=parts[1].upper() if len(parts)>1 else "LOBO"
        if plan not in PLANES:
            plan="LOBO"
        usd=PLANES[plan]
        ars=usd*DOLAR_CRIPTO["valor"]
        bot.send_message(message.chat.id, f"🐺 Queres {plan} - ${usd} USD\n\nPASO 2: Paga ${ars} ARS (aprox, dolar cripto ${DOLAR_CRIPTO['valor']} act {DOLAR_CRIPTO['actualizado']})\nAlias MP DEMO: {ALIAS_MP_DEMO}\n\nLuego manda /comprobante + foto\n\nUSDT opcional: {usd} USDT BEP20: 0xDEMO123 (DEMO)", reply_markup=get_menu_botones(es_admin(message.chat.id)))
    except:
        bot.send_message(message.chat.id,"Usa: /quiero LOBO", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["🐺 QUIERO LOBO", "QUIERO LOBO", "🦖 QUIERO MEGALODON"])
def quiero_btn(message):
    txt = message.text
    if "MEGALODON" in txt:
        plan="MEGALODON"
    else:
        plan="LOBO"
    usd=PLANES[plan]
    ars=usd*DOLAR_CRIPTO["valor"]
    bot.send_message(message.chat.id, f"🐺 Queres {plan} - ${usd} USD = ${ars} ARS\nAlias: {ALIAS_MP_DEMO}\nDolar: ${DOLAR_CRIPTO['valor']}\nLuego toca 📸 COMPROBANTE", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📸 COMPROBANTE", "/comprobante", "COMPROBANTE"])
def comprobante(message):
    for admin_id in ADMINS_IDS:
        try:
            bot.forward_message(admin_id, message.chat.id, message.message_id)
            bot.send_message(admin_id, f"💰 NUEVO PAGO\nDe: {message.chat.id}\nPara dar de alta: /alta {message.chat.id} 30 LOBO\nO /alta {message.chat.id} 7 CACHORRO")
        except:
            pass
    bot.send_message(message.chat.id, "✅ Comprobante recibido Lobo. En 5 min te doy de alta. ATACAMOS!", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📈 ESTRATEGIAS", "/estrategias", "ESTRATEGIAS"])
def estrategias(message):
    ud=get_user_data(message.chat.id)
    est=ud["estrategias"]
    txt=f"📈 ESTRATEGIAS FUTURO + CEDEARs - {ud['caja']}\n\n"
    txt+=f"🦖 MEGALODON TOTAL: {est['MEGALODON']['ops']} ops - Win {calcular_winrate_estrategia(est['MEGALODON'])}% - Neto ${est['MEGALODON']['neto']}\n"
    txt+=f"🐀 RATA: {est['RATA']['ops']} ops - Win {calcular_winrate_estrategia(est['RATA'])}% - Neto ${est['RATA']['neto']}\n"
    txt+=f"🐺 LOBO: {est['LOBO']['ops']} ops - Win {calcular_winrate_estrategia(est['LOBO'])}% - Neto ${est['LOBO']['neto']}\n"
    txt+=f"🦈 TIBURON: {est['TIBURON']['ops']} ops - Win {calcular_winrate_estrategia(est['TIBURON'])}% - Neto ${est['TIBURON']['neto']}\n\n"
    txt+=f"📊 MERCADO FUTURO:\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}\n"
    txt+=f"CEDEARs (DEMO): AAPL ${CEDEARS['AAPL']} TSLA ${CEDEARS['TSLA']} NVDA ${CEDEARS['NVDA']}\n\n"
    txt+=f"Dolar Cripto: ${DOLAR_CRIPTO['valor']} ({DOLAR_CRIPTO['fuente']} {DOLAR_CRIPTO['actualizado']})"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(commands=['alta'])
def alta(message):
    if not es_admin(message.chat.id):
        return
    try:
        parts=message.text.split()
        id_cliente=int(parts[1])
        dias=int(parts[2])
        plan="CACHORRO GRATIS 7 DIAS" if len(parts)<4 or parts[3].upper() in ["CACHORRO","GRATIS"] else parts[3].upper()
        vence=datetime.now()+timedelta(days=dias)
        ESTADO["socios"][id_cliente]={"alta":datetime.now(),"vence":vence,"plan":plan}
        user_data = get_user_data(id_cliente)
        user_data["balance"]=BALANCE_INICIAL
        user_data["balance_inicial"]=BALANCE_INICIAL
        user_data["neto_hoy"]=0.0
        user_data["ops_hoy"]=0
        user_data["ganadas"]=0
        user_data["perdidas"]=0
        user_data["historial"]=[]
        user_data["prendido"]=False
        user_data["estrategias"]={"RATA":{"ops":0,"ganadas":0,"neto":0.0},"LOBO":{"ops":0,"ganadas":0,"neto":0.0},"TIBURON":{"ops":0,"ganadas":0,"neto":0.0},"MEGALODON":{"ops":0,"ganadas":0,"neto":0.0}}
        if id_cliente in ADMINS_IDS:
            user_data["caja"]=f"ADMIN MEGALODON 100%"
            user_data["modo"]="MEGALODON"
            user_data["mercado"]="MEGALODON FULL 100% - TODAS LAS BESTIAS"
        else:
            user_data["caja"]=f"SOCIO {plan}"
            user_data["modo"]="CACHORRO"
            user_data["mercado"]="CACHORRO GRATIS 7 DIAS (20%)"
        guardar_datos()
        bot.send_message(message.chat.id,f"✅ Alta OK\n🟠 CAJA SOCIO: {id_cliente}\nPlan: {plan}\nVence: {vence.strftime('%d/%m')} ({dias}d)\nLink del socio: {WEB_URL}/?id={id_cliente}\n💾 {DATA_FILE}", reply_markup=get_menu_botones(True))
        try:
            bot.send_message(id_cliente,f"""🐺 ¡Fuiste dado de alta!
Plan: {plan} por {dias} días
Tu balance arranca $200 SEPARADO (solo tuyo)

👉 TU WEB PRIVADA (solo tu caja):
{WEB_URL}/?id={id_cliente}

Guarda ese link, ahi ves tu plata en vivo separada del admin.
Toca 🚀 PRENDER para arrancar
📊 BALANCE para ver tu caja""", reply_markup=get_menu_botones(False))
        except Exception as e:
            bot.send_message(message.chat.id,f"⚠️ No le pude mandar mensaje al socio {id_cliente}, seguro no hablo con el bot aun. Pasale vos el link: {WEB_URL}/?id={id_cliente}")
    except Exception as e:
        bot.send_message(message.chat.id,f"Error /alta: {e}")

@bot.message_handler(commands=['reset'])
def reset_user(message):
    if not es_admin(message.chat.id):
        return
    try:
        parts=message.text.split()
        idc=int(parts[1])
        monto=float(parts[2]) if len(parts)>2 else BALANCE_INICIAL
        user_data = get_user_data(idc)
        user_data["balance"]=monto
        user_data["balance_inicial"]=monto
        user_data["btc_inicial"]=monto/2
        user_data["bnb_inicial"]=monto/2
        user_data["neto_hoy"]=0.0
        user_data["ops_hoy"]=0
        user_data["ganadas"]=0
        user_data["perdidas"]=0
        user_data["historial"]=[]
        user_data["pausa_hasta"]=None
        user_data["estrategias"]={"RATA":{"ops":0,"ganadas":0,"neto":0.0},"LOBO":{"ops":0,"ganadas":0,"neto":0.0},"TIBURON":{"ops":0,"ganadas":0,"neto":0.0},"MEGALODON":{"ops":0,"ganadas":0,"neto":0.0}}
        guardar_datos()
        bot.send_message(message.chat.id,f"♻️ RESET OK {idc} -> ${monto} (solo su caja)", reply_markup=get_menu_botones(True))
    except Exception as e:
        bot.send_message(message.chat.id,f"Error reset: {e}")

@bot.message_handler(commands=['addbalance','add'])
def add_balance(message):
    if not es_admin(message.chat.id):
        return
    try:
        parts=message.text.split()
        idc=int(parts[1])
        monto=float(parts[2])
        user_data=get_user_data(idc)
        user_data["balance"]=round(user_data["balance"]+monto,2)
        guardar_datos()
        bot.send_message(message.chat.id,f"➕ ${monto} a {idc} -> ${user_data['balance']}", reply_markup=get_menu_botones(True))
    except:
        bot.send_message(message.chat.id,"Uso: /add <ID> <MONTO>")

@bot.message_handler(commands=['baja'])
def baja(message):
    if not es_admin(message.chat.id):
        return
    try:
        idc=int(message.text.split()[1])
        if idc in ESTADO["socios"]:
            del ESTADO["socios"][idc]
        if idc in USUARIOS:
            del USUARIOS[idc]
        guardar_datos()
        bot.send_message(message.chat.id,f"🗑️ Baja OK {idc}", reply_markup=get_menu_botones(True))
    except:
        bot.send_message(message.chat.id,"Uso: /baja <ID>")

@bot.message_handler(func=lambda m: m.text in ["👥 SOCIOS", "/socios"])
def socios(message):
    if not es_admin(message.chat.id):
        return
    admin=get_user_data(ADMINS_IDS[0])
    txt=f"👥 V26.1 MEGALODON FULL + ESTRATEGIAS + CEDEARS\n\n🔵🦖 ADMIN MEGALODON 100%:\n {ADMINS_IDS[0]} - ${admin['balance']} - {get_estado_texto(admin)} - {admin['modo']}\nLink: {WEB_URL} (sin?id)\nDolar ${DOLAR_CRIPTO['valor']} | CEDEARs AAPL ${CEDEARS['AAPL']}\n\n🟠 SOCIOS (20% - links privados):\n"
    if not ESTADO["socios"]:
        txt+=" Sin socios\n"
    else:
        for cid,data in ESTADO["socios"].items():
            bal = USUARIOS.get(cid, {}).get("balance", 200)
            txt+=f" {cid} - {data['plan']} - ${bal} - {WEB_URL}/?id={cid}\n"
    bot.send_message(message.chat.id,txt, reply_markup=get_menu_botones(True))

@bot.message_handler(func=lambda m: m.text in ["💾 DEBUG", "/debug"])
def debug_cmd(message):
    if not es_admin(message.chat.id):
        return
    size=os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0
    bot.send_message(message.chat.id,f"💾 DEBUG V26.1 FULL SUMADO\nFile: {DATA_FILE}\nSize: {size}b\nADMIN MEGALODON ${USUARIOS.get(ADMINS_IDS[0],{}).get('balance','?')} {USUARIOS.get(ADMINS_IDS[0],{}).get('modo','?')}\nSocios: {len(ESTADO['socios'])}\nAlias DEMO: {ALIAS_MP_DEMO}\nDolar ${DOLAR_CRIPTO['valor']} {DOLAR_CRIPTO['fuente']}\nCEDEARs {CEDEARS}\nLineas: 682+", reply_markup=get_menu_botones(True))

@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if es_admin(message.chat.id):
        ud=get_user_data(message.chat.id)
        bot.send_message(message.chat.id,f"👋 MANADA V26.1 ADMIN MEGALODON 100% 🦖\nModo: {ud['modo']} - {ud['mercado']}\nBalance ${ud['balance']} - Dolar ${DOLAR_CRIPTO['valor']}\nEstrategias: RATA/LOBO/TIBURON activas\nCEDEARs: AAPL ${CEDEARS['AAPL']}\n{BIENVENIDA}\n\nTu web: {WEB_URL}\nToca los botones de abajo 👇", reply_markup=get_menu_botones(True))
    else:
        if not acceso:
            bot.send_message(message.chat.id, BIENVENIDA + f"\n\nTu ID: {message.chat.id}\nAlias DEMO: {ALIAS_MP_DEMO} Dolar ${DOLAR_CRIPTO['valor']}\nToca 💰 PAGAR para ver como pagar\nToca 🆔 ID", reply_markup=get_menu_botones(False))
        else:
            bot.send_message(message.chat.id,f"👋 MANADA V26.1 🐺\nTu plan: {ESTADO['socios'][message.chat.id]['plan']} - Quedan {dias_rest} dias\nTu web privada:\n{WEB_URL}/?id={message.chat.id}\nToca 🚀 PRENDER para arrancar\nToca 💰 PAGAR si queres renovar", reply_markup=get_menu_botones(False))

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/Prender", "/prender", "PRENDER"])
def prender(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso:
        bot.send_message(message.chat.id,"⛔ Vencido - toca 💰 PAGAR para renovar", reply_markup=get_menu_botones(False))
        return
    user_data = get_user_data(message.chat.id)
    user_data["prendido"]=True
    user_data["pausa_hasta"]=None
    if es_admin(message.chat.id):
        user_data["modo"]="MEGALODON"
        user_data["mercado"]="MEGALODON FULL 100% - TODAS LAS BESTIAS"
    else:
        user_data["modo"]="CACHORRO"
        user_data["mercado"]="CACHORRO GRATIS 7 DIAS (20%)"
    guardar_datos()
    link = f"{WEB_URL}/?id={message.chat.id}" if not es_admin(message.chat.id) else WEB_URL
    caja = user_data["caja"]
    bot.send_message(message.chat.id,f"🚀 {caja} ACTIVADA - ${user_data['balance']}\nModo {user_data['modo']}\nTu web: {link}\nToca 📊 BALANCE", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance", "BALANCE"])
def balance(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso:
        return
    user_data = get_user_data(message.chat.id)
    win=calcular_winrate(user_data)
    if es_admin(message.chat.id):
        bot.send_message(message.chat.id,f"💰 🔵🦖 CAJA ADMIN MEGALODON 100% SEPARADA\nBalance: ${user_data['balance']} (solo tuyo)\nNeto: ${user_data['neto_hoy']} ({user_data['ops_hoy']} ops) Win {win}%\nModo: {user_data['modo']} | {user_data['mercado']}\nEstado: {get_estado_texto(user_data)}\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']} | CEDEARs AAPL ${CEDEARS['AAPL']}\nDolar ${DOLAR_CRIPTO['valor']}\nWeb: {WEB_URL}", reply_markup=get_menu_botones(True))
    else:
        plan=ESTADO["socios"][message.chat.id]["plan"]
        bot.send_message(message.chat.id,f"💰 🟠 TU CAJA - PLAN {plan}\nBalance: ${user_data['balance']} USDT (solo tuyo)\nNeto: ${user_data['neto_hoy']} ({user_data['ops_hoy']} ops) Win {win}%\nModo: {user_data['modo']} | {user_data['mercado']}\nEstado: {get_estado_texto(user_data)}\nTu web privada:\n{WEB_URL}/?id={message.chat.id}\nToca 📈 ESTRATEGIAS para ver detalle", reply_markup=get_menu_botones(False))

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL", "/historial", "HISTORIAL"])
def historial(message):
    user_data = get_user_data(message.chat.id)
    hist="\n".join(user_data["historial"][-15:]) or "Sin ops aun"
    bot.send_message(message.chat.id,f"📜 HISTORIAL {user_data['caja']}\n{hist}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(commands=['Apagar','apagar'])
def apagar(message):
    user_data = get_user_data(message.chat.id)
    markup=telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("RETIRAR 💸",callback_data="retirar"),telebot.types.InlineKeyboardButton("REANUDAR ▶️",callback_data="reanudar"))
    user_data["prendido"]=False
    guardar_datos()
    bot.send_message(message.chat.id,f"🛑 Tu caja {user_data['caja']} pausada en ${user_data['balance']}\nLas otras siguen.",reply_markup=markup)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    user_data = get_user_data(c.message.chat.id)
    if c.data=="retirar":
        bot.send_message(c.message.chat.id,f"💸 Tu caja {user_data['caja']}: ${user_data['balance']}")
    elif c.data=="reanudar":
        user_data["prendido"]=True
        guardar_datos()
        bot.send_message(c.message.chat.id,"▶️ Reanudado, solo tu caja.")

HTML="""<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="google" content="notranslate"><title>V26.1 MEGALODON + ESTRATEGIAS + CEDEARS</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial}.header{background:#1e222d;padding:10px}.box{padding:12px;margin:6px;border-radius:10px;font-size:13px;line-height:1.6}.admin{background:#0d2a4a;border-left:5px solid #00ffea}.socio{background:#3a2a1a;border-left:5px solid #ff9800}.contador{background:#1e1e00;border:2px solid #ffcc00;color:#ffcc00;font-size:18px;font-weight:bold;text-align:center}.estrategia{background:#1a2a1a;border-left:5px solid #00ff00}.cedears{background:#2a1a2a;border-left:5px solid #ff00ff}.kpi{display:inline-block;background:#1e222d;padding:6px 9px;border-radius:6px;margin:3px;font-size:12px;border:1px solid #2a2e39}.btn{display:inline-block;margin-top:10px;padding:9px 16px;background:#00ffea;color:#000;border-radius:8px;text-decoration:none;font-weight:bold}.btn2{display:inline-block;margin-left:6px;padding:9px 16px;background:#2a2e39;color:#fff;border-radius:8px;text-decoration:none}#chart_btc{height:45vh}#chart_bnb{height:25vh}#chart_cedears{height:25vh}a{color:#00ffea}</style></head><body><div class="header"><b id="titulo">🦖 V26.1 MEGALODON + ESTRATEGIAS + CEDEARS</b><div id="admin" class="box admin">Cargando...</div><div id="contador" class="box contador" style="display:none"></div><div id="estrategias" class="box estrategia">Cargando estrategias...</div><div id="cedears" class="box cedears">Cargando CEDEARs...</div><div id="socios" class="box socio">Cargando SOCIOS...</div><div id="infoPlan" class="box socio" style="display:none"></div></div><div id="chart_btc"></div><div id="chart_bnb"></div><div id="chart_cedears"></div>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"chart_btc"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","container_id":"chart_bnb"});
new TradingView.widget({"autosize":true,"symbol":"NASDAQ:AAPL","interval":"5","theme":"dark","container_id":"chart_cedears"});
function getId(){return new URLSearchParams(window.location.search).get('id')}
async function r(){
 let sid=getId();
 if(sid){
   try{
     let d=await (await fetch('/api/socio/'+sid)).json();
     if(d.error){document.getElementById('admin').innerHTML='⛔ Socio no existe<br><a class="btn" href="/">⬅️ Volver a mi caja ADMIN</a>';return}
     document.getElementById('titulo').innerHTML=`🐺 CAJA SOCIO ${sid} - PLAN ${d.plan}`;
     document.getElementById('admin').className='box socio';
     document.getElementById('admin').innerHTML=`🟠 TU CAJA - PLAN ${d.plan}<br><span class="kpi">💰 Bal: $${d.balance}</span><span class="kpi">📈 Neto: $${d.neto_hoy}</span><span class="kpi">🔄 Ops: ${d.ops_hoy}</span><span class="kpi">🎯 Win: ${d.winrate}%</span><br><span class="kpi">⚙️ Modo: ${d.modo}</span><span class="kpi">📊 Merc: ${d.mercado}</span><br><span class="kpi">₿ BTC: $${d.btc}</span><span class="kpi">🔶 BNB: $${d.bnb}</span><br>Estado: ${d.estado_texto}<br>ID ${sid}<br><a class="btn" href="/">⬅️ Volver a mi caja ADMIN</a> <a class="btn2" href="/?id=${sid}">🔄 Recargar</a>`;
     document.getElementById('contador').style.display='block';
     if(d.vence_dias<=0 && d.vence_horas<=0){document.getElementById('contador').innerHTML=`⛔ PLAN VENCIDO<br>Venció: ${d.vence}<br>Contacta al admin para renovar`;document.getElementById('contador').style.borderColor='red';document.getElementById('contador').style.color='red';}
     else if(d.vence_dias==0){document.getElementById('contador').innerHTML=`⏰ TE QUEDA HOY - VENCE EN ${d.vence_horas}h ${d.vence_mins}m<br>Plan ${d.plan} - Vence ${d.vence}`;}
     else{document.getElementById('contador').innerHTML=`⏳ TE QUEDAN ${d.vence_dias} DIAS ${d.vence_horas}h<br>Plan ${d.plan} - Vence: ${d.vence}<br><small>Manana te quedaran ${d.vence_dias-1} dias</small>`;}
     document.getElementById('estrategias').innerHTML=`📈 ESTRATEGIAS FUTURO: RATA ${d.estrategias.RATA.ops} ops Win ${d.estrategias.RATA.winrate}% Neto $${d.estrategias.RATA.neto} | LOBO ${d.estrategias.LOBO.ops} ops Win ${d.estrategias.LOBO.winrate}% | TIBURON ${d.estrategias.TIBURON.ops} ops`;
     document.getElementById('cedears').innerHTML=`📊 CEDEARs FUTURO: AAPL $${d.cedears.AAPL} | TSLA $${d.cedears.TSLA} | NVDA $${d.cedears.NVDA} | Dolar $${d.dolar.valor}`;
     document.getElementById('socios').style.display='none';document.getElementById('infoPlan').style.display='block';document.getElementById('infoPlan').innerHTML=`📋 Link privado:?id=${sid}`;
   }catch(e){document.getElementById('admin').innerHTML='Error carga<br><a class="btn" href="/">⬅️ Volver a ADMIN</a>'}
 }else{
   let a=await (await fetch('/api/data')).json();
   document.getElementById('admin').innerHTML=`🔵🦖 CAJA ADMIN MEGALODON 100% - TODAS LAS BESTIAS<br><span class="kpi">💰 Bal: $${a.balance}</span><span class="kpi">📈 Neto: $${a.neto_hoy}</span><span class="kpi">🔄 Ops: ${a.ops_hoy}</span><span class="kpi">🎯 Win: ${a.winrate}%</span><br><span class="kpi">⚙️ Modo: ${a.modo}</span><span class="kpi">📊 Merc: ${a.mercado}</span><br><span class="kpi">₿ BTC: $${a.btc}</span><span class="kpi">🔶 BNB: $${a.bnb}</span><br>Estado: ${a.estado_texto}<br>Disco: ${a.disco} | Dolar: $${a.dolar.valor} ${a.dolar.fuente}`;
   document.getElementById('estrategias').innerHTML=`📈 ESTRATEGIAS FUTURO ADMIN MEGALODON:<br>🦖 MEGALODON: ${a.estrategias.MEGALODON.ops} ops Win ${a.estrategias.MEGALODON.winrate}% Neto $${a.estrategias.MEGALODON.neto}<br>🐀 RATA: ${a.estrategias.RATA.ops} ops Win ${a.estrategias.RATA.winrate}% Neto $${a.estrategias.RATA.neto}<br>🐺 LOBO: ${a.estrategias.LOBO.ops} ops Win ${a.estrategias.LOBO.winrate}% Neto $${a.estrategias.LOBO.neto}<br>🦈 TIBURON: ${a.estrategias.TIBURON.ops} ops Win ${a.estrategias.TIBURON.winrate}% Neto $${a.estrategias.TIBURON.neto}`;
   document.getElementById('cedears').innerHTML=`📊 CEDEARs FUTURO (DEMO): AAPL $${a.cedears.AAPL} | TSLA $${a.cedears.TSLA} | NVDA $${a.cedears.NVDA} | MELI $${a.cedears.MELI} | NASDAQ AAPL chart abajo`;
   let s=await (await fetch('/api/socios')).json();let h='🟠 CAJAS SOCIOS 20% - CONTADOR INVERSO:<br>';
   for(let k in s.socios){let u=s.socios[k];h+=`<div style="margin:8px 0;padding:8px;background:#1e222d;border-radius:8px">Socio ${k} | ${u.plan}<br>💰 $${u.balance} | Neto $${u.neto_hoy} | ${u.ops} ops | Win ${u.winrate}%<br>⏳ Quedan ${u.vence_dias}d | ${u.modo} | ${u.mercado} | ${u.estado}<br><a class="btn" href="/?id=${k}">➡️ Ver?id=${k}</a></div>`;}
   if(Object.keys(s.socios).length==0)h+='Sin socios - /alta';document.getElementById('socios').innerHTML=h;
 }
}
setInterval(r,3000);r();
</script></body></html>"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    admin_data = get_user_data(ADMINS_IDS[0])
    # calcular winrates estrategias
    est_out={}
    for k,v in admin_data["estrategias"].items():
        est_out[k]={"ops":v["ops"],"winrate":calcular_winrate_estrategia(v),"neto":v["neto"],"ganadas":v["ganadas"]}
    return jsonify({
        "balance":admin_data["balance"],
        "neto_hoy":admin_data["neto_hoy"],
        "ops_hoy":admin_data["ops_hoy"],
        "winrate":calcular_winrate(admin_data),
        "modo":admin_data["modo"],
        "mercado":admin_data["mercado"],
        "btc":ESTADO["btc"],
        "bnb":ESTADO["bnb"],
        "estado_texto":get_estado_texto(admin_data),
        "disco":DATA_FILE,
        "estrategias":est_out,
        "cedears":CEDEARS,
        "dolar":DOLAR_CRIPTO
    })

@app.route('/api/socios')
def api_socios():
    out={}
    for cid,d in ESTADO["socios"].items():
        u=USUARIOS.get(cid,{"balance":200,"ops_hoy":0,"prendido":False,"neto_hoy":0,"ganadas":0,"perdidas":0,"modo":"CACHORRO","mercado":""})
        delta = d["vence"] - datetime.now()
        dias = delta.days if delta.total_seconds()>0 else 0
        out[cid]={
            "balance":u["balance"],
            "ops":u["ops_hoy"],
            "estado":get_estado_texto(u),
            "plan":d["plan"],
            "neto_hoy":u["neto_hoy"],
            "winrate":calcular_winrate(u),
            "modo":u["modo"],
            "mercado":u["mercado"],
            "vence_dias":dias
        }
    return jsonify({"socios":out})

@app.route('/api/socio/<int:socio_id>')
def api_socio_individual(socio_id):
    if socio_id not in ESTADO["socios"]:
        return jsonify({"error":"no existe"}),404
    sd=ESTADO["socios"][socio_id]
    u=USUARIOS.get(socio_id) or get_user_data(socio_id)
    delta = sd["vence"] - datetime.now()
    if delta.total_seconds() <= 0:
        dias=0; horas=0; mins=0
    else:
        dias=delta.days
        horas=int(delta.total_seconds()//3600)%24
        mins=int(delta.total_seconds()//60)%60
    est_out={}
    for k,v in u["estrategias"].items():
        est_out[k]={"ops":v["ops"],"winrate":calcular_winrate_estrategia(v),"neto":v["neto"]}
    return jsonify({
        "balance":u["balance"],
        "neto_hoy":u["neto_hoy"],
        "ops_hoy":u["ops_hoy"],
        "winrate":calcular_winrate(u),
        "modo":u["modo"],
        "mercado":u["mercado"],
        "estado_texto":get_estado_texto(u),
        "plan":sd["plan"],
        "vence_dias":dias,
        "vence_horas":horas,
        "vence_mins":mins,
        "vence":sd["vence"].strftime("%d/%m/%Y"),
        "id":socio_id,
        "btc":ESTADO["btc"],
        "bnb":ESTADO["bnb"],
        "estrategias":est_out,
        "cedears":CEDEARS,
        "dolar":DOLAR_CRIPTO
    })

def run_bot():
    bot.infinity_polling(skip_pending=True)

threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()
threading.Thread(target=actualizar_dolar_y_cedears, daemon=True).start()

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
