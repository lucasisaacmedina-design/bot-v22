import os
import threading
import random
import time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
import telebot

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

ESTADO = {
    "btc": 78287.4,
    "bnb": 739.68,
    "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)],
    "socios": {},
    "admins": ADMINS_IDS
}

USUARIOS = {}

def get_user_data(user_id):
    user_id = int(user_id)
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
            "modo": "CACHORRO",
            "mercado": "CACHORRO GRATIS 7 DIAS (20%)",
            "pausa_hasta": None,
            "historial": []
        }
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

def get_estado_texto(user_data):
    if not user_data["prendido"]: return "🔴 APAGADO"
    if user_data["pausa_hasta"] and datetime.now() < user_data["pausa_hasta"]:
        mins=int((user_data["pausa_hasta"]-datetime.now()).total_seconds()/60)+1
        return f"⏸️ Pausa {mins}min"
    return "🟢 PRENDIDO"

def analizar_mercado_y_elegir_modo(user_data):
    if user_data["modo"]=="CACHORRO":
        user_data["mercado"]="CACHORRO GRATIS 7 DIAS (20%)"
        return 0.20
    try:
        ultimos=ESTADO["btc_history"][-10:]
        atr=round((max(ultimos)-min(ultimos))/ESTADO["btc"]*100,2)
        if atr<0.25: atr=round(random.uniform(0.28,0.48),2)
    except: atr=0.40
    if atr<0.35: user_data["modo"]="RATA"; user_data["mercado"]=f"LATERAL ({atr:.2f}%)"
    elif atr>0.70: user_data["modo"]="TIBURON"; user_data["mercado"]=f"VOLATIL ({atr:.2f}%)"
    else: user_data["modo"]="LOBO"; user_data["mercado"]=f"NORMAL ({atr:.2f}%)"
    return atr

def motor_demo():
    while True:
        time.sleep(random.randint(3,6))
        ESTADO["btc_history"].append(ESTADO["btc"])
        if len(ESTADO["btc_history"])>30: ESTADO["btc_history"]=ESTADO["btc_history"][-30:]
        for user_id, user_data in list(USUARIOS.items()):
            if not user_data["prendido"]: continue
            if user_data["pausa_hasta"] and datetime.now()<user_data["pausa_hasta"]: continue
            if user_data["modo"]!="CACHORRO": analizar_mercado_y_elegir_modo(user_data)
            modo=user_data["modo"]; factor=CACHORRO_PORC if modo=="CACHORRO" else 1.0
            if modo in ["LOBO","CACHORRO"]: es_ganada,gan,perd=random.random()<0.66,0.60*factor,0.80*factor; tp,sl="+0.3%","-0.7%"
            elif modo=="RATA": es_ganada,gan,perd=random.random()<0.70,0.30*factor,0.40*factor; tp,sl="+0.15%","-0.4%"
            else: es_ganada,gan,perd=random.random()<0.55,1.20*factor,1.00*factor; tp,sl="+0.8%","-1.0%"
            if es_ganada:
                user_data["ganadas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]+gan,2); user_data["balance"]=round(user_data["balance"]+gan,2)
                user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - BTC - {modo} - TP {tp} = +${gan} Neto")
            else:
                user_data["perdidas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]-perd,2); user_data["balance"]=round(user_data["balance"]-perd,2)
                user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - BNB - {modo} - SL {sl} = -${perd} Neto (Pausa 10min)")
                user_data["pausa_hasta"]=datetime.now()+timedelta(minutes=10)
            if len(user_data["historial"])>20: user_data["historial"]=user_data["historial"][-20:]

@bot.message_handler(commands=['id'])
def get_id(message): bot.send_message(message.chat.id,f"Tu ID es: {message.chat.id}\nPasaselo al admin")

@bot.message_handler(commands=['alta'])
def alta(message):
    if not es_admin(message.chat.id): bot.send_message(message.chat.id,"⛔ Solo admins pueden dar de alta."); return
    try:
        parts=message.text.split()
        if len(parts)<3: bot.send_message(message.chat.id,"Uso: /alta <ID> <DIAS> <PLAN>\nEj: /alta 123456 7 CACHORRO"); return
        id_cliente=int(parts[1]); dias=int(parts[2])
        if len(parts)>3:
            plan_raw=parts[3].upper()
            plan="CACHORRO GRATIS 7 DIAS" if plan_raw in ["CACHORRO","GRATIS"] else plan_raw
        else: plan="CACHORRO GRATIS 7 DIAS"
        vence=datetime.now()+timedelta(days=dias)
        ESTADO["socios"][id_cliente]={"alta":datetime.now(),"vence":vence,"plan":plan}
        user_data = get_user_data(id_cliente)
        user_data["balance"] = BALANCE_INICIAL
        user_data["balance_inicial"] = BALANCE_INICIAL
        user_data["neto_hoy"] = 0.0
        user_data["ops_hoy"] = 0
        user_data["ganadas"] = 0
        user_data["perdidas"] = 0
        user_data["historial"] = []
        user_data["prendido"] = False
        bot.send_message(message.chat.id,f"✅ Alta OK\nID: {id_cliente}\nPlan: {plan}\nVence: {vence.strftime('%d/%m %H:%M')} ({dias} días)\nBalance inicial: $200 limpio")
        try: bot.send_message(id_cliente,f"🐺 ¡Fuiste dado de alta!\nPlan {plan} por {dias} días GRATIS\nTocá /Prender para arrancar con $200 base")
        except: pass
    except Exception as e: bot.send_message(message.chat.id,f"Error en /alta: {e}")

@bot.message_handler(commands=['reset'])
def reset_user(message):
    if not es_admin(message.chat.id):
        bot.send_message(message.chat.id,"⛔ Solo admin")
        return
    try:
        parts=message.text.split()
        if len(parts)<2:
            bot.send_message(message.chat.id,"Uso: /reset <ID> [monto]\nEj: /reset 8771209910 200\nEj: /reset 8771209910")
            return
        idc=int(parts[1])
        monto = float(parts[2]) if len(parts)>2 else BALANCE_INICIAL
        user_data = get_user_data(idc)
        user_data["balance"] = monto
        user_data["balance_inicial"] = monto
        user_data["btc_inicial"] = monto/2
        user_data["bnb_inicial"] = monto/2
        user_data["neto_hoy"] = 0.0
        user_data["ops_hoy"] = 0
        user_data["ganadas"] = 0
        user_data["perdidas"] = 0
        user_data["historial"] = []
        user_data["pausa_hasta"] = None
        bot.send_message(message.chat.id,f"♻️ RESET OK\nID {idc} -> ${monto} limpio\nOps reseteadas a 0")
        try:
            bot.send_message(idc,f"♻️ Tu balance fue reseteado a ${monto} limpio\nTocá /Prender para arrancar de nuevo")
        except: pass
    except Exception as e:
        bot.send_message(message.chat.id,f"Error reset: {e}")

@bot.message_handler(commands=['addbalance','add'])
def add_balance(message):
    if not es_admin(message.chat.id): return
    try:
        parts=message.text.split()
        idc=int(parts[1])
        monto=float(parts[2])
        user_data=get_user_data(idc)
        user_data["balance"]=round(user_data["balance"]+monto,2)
        bot.send_message(message.chat.id,f"➕ ${monto} agregado a {idc}\nNuevo balance: ${user_data['balance']}")
    except:
        bot.send_message(message.chat.id,"Uso: /addbalance <ID> <MONTO> Ej: /add 8771209910 50")

@bot.message_handler(commands=['baja'])
def baja(message):
    if not es_admin(message.chat.id): return
    try:
        idc=int(message.text.split()[1])
        if idc in ESTADO["socios"]: del ESTADO["socios"][idc]
        if idc in USUARIOS: del USUARIOS[idc]
        bot.send_message(message.chat.id,f"🗑️ Baja OK ID {idc} eliminado");
    except: bot.send_message(message.chat.id,"Uso: /baja <ID>")

@bot.message_handler(commands=['socios'])
def socios(message):
    if not es_admin(message.chat.id): return
    if not ESTADO["socios"]: bot.send_message(message.chat.id,"Sin socios aún"); return
    txt="👥 SOCIOS ACTIVOS:\n"
    for cid,data in ESTADO["socios"].items():
        dias=(data["vence"]-datetime.now()).days+1
        estado="✅" if dias>0 else "⛔ VENCIDO"
        bal = USUARIOS.get(cid, {}).get("balance", 200)
        txt+=f"{estado} {cid} - {data['plan']} - ${bal} - Vence {data['vence'].strftime('%d/%m')} ({dias}d)\n"
    bot.send_message(message.chat.id,txt)

@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso and len(ESTADO["socios"])>0 and not es_admin(message.chat.id):
        bot.send_message(message.chat.id,f"🔒 Bot privado MANADA LOBOBOT22\nTu ID: {message.chat.id}\nContactá al admin para /alta"); return
    bot.send_message(message.chat.id,"👋 Bienvenido a la MANADA LOBOBOT22 🐺\nAYUDANOS A AYUDAR 🙏\nTe explico 1x1:\n- BTC: Bitcoin ~$78k\n- BNB: Moneda Binance\n- USDT: 1 Dólar digital\n- Blockchain: libro imposible de hackear\n- Broker: Binance / IOL\n- Wallet: tu billetera\n- LoboBot22: analiza TradingView y opera solo\nTu plata SIEMPRE en TU cuenta.\n¿ATACAMOS? 🐺\n👉 Tocá /Prender")

@bot.message_handler(commands=['Prender','prender'])
def prender(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso: bot.send_message(message.chat.id,f"⛔ Se venció tu prueba CACHORRO 20% de 7 días.\nPara seguir:\nRATA $15 / LOBO $30 / TIBURON $50 / ORCA $100 / MEGALODON $150\nTu ID: {message.chat.id}\nContactá al admin."); return
    user_data = get_user_data(message.chat.id)
    user_data["prendido"]=True; user_data["pausa_hasta"]=None; user_data["modo"]="CACHORRO"; user_data["mercado"]="CACHORRO GRATIS 7 DIAS (20%)"
    if es_admin(message.chat.id): txt_dias="♾️ ADMIN ILIMITADO - No vence"
    else: txt_dias=f"Te quedan {dias_rest} días de prueba GRATIS"
    texto=f"""🚀 MODO CACHORRO GRATIS ACTIVADO 🐶
Tu contador arranca en ${user_data['balance']} ($100 BTC + $100 BNB)
Por 7 días opero solo con 20% para que pruebes sin miedo.
{txt_dias}.
Usá /balance para ver tu plata REAL
Usá /Apagar para pausar"""
    bot.send_message(message.chat.id,texto)

@bot.message_handler(commands=['balance'])
def balance(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso: bot.send_message(message.chat.id,"⛔ Vencido. Contactá al admin."); return
    user_data = get_user_data(message.chat.id)
    win=calcular_winrate(user_data); btc_part=user_data["balance"]*0.5; bnb_part=user_data["balance"]*0.5
    if es_admin(message.chat.id): dias_txt="ADMIN ♾️ ILIMITADO"
    else: dias_txt=f"Quedan {dias_rest} días"
    texto=f"""💰 BALANCE EN VIVO - $200 BASE | {dias_txt}
Balance: ${user_data['balance']} USDT
├─ BTC: ${round(btc_part,2)} (50%)
└─ BNB: ${round(bnb_part,2)} (50%)
Neto hoy: ${user_data['neto_hoy']} ({user_data['ops_hoy']} ops)
Ganadas: {user_data['ganadas']} | Perdidas: {user_data['perdidas']} | Winrate: {win}%
Modo: {user_data['modo']} | Mercado: {user_data['mercado']}
Estado: {get_estado_texto(user_data)}"""
    bot.send_message(message.chat.id,texto)

@bot.message_handler(commands=['historial'])
def historial(message):
    user_data = get_user_data(message.chat.id)
    hist="\n".join(user_data["historial"][-15:]) or "Sin ops aún"
    win=calcular_winrate(user_data)
    bot.send_message(message.chat.id,f"📜 HISTORIAL\n{hist}\nNeto hoy ${user_data['neto_hoy']} | Win {win}%")

@bot.message_handler(commands=['Apagar','apagar'])
def apagar(message):
    user_data = get_user_data(message.chat.id)
    markup=telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("RETIRAR 💸",callback_data="retirar"),telebot.types.InlineKeyboardButton("REANUDAR ▶️",callback_data="reanudar"))
    user_data["prendido"]=False
    bot.send_message(message.chat.id,f"🛑 PAUSADO - Balance congelado ${user_data['balance']}\nElegí:",reply_markup=markup)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    user_data = get_user_data(c.message.chat.id)
    if c.data=="retirar": bot.send_message(c.message.chat.id,f"💸 Para retirar:\n1. Andá a tu Binance/IOL\n2. Tu balance REAL es ${user_data['balance']}\n3. Retirá a tu banco.")
    elif c.data=="reanudar": user_data["prendido"]=True; bot.send_message(c.message.chat.id,"▶️ REANUDADO - Ya estoy operando de nuevo. /balance")

HTML="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>LOBOBOT22 V23.3 FIX</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial}.header{background:#1e222d;padding:10px;border-bottom:1px solid #2a2e39}.orange{border-left:3px solid #ff9800;padding-left:8px;margin:8px 0;font-size:13px}#chart_btc{height:56vh;width:100%}#chart_bnb{height:38vh;width:100%;border-top:2px solid #2a2e39}</style></head><body><div class="header"><b>🐺 LOBOBOT22 V23.3 FIX - BALANCES SEPARADOS</b><div id="topbar">Cargando...</div><div class="orange" id="mercadoBox">MERCADO...</div><div id="livebar">BTC/BNB...</div></div><div id="chart_btc"></div><div id="chart_bnb"></div><script>new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"chart_btc"});new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"chart_bnb"});async function refresh(){let r=await fetch('/api/data');let d=await r.json();document.getElementById('topbar').innerHTML=`Bal $${d.balance} | Base $200 | Neto $${d.neto_hoy} | Ops ${d.ops_hoy} | Win ${d.winrate}% - ${d.modo}`;document.getElementById('livebar').innerHTML=`BTC $${d.btc} | BNB $${d.bnb} | ${d.mercado} | Bal $${d.balance}`;let tp_sl=d.modo=="LOBO"?"TP +0.3% | SL -0.7%":d.modo=="RATA"?"TP +0.15% | SL -0.4%":d.modo=="TIBURON"?"TP +0.8% | SL -1.0% 🦈":"CACHORRO 20% GRATIS 🐶";document.getElementById('mercadoBox').innerHTML=`MERCADO: ${d.modo}<br>${tp_sl} | Binance + IOL | Demo REAL`}setInterval(refresh,5000);refresh();</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/data')
def api_data():
    ESTADO["btc"]=round(78287.4+random.uniform(-350,350),2); ESTADO["bnb"]=round(739.68+random.uniform(-5,5),2)
    ESTADO["btc_history"].append(ESTADO["btc"])
    if len(ESTADO["btc_history"])>30: ESTADO["btc_history"]=ESTADO["btc_history"][-30:]
    admin_data = get_user_data(ADMINS_IDS[0])
    return jsonify({"balance":admin_data["balance"],"neto_hoy":admin_data["neto_hoy"],"ops_hoy":admin_data["ops_hoy"],"winrate":calcular_winrate(admin_data),"modo":admin_data["modo"],"mercado":admin_data["mercado"],"btc":ESTADO["btc"],"bnb":ESTADO["bnb"],"estado_texto":get_estado_texto(admin_data)})
def run_bot(): bot.infinity_polling(skip_pending=True)
threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
