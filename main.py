import os, time, requests, threading
from flask import Flask, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

estado = {
  "BTCUSDT": {"precio": 78626, "entry": 78626, "pnl": 0.0, "en_posicion": False},
  "BNBUSDT": {"precio": 753.67, "entry": 753.67, "pnl": 0.0, "en_posicion": False},
  "cuenta": {"balance": 1000.0, "ganancia": 0.0, "ops": 0}
}

def get_precio(s):
    try:
        if s == "BTCUSDT":
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5).json()
            return float(r["bitcoin"]["usd"])
        else:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd", timeout=5).json()
            return float(r["binancecoin"]["usd"])
    except:
        return None

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except:
        pass

HTML = """<html><head><meta name="viewport" content="width=device-width"><script src="https://s3.tradingview.com/tv.js"></script></head>
<body style="background:#0a0a0a;color:#fff;font-family:Arial;padding:10px">
<div style="background:#1a1a1a;padding:12px;border-radius:12px;max-width:900px;margin:auto">
<h3>🐺 LOBO V28.2 - 87 LINEAS AUTO</h3>
<div>Bal ${{ "%.2f"|format(cuenta.balance) }} | Neta ${{ "%+.2f"|format(cuenta.ganancia) }} | Ops {{ cuenta.ops }}</div>
<div>BTC ${{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% {{ "🟢 EN POS" if btc.en_posicion else "🔴 ESPERANDO" }} | BNB ${{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}%</div>
</div>
<div style="max-width:900px;margin:10px auto"><div id="tv_btc" style="height:400px"></div></div>
<div style="max-width:900px;margin:10px auto"><div id="tv_bnb" style="height:400px"></div></div>
<script>
new TradingView.widget({"autosize":true,"height":400,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"tv_btc"});
new TradingView.widget({"autosize":true,"height":400,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","container_id":"tv_bnb"});
</script></body></html>"""

app = Flask(__name__)

@app.route("/")
def home():
    return render_template_string(HTML, btc=estado["BTCUSDT"], bnb=estado["BNBUSDT"], cuenta=estado["cuenta"])

def loop():
    last = 0
    while True:
        for s in ["BTCUSDT", "BNBUSDT"]:
            p = get_precio(s)
            if p:
                estado[s]["precio"] = p
                if estado[s]["en_posicion"]:
                    estado[s]["pnl"] = ((p - estado[s]["entry"]) / estado[s]["entry"]) * 100
                    if estado[s]["pnl"] >= 0.6:
                        estado["cuenta"]["balance"] += 0.18
                        estado["cuenta"]["ganancia"] += 0.18
                        estado["cuenta"]["ops"] += 1
                        tg(f"✅ TP +0.6% {s} ${p:.2f} +$0.18 Bal ${estado['cuenta']['balance']:.2f}")
                        estado[s]["en_posicion"] = False
                        estado[s]["pnl"] = 0
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last+1}&timeout=3", timeout=10).json()
            if r.get("ok"):
                for u in r["result"]:
                    last = u["update_id"]
                    if "message" not in u: continue
                    if str(u["message"]["chat"]["id"])!= str(CHAT_ID): continue
                    txt = u["message"].get("text", "").lower()
                    if "/comprar" in txt:
                        for s in ["BTCUSDT", "BNBUSDT"]:
                            p = get_precio(s) or estado[s]["precio"]
                            estado[s]["entry"] = p
                            estado[s]["en_posicion"] = True
                            estado[s]["pnl"] = 0
                        tg(f"🟢 COMPRA 87 LINEAS\nBTC ${estado['BTCUSDT']['precio']:.2f}\nBNB ${estado['BNBUSDT']['precio']:.2f}\nTP +0.6% ON")
                    if "/balance" in txt:
                        tg(f"🏦 V28.2 87L\nBal ${estado['cuenta']['balance']:.2f} Neta ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}")
        except Exception as e:
            print(e)
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
