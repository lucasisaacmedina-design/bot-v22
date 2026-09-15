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
ADMINS_IDS = [6530209116]
WEB_URL = "https://bot-v22-1.onrender.com"
DATA_FILE = "/data/manada.json"
os.makedirs("/data", exist_ok=True)

ALIAS_MP_DEMO = "manada.lobo.demo.mp"
DOLAR_CRIPTO = {"valor": 1480, "actualizado": "inicio", "fuente": "DEMO"}

print(f"### V22.9 FINAL LIMPIO - SIN ESTADO - SIN CUADRO ESTRATEGIA ###")

ESTADO = {"btc": 78287.4, "bnb": 739.68, "btc_history": [78287.4 + random.uniform(-200,200) for _ in range(30)], "socios": {}, "admins": ADMINS_IDS}
USUARIOS = {}
LOCK = threading.Lock()

def actualizar_dolar():
    while True:
        try:
            r = requests.get("https://criptoya.com/api/dolar", timeout=10).json()
            if r and 'cripto' in r and 'ccb' in r['cripto']:
                DOLAR_CRIPTO["valor"] = int(float(r['cripto']['ccb']))
                DOLAR_CRIPTO["actualizado"] = datetime.now().strftime("%H:%M")
        except: DOLAR_CRIPTO["valor"] += random.randint(-5,5)
        time.sleep(1800)

BIENVENIDA = "Hola Lobo V22.9 BASE SOLIDA\nRATA LATERAL / LOBO NORMAL / TIBURON VOLATIL\nCACHORRO 20% 7 DIAS"

def get_menu_botones(admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if admin:
        markup.add(types.KeyboardButton("📊 BALANCE"), types.KeyboardButton("🚀 PRENDER"))
        markup.add(types.KeyboardButton("👥 SOCIOS"), types.KeyboardButton("📈 ESTRATEGIAS"))
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
                v["estrategias"].pop("ORCA", None); v["estrategias"].pop("MEGALODON", None)
                USUARIOS[int(k)] = v
            except: pass
    except: pass

cargar_datos()

def get_user_data(user_id):
    user_id = int(user_id); es_admin_id = user_id in ADMINS_IDS
    if user_id not in USUARIOS:
        USUARIOS[user_id] = {"prendido": False, "balance": BALANCE_INICIAL, "ops_hoy": 0, "neto_hoy": 0.0, "ganadas": 0, "perdidas": 0, "modo": "LOBO" if es_admin_id else "CACHORRO", "mercado": "BASE SOLIDA BTC+BNB" if es_admin_id else "CACHORRO GRATIS 7 DIAS (20%)", "pausa_hasta": None, "historial": [], "caja": "ADMIN BASE SOLIDA" if es_admin_id else "SOCIO", "estrategias": {"RATA": {"ops":0,"ganadas":0,"neto":0.0}, "LOBO": {"ops":0,"ganadas":0,"neto":0.0}, "TIBURON": {"ops":0,"ganadas":0,"neto":0.0}}}
        guardar_datos()
    USUARIOS[user_id]["estrategias"].pop("ORCA", None); USUARIOS[user_id]["estrategias"].pop("MEGALODON", None)
    for k in ["RATA","LOBO","TIBURON"]:
        if k not in USUARIOS[user_id]["estrategias"]: USUARIOS[user_id]["estrategias"][k] = {"ops":0,"ganadas":0,"neto":0.0}
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
            if es_ganada: user_data["ganadas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]+gan,2); user_data["balance"]=round(user_data["balance"]+gan,2); user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - {activo_base} - {modo_log} - TP {tp} = +${gan}")
            else: user_data["perdidas"]+=1; user_data["ops_hoy"]+=1; user_data["neto_hoy"]=round(user_data["neto_hoy"]-perd,2); user_data["balance"]=round(user_data["balance"]-perd,2); user_data["historial"].append(f"{datetime.now().strftime('%H:%M')} - {activo_base} - {modo_log} - SL {sl} = -${perd}");
            if not es_admin_id and not es_ganada: user_data["pausa_hasta"]=datetime.now()+timedelta(minutes=10)
            if len(user_data["historial"])>20: user_data["historial"]=user_data["historial"][-20:]
        contador+=1
        if contador>=10: guardar_datos(); contador=0

@bot.message_handler(commands=['id'])
def get_id(message): bot.send_message(message.chat.id,f"Tu ID es: {message.chat.id}\nLink: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(es_admin(message.chat.id)))
@bot.message_handler(func=lambda m: m.text in ["📈 ESTRATEGIAS", "/estrategias"])
def estrategias(message):
    ud=get_user_data(message.chat.id); est=ud["estrategias"]
    txt=f"📈 V22.9 BASE SOLIDA - {ud['caja']}\nModo: {ud['modo']}\nMercado: {ud['mercado']}\n\nRATA: {est['RATA']['ops']} ops Win {calcular_winrate_estrategia(est['RATA'])}% Neto ${est['RATA']['neto']}\nLOBO: {est['LOBO']['ops']} ops Win {calcular_winrate_estrategia(est['LOBO'])}% Neto ${est['LOBO']['neto']}\nTIBURON: {est['TIBURON']['ops']} ops Win {calcular_winrate_estrategia(est['TIBURON'])}% Neto ${est['TIBURON']['neto']}\n\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}"
    bot.send_message(message.chat.id, txt, reply_markup=get_menu_botones(es_admin(message.chat.id)))
@bot.message_handler(commands=['start'])
def start(message):
    acceso,dias_rest=tiene_acceso(message.chat.id); ud=get_user_data(message.chat.id)
    if es_admin(message.chat.id): bot.send_message(message.chat.id,f"👋 V22.9 ADMIN BASE SOLIDA 🐺\nBalance ${ud['balance']} - {ud['modo']}\n{ud['mercado']}\nTu web: {WEB_URL}", reply_markup=get_menu_botones(True))
    else:
        if not acceso: bot.send_message(message.chat.id, BIENVENIDA + f"\n\nTu ID: {message.chat.id}", reply_markup=get_menu_botones(False))
        else: bot.send_message(message.chat.id,f"👋 MANADA V22.9\nPlan: {ESTADO['socios'][message.chat.id]['plan']} - {dias_rest} dias\nWeb: {WEB_URL}/?id={message.chat.id}", reply_markup=get_menu_botones(False))
@bot.message_handler(func=lambda m: m.text in ["🚀 PRENDER", "/prender"])
def prender(message):
    acceso,_=tiene_acceso(message.chat.id)
    if not acceso: bot.send_message(message.chat.id,"⛔ Vencido", reply_markup=get_menu_botones(False)); return
    user_data = get_user_data(message.chat.id); user_data["prendido"]=True; user_data["pausa_hasta"]=None
    if es_admin(message.chat.id): analizar_mercado_y_elegir_modo(user_data)
    else: user_data["modo"]="CACHORRO"; user_data["mercado"]="CACHORRO GRATIS 7 DIAS (20%)"
    guardar_datos(); bot.send_message(message.chat.id,f"🚀 {user_data['caja']} ACTIVADA - ${user_data['balance']}\nModo {user_data['modo']} - {user_data['mercado']}", reply_markup=get_menu_botones(es_admin(message.chat.id)))
@bot.message_handler(func=lambda m: m.text in ["📊 BALANCE", "/balance"])
def balance(message):
    if not tiene_acceso(message.chat.id)[0]: return
    ud = get_user_data(message.chat.id); win=calcular_winrate(ud)
    bot.send_message(message.chat.id,f"💰 {ud['caja']}\nBalance: ${ud['balance']}\nNeto Hoy: ${ud['neto_hoy']}\nOps Hoy: {ud['ops_hoy']} - Winrate: {win}%\nModo: {ud['modo']}\nMercado: {ud['mercado']}\nBTC ${ESTADO['btc']} BNB ${ESTADO['bnb']}", reply_markup=get_menu_botones(es_admin(message.chat.id)))
@bot.message_handler(func=lambda m: m.text in ["📜 HISTORIAL", "/historial"])
def historial(message): ud = get_user_data(message.chat.id); hist="\n".join(ud["historial"][-15:]) or "Sin ops"; bot.send_message(message.chat.id,f"📜 {ud['caja']}\n{hist}", reply_markup=get_menu_botones(es_admin(message.chat.id)))
@bot.message_handler(func=lambda m: m.text in ["💰 PAGAR", "/pagar"])
def pagar(message): bot.send_message(message.chat.id,f"PAGAR V22.9 - Dolar ${DOLAR_CRIPTO['valor']}\nAlias: {ALIAS_MP_DEMO}", reply_markup=get_menu_botones(es_admin(message.chat.id)))
@bot.message_handler(commands=['alta','socios'])
def admin_cmds(message):
    if not es_admin(message.chat.id): return
    if message.text.startswith('/alta'):
        try:
            parts=message.text.split(); id_cliente=int(parts[1]); dias=int(parts[2]); plan=parts[3].upper() if len(parts)>3 else "CACHORRO"
            vence=datetime.now()+timedelta(days=dias); ESTADO["socios"][id_cliente]={"alta":datetime.now(),"vence":vence,"plan":plan}
            ud = get_user_data(id_cliente); ud["balance"]=200.0; ud["neto_hoy"]=0; ud["ops_hoy"]=0; ud["ganadas"]=0; ud["perdidas"]=0; ud["historial"]=[]; ud["prendido"]=False; ud["estrategias"]={"RATA":{"ops":0,"ganadas":0,"neto":0.0},"LOBO":{"ops":0,"ganadas":0,"neto":0.0},"TIBURON":{"ops":0,"ganadas":0,"neto":0.0}}
            guardar_datos(); bot.send_message(message.chat.id,f"✅ Alta {id_cliente} {plan} {dias}d -> {WEB_URL}/?id={id_cliente}")
        except Exception as e: bot.send_message(message.chat.id,f"Error: {e}")
    elif message.text.startswith('/socios'):
        txt=f"👥 SOCIOS\n"
        for cid,d in ESTADO["socios"].items(): txt+=f"{cid} {d['plan']} - {WEB_URL}/?id={cid}\n"
        bot.send_message(message.chat.id, txt)

# === HTML FINAL V22.9 - SIN ESTADO - SIN CUADRO VERDE ===
HTML="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>V22.9 FINAL LIMPIO</title><script src="https://s3.tradingview.com/tv.js"></script><style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial}.header{background:#1e222d;padding:10px}.box{padding:12px;margin:6px;border-radius:10px;font-size:13px;line-height:1.7}.admin{background:#0d2a4a;border-left:5px solid #00ffea}.socio{background:#2a2218;border-left:5px solid #ff9800}.kpi{display:inline-block;background:#1e222d;padding:7px 10px;border-radius:6px;margin:3px;font-size:12px;border:1px solid #2a2e39}#chart_btc{height:50vh}#chart_bnb{height:30vh}.btn{display:inline-block;margin-top:8px;padding:8px 14px;background:#00ffea;color:#000;border-radius:6px;text-decoration:none;font-weight:bold}</style></head><body><div class="header"><b id="titulo">V22.9 BASE SOLIDA - FINAL LIMPIO</b><div id="admin" class="box admin">Cargando detalle...</div><div id="socios" class="box socio">Cargando socios...</div></div><div id="chart_btc"></div><div id="chart_bnb"></div>
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
       🟠 TU CAJA CACHORRO 20%<br>
       <span class="kpi">💰 Balance: $${d.balance}</span>
       <span class="kpi">📈 Neto Hoy: $${d.neto_hoy}</span>
       <span class="kpi">🔄 Ops Hoy: ${d.ops_hoy}</span>
       <span class="kpi">🎯 Winrate: ${d.winrate}%</span><br>
       <span class="kpi">⚙️ Modo: ${d.modo}</span>
       <span class="kpi">📊 Mercado: ${d.mercado}</span><br>
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
   for(let k in s.socios){let u=s.socios[k];h+=`<div style="margin:8px 0;padding:8px;background:#1e222d;border-radius:8px">👤 ${k} - ${u.plan} | 💰 $${u.balance} | 📈 Neto $${u.neto_hoy} | 🔄 ${u.ops} ops | 🎯 Win ${u.winrate}%<br>⚙️ ${u.modo} | 📊 ${u.mercado}<br><a class="btn" href="/?id=${k}">VER CAJA?id=${k}</a></div>`;}
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
