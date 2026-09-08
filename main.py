import os, time, requests, threading, io, datetime, random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, Response

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
URL_BOT = "https://bot-v22.onrender.com"
SYMBOLS_LIST = ["BTCUSDT", "BNBUSDT"]

def crear_historial_suave(base, variacion, n=50):
    hist = []
    val = base
    for i in range(n):
        val += random.uniform(-variacion, variacion)
        hist.append(val)
    return hist

estado_global = {
    "BTCUSDT": {"precio": 78645, "entry": 78079, "ema": 77140, "rsi": 54, "pnl": 0.72, "historial": crear_historial_suave(78000, 25)},
    "BNBUSDT": {"precio": 753.67, "entry": 639.78, "ema": 640, "rsi": 62, "pnl": 17.76, "historial": crear_historial_suave(640, 1.2)}
}

def enviar_grafico_telegram(symbol):
    try:
        fig, ax = plt.subplots(figsize=(6, 2.5))
        fig.patch.set_facecolor('black')
        ax.set_facecolor('black')
        d = estado_global[symbol]
        ax.plot(d["historial"], color='#00ff88', linewidth=1.8)
        ema_vals = [sum(d["historial"][max(0,i-20):i+1])/min(20,i+1) for i in range(len(d["historial"]))]
        ax.plot(ema_vals, color='#ffaa00', linestyle='--', linewidth=1.2)
        ax.set_title(f'{symbol} {d["precio"]:.2f} | EMA50 {d["ema"]:.0f} | RSI {d["rsi"]:.0f} | {d["pnl"]:+.2f}%', color='white', fontsize=8)
        ax.tick_params(colors='white', labelsize=6)
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', facecolor='black', dpi=120)
        plt.close(fig)
        buf.seek(0)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        requests.post(url, data={"chat_id": CHAT_ID, "caption": f"📈 LOBO V25 DUAL - {symbol}\n💵 ${d['precio']:.2f} | EMA ${d['ema']:.0f} | RSI {d['rsi']:.0f}\n💰 {d['pnl']:+.2f}% -> Obj +0.6% (${d['entry']*1.006:.2f})\n🔗 {URL_BOT}"}, files={"photo": buf}, timeout=15)
    except: pass

def actualizar_datos_simbolo(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()
        precio = float(r["price"])
        d = estado_global[symbol]
        d["precio"] = precio
        d["historial"].append(precio)
        if len(d["historial"]) > 100: d["historial"].pop(0)
        d["ema"] = sum(d["historial"][-50:]) / min(50, len(d["historial"]))
        d["pnl"] = ((d["precio"] - d["entry"]) / d["entry"]) * 100
        if d["pnl"] >= 0.6 or d["pnl"] <= -0.6:
            d["entry"] = d["precio"]
    except: pass

HTML_TEMPLATE = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOBO V25 DOBLE</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:10px}
.card{background:#1a1a1a;border-radius:12px;padding:12px;border:1px solid #333;max-width:750px;margin:10px auto}
.top{display:flex;justify-content:space-between}
.pill{background:#222;padding:4px 10px;border-radius:20px;font-size:12px}
.pos{color:#00ff88;font-weight:bold}.neg{color:#ff4444}
.grafico{width:100%;height:300px;background:#000;border-radius:10px;margin-top:10px;display:block}
.boton{display:block;background:#00ff88;color:#000;text-align:center;padding:12px;border-radius:10px;text-decoration:none;font-weight:bold;margin-top:10px}
</style></head><body>
<div class="card">
<div class="top"><h3 style="margin:0">🐺 LOBO V25 DOBLE</h3><span class="pill">TP +0.6% | SL -0.6%</span></div>
<div style="margin-top:10px">💼 Total: ${{ "%.2f"|format(29.94) }} | BTC ${{ "%.2f"|format(btc.precio) }} | BNB ${{ "%.2f"|format(bnb.precio) }}</div>
<div style="display:flex;gap:10px;margin-top:10px">
<div style="flex:1;background:#222;padding:10px;border-radius:10px;font-size:13px">BTCUSDT: ${{ "%.2f"|format(btc.entry) }}<br><span class="{{ 'pos' if btc.pnl>=0 else 'neg' }}">{{ "%+.2f"|format(btc.pnl) }}% Vendiendo -> Obj +0.6%</span></div>
<div style="flex:1;background:#222;padding:10px;border-radius:10px;font-size:13px">BNBUSDT: ${{ "%.2f"|format(bnb.entry) }}<br><span class="{{ 'pos' if bnb.pnl>=0 else 'neg' }}">{{ "%+.2f"|format(bnb.pnl) }}% Vendiendo</span></div>
</div>
<img src="/chart?t={{ btc.precio }}" class="grafico">
<a class="boton" href="https://t.me/LoboBot22_SinCulpa_bot">📲 Ver en Telegram /estado</a>
</div>
</body></html>
"""

app = Flask(__name__)
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, btc=estado_global["BTCUSDT"], bnb=estado_global["BNBUSDT"])

@app.route("/chart")
def chart():
    try:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.5, 3.5), sharex=True)
        fig.patch.set_facecolor('#000000')
        for ax in [ax1, ax2]: ax.set_facecolor('#000000')

        ax1.plot(estado_global["BTCUSDT"]["historial"], color='#00ff88', linewidth=1.8)
        ax1.set_ylabel('BTC $', color='#00ff88', fontsize=8)
        ax1.tick_params(colors='white', labelsize=7)
        ax1.grid(True, alpha=0.1, color='white')

        ax2.plot(estado_global["BNBUSDT"]["historial"], color='#ffaa00', linewidth=1.8)
        ax2.set_ylabel('BNB $', color='#ffaa00', fontsize=8)
        ax2.tick_params(colors='white', labelsize=7)
        ax2.grid(True, alpha=0.1, color='white')

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='#000000', dpi=110)
        plt.close(fig)
        buf.seek(0)
        return Response(buf.getvalue(), mimetype='image/png')
    except Exception as e:
        return str(e)

def loop_principal_lobo():
    last_update_id = 0
    while True:
        try:
            for sym in SYMBOLS_LIST:
                actualizar_datos_simbolo(sym)
            try:
                resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=2", timeout=10).json()
                if resp.get("ok"):
                    for upd in resp.get("result", []):
                        last_update_id = upd["update_id"]
                        texto = upd.get("message", {}).get("text", "")
                        chat = str(upd.get("message", {}).get("chat", {}).get("id", ""))
                        if chat == str(CHAT_ID) and "/estado" in texto.lower():
                            for s in SYMBOLS_LIST:
                                enviar_grafico_telegram(s)
                                time.sleep(1)
            except: pass
            time.sleep(4)
        except: time.sleep(5)

threading.Thread(target=loop_principal_lobo, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
