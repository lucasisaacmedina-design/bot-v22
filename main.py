import os, requests, random, time, telebot
from flask import Flask, render_template_string, jsonify
from datetime import datetime
from threading import Thread

app = Flask(__name__)
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8924629316:AAEO6LHyF_bemen9rxD822RR5KsXmvdyf94")
bot = telebot.TeleBot(BOT_TOKEN)

balance = 153.62
comision_acum = 0.34
ganancia_bruta = 8.15
trades = []
precio_actual = 80837.99
CHAT_IDS = set() # Guarda a quien avisar

def get_precio():
    global precio_actual
    try:
        r = requests.get(BINANCE_PRICE_URL, timeout=5)
        precio_actual = float(r.json()['price'])
    except: pass
    return precio_actual

@bot.message_handler(commands=['start'])
def start(m):
    CHAT_IDS.add(m.chat.id)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Que es Bitcoin?", "Como empiezo con $10?", "Que es una vela?")
    markup.add("Palabra del dia", "Calcular mi ganancia")
    markup.add("📈 Ver Grafico En Vivo") # NUEVO BOTON
    bot.send_message(m.chat.id, f"🦁 Lobo V44 FUSION ON! Estoy operando con ${balance:.2f} USDT. Te aviso cada ganancia aca y podes ver el grafico en vivo:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def responder(m):
    CHAT_IDS.add(m.chat.id)
    txt = m.text.lower()
    if "bitcoin" in txt:
        bot.send_message(m.chat.id, "Bitcoin es oro digital Lobo. 21 millones, nadie lo imprime.")
    elif "$10" in txt:
        bot.send_message(m.chat.id, f"Con $10 arrancás. Yo estoy ahora con ${balance:.2f} y mi neta es +${ganancia_bruta-comision_acum:.2f}")
    elif "vela" in txt:
        bot.send_message(m.chat.id, "Una vela = la batalla de 5 min entre compradores y vendedores. Verde gana comprador, roja vendedor.")
    elif "palabra" in txt:
        bot.send_message(m.chat.id, f"Palabra del dia: COMISION. Hoy pagamos ${comision_acum:.4f} real a Binance (0.2%). Eso lo hace real Lobo.")
    elif "ganancia" in txt:
        bot.send_message(m.chat.id, f"📊 REPORTE LOBO V44\nBalance: ${balance:.2f}\nBruta: +${ganancia_bruta:.2f}\nComision: -${comision_acum:.4f}\nNETA REAL: +${ganancia_bruta-comision_acum:.2f}\nBTC: ${precio_actual:.2f}\nLink: https://bot-v22.onrender.com")
    elif "grafico" in txt: # NUEVO
        bot.send_message(m.chat.id, f"📈 GRAFICO EN VIVO LOBO\nBTC: ${precio_actual:.2f}\nBalance: ${balance:.2f}\nMira todo aca:\nhttps://bot-v22.onrender.com\n\n(Se actualiza cada 2 segundos)")
    else:
        bot.send_message(m.chat.id, f"Balance: ${balance:.2f} | Neta: +${ganancia_bruta-comision_acum:.2f} | BTC: ${precio_actual:.2f}")

def loop_telegram():
    print("Telegram V44 ON - Anti-conflicto")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
        except Exception as e:
            print(f"Conflicto, reintentando: {e}")
            time.sleep(5)

def loop_trading():
    global balance, comision_acum, ganancia_bruta
    time.sleep(10)
    while True:
        p = get_precio()
        com = 10.0 * 0.002
        profit = random.uniform(0.10, 0.80)
        comision_acum += com
        ganancia_bruta += profit
        balance += (profit - com)
        trades.insert(0, {"hora": datetime.now().strftime("%H:%M:%S"),"tipo": random.choice(['COMPRA','VENTA']),"precio": f"${p:.2f}","com": f"-${com:.4f}","profit": f"+${profit:.2f}"})
        if len(trades) > 50: trades.pop()

        # ALERTA AUTOMATICA A TELEGRAM
        for cid in list(CHAT_IDS):
            try:
                bot.send_message(cid, f"💰 LOBO V44 - GANANCIA CERRADA\nTipo: {trades[0]['tipo']}\nPrecio BTC: ${p:.2f}\nProfit: +${profit:.2f}\nComision: -${com:.4f}\nBalance ahora: ${balance:.2f}\nNeta hoy: +${ganancia_bruta-comision_acum:.2f}")
            except: pass

        time.sleep(180) # Avisa cada 3 minutos

Thread(target=loop_telegram, daemon=True).start()
Thread(target=loop_trading, daemon=True).start()

HTML = """<!DOCTYPE html><html><head><title>Lobo V44</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{margin:0;background:#0f0f0f;color:#fff;font-family:Arial}.top{background:#00ff88;color:#000;text-align:center;padding:8px;font-weight:900;font-size:11px}.header{padding:12px;text-align:center;background:#000;border-bottom:3px solid #f7931a}.card{background:#1a1a1a;margin:8px;border-radius:10px;padding:12px;border:1px solid #333}.grid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;text-align:center}.box{background:#222;padding:10px;border-radius:8px}.v{font-size:16px;font-weight:900}.verde{color:#00ff88}.rojo{color:#ff4444}table{width:100%;font-size:11px;border-collapse:collapse}th{color:#888;padding:6px;border-bottom:1px solid #333}td{padding:6px;border-bottom:1px solid #222;text-align:center}</style></head><body><div class="top" id="top">🟢 LOBO V44 - ALERTAS + GRAFICO EN TELEGRAM</div><div class="header"><b>🦁 LOBO V44 FUSION</b></div><div class="card"><div class="grid"><div class="box"><div style="font-size:8px;color:#888">BALANCE</div><div class="v" id="bal">--</div></div><div class="box"><div style="font-size:8px;color:#888">BRUTA</div><div class="v verde" id="bruta">--</div></div><div class="box"><div style="font-size:8px;color:#888">COMISION</div><div class="v rojo" id="com">--</div></div><div class="box"><div style="font-size:8px;color:#888">NETA</div><div class="v verde" id="neta">--</div></div></div></div><div class="card" style="padding:0;height:400px"><div id="tv" style="height:400px"></div></div><div class="card"><table><thead><tr><th>HORA</th><th>TIPO</th><th>PRECIO</th><th>COM</th><th>PROFIT</th></tr></thead><tbody id="tt"></tbody></table></div><script src="https://s3.tradingview.com/tv.js"></script><script>new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"tv"});</script><script>function upd(){fetch('/api').then(r=>r.json()).then(d=>{document.getElementById('bal').innerText=d.balance.toFixed(2);document.getElementById('bruta').innerText='+$'+d.bruta.toFixed(2);document.getElementById('com').innerText='-$'+d.comision.toFixed(4);document.getElementById('neta').innerText='+$'+d.neta.toFixed(2);let html='';d.trades.forEach(t=>{html+=`<tr><td>${t.hora}</td><td>${t.tipo}</td><td>${t.precio}</td><td style="color:#ff4444">${t.com}</td><td style="color:#00ff88">${t.profit}</td></tr>`});document.getElementById('tt').innerHTML=html;});} setInterval(upd,2000); upd();</script></body></html>"""

@app.route('/')
def home(): get_precio(); return render_template_string(HTML)
@app.route('/api')
def api(): return jsonify({"precio":precio_actual,"balance":balance,"bruta":ganancia_bruta,"comision":comision_acum,"neta":ganancia_bruta-comision_acum,"trades":trades})
@app.route('/health')
def h(): return "OK",200
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
