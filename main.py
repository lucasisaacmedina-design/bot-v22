import os, time, requests, threading, io, random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, Response

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
URL_BOT = "https://bot-v22.onrender.com"
SYMBOLS_LIST = ["BTCUSDT", "BNBUSDT"]

# HISTORIAL YA EN PRECIO REAL PARA QUE NO SALTE
def crear_historial(base, n=50):
    h = [base]
    for _ in range(n-1):
        h.append(h[-1] + random.uniform(-base*0.0005, base*0.0005))
    return h

estado_global = {
    "BTCUSDT": {"precio": 78645, "entry": 78645, "ema": 78645, "rsi": 54, "pnl": 0.0, "historial": crear_historial(78645)},
    "BNBUSDT": {"precio": 753.67, "entry": 753.67, "ema": 753.67, "rsi": 55, "pnl": 0.0, "historial": crear_historial(753.67)}
}

def enviar_grafico_telegram(symbol):
    try:
        d = estado_global[symbol]
        fig, ax = plt.subplots(figsize=(6, 2.6))
        fig.patch.set_facecolor('black')
        ax.set_facecolor('black')
        # Precio suave
        ax.plot(d["historial"], color='#00ff88', linewidth=1.8, label='Precio')
        # EMA 20 real, sin salto
        ema = []
        for i in range(len(d["historial"])):
            ventana = d["historial"][max(0,i-20):i+1]
            ema.append(sum(ventana)/len(ventana))
        ax.plot(ema, color='#ffaa00', linestyle='--', linewidth=1.1, label='EMA20')
        ax.set_title(f'{symbol} {d["precio"]:.2f} | EMA {d["ema"]:.0f} | RSI {d["rsi"]} | {d["pnl"]:+.2f}%', color='white', fontsize=8)
        ax.tick_params(colors='white', labelsize=6)
        ax.grid(True, alpha=0.08, color='white')
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', facecolor='black', dpi=120)
        plt.close(fig)
        buf.seek(0)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        requests.post(url, data={"chat_id": CHAT_ID, "caption": f"📈 LOBO V25 DUAL - {symbol}\n💵 ${d['precio']:.2f} | EMA ${d['ema']:.0f} | RSI {d['rsi']}\n💰 {d['pnl']:+.2f}% -> Obj +0.6% (${d['entry']*1.006:.2f})\n🔗 {URL_BOT}"}, files={"photo": buf}, timeout=15)
    except Exception as e:
        print(e)

def actualizar_datos_simbolo(symbol):
    try:
        precio = float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()["price"])
        d = estado_global[symbol]
        d["precio"] = precio
        d["historial"].append(precio)
        if len(d["historial"]) > 50: d["historial"].pop(0)
        d["ema"] = sum(d["historial"][-20:]) / len(d["historial"][-20:])
        d["pnl"] = ((precio - d["entry"]) / d["entry"]) * 100
        # CIERRE AUTOMATICO
        if d["pnl"] >= 0.6 or d["pnl"] <= -0.6:
            print(f"TP/SL {symbol} {d['pnl']:.2f}%")
            d["entry"] = precio
            d["pnl"] = 0.0
    except Exception as e:
        print(f"Err {symbol} {e}")

HTML_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOBO V25 DOBLE</title><style>
body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:10px}
.card{background:#1a1a1a;border-radius:12px;padding:12px;border:1px solid #333;max-width:750px;margin:10px auto}
.grafico{width:100%;height:300px;background:#000;border-radius:10px;margin-top:10px}
</style></head><body><div class="card">
<h3 style="margin:0">🐺 LOBO V25 DOBLE FIX</h3>
<div>BTC ${{ "%.2f"|format(btc.precio) }} | {{ "%+.2f"|format(btc.pnl) }}% | BNB ${{ "%.2f"|format(bnb.precio) }} | {{ "%+.2f"|format(bnb.pnl) }}%</div>
<img src="/chart?t={{ btc.precio }}" class="grafico">
</div></body></html>
"""

app = Flask(__name__)
@app.route("/")
def home(): return render_template_string(HTML_TEMPLATE, btc=estado_global["BTCUSDT"], bnb=estado_global["BNBUSDT"])
@app.route("/chart")
def chart():
    try:
        fig, (ax1, ax2) = plt.subplots(2,1, figsize=(7.5,3.5), sharex=True)
        fig.patch.set_facecolor('black')
        for ax in [ax1,ax2]: ax.set_facecolor('black'); ax.grid(True, alpha=0.1, color='white'); ax.tick_params(colors='white', labelsize=7)
        ax1.plot(estado_global["BTCUSDT"]["historial"], color='#00ff88', linewidth=1.8)
        ax1.set_ylabel('BTC $', color='#00ff88', fontsize=8)
        ax2.plot(estado_global["BNBUSDT"]["historial"], color='#ffaa00', linewidth=1.8)
        ax2.set_ylabel('BNB $', color='#ffaa00', fontsize=8)
        buf = io.BytesIO(); plt.tight_layout(); plt.savefig(buf, format='png', facecolor='black', dpi=110); plt.close(fig); buf.seek(0)
        return Response(buf.getvalue(), mimetype='image/png')
    except Exception as e: return str(e)

def loop():
    last=0
    while True:
        for s in SYMBOLS_LIST: actualizar_datos_simbolo(s)
        try:
            r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last+1}&timeout=2", timeout=10).json()
            if r.get("ok"):
                for u in r["result"]:
                    last=u["update_id"]
                    if str(u["message"]["chat"]["id"])==str(CHAT_ID) and "/estado" in u["message"].get("text","").lower():
                        for s in SYMBOLS_LIST: enviar_grafico_telegram(s); time.sleep(1)
        except: pass
        time.sleep(4)

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
