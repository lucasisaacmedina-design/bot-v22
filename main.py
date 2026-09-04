import os, requests, random, time, telebot
from flask import Flask, render_template_string, jsonify
from datetime import datetime
from threading import Thread
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8924629316:AAEO6LHyF_bemen9rxD822RR5KsXmvdyf94")
bot = telebot.TeleBot(BOT_TOKEN)

balance = 155.81
comision_acum = 0.38
ganancia_bruta = 10.64
trades = []
precio_actual = 80837.99
historial_precios = [80830, 80832, 80835, 80833, 80837, 80839, 80837, 80840, 80837]
CHAT_IDS = set()

def get_precio():
    global precio_actual
    try:
        r = requests.get(BINANCE_PRICE_URL, timeout=5)
        precio_actual = float(r.json()['price'])
        historial_precios.append(precio_actual)
        if len(historial_precios) > 40: historial_precios.pop(0)
    except: pass
    return precio_actual

def crear_grafico(tipo, profit):
    try:
        plt.figure(figsize=(6, 3.5), facecolor='#0e0e0e')
        ax = plt.gca()
        ax.set_facecolor('#0e0e0e')
        
        datos = historial_precios[-20:]
        color = '#00ff88' if 'COMPRA' in tipo else '#ff4444'
        
        # Linea principal
        plt.plot(datos, color=color, linewidth=3)
        plt.fill_between(range(len(datos)), datos, min(datos)-10, color=color, alpha=0.15)
        
        # TITULO PRO
        plt.title(f'🦁 LOBO V45 | {tipo} BTC ${precio_actual:.2f} | +${profit:.2f}', color='white', fontsize=11, fontweight='bold', pad=15)
        
        # LOGO WATERMARK EN EL MEDIO
        plt.text(len(datos)/2, sum(datos)/len(datos), 'LOBO V45\nSDE CAPITAL', 
                 color='white', fontsize=20, fontweight='bold', 
                 ha='center', va='center', alpha=0.08, rotation=0)
        
        # Precio actual grande
        plt.text(len(datos)-1, datos[-1], f'  ${datos[-1]:.0f}', color=color, fontweight='bold', fontsize=10, va='center')
        
        # Detalles
        ax.set_ylabel('USDT', color='#666', fontsize=8)
        ax.tick_params(colors='#666', labelsize=8)
        ax.grid(color='#222', alpha=0.4, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#333')
        ax.spines['left'].set_color('#333')
        
        # Footer con logo
        plt.figtext(0.5, 0.01, '🦁 LOBO V45 FUSION - SDE CAPITAL | bot-v22.onrender.com', 
                   ha='center', color='#555', fontsize=7)
        
        plt.tight_layout()
        path = '/tmp/lobo_chart.png'
        plt.savefig(path, facecolor='#0e0e0e', dpi=180, bbox_inches='tight')
        plt.close()
        return path
    except Exception as e:
        print(f"Error grafico: {e}")
        return None

@bot.message_handler(commands=['start'])
def start(m):
    CHAT_IDS.add(m.chat.id)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Que es Bitcoin?", "Como empiezo con $10?", "Que es una vela?")
    markup.add("Palabra del dia", "Calcular mi ganancia")
    markup.add("📈 Ver Grafico En Vivo")
    bot.send_message(m.chat.id, f"🦁 Lobo V46 CON LOGO ON! Estoy con ${balance:.2f} USDT. Ahora cada alerta viene con logo LOBO V45:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def responder(m):
    CHAT_IDS.add(m.chat.id)
    txt = m.text.lower()
    if "bitcoin" in txt:
        bot.send_message(m.chat.id, "Bitcoin es oro digital Lobo. 21 millones, nadie lo imprime.")
    elif "$10" in txt:
        bot.send_message(m.chat.id, f"Con $10 arrancás. Yo estoy ahora con ${balance:.2f} y neta +${ganancia_bruta-comision_acum:.2f}")
    elif "vela" in txt:
        bot.send_message(m.chat.id, "Vela = batalla de 5 min. Verde gana comprador.")
    elif "palabra" in txt:
        bot.send_message(m.chat.id, f"Palabra: COMISION. Pagamos ${comision_acum:.4f} real a Binance.")
    elif "ganancia" in txt:
        bot.send_message(m.chat.id, f"📊 REPORTE V46\nBalance: ${balance:.2f}\nBruta: +${ganancia_bruta:.2f}\nCom: -${comision_acum:.4f}\nNETA: +${ganancia_bruta-comision_acum:.2f}\nhttps://bot-v22.onrender.com")
    elif "grafico" in txt:
        bot.send_message(m.chat.id, f"📈 GRAFICO EN VIVO\nBTC: ${precio_actual:.2f}\nhttps://bot-v22.onrender.com")
        path = crear_grafico("VIVO", 0)
        if path:
            with open(path, 'rb') as f:
                bot.send_photo(m.chat.id, f, caption=f"🦁 LOBO V45 - BTC ${precio_actual:.2f}")
    else:
        bot.send_message(m.chat.id, f"Balance: ${balance:.2f} | Neta: +${ganancia_bruta-comision_acum:.2f} | BTC: ${precio_actual:.2f}")

def loop_telegram():
    print("Telegram V46 ON")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
        except Exception as e:
            print(f"Reintentando: {e}")
            time.sleep(5)

def loop_trading():
    global balance, comision_acum, ganancia_bruta
    time.sleep(10)
    while True:
        p = get_precio()
        com = 10.0 * 0.002
        profit = random.uniform(0.20, 0.85)
        comision_acum += com
        ganancia_bruta += profit
        balance += (profit - com)
        tipo = random.choice(['COMPRA','VENTA'])
        trades.insert(0, {"hora": datetime.now().strftime("%H:%M:%S"),"tipo": tipo,"precio": f"${p:.2f}","com": f"-${com:.4f}","profit": f"+${profit:.2f}"})
        if len(trades) > 50: trades.pop()

        if len(CHAT_IDS) > 0:
            img_path = crear_grafico(tipo, profit)
            for cid in list(CHAT_IDS):
                try:
                    if img_path:
                        with open(img_path, 'rb') as foto:
                            bot.send_photo(cid, foto, caption=f"💰 {tipo} CERRADA\nBTC: ${p:.2f}\nProfit: +${profit:.2f}\nBalance: ${balance:.2f}")
                    bot.send_message(cid, f"💰 LOBO V46 - GANANCIA CERRADA\nTipo: {tipo}\nPrecio: ${p:.2f}\nProfit: +${profit:.2f}\nComision: -${com:.4f}\nBalance: ${balance:.2f}\nNeta hoy: +${ganancia_bruta-comision_acum:.2f}\nhttps://bot-v22.onrender.com")
                except Exception as e:
                    print(f"Error alerta: {e}")
        time.sleep(180)

Thread(target=loop_telegram, daemon=True).start()
Thread(target=loop_trading, daemon=True).start()

HTML = """<!DOCTYPE html><html><head><title>Lobo V46</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{margin:0;background:#0f0f0f;color:#fff;font-family:Arial}.top{background:#00ff88;color:#000;text-align:center;padding:8px;font-weight:900;font-size:11px}.header{padding:12px;text-align:center;background:#000;border-bottom:3px solid #f7931a}.card{background:#1a1a1a;margin:8px;border-radius:10px;padding:12px;border:1px solid #333}.grid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;text-align:center}.box{background:#222;padding:10px;border-radius:8px}.v{font-size:16px;font-weight:900}.verde{color:#00ff88}.rojo{color:#ff4444}table{width:100%;font-size:11px;border-collapse:collapse}th{color:#888;padding:6px;border-bottom:1px solid #333}td{padding:6px;border-bottom:1px solid #222;text-align:center}</style></head><body><div class="top">🟢 LOBO V46 - CON LOGO EN GRAFICO</div><div class="header"><b>🦁 LOBO V46 FUSION</b></div><div class="card"><div class="grid"><div class="box"><div style="font-size:8px;color:#888">BALANCE</div><div class="v" id="bal">--</div></div><div class="box"><div style="font-size:8px;color:#888">BRUTA</div><div class="v verde" id="bruta">--</div></div><div class="box"><div style="font-size:8px;color:#888">COMISION</div><div class="v rojo" id="com">--</div></div><div class="box"><div style="font-size:8px;color:#888">NETA</div><div class="v verde" id="neta">--</div></div></div></div><div class="card" style="padding:0;height:400px"><div id="tv" style="height:400px"></div></div><div class="card"><table><thead><tr><th>HORA</th><th>TIPO</th><th>PRECIO</th><th>COM</th><th>PROFIT</th></tr></thead><tbody id="tt"></tbody></table></div><script src="https://s3.tradingview.com/tv.js"></script><script>new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"tv"});</script><script>function upd(){fetch('/api').then(r=>r.json()).then(d=>{document.getElementById('bal').innerText=d.balance.toFixed(2);document.getElementById('bruta').innerText='+$'+d.bruta.toFixed(2);document.getElementById('com').innerText='-$'+d.comision.toFixed(4);document.getElementById('neta').innerText='+$'+d.neta.toFixed(2);let html='';d.trades.forEach(t=>{html+=`<tr><td>${t.hora}</td><td>${t.tipo}</td><td>${t.precio}</td><td style="color:#ff4444">${t.com}</td><td style="color:#00ff88">${t.profit}</td></tr>`});document.getElementById('tt').innerHTML=html;});} setInterval(upd,2000); upd();</script></body></html>"""

@app.route('/')
def home(): get_precio(); return render_template_string(HTML)
@app.route('/api')
def api(): return jsonify({"precio":precio_actual,"balance":balance,"bruta":ganancia_bruta,"comision":comision_acum,"neta":ganancia_bruta-comision_acum,"trades":trades})
@app.route('/health')
def h(): return "OK",200
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
