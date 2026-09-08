import os, time, requests, threading, io, datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
URL_BOT = "https://bot-v22.onrender.com"

# CONFIG SCALPING FIJO DUAL
TP = 0.006 # 0.6%
SL = 0.006 # 0.6%
EMA_PERIODO = 50
RSI_PERIODO = 14
SYMBOLS = ["BTCUSDT", "BNBUSDT"]

app = Flask(__name__)

estado_global = {
    "BTCUSDT": {"entry": 78085.0, "qty": 0.000189, "capital": 0.0, "trades": 1, "wins": 1, "pnl": -0.04, "pnl_pct": -0.27, "precio": 78085, "ema": 78336, "rsi": 42},
    "BNBUSDT": {"entry": 640.0, "qty": 0.02, "capital": 0.0, "trades": 1, "wins": 1, "pnl": 0.1, "pnl_pct": 0.15, "precio": 640, "ema": 642, "rsi": 45}
}

def binance_klines(symbol, limit=200):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=5m&limit={limit}"
        data = requests.get(url, timeout=10).json()
        closes = [float(k[4]) for k in data]
        return closes
    except:
        return [estado_global[symbol]["precio"]]*limit

def calcular_ema(closes, periodo):
    ema = closes[0]
    k = 2/(periodo+1)
    for c in closes[1:]:
        ema = c*k + ema*(1-k)
    return ema

def calcular_rsi(closes, periodo=14):
    try:
        deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
        gains = [d if d>0 else 0 for d in deltas[-periodo:]]
        losses = [-d if d<0 else 0 for d in deltas[-periodo:]]
        avg_gain = sum(gains)/periodo
        avg_loss = sum(losses)/periodo + 0.000001
        rs = avg_gain/avg_loss
        rsi = 100 - (100/(1+rs))
        return rsi
    except:
        return 50

def actualizar_simbolo(symbol):
    closes = binance_klines(symbol, 200)
    precio = closes[-1]
    ema = calcular_ema(closes, EMA_PERIODO)
    rsi = calcular_rsi(closes, RSI_PERIODO)
    estado_global[symbol]["precio"] = precio
    estado_global[symbol]["ema"] = ema
    estado_global[symbol]["rsi"] = rsi
    estado_global[symbol]["closes"] = closes
    return closes, precio, ema, rsi

def crear_grafico_lobo(symbol, closes, ema, precio, rsi):
    plt.figure(figsize=(8,4), facecolor='#0e0e0e')
    ax = plt.gca()
    ax.set_facecolor('#0e0e0e')
    plt.plot(closes[-100:], color='#00ff88', linewidth=1.8, label='Precio')
    ema_line = []
    e = closes[0]
    k = 2/(EMA_PERIODO+1)
    for c in closes:
        e = c*k + e*(1-k)
        ema_line.append(e)
    plt.plot(ema_line[-100:], color='orange', linestyle='--', linewidth=1.2, label=f'EMA{EMA_PERIODO}')
    plt.title(f'{symbol} ${precio:.2f} | EMA{EMA_PERIODO} ${ema:.2f} | RSI {rsi:.0f} | SCALPING 0.6%', color='white', fontsize=10)
    plt.legend(facecolor='#1a1a1a', edgecolor='gray', fontsize=7, labelcolor='white')
    plt.tick_params(colors='gray', labelsize=7)
    plt.grid(color='#222222', linestyle='--', linewidth=0.5)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='#0e0e0e', bbox_inches='tight', dpi=150)
    plt.close()
    buf.seek(0)
    return buf

def send_text(text):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=15)
    except Exception as e:
        print(f"Error send_text: {e}")

def send_photo(buf, caption):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": ("grafico.png", buf, "image/png")}, timeout=25)
    except Exception as e:
        print(f"Error send_photo: {e}")

def loop_principal():
    last_update_id = 0
    print("LOOP DUAL BTC+BNB INICIADO")
    while True:
        try:
            # 1. Actualizar datos de ambos
            for sym in SYMBOLS:
                actualizar_simbolo(sym)

            # 2. Manejar /estado
            try:
                url_updates = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=10"
                r = requests.get(url_updates, timeout=15).json()
                for upd in r.get("result", []):
                    last_update_id = upd["update_id"]
                    mensaje = upd.get("message", {}).get("text", "")
                    if "/estado" in mensaje:
                        texto = f"💰 ESTADO LOBO V25 DUAL SCALPING 0.6% - {datetime.datetime.now().strftime('%H:%M:%S')}\n\n"
                        total_global = 0
                        for sym in SYMBOLS:
                            d = estado_global[sym]
                            pct = ((d["precio"] - d["entry"]) / d["entry"] * 100) if d["entry"] else 0
                            objetivo = d["entry"] * (1+TP)
                            total_global += d["qty"] * d["precio"]
                            texto += f"--- {sym} ---\n"
                            texto += f"💵 Capital: ${d['capital']:.2f}\n"
                            texto += f"₿ Qty: {d['qty']}\n"
                            texto += f"📈 Precio: ${d['precio']:.2f} | EMA{EMA_PERIODO}: ${d['ema']:.2f} | RSI: {d['rsi']:.0f}\n"
                            texto += f"💼 Entry: ${d['entry']:.2f} | Ahora: {pct:+.2f}%\n"
                            texto += f"💰 Vendiendo: {pct:+.2f}% -> Objetivo +0.6% (${objetivo:.2f}) | SL -0.6%\n\n"
                        texto += f"💼 Total Cuenta: ${total_global:.2f}\n"
                        texto += f"TP +0.6% | SL -0.6% | EMA{EMA_PERIODO} + RSI SCALPING DUAL\n"
                        texto += f"🔗 {URL_BOT}"
                        send_text(texto)
            except Exception as e:
                print(f"Error telegram check: {e}")

            # 3. Envio automatico cada 5 minutos con grafico
            if int(time.time()) % 300 < 12:
                for sym in SYMBOLS:
                    d = estado_global[sym]
                    closes = d.get("closes", [d["precio"]]*100)
                    pct = ((d["precio"] - d["entry"]) / d["entry"] * 100) if d["entry"] else 0
                    objetivo = d["entry"] * (1+TP)
                    buf = crear_grafico_lobo(sym, closes, d["ema"], d["precio"], d["rsi"])
                    caption = f"📈 LOBO V25 DUAL SCALPING 0.6%\n{sym}: ${d['precio']:.2f} | EMA{EMA_PERIODO} ${d['ema']:.0f}\n💰 Vendiendo: {pct:+.2f}% -> Obj +0.6% (${objetivo:.2f}) | SL -0.6%\nTP +0.6% | SL -0.6% | EMA{EMA_PERIODO}+RSI {d['rsi']:.0f}\n🔗 {URL_BOT}"
                    send_photo(buf, caption)
                time.sleep(40)

            time.sleep(4)

        except Exception as e:
            print(f"Error loop principal: {e}")
            time.sleep(10)

HTML_DASH = """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lobo V25 DUAL</title>
<style>
body{background:#0e0e0e;color:white;font-family:Arial;margin:0;padding:10px}
.card{background:#1a1a1a;border:1px solid #333;padding:12px;border-radius:10px;margin-bottom:10px}
.chart{height:750px;border:1px solid #333;border-radius:10px;overflow:hidden}
#tv{height:750px}
.badge{padding:4px 8px;border-radius:6px;font-size:12px}
.green{background:#00ff8844;color:#00ff88}
.orange{background:#ffaa0044;color:orange}
</style></head><body>
<h2>🐺 LOBO V25 DUAL BTC+BNB SCALPING 0.6%</h2>
<div style="display:flex;gap:10px;flex-wrap:wrap">
{% for sym,data in estado.items() %}
<div class="card">
<b>{{sym}}</b> <span class="badge green">SCALPING 0.6%</span><br>
Precio: ${{ "%.2f"|format(data.precio) }} | EMA{{ema}}: ${{ "%.2f"|format(data.ema) }} | RSI: {{ "%.0f"|format(data.rsi) }}<br>
Entry: ${{ data.entry }} | P&L: {{ "%.2f"|format(((data.precio-data.entry)/data.entry*100)) }}%<br>
Qty: {{data.qty}}
</div>
{% endfor %}
</div>
<div class="chart"><div id="tv"></div></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"tv","height":750})
</script>
<p><a href="{{url}}" style="color:gray">{{url}}</a> | Actualizado: {{hora}}</p>
</body></html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_DASH, estado=estado_global, ema=EMA_PERIODO, url=URL_BOT, hora=datetime.datetime.now().strftime("%H:%M:%S"))

# Iniciar hilo
threading.Thread(target=loop_principal, daemon=True).start()

if __name__ == "__main__":
    send_text("🐺 LoboBot V25 DUAL COMPLETO BTC+BNB SCALPING 0.6% + GRAFICO + FORMATO LINDO - VIVO")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
