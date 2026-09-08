import os, time, requests, threading, io, random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, Response

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
URL_BOT = "https://bot-v22.onrender.com"
SYMBOLS_LIST = ["BTCUSDT", "BNBUSDT"]

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
        fig.patch.set_facecolor('black'); ax.set_facecolor('black')
        ax.plot(d["historial"], color='#00ff88', linewidth=1.8, label='Precio')
        ema = [sum(d["historial"][max(0,i-20):i+1])/len(d["historial"][max(0,i-20):i+1]) for i in range(len(d["historial"]))]
        ax.plot(ema, color='#ffaa00', linestyle='--', linewidth=1.1, label='EMA20')
        ax.set_title(f'{symbol} {d["precio"]:.2f} | EMA {d["ema"]:.0f} | RSI {d["rsi"]} | {d["pnl"]:+.2f}%', color='white', fontsize=8)
        ax.tick_params(colors='white', labelsize=6); ax.grid(True, alpha=0.08, color='white')
        buf = io.BytesIO(); plt.tight_layout(); plt.savefig(buf, format='png', facecolor='black', dpi=120); plt.close(fig); buf.seek(0)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        requests.post(url, data={"chat_id": CHAT_ID, "caption": f"📈 LOBO V26 TRADINGVIEW DUAL - {symbol}\n💵 ${d['precio']:.2f} | EMA ${d['ema']:.0f} | RSI {d['rsi']}\n💰 {d['pnl']:+.2f}% -> Obj +0.6% (${d['entry']*1.006:.2f})\n🔗 {URL_BOT}"}, files={"photo": buf}, timeout=15)
    except Exception as e: print(e)

def actualizar_datos_simbolo(symbol):
    try:
        precio = float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()["price"])
        d = estado_global[symbol]
        d["precio"] = precio; d["historial"].append(precio)
        if len(d["historial"]) > 50: d["historial"].pop(0)
        d["ema"] = sum(d["historial"][-20:]) / len(d["historial"][-20:])
        d["pnl"] = ((precio - d["entry"]) / d["entry"]) * 100
        if d["pnl"] >= 0.6 or d["pnl"] <= -0.6:
            print(f"TP/SL {symbol} {d['pnl']:.2f}%"); d["entry"] = precio; d["pnl"] = 0.0
    except Exception as e: print(f"Err {symbol} {e}")

HTML_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOBO V26 TRADINGVIEW</title><style>
body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:10px}
.card{background:#1a1a1a;border-radius:12px;padding:12px;border:1px solid #333;max-width:800px;margin:10px auto}
.titulo{color:#00ff88;font-weight:bold}
.obj{color:#ffaa00}
</style>
<script src="https://s3.tradingview.com/tv.js"></script>
</head><body>
<div class="card">
<h3 style="margin:0">🐺 LOBO V26 DUAL + TRADINGVIEW REAL</h3>
<div style="margin:8px 0; font-size:14px">
<span class="titulo">BTC</span> ${{ "%.2f"|format(btc.precio) }} | <span class="{{ 'obj' if btc.pnl>0 else '' }}">{{ "%+.2f"|format(btc.pnl) }}%</span> -> Obj ${{ "%.2f"|format(btc.entry*1.006) }} |
<span class="titulo">BNB</span> ${{ "%.2f"|format(bnb.precio) }} | <span class="{{ 'obj' if bnb.pnl>0 else '' }}">{{ "%+.2f"|format(bnb.pnl) }}%</span> -> Obj ${{ "%.2f"|format(bnb.entry*1.006) }}
</div>
</div>

<div class="card">
<div style="color:#888; font-size:12px; margin-bottom:5px">BTCUSDT - BINANCE - 5m - Real TradingView</div>
<div id="tv_btc" style="height:400px;"></div>
</div>

<div class="card">
<div style="color:#888; font-size:12px; margin-bottom:5px">BNBUSDT - BINANCE - 5m - Real TradingView</div>
<div id="tv_bnb" style="height:400px;"></div>
</div>

<script>
new TradingView.widget({
  "autosize": true, "height": 400, "symbol": "BINANCE:BTCUSDT",
  "interval": "5", "timezone": "America/Argentina/Buenos_Aires",
  "theme": "dark", "style": "1", "locale": "es",
  "studies": ["EMA@tv-basicstudies", "RSI@tv-basicstudies"],
  "container_id": "tv_btc"
});
new TradingView.widget({
  "autosize": true, "height": 400, "symbol": "BINANCE:BNBUSDT",
  "interval": "5", "timezone": "America/Argentina/Buenos_Aires",
  "theme": "dark", "style": "1", "locale": "es",
  "studies": ["EMA@tv-basicstudies", "RSI@tv-basicstudies"],
  "container_id": "tv_bnb"
});
</script>
</body></html>
"""

app = Flask(__name__)
@app.route("/")
def home(): return render_template_string(HTML_TEMPLATE, btc=estado_global["BTCUSDT"], bnb=estado_global["BNBUSDT"])

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
