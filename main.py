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

# === CONFIG V22.8 BASE SOLIDA ===
# RATA, LOBO, TIBURON operan BTC + BNB
# ORCA desbloquea en $500 - MEGALODON en $1000
ALIAS_MP_DEMO = "manada.lobo.demo.mp"
DOLAR_CRIPTO = {"valor": 1480, "actualizado": "inicio", "fuente": "DEMO"}
CEDEARS = {"AAPL": 1200.5, "TSLA": 890.3, "NVDA": 1450.8, "MELI": 2500.0, "MSFT": 1100.0, "GOOGL": 980.5}
IOL_TOKEN = {"estado": "BLOQUEADO hasta $1000"}

print(f"### V22.8 BASE SOLIDA RATA/LOBO/TIBURON BTC+BNB + CACHORRO 20% ###")

ESTADO = {
    "btc": 78287.4,
    "bnb": 739.68,
    "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)],
    "socios": {},
    "admins": ADMINS_IDS,
    "cedears_history": {}
}
USUARIOS = {}
LOCK = threading.Lock()

def actualizar_dolar():
    while True:
        try:
            r = requests.get("https://criptoya.com/api/dolar", timeout=10).json()
            if r and 'cripto' in r and 'ccb' in r['cripto']:
                DOLAR_CRIPTO["valor"] = int(float(r['cripto']['ccb']))
                DOLAR_CRIPTO["actualizado"] = datetime.now().strftime("%H:%M")
                DOLAR_CRIPTO["fuente"] = "criptoya"
        except:
            DOLAR_CRIPTO["valor"] += random.randint(-5,5)
        time.sleep(1800)

BIENVENIDA = """
Hola Lobo V22.8 BASE SOLIDA

🐀 RATA 0.2% BTC/BNB LATERAL
🐺 LOBO 0.5% BTC/BNB NORMAL
🦈 TIBURON 1.2% BTC/BNB VOLATIL

🐋 ORCA FUTURO BLOQ hasta $500
🦖 MEGALODON CEDEARs BLOQ hasta $1000

CACHORRO 20% LLAMADOR 7 DIAS
"""

def get_menu_botones(admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if admin:
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("👥 SOCIOS"), types.KeyboardButton("📈 ESTRATEGIAS"))
        markup.add(types.KeyboardButton("💰 PAGAR"), types.KeyboardButton("🐺 QUIERO LOBO"))
    else:
        markup.add(types.KeyboardButton("💰 PAGAR"), types.KeyboardButton("🐺 QUIERO LOBO"))
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("📈 ESTRATEGIAS"), types.KeyboardButton("📜 HISTORIAL"))
        markup.add(types.KeyboardButton("🆔 ID"))
    return markup

def guardar_datos():
    try:
        with LOCK:
            socios_ser = {}
            for k,v in ESTADO["socios"].items():
                socios_ser[str(k)] = {"alta": v["alta"].isoformat(), "vence": v["vence"].isoformat(), "plan": v["plan"]}
            usuarios_ser = {}
            for k,v in USUARIOS.items():
                vd = v.copy()
                if vd.get("pausa_hasta") and isinstance(vd["pausa_hasta"], datetime):
                    vd["pausa_hasta"] = vd["pausa_hasta"].isoformat()
                usuarios_ser[str(k)] = vd
            data = {"socios": socios_ser, "usuarios": usuarios_ser, "guardado": datetime.now().isoformat()}
            with open(DATA_FILE+".tmp", "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(DATA_FILE+".tmp", DATA_FILE)
    except Exception as e:
        print(f"Error guardando: {e}")

def cargar_datos():
    try:
        if not os.path.exists(DATA_FILE): return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k,v in data.get("socios", {}).items():
            try:
                ESTADO["socios"][int(k)] = {"alta": datetime.fromisoformat(v["alta"]), "vence": datetime.fromisoformat(v["vence"]), "plan": v["plan"]}
            except: pass
        for k,v in data.get("usuarios", {}).items():
            try:
                if v.get("pausa_hasta"):
                    try: v["pausa_hasta"] = datetime.fromisoformat(v["pausa_hasta"])
                    except: v["pausa_hasta"] = None
                # FIX viejo
                if "MEGALODON" in v.get("estrategias",{}):
                    del v["estrategias"]["MEGALODON"]
                if "ORCA" in v.get("estrategias",{}):
                    del v["estrategias"]["ORCA"]
                if "estrategias" not in v:
                    v["estrategias"] = {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}
                USUARIOS[int(k)] = v
            except: pass
    except Exception as e:
        print(f"Error cargando: {e}")

cargar_datos()

def get_user_data(user_id):
    user_id = int(user_id)
    es_admin_id = user_id in ADMINS_IDS
    if user_id not in USUARIOS:
        USUARIOS[user_id] = {
            "prendido": False, "balance": BALANCE_INICIAL, "balance_inicial": BALANCE_INICIAL,
            "btc_inicial": 100.0, "bnb_inicial": 100.0, "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0,
            "modo": "LOBO" if es_admin_id else "CACHORRO",
            "mercado": "BASE SOLIDA BTC+BNB" if es_admin_id else "CACHORRO GRATIS 7 DIAS (20%)",
            "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA" if es_admin_id else "SOCIO",
            "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}
        }
        guardar_datos()
    if es_admin_id:
        USUARIOS[user_id]["caja"] = "ADMIN BASE SOLIDA"
    # Asegurar solo 3 estrategias
    if "estrategias" not in USUARIOS[user_id]:
        USUARIOS[user_id]["estrategias"] = {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}
    USUARIOS[user_id]["estrategias"].pop("ORCA", None)
    USUARIOS[user_id]["estrategias"].pop("MEGALODON", None)
    for k in ["RATA","LOBO","TIBURON"]:
        if k not in USUARIOS[user_id]["estrategias"]:
            USUARIOS[user_id]["estrategias"][k] = {"ops":0,"ganadas":0,"neto":0.0}
    return USUARIOS[user_id]

def es_admin(chat_id):
    try: return int(chat_id) in ESTADO["admins"]
    except: return False

def tiene_acceso(chat_id):
    chat_id=int(chat_id)
    if es_admin(chat_id): return True, 999
    socio=ESTADO["socios"].get(chat_id)
    if not socio: return False, 0
    if datetime.now() > socio["vence"]: return False, 0
    dias=(socio["vence"]-datetime.now()).days+1
    return True, dias

def calcular_winrate(user_data):
    total=user_data["ganadas"]+user_data["perdidas"]
    return round((user_data["ganadas"]/total)*100) if total else 0

def calcular_winrate_estrategia(est):
    if est["ops"] == 0: return 0
    return round((est["ganadas"]/est["ops"])*100)

def get_estado_texto(user_data):
    if not user_data["prendido"]: return "🔴 APAGADO"
    if user_data["pausa_hasta"] and isinstance(user_data["pausa_hasta"], datetime) and datetime.now() < user_data["pausa_hasta"]:
        mins=int((user_data["pausa_hasta"]-datetime.now()).total_seconds()/60)+1
        return f"⏸️ Pausa {mins}min (solo esta caja)"
    return "🟢 PRENDIDO"

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
            if not user_data["prendido"]: continue
            es_admin_id = int(user_id) in ADMINS_IDS
            if not es_admin_id:
                if user_data["pausa_hasta"] and isinstance(user_data["pausa_hasta"], datetime) and datetime.now()<user_data["pausa_hasta"]:
                    continue
            # === BASE SOLIDA: SOLO 3 ESTRATEGIAS x 2 MONEDAS ===
            if es_admin_id:
                # Pesos: RATA 30, LOBO 40, TIBURON 30
                modo_elegido = random.choices(["RATA","LOBO","TIBURON"], weights=[30,40,30], k=1)[0]
                # Cada modo puede ser BTC o BNB
                activo_base = random.choice(["BTC","BNB"])
                if modo_elegido == "RATA":
                    es_ganada,gan,perd=random.random()<0.72,0.80,0.50
                    tp,sl=f"+0.2% {activo_base}",f"-0.4% {activo_base}"
                elif modo_elegido == "LOBO":
                    es_ganada,gan,perd=random.random()<0.68,1.80,1.00
                    tp,sl=f"+0.5% {activo_base}",f"-0.8% {activo_base}"
                else: # TIBURON
                    es_ganada,gan,perd=random.random()<0.60,3.20,1.50
                    tp,sl=f"+1.2% {activo_base}",f"-1.0% {activo_base}"
                user_data["estrategias"][modo_elegido]["ops"]+=1
                if es_ganada:
                    user_data["estrategias"][modo_elegido]["ganadas"]+=1
                    user_data["estrategias"][modo_elegido]["neto"]=round(user_data["estrategias"][modo_elegido]["neto"]+gan,2)
                else:
                    user_data["estrategias"][modo_elegido]["neto"]=round(user_data["estrategias"][modo_elegido]["neto"]-perd,2)
            else:
                # CACHORRO 20% LLAMADOR
                modo = user_data["modo"]
                factor = CACHORRO_PORC
                activo_base = random.choice(["BTC","BNB"])
                if modo in ["LOBO","CACHORRO"]:
                    es_ganada,gan,perd=random.random()<0.66,0.60*factor,0.80*factor
                    tp,sl=f"+0.3% {activo_base}",f"-0.7% {activo_base}"
                    modo_log = "CACHORRO"
                elif modo=="RATA":
                    es_ganada,gan,perd=random.random()<0.70,0.30*factor,0.40*factor
                    tp,sl=f"+0.15% {activo_base}",f"-0.4% {activo_base}"
                    modo_log = "RATA"
                else:
                    es_ganada,gan,perd=random.random()<0.55,1.20*factor,1.00*factor
                    tp,sl=f"+0.8% {activo_base}",f"-1.0% {activo_base}"
                    modo_log = "TIBURON"
                if modo_log not in user_data["estrategias"]:
                    user_data["estrategias"][modo_log]={"ops":0,"ganadas":0,"neto":0.0}
                user_data["estrategias"][modo_log]["ops"]+=1
                if es_ganada:
                    user_data["estrategias"][modo_log]["ganadas"]+=1
                    user_data["estrategias"][modo_log]["neto"]=round(user_data["estrategias"][modo_log]["neto"]+gan,2)
                else:
                    user_data["estrategias"][modo_log]["neto"]=round(user_data["estrategias"][modo_log]["neto"]-perd,2)
            modo_log = modo_elegido if es_admin_id else user_data["modo"]
            activo = activo_base
            if es_ganada:
                user_data["ganadas"]+=1
                user_data["ops_hoy"]+=1
                user_data["neto_hoy"]=round(user_data["neto_hoy"]+gan,2)
                user_data["balance"]=round(user_data["balance"]+gan,2)
                user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - {activo} - {modo_log} - TP {tp} = +${gan}")
            else:
                user_data["perdidas"]+=1
                user_data["ops_hoy"]+=1
                user_data["neto_hoy"]=round(user_data["neto_hoy"]-perd,2)
                user_data["balance"]=round(user_data["balance"]-perd,2)
                user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - {activo} - {modo_log} - SL {sl} = -${perd} (Pausa 10min)")
                if not es_admin_id:
                    user_data["pausa_hasta"]=datetime.now()+timedelta(minutes=10)
            if len(user_data["historial"])>20:
                user_data["historial"]=user_data["historial"][-20:]
        contador+=1
        if contador>=10:
            guardar_datos()
            contador=0

# --- HANDLERS SIMPLIFICADOS ---
@bot.message_handler(commands=['id'])
def get_id(message):
    bot.send_message(message.chat.id,f"Tu ID es: {message.chat.id}\nLink: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📈 ESTRATEGIAS", "/estrategias"])
def estrategias(message):
    ud=get_user_data(message.chat.id)
    est=ud["estrategias"]
    bal = ud["balance"]
    txt=f"📈 V22.8 BASE SOLIDA BTC+BNB - {ud['caja']}\n\n"
    txt+=f"🐀 RATA: {est['RATA']['ops']} ops - Win {calcular_winrate_estrategia(est['RATA'])}% - Neto ${est['RATA']['neto']}\n"
    txt+=f"🐺 LOBO: {est['LOBO']['ops']} ops - Win {calcular_winrate_estrategia(est['LOBO'])}% - Neto ${est['LOBO']['neto']}\n"
    txt+=f"🦈 TIBURON: {est['TIBURON']['ops']} ops - Win {calcular_winrate_estrategia(est['TIBURON'])}% - Neto ${est['TIBURON']['neto']}\n\n"
    if bal < 500:
        txt+=f"🔒 ORCA FUTURO 2% BLOQUEADO (desbloquea en $500, vas ${bal})\n"
    else:
        txt+=f"🔓 ORCA FUTURO 2% DESBLOQUEADO!\n"
    if bal < 1000:
        txt+=f"🔒 MEGALODON CEDEARs BLOQUEADO (desbloquea en $1000, vas ${bal})\n\n"
    else:
        txt+=f"🔓 MEGALODON CEDEARs DESBLOQUEADO!\n\n"
    txt+=f"BTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}\nDolar: ${DOLAR_CRIPTO['valor']}"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    ud=get_user_data(message.chat.id)
    if es_admin(message.chat.id):
        bot.send_message(message.chat.id,f"👋 V22.8 ADMIN BASE SOLIDA 🐺\nBalance ${ud['balance']} - {ud['modo']}\n3 Estrategias BTC+BNB\nORCA se desbloquea $500\nMEGALODON $1000\nTu web: {WEB_URL}", reply_markup=get_menu_botones(True))
    else:
        if not acceso:
            bot.send_message(message.chat.id, BIENVENIDA + f"\n\nTu ID: {message.chat.id}", reply_markup=get_menu_botones(False))
        else:
            bot.send_message(message.chat.id,f"👋 MANADA V22.8\nPlan: {ESTADO['socios'][message.chat.id]['plan']} - {dias_rest} dias\nWeb: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(False))

@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/prender"])
def prender(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso:
        bot.send_message(message.chat.id,"⛔ Vencido - toca 💰 PAGAR", reply_markup=get_menu_botones(False))
        return
    user_data = get_user_data(message.chat.id)
    user_data["prendido"]=True
    user_data["pausa_hasta"]=None
    if es_admin(message.chat.id):
        user_data["modo"]="LOBO"
        user_data["mercado"]="BASE SOLIDA BTC+BNB"
    else:
        user_data["modo"]="CACHORRO"
        user_data["mercado"]="CACHORRO GRATIS 7 DIAS (20%)"
    guardar_datos()
    bot.send_message(message.chat.id,f"🚀 {user_data['caja']} ACTIVADA - ${user_data['balance']}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance"])
def balance(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso: return
    ud = get_user_data(message.chat.id)
    win=calcular_winrate(ud)
    bot.send_message(message.chat.id,f"💰 {ud['caja']}\nBal: ${ud['balance']}\nNeto: ${ud['neto_hoy']} ({ud['ops_hoy']} ops) Win {win}%\nModo: {ud['modo']}\nEstado: {get_estado_texto(ud)}\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL", "/historial"])
def historial(message):
    ud = get_user_data(message.chat.id)
    hist="\n".join(ud["historial"][-15:]) or "Sin ops"
    bot.send_message(message.chat.id,f"📜 {ud['caja']}\n{hist}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(func=lambda m: m.text in ["💰 PAGAR", "/pagar"])
def pagar(message):
    bot.send_message(message.chat.id,f"PAGAR V22.8 BASE SOLIDA - Dolar ${DOLAR_CRIPTO['valor']}\nAlias: {ALIAS_MP_DEMO}", reply_markup=get_menu_botones(es_admin(message.chat.id)))

@bot.message_handler(commands=['alta','reset','socios','debug'])
def admin_cmds(message):
    if not es_admin(message.chat.id): return
    if message.text.startswith('/alta'):
        try:
            parts=message.text.split()
            id_cliente=int(parts[1]); dias=int(parts[2]); plan=parts[3].upper() if len(parts)>3 else "CACHORRO"
            vence=datetime.now()+timedelta(days=dias)
            ESTADO["socios"][id_cliente]={"alta":datetime.now(),"vence":vence,"plan":plan}
            ud = get_user_data(id_cliente)
            ud["balance"]=BALANCE_INICIAL; ud["neto_hoy"]=0; ud["ops_hoy"]=0; ud["ganadas"]=0; ud["perdidas"]=0; ud["historial"]=[]; ud["prendido"]=False
            ud["estrategias"]={"RATA":{"ops":0,"ganadas":0,"neto":0.0},"LOBO":{"ops":0,"ganadas":0,"neto":0.0},"TIBURON":{"ops":0,"ganadas":0,"neto":0.0}}
            guardar_datos()
            bot.send_message(message.chat.id,f"✅ Alta {id_cliente} {plan} {dias}d")
        except Exception as e:
            bot.send_message(message.chat.id,f"Error: {e}")
    elif message.text.startswith('/socios'):
        txt=f"👥 SOCIOS - Dolar ${DOLAR_CRIPTO['valor']}\n"
        for cid,d in ESTADO["socios"].items():
            txt+=f"{cid} {d['plan']} - {WEB_URL}/?id={cid}\n"
        bot.send_message(message.chat.id, txt)

HTML="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>V22.8 BASE SOLIDA</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial}.header{background:#1e222d;padding:10px}.box{padding:12px;margin:6px;border-radius:10px;font-size:13px}.admin{background:#0d2a4a;border-left:5px solid #00ffea}.kpi{display:inline-block;background:#1e222d;padding:6px 9px;border-radius:6px;margin:3px;font-size:12px;border:1px solid #2a2e39}#chart_btc{height:40vh}#chart_bnb{height:22vh}</style></head><body><div class="header"><b id="titulo">V22.8 BASE SOLIDA</b><div id="admin" class="box admin">Cargando...</div><div id="est" class="box admin"></div></div><div id="chart_btc"></div><div id="chart_bnb"></div>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"chart_btc"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","container_id":"chart_bnb"});
async function r(){
 let a=await (await fetch('/api/data')).json();
 document.getElementById('admin').innerHTML=`ADMIN BASE SOLIDA $${a.balance} Neto $${a.neto_hoy} ${a.ops_hoy} ops Win ${a.winrate}%<br>BTC $${a.btc} BNB $${a.bnb} | ${a.estado_texto}`;
 document.getElementById('est').innerHTML=`RATA ${a.estrategias.RATA.ops} ops Win ${a.estrategias.RATA.winrate}% | LOBO ${a.estrategias.LOBO.ops} | TIBURON ${a.estrategias.TIBURON.ops}<br>${a.balance < 500? '🔒 ORCA BLOQ hasta $500' : '🔓 ORCA DESBLOQ'} | ${a.balance < 1000? '🔒 MEGALODON BLOQ hasta $1000' : '🔓 MEGALODON DESBLOQ'}`;
}
setInterval(r,3000);r();
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    admin_data = get_user_data(ADMINS_IDS[0])
    est_out={}
    for k,v in admin_data["estrategias"].items():
        est_out[k]={"ops":v["ops"],"winrate":calcular_winrate_estrategia(v),"neto":v["neto"]}
    return jsonify({"balance":admin_data["balance"],"neto_hoy":admin_data["neto_hoy"],"ops_hoy":admin_data["ops_hoy"],"winrate":calcular_winrate(admin_data),"modo":admin_data["modo"],"mercado":admin_data["mercado"],"btc":ESTADO["btc"],"bnb":ESTADO["bnb"],"estado_texto":get_estado_texto(admin_data),"estrategias":est_out,"dolar":DOLAR_CRIPTO})

def run_bot(): bot.infinity_polling(skip_pending=True)
threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()
threading.Thread(target=actualizar_dolar, daemon=True).start()

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
    
