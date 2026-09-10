import os, threading, random, time, math, wave, struct, urllib.request
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, Response
import telebot

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("Falta BOT_TOKEN en Render")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ULTIMO_CHAT_ID = None

# === AUDIOS REALES ===
def bajar_audios():
    try:
        if not os.path.exists("aullido_real.mp3"):
            urllib.request.urlretrieve("https://www.orangefreesounds.com/wp-content/uploads/2014/10/Wolf-howl-sound.mp3", "aullido_real.mp3")
            print("Aullido real bajado")
    except Exception as e:
        print("Fallo aullido", e)
    try:
        if not os.path.exists("llanto_real.mp3"):
            # lobo whimper / aullido triste real
            urllib.request.urlretrieve("https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3?filename=wolf-howling-90999.mp3", "llanto_real.mp3")
    except:
        pass

def respaldo_sintetico():
    if not os.path.exists("aullido.wav"):
        fr=22050; dur=2.2
        with wave.open("aullido.wav",'w') as w:
            w.setparams((1,2,fr,0,'NONE','not compressed'))
            for i in range(int(fr*dur)):
                t=i/fr; f=400+600*t/dur; v=int(14000*math.sin(2*math.pi*f*t))
                w.writeframes(struct.pack('<h',v))
    if not os.path.exists("llanto.wav"):
        fr=22050; dur=2.5
        with wave.open("llanto.wav",'w') as w:
            w.setparams((1,2,fr,0,'NONE','not compressed'))
            for i in range(int(fr*dur)):
                t=i/fr; f=700-500*t/dur; v=int(12000*math.sin(2*math.pi*f*t)*math.exp(-t))
                w.writeframes(struct.pack('<h',v))

bajar_audios()
respaldo_sintetico()

def get_file(t):
    if t=="aullido":
        return "aullido_real.mp3" if os.path.exists("aullido_real.mp3") else "aullido.wav"
    return "llanto_real.mp3" if os.path.exists("llanto_real.mp3") else "llanto.wav"

ESTADO = {
    "prendido": False,
    "balance": 199.60,
    "ops_hoy": 4,
    "neto_hoy": -0.40,
    "ganadas": 2,
    "perdidas": 2,
    "modo": "LOBO",
    "mercado": "NORMAL (0.30%)",
    "pausa_hasta": None,
    "btc": 78430,
    "bnb": 737.50,
    "historial": [
        "14:00 - BTC - LOBO - TP +0.3% = +$0.60 Neto",
        "14:30 - BTC - LOBO - TP +0.3% = +$0.60 Neto",
        "15:10 - BNB - RATA - SL -0.7% = -$0.80 Neto",
        "01:33 - BNB - RATA - SL -0.7% = -$0.80 Neto"
    ],
    "btc_history": [78430 + random.uniform(-200,200) for _ in range(30)],
    "balance_history": [199.60 + random.uniform(-1,1) for _ in range(30)],
    "last_event": "none"
}

def calcular_winrate():
    total = ESTADO["ganadas"] + ESTADO["perdidas"]
    if total == 0: return 0
    return round((ESTADO["ganadas"] / total) * 100)

def get_estado_texto():
    if not ESTADO["prendido"]: return "🔴 APAGADO"
    if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]:
        mins = int((ESTADO["pausa_hasta"] - datetime.now()).total_seconds()/60)+1
        return f"⏸️ Pausa {mins}min"
    return "🟢 PRENDIDO"

def motor_demo():
    while True:
        time.sleep(random.randint(45, 90))
        if not ESTADO["prendido"]: continue
        if ESTADO["pausa_hasta"] and datetime.now() < ESTADO["pausa_hasta"]: continue
        if not ULTIMO_CHAT_ID: continue
        
        es_ganada = random.random() < 0.66
        hora = datetime.now().strftime('%H:%M')
        if es_ganada:
            ESTADO["ganadas"] += 1
            ESTADO["ops_hoy"] += 1
            ESTADO["neto_hoy"] = round(ESTADO["neto_hoy"] + 0.60, 2)
            ESTADO["balance"] = round(ESTADO["balance"] + 0.60, 2)
            ESTADO["historial"].append(f"{hora} - BTC - LOBO - TP +0.3% = +$0.60 Neto")
            ESTADO["last_event"] = "win"
            try:
                bot.send_message(ULTIMO_CHAT_ID, f"🐺 AUUUUU! LOBO GANÓ 🔊 REAL\n✅ {hora} - TP +0.3% = +$0.60 Neto\nBalance ${ESTADO['balance']} | Neto ${ESTADO['neto_hoy']}")
                with open(get_file("aullido"),"rb") as f:
                    bot.send_voice(ULTIMO_CHAT_ID, f, caption="🐺 AUUUUU REAL 🔊")
            except Exception as e:
                print(e)
        else:
            ESTADO["perdidas"] += 1
            ESTADO["ops_hoy"] += 1
            ESTADO["neto_hoy"] = round(ESTADO["neto_hoy"] - 0.80, 2)
            ESTADO["balance"] = round(ESTADO["balance"] - 0.80, 2)
            ESTADO["historial"].append(f"{hora} - BNB - RATA - SL -0.7% = -$0.80 Neto (Pausa 10min)")
            ESTADO["pausa_hasta"] = datetime.now() + timedelta(minutes=10)
            ESTADO["last_event"] = "loss"
            try:
                bot.send_message(ULTIMO_CHAT_ID, f"😢 auuu... Lobo llora REAL 🔊\n❌ {hora} - SL -0.7% = -$0.80 Neto\nBalance ${ESTADO['balance']}")
                with open(get_file("llanto"),"rb") as f:
                    bot.send_voice(ULTIMO_CHAT_ID, f, caption="😢 llanto real")
            except: pass
        
        if len(ESTADO["historial"]) > 20:
            ESTADO["historial"] = ESTADO["historial"][-20:]
        ESTADO["balance_history"].append(ESTADO["balance"])
        if len(ESTADO["balance_history"]) > 30:
            ESTADO["balance_history"] = ESTADO["balance_history"][-30:]

@bot.message_handler(commands=['start'])
def start(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    texto = f"""👋 ¡Bienvenido a LOBOBOT22 🐺 V33.2 REAL!
Ahora AULLO con audio REAL de lobo salvaje cuando gano y LLORO REAL cuando pierdo.
1️⃣ /introduccion 2️⃣ /estrategias 3️⃣ /modo 4️⃣ /prender 5️⃣ /balance 6️⃣ /historial 7️⃣ /help 8️⃣ /apagar"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['introduccion', 'start_intro'])
def introduccion(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    texto = """👋 1 BIENVENIDO V33.2 REAL WOLF
BTC ~$78.000 | BNB ~$737 | USDT = 1 Dólar
Bal $199.60 real neto +0.60+0.60-0.80-0.80 = -0.40
Gana = 🔊 AULLIDO REAL | Pierde = 🔊 LLANTO REAL
Siguiente: /estrategias y /prender"""
    bot.send_message(message.chat.id, texto)

@bot.message_handler(commands=['estrategias'])
def estrategias(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    bot.send_message(message.chat.id, "📊 2 ESTRATEGIAS\n🐺 LOBO NORMAL 0.30% TP +0.3% SL -0.7%\n🐀 RATA LATERAL 0.10%\n🦈 TIBURON VOLATIL pausa\n/modo")

@bot.message_handler(commands=['modo'])
def modo(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    estado = get_estado_texto(); win = calcular_winrate()
    bot.send_message(message.chat.id, f"⚙️ 3 MODO\nMercado: {ESTADO['mercado']}\nModo: 🐺 {ESTADO['modo']}\nBTC: ${ESTADO['btc']} | BNB: ${ESTADO['bnb']}\nEstado: {estado} | Win {win}% ({ESTADO['ganadas']}W/{ESTADO['perdidas']}L)")

@bot.message_handler(commands=['prender', 'iniciar'])
def prender(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    ESTADO["prendido"] = True
    bot.send_message(message.chat.id, f"🚀 4 BOT PRENDIDO 🔊\n🟢 PRENDIDO | Bal ${ESTADO['balance']} | {ESTADO['mercado']} MODO {ESTADO['modo']}\n¡Vas a escucharme aullar!")
    try:
        with open(get_file("aullido"),"rb") as f: bot.send_voice(message.chat.id, f, caption="🐺 AUUU REAL listo para cazar!")
    except: pass

@bot.message_handler(commands=['balance'])
def balance(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    estado = get_estado_texto(); win = calcular_winrate()
    falta = round(abs(ESTADO['neto_hoy'])+0.60,2) if ESTADO['neto_hoy']<0 else 0
    revenge = f"🎯 REVENGE: Falta ${falta} para profit" if ESTADO['neto_hoy']<0 else f"🔥 PROFIT +${ESTADO['neto_hoy']} AUUU!"
    bot.send_message(message.chat.id, f"💰 5 BALANCE V33.2 REAL 🔊\nBalance: ${ESTADO['balance']} USDT\nNeto hoy: ${ESTADO['neto_hoy']} ({ESTADO['ops_hoy']} ops)\n{revenge}\nOps: {ESTADO['ops_hoy']} | W:{ESTADO['ganadas']} L:{ESTADO['perdidas']} Win {win}%\nEstado: {estado}")

@bot.message_handler(commands=['historial'])
def historial(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    hist = "\n".join(ESTADO["historial"]); win = calcular_winrate()
    bot.send_message(message.chat.id, f"📜 6 HISTORIAL\n{hist}\n\nTotal Neto: ${ESTADO['neto_hoy']} | Win {win}% ({ESTADO['ganadas']}W/{ESTADO['perdidas']}L)")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    estado = get_estado_texto(); win = calcular_winrate()
    bot.send_message(message.chat.id, f"❓ 7 HELP\nPausa 10min = llanto REAL cuidando plata\nBal -$0.40 = REAL +0.60+0.60-0.80-0.80\nEstado: {estado} | Bal ${ESTADO['balance']} | Win {win}%")

@bot.message_handler(commands=['apagar', 'stop'])
def apagar(message):
    global ULTIMO_CHAT_ID; ULTIMO_CHAT_ID=message.chat.id
    ESTADO["prendido"] = False
    bot.send_message(message.chat.id, f"🛑 8 BOT PAUSADO\n🔴 APAGADO | Bal ${ESTADO['balance']} USDT")
    try:
        with open(get_file("llanto"),"rb") as f: bot.send_voice(message.chat.id, f, caption="😢 a dormir...")
    except: pass

HTML = """
<!DOCTYPE html><html translate="no" class="notranslate"><head>
<meta charset="utf-8"><meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>LOBOBOT22 V33.2 REAL</title>
<script src="https://s3.tradingview.com/tv.js"></script>
<style>body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial,sans-serif}
.header{background:#1e222d;padding:10px 14px;border-bottom:1px solid #2a2e39}
.header b{color:#fff;font-size:16px}.line{font-size:13px;margin-top:4px}
.orange{border-left:3px solid #ff9800;padding-left:8px;margin:8px 0;color:#d1d4dc;font-size:13px}
#chart_btc{height:56vh;width:100%}#chart_bnb{height:38vh;width:100%;border-top:2px solid #2a2e39}
#wolf{position:fixed;top:70px;right:20px;font-size:32px;display:none;background:#1e222d;padding:6px 10px;border-radius:10px;border:1px solid #ff9800;z-index:99}
button{border:none;padding:7px 12px;border-radius:8px;cursor:pointer;margin-right:6px;font-weight:bold}
</style></head><body>
<div class="header notranslate" translate="no">
<b>🐺 LOBOBOT22 V33.2 REAL WOLF 🔊</b><br>
<button style="background:#ff9800" onclick="document.getElementById('howl').play()">🐺 🔊 AULLIDO REAL</button>
<button style="background:#444;color:#fff" onclick="document.getElementById('cry').play()">😢 LLANTO REAL</button>
<br><div class="line notranslate" id="topbar">Bal $199.60 | Neta $-0.40 | Ops 4 | Win 50%</div>
<div class="orange">MERCADO: NORMAL | MODO: LOBO 🐺<br><span id="revenge">TP +0.3% SL -0.7%</span></div>
<div class="line notranslate" id="livebar">BTC $78,308 | BNB $737 | NORMAL (0.30%)</div>
</div>
<div id="wolf"></div>
<div id="chart_btc"></div><div id="chart_bnb"></div>

<audio id="howl" preload="auto"><source src="/audio/aullido" type="audio/mpeg"></audio>
<audio id="cry" preload="auto"><source src="/audio/llanto" type="audio/mpeg"></audio>

<script>
new TradingView.widget({"autosize": true,"symbol": "BINANCE:BTCUSDT","interval": "5","timezone": "America/Argentina/Buenos_Aires","theme": "dark","style": "1","locale": "es","toolbar_bg": "#131722","container_id": "chart_btc"});
new TradingView.widget({"autosize": true,"symbol": "BINANCE:BNBUSDT","interval": "5","timezone": "America/Argentina/Buenos_Aires","theme": "dark","style": "1","locale": "es","toolbar_bg": "#131722","container_id": "chart_bnb"});
let lastBal=199.6;
async function refresh(){
 try{
  let r=await fetch('/api/data');let d=await r.json();
  document.getElementById('topbar').innerHTML=`Bal $${d.balance} | Neta $${d.neto_hoy} | Ops ${d.ops_hoy} | Win ${d.winrate}% | ${d.estado_texto}`;
  document.getElementById('livebar').innerHTML=`BTC $${d.btc} | BNB $${d.bnb} | ${d.mercado} | Bal $${d.balance} | Neta $${d.neto_hoy} | Win ${d.winrate}%`;
  document.getElementById('revenge').innerHTML=d.neto_hoy<0?`🎯 Falta $${(Math.abs(d.neto_hoy)+0.6).toFixed(2)} para profit | Próximo TP +$0.60`:`🔥 PROFIT +$${d.neto_hoy} ¡AUUUU REAL!`;
  if(d.balance!=lastBal){
   let w=document.getElementById('wolf');
   if(d.last_event=='win'){document.getElementById('howl').play().catch(()=>{}); w.innerHTML='🐺 AUUUU REAL! +$0.60 🔊'; w.style.display='block'; setTimeout(()=>w.style.display='none',4000);}
   if(d.last_event=='loss'){document.getElementById('cry').play().catch(()=>{}); w.innerHTML='😢 auuu REAL -$0.80'; w.style.display='block'; setTimeout(()=>w.style.display='none',4000);}
   lastBal=d.balance;
  }
 }catch(e){}
}
setInterval(refresh,4000); refresh();
</script></body></html>
"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/audio/<tipo>')
def audios(tipo):
    fname = get_file("aullido" if tipo=="aullido" else "llanto")
    if not os.path.exists(fname): return "no audio", 404
    data = open(fname,"rb").read()
    mime = "audio/mpeg" if fname.endswith(".mp3") else "audio/wav"
    return Response(data, mimetype=mime)

@app.route('/api/data')
def api_data():
    ESTADO["btc"] = round(78430 + random.uniform(-150,150),2)
    ESTADO["bnb"] = round(737.50 + random.uniform(-2,2),2)
    return jsonify({
        "balance": ESTADO["balance"],
        "neto_hoy": ESTADO["neto_hoy"],
        "ops_hoy": ESTADO["ops_hoy"],
        "winrate": calcular_winrate(),
        "ganadas": ESTADO["ganadas"],
        "perdidas": ESTADO["perdidas"],
        "modo": ESTADO["modo"],
        "mercado": ESTADO["mercado"],
        "btc": ESTADO["btc"],
        "bnb": ESTADO["bnb"],
        "estado_texto": get_estado_texto(),
        "last_event": ESTADO["last_event"]
    })

def run_bot(): bot.infinity_polling(skip_pending=True)
threading.Thread(target=run_bot, daemon=True).start()
threading.Thread(target=motor_demo, daemon=True).start()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
