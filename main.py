import os, time, requests, threading, io, datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, Response
import random

# --- 1. CONFIG RENDER (tus nombres exactos de la foto) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
BINANCE_KEY = os.environ.get("BINANCE_TESTNET_API_KEY", "")
BINANCE_SECRET = os.environ.get("BINANCE_TESTNET_API_SECRET", "")
URL_BOT = "https://bot-v22.onrender.com"
SYMBOLS_LIST = ["BTCUSDT", "BNBUSDT"]

# --- 2. ESTADO GLOBAL ---
estado_global = {
    "BTCUSDT": {"precio": 78645, "entry": 78079, "ema": 77140, "rsi": 54, "pnl": 0.72, "historial": []},
    "BNBUSDT": {"precio": 753.67, "entry": 639.78, "ema": 640, "rsi": 62, "pnl": 17.76, "historial": []}
}
total_cuenta = 29.94
estado_global["BTCUSDT"]["historial"] = [78000 + random.uniform(-200,200) for _ in range(50)]
estado_global["BNBUSDT"]["historial"] = [640 + random.uniform(-10,10) for _ in range(50)]

def enviar_texto_telegram(texto):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": texto}, timeout=10)
    except Exception as e:
        print(f"Telegram send error {e}")

def actualizar_datos_simbolo(symbol):
    try:
        # Precio real Binance
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()
        precio = float(r["price"])
        d = estado_global[symbol]
        d["precio"] = precio
        d["historial"].append(precio)
        if len(d["historial"]) > 100: d["historial"].pop(0)
        # Simula EMA, RSI y PnL para dashboard
        d["ema"] = sum(d["historial"][-50:]) / min(50, len(d["historial"]))
        d["pnl"] = ((d["precio"] - d["entry"]) / d["entry"]) * 100
        # TP +0.6% SL -0.6%
        if d["pnl"] >= 0.6:
            enviar_texto_telegram(f"✅ TP ALCANZADO {symbol} {d['pnl']:.2f}% -> Vendiendo")
            d["entry"] = d["precio"]
        if d["pnl"] <= -0.6:
            enviar_texto_telegram(f"🛑 SL ALCANZADO {symbol} {d['pnl']:.2f}% -> Vendiendo")
            d["entry"] = d["precio"]
    except Exception as e:
        print(f"Error actualizando {symbol}: {e}")

# --- 3. DASHBOARD 750PX CON GRAFICO NEGRO (TU FOTO) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOBO V25 DUAL</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:10px}
.card{background:#1a1a1a;border-radius:12px;padding:12px;margin-bottom:10px;border:1px solid #333;max-width:750px;margin:10px auto}
.top{display:flex;justify-content:space-between;align-items:center}
.pill{background:#222;padding:4px 10px;border-radius:20px;font-size:12px}
.pos{color:#00ff88;font-weight:bold}.neg{color:#ff4444;font-weight:bold}
.grafico{width:100%;height:280px;background:#000;border-radius:10px;margin-top:10px;display:block}
.boton{display:block;background:#00ff88;color:#000;text-align:center;padding:12px;border-radius:10px;text-decoration:none;font-weight:bold;margin-top:10px}
</style></head><body>
<div class="card">
<div class="top"><h3 style="margin:0">🐺 LOBO V25 DUAL</h3><span class="pill">TP +0.6% | SL -0.6%</span></div>
<div style="margin-top:10px">💼 Total: ${{ "%.2f"|format(total) }} | BTC ${{ "%.2f"|format(btc.precio) }} | BNB ${{ "%.2f"|format(bnb.precio) }}</div>
<div style="display:flex;gap:10px;margin-top:10px">
<div style="flex:1;background:#222;padding:10px;border-radius:10px">
BTCUSDT<br>Entry: ${{ "%.2f"|format(btc.entry) }}<br>
<span class="{{ 'pos' if btc.pnl>=0 else 'neg' }}">{{ "%+.2f"|format(btc.pnl) }}%</span> Vendiendo -> Obj +0.6% (${{ "%.2f"|format(btc.entry*1.006) }})
</div>
<div style="flex:1;background:#222;padding:10px;border-radius:10px">
BNBUSDT<br>Entry: ${{ "%.2f"|format(bnb.entry) }}<br>
<span class="{{ 'pos' if bnb.pnl>=0 else 'neg' }}">{{ "%+.2f"|format(bnb.pnl) }}%</span> Vendiendo -> Obj +0.6% (${{ "%.2f"|format(bnb.entry*1.006) }})
</div>
</div>
<img src="/chart" class="grafico">
<a class="boton" href="https://t.me/LoboBot22_SinCulpa_bot">📲 Ver en Telegram /estado</a>
</div>
</body></html>
"""

app = Flask(__name__)

@app.route("/")
def home():
    btc = estado_global["BTCUSDT"]
    bnb = estado_global["BNBUSDT"]
    return render_template_string(HTML_TEMPLATE, btc=btc, bnb=bnb, total=total_cuenta)

@app.route("/chart")
def chart():
    try:
        fig, ax = plt.subplots(figsize=(7.5, 2.8))
        fig.patch.set_facecolor('#000000')
        ax.set_facecolor('#000000')
        ax.plot(estado_global["BTCUSDT"]["historial"], color='#00ff88', label='BTC')
        ax.plot(estado_global["BNBUSDT"]["historial"], color='#ffaa00', label='BNB')
        ax.tick_params(colors='white')
        ax.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='#000000')
        plt.close(fig)
        buf.seek(0)
        return Response(buf.getvalue(), mimetype='image/png')
    except Exception as e:
        return str(e)

def loop_principal_lobo():
    last_update_id = 0
    print("LOOP LOBO V25 DUAL")
    while True:
        try:
            for sym in SYMBOLS_LIST:
                actualizar_datos_simbolo(sym)
            try:
                url_updates = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=2"
                resp = requests.get(url_updates, timeout=10).json()
                if resp.get("ok"):
                    for upd in resp.get("result", []):
                        last_update_id = upd["update_id"]
                        msg = upd.get("message", {})
                        texto = msg.get("text", "")
                        chat = str(msg.get("chat", {}).get("id", ""))
                        if chat == str(CHAT_ID) and "/estado" in texto.lower():
                            hora_now = datetime.datetime.now().strftime('%H:%M:%S')
                            txt = f"💰 ESTADO LOBO V25 DUAL COMPLETO - {hora_now}\n\n"
                            for s in SYMBOLS_LIST:
                                d = estado_global[s]
                                txt += f"{s}: ${d['precio']:.2f} EMA50 ${d['ema']:.0f} RSI {d['rsi']:.0f}\n"
                                txt += f"💰 Vendiendo: {d['pnl']:+.2f}% -> Obj +0.6% (${d['entry']*1.006:.2f})\n\n"
                            txt += f"💼 Total Cuenta: ${total_cuenta:.2f}\n🔗 {URL_BOT}"
                            enviar_texto_telegram(txt)
            except Exception as e:
                print(f"Telegram error: {e}")
            time.sleep(3)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(5)

threading.Thread(target=loop_principal_lobo, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
