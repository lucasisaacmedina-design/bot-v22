import os
import json
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
WEB_URL = "https://bot-v22-1.onrender.com"

DATA_FILE = "/data/manada.json"
os.makedirs("/data", exist_ok=True)
print(f"### V25.4 FULL RESTAURADO 374 + RETORNO - DISCO: {DATA_FILE} ###")

ESTADO = {
    "btc": 78287.4,
    "bnb": 739.68,
    "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)],
    "socios": {},
    "admins": ADMINS_IDS
}
USUARIOS = {}
LOCK = threading.Lock()

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
                "guardado": datetime.now().isoformat()
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
                USUARIOS[int(k)] = v
            except:
                pass
    except Exception as e:
        print(f"Error cargando: {e}")

cargar_datos()

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
            "historial": [],
            "caja": "ADMIN" if user_id in ADMINS_IDS else "SOCIO"
        }
        guardar_datos()
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

def get_estado_texto(user_data):
    if not user_data["prendido"]:
        return "🔴 APAGADO"
    if user_data["pausa_hasta"] and isinstance(user_data["pausa_hasta"], datetime) and datetime.now() < user_data["pausa_hasta"]:
        mins=int((user_data["pausa_hasta"]-datetime.now()).total_seconds()/60)+1
        return f"⏸️ Pausa {mins}min (solo esta caja)"
    return "🟢 PRENDIDO"

def analizar_mercado_y_elegir_modo(user_data):
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
        ESTADO["btc_history"].append(ESTADO["btc"])
        if len(ESTADO["btc_history"])>30:
            ESTADO["btc_history"]=ESTADO["btc_history"][-30:]
        for user_id, user_data in list(USUARIOS.items()):
            if not user_data["prendido"]:
                continue
            if user_data["pausa_hasta"] and isinstance(user_data["pausa_hasta"], datetime) and datetime.now()<user_data["pausa_hasta"]:
                continue
            if user_data["modo"]!="CACHORRO":
                analizar_mercado_y_elegir_modo(user_data)
            modo=user_data["modo"]
            factor=1.0 if int(user_id) in ADMINS_IDS else CACHORRO_PORC
            if modo in ["LOBO","CACHORRO"]:
                es_ganada,gan,perd=random.random()<0.66,0.60*factor,0.80*factor
                tp,sl="+0.3%","-0.7%"
            elif modo=="RATA":
                es_ganada,gan,perd=random.random()<0.70,0.30*factor,0.40*factor
                tp,sl="+0.15%","-0.4%"
            else:
                es_ganada,gan,perd=random.random()<0.55,1.20*factor,1.00*factor
                tp,sl="+0.8%","-1.0%"
            if es_ganada:
                user_data["ganadas"]+=1
                user_data["ops_hoy"]+=1
                user_data["neto_hoy"]=round(user_data["neto_hoy"]+gan,2)
                user_data["balance"]=round(user_data["balance"]+gan,2)
                user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - BTC - {modo} - TP {tp} = +${gan} Neto")
            else:
                user_data["perdidas"]+=1
                user_data["ops_hoy"]+=1
                user_data["neto_hoy"]=round(user_data["neto_hoy"]-perd,2)
                user_data["balance"]=round(user_data["balance"]-perd,2)
                user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - BNB - {modo} - SL {sl} = -${perd} Neto (Pausa 10min)")
                user_data["pausa_hasta"]=datetime.now()+timedelta(minutes=10)
            if len(user_data["historial"])>20:
                user_data["historial"]=user_data["historial"][-20:]
        contador+=1
        if contador>=10:
            guardar_datos()
            contador=0

@bot.message_handler(commands=['id'])
def get_id(message):
    bot.send_message(message.chat.id,f"Tu ID es: {message.chat.id}")

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
        user_data["caja"]=f"SOCIO {plan}"
        guardar_datos()
        bot.send_message(message.chat.id,f"✅ Alta OK\n🟠 CAJA SOCIO: {id_cliente}\nPlan: {plan}\nVence: {vence.strftime('%d/%m')} ({dias}d)\nLink del socio: {WEB_URL}/?id={id_cliente}\n💾 {DATA_FILE}")
        try:
            bot.send_message(id_cliente,f"""🐺 ¡Fuiste dado de alta!
Plan: {plan} por {dias} días
Tu balance arranca $200 SEPARADO (solo tuyo)

👉 TU WEB PRIVADA (solo tu caja):
{WEB_URL}/?id={id_cliente}

Guardá ese link, ahí ves tu plata en vivo separada del admin.
Tocá /Prender para arrancar
/balance para ver tu caja""")
        except Exception as e:
            bot.send_message(message.chat.id,f"⚠️ No le pude mandar mensaje al socio {id_cliente}, seguro no habló con el bot aún. Pasale vos el link: {WEB_URL}/?id={id_cliente}")
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
        guardar_datos()
        bot.send_message(message.chat.id,f"♻️ RESET OK {idc} -> ${monto} (solo su caja)")
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
        bot.send_message(message.chat.id,f"➕ ${monto} a {idc} -> ${user_data['balance']}")
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
        bot.send_message(message.chat.id,f"🗑️ Baja OK {idc}");
    except:
        bot.send_message(message.chat.id,"Uso: /baja <ID>")

@bot.message_handler(commands=['socios'])
def socios(message):
    if not es_admin(message.chat.id):
        return
    admin=get_user_data(ADMINS_IDS[0])
    txt=f"👥 V25.4 CAJAS SEPARADAS FULL - Link por socio\n\n🔵 ADMIN (vos) 100%:\n {ADMINS_IDS[0]} - ${admin['balance']} - {get_estado_texto(admin)}\nLink: {WEB_URL} (sin?id)\n\n🟠 SOCIOS (20% - links privados):\n"
    if not ESTADO["socios"]:
        txt+=" Sin socios\n"
    else:
        for cid,data in ESTADO["socios"].items():
            bal = USUARIOS.get(cid, {}).get("balance", 200)
            txt+=f" {cid} - {data['plan']} - ${bal} - {WEB_URL}/?id={cid}\n"
    bot.send_message(message.chat.id,txt)

@bot.message_handler(commands=['debug'])
def debug_cmd(message):
    if not es_admin(message.chat.id):
        return
    size=os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0
    bot.send_message(message.chat.id,f"💾 DEBUG V25.4\nFile: {DATA_FILE}\nSize: {size}b\nADMIN ${USUARIOS.get(ADMINS_IDS[0],{}).get('balance','?')}\nSocios: {len(ESTADO['socios'])}")

@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso and len(ESTADO["socios"])>0 and not es_admin(message.chat.id):
        bot.send_message(message.chat.id,f"🔒 Bot privado\nTu ID: {message.chat.id}")
        return
    if es_admin(message.chat.id):
        bot.send_message(message.chat.id,f"👋 MANADA V25.4 ADMIN 🐺\nTu web: {WEB_URL}\nWeb de socio: {WEB_URL}/?id=ID\n/Prender /socios /balance /debug")
    else:
        u=get_user_data(message.chat.id)
        bot.send_message(message.chat.id,f"👋 MANADA V25.4 🐺\nTu plan: {ESTADO['socios'][message.chat.id]['plan']}\nTu web privada:\n{WEB_URL}/?id={message.chat.id}\n/Prender para arrancar con tu caja separada")

@bot.message_handler(commands=['Prender','prender'])
def prender(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso:
        bot.send_message(message.chat.id,"⛔ Vencido")
        return
    user_data = get_user_data(message.chat.id)
    user_data["prendido"]=True
    user_data["pausa_hasta"]=None
    user_data["modo"]="CACHORRO"
    user_data["mercado"]="CACHORRO GRATIS 7 DIAS (20%)"
    guardar_datos()
    link = f"{WEB_URL}/?id={message.chat.id}" if not es_admin(message.chat.id) else WEB_URL
    caja = "🔵 ADMIN 100%" if es_admin(message.chat.id) else "🟠 SOCIO 20%"
    bot.send_message(message.chat.id,f"🚀 {caja} ACTIVADA - ${user_data['balance']}\nTu web: {link}\n/balance")

@bot.message_handler(commands=['balance'])
def balance(message):
    acceso,dias_rest=tiene_acceso(message.chat.id)
    if not acceso:
        return
    user_data = get_user_data(message.chat.id)
    win=calcular_winrate(user_data)
    if es_admin(message.chat.id):
        bot.send_message(message.chat.id,f"💰 🔵 CAJA ADMIN 100% SEPARADA\nBalance: ${user_data['balance']} (solo tuyo)\nNeto: ${user_data['neto_hoy']} ({user_data['ops_hoy']} ops) Win {win}%\nModo: {user_data['modo']} | {user_data['mercado']}\nEstado: {get_estado_texto(user_data)}\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}\nWeb: {WEB_URL}")
    else:
        plan=ESTADO["socios"][message.chat.id]["plan"]
        bot.send_message(message.chat.id,f"💰 🟠 TU CAJA - PLAN {plan}\nBalance: ${user_data['balance']} USDT (solo tuyo)\nNeto: ${user_data['neto_hoy']} ({user_data['ops_hoy']} ops) Win {win}%\nModo: {user_data['modo']} | {user_data['mercado']}\nEstado: {get_estado_texto(user_data)}\nTu web privada:\n{WEB_URL}/?id={message.chat.id}")

@bot.message_handler(commands=['historial'])
def historial(message):
    user_data = get_user_data(message.chat.id)
    hist="\n".join(user_data["historial"][-15:]) or "Sin ops aún"
    bot.send_message(message.chat.id,f"📜 HISTORIAL {user_data['caja']}\n{hist}")

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

# HTML V25.4 FULL CON RETORNO Y DETALLES
HTML="""<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="google" content="notranslate"><title>V25.4 FULL 374</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial}.header{background:#1e222d;padding:10px}.box{padding:12px;margin:6px;border-radius:10px;font-size:13px;line-height:1.6}.admin{background:#0d2a4a;border-left:5px solid #00bfff}.socio{background:#3a2a1a;border-left:5px solid #ff9800}.kpi{display:inline-block;background:#1e222d;padding:6px 9px;border-radius:6px;margin:3px;font-size:12px;border:1px solid #2a2e39}.btn{display:inline-block;margin-top:10px;padding:9px 16px;background:#00bfff;color:#000;border-radius:8px;text-decoration:none;font-weight:bold}.btn2{display:inline-block;margin-left:6px;padding:9px 16px;background:#2a2e39;color:#fff;border-radius:8px;text-decoration:none}#chart_btc{height:50vh}#chart_bnb{height:28vh}a{color:#00bfff}</style></head><body><div class="header"><b id="titulo">🐺 V25.4 FULL 374 - CAJAS SEPARADAS</b><div id="admin" class="box admin">Cargando ADMIN FULL...</div><div id="socios" class="box socio">Cargando SOCIOS...</div><div id="infoPlan" class="box socio" style="display:none"></div></div><div id="chart_btc"></div><div id="chart_bnb"></div>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"chart_btc"});
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","container_id":"chart_bnb"});
function getId(){return new URLSearchParams(window.location.search).get('id')}
async function r(){
 let sid=getId();
 if(sid){
   try{
     let d=await (await fetch('/api/socio/'+sid)).json();
     if(d.error){document.getElementById('admin').innerHTML='⛔ Socio no existe<br><a class="btn" href="/">⬅️ Volver a mi caja ADMIN</a>';return}
     document.getElementById('titulo').innerHTML=`🐺 CAJA SOCIO ${sid} - PLAN ${d.plan}`;
     document.getElementById('admin').className='box socio';
     document.getElementById('admin').innerHTML=`🟠 TU CAJA - PLAN ${d.plan}<br>
        <span class="kpi">💰 Bal: $${d.balance}</span>
        <span class="kpi">📈 Neto: $${d.neto_hoy}</span>
        <span class="kpi">🔄 Ops: ${d.ops_hoy}</span>
        <span class="kpi">🎯 Win: ${d.winrate}%</span><br>
        <span class="kpi">⚙️ Modo: ${d.modo}</span>
        <span class="kpi">📊 Merc: ${d.mercado}</span><br>
        <span class="kpi">₿ BTC: $${d.btc}</span>
        <span class="kpi">🔶 BNB: $${d.bnb}</span><br>
        Estado: ${d.estado_texto}<br>Vence: ${d.vence} (${d.vence_dias}d) | ID ${sid}<br>
        <a class="btn" href="/">⬅️ Volver a mi caja ADMIN</a> <a class="btn2" href="/?id=${sid}">🔄 Recargar</a>`;
     document.getElementById('socios').style.display='none';
     let tp=d.modo=='LOBO'?'+0.3% / -0.7%':d.modo=='RATA'?'+0.15% / -0.4%':d.modo=='TIBURON'?'+0.8% / -1.0%':'CACHORRO 20%';
     document.getElementById('infoPlan').style.display='block';
     document.getElementById('infoPlan').innerHTML=`📋 TU PLAN: ${d.plan} | TP/SL: ${tp}<br>Link privado:?id=${sid}`;
   }catch(e){document.getElementById('admin').innerHTML='Error carga<br><a class="btn" href="/">⬅️ Volver a ADMIN</a>'}
 }else{
   let a=await (await fetch('/api/data')).json();
   document.getElementById('admin').innerHTML=`🔵 CAJA ADMIN 100% - TU PARTE SEPARADA<br>
      <span class="kpi">💰 Bal: $${a.balance}</span>
      <span class="kpi">📈 Neto: $${a.neto_hoy}</span>
      <span class="kpi">🔄 Ops: ${a.ops_hoy}</span>
      <span class="kpi">🎯 Win: ${a.winrate}%</span><br>
      <span class="kpi">⚙️ Modo: ${a.modo}</span>
      <span class="kpi">📊 Merc: ${a.mercado}</span><br>
      <span class="kpi">₿ BTC: $${a.btc}</span>
      <span class="kpi">🔶 BNB: $${a.bnb}</span><br>
      Estado: ${a.estado_texto}<br>Disco: ${a.disco}`;
   let s=await (await fetch('/api/socios')).json();
   let h='🟠 CAJAS SOCIOS 20% SEPARADAS (click Ver):<br>';
   for(let k in s.socios){
     let u=s.socios[k];
     h+=`<div style="margin:8px 0;padding:8px;background:#1e222d;border-radius:8px">Socio ${k} | ${u.plan}<br>
     💰 Bal: $${u.balance} | 📈 Neto: $${u.neto_hoy} | 🔄 Ops: ${u.ops} | 🎯 Win: ${u.winrate}%<br>
     ⚙️ ${u.modo} | ${u.mercado} | ${u.estado}<br>
     <a class="btn" href="/?id=${k}">➡️ Ver?id=${k}</a></div>`;
   }
   if(Object.keys(s.socios).length==0)h+='Sin socios - /alta';
   document.getElementById('socios').innerHTML=h;
 }
}
setInterval(r,3000);r();
</script></body></html>"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    ESTADO["btc"]=round(78287.4+random.uniform(-350,350),2)
    ESTADO["bnb"]=round(739.68+random.uniform(-5,5),2)
    admin_data = get_user_data(ADMINS_IDS[0])
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
        "disco":DATA_FILE
    })

@app.route('/api/socios')
def api_socios():
    out={}
    for cid,d in ESTADO["socios"].items():
        u=USUARIOS.get(cid,{"balance":200,"ops_hoy":0,"prendido":False,"neto_hoy":0,"ganadas":0,"perdidas":0,"modo":"CACHORRO","mercado":""})
        out[cid]={
            "balance":u["balance"],
            "ops":u["ops_hoy"],
            "estado":get_estado_texto(u),
            "plan":d["plan"],
            "neto_hoy":u["neto_hoy"],
            "winrate":calcular_winrate(u),
            "modo":u["modo"],
            "mercado":u["mercado"]
        }
    return jsonify({"socios":out})

@app.route('/api/socio/<int:socio_id>')
def api_socio_individual(socio_id):
    if socio_id not in ESTADO["socios"]:
        return jsonify({"error":"no existe"}),404
    sd=ESTADO["socios"][socio_id]
    u=USUARIOS.get(socio_id) or get_user_data(socio_id)
    dias=(sd["vence"]-datetime.now()).days+1
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
        "vence":sd["vence"].strftime("%d/%m/%Y"),
        "id":socio_id,
        "btc":ESTADO["btc"],
        "bnb":ESTADO["bnb"]
    })

def run_bot():
    bot.infinity_polling(skip_pending=True)

threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
