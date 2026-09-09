import os, time, requests, threading
from flask import Flask, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

# --- CONFIG V28.6 PRUEBA ---
MONTO_BTC = 100.0
MONTO_BNB = 100.0
COMISION_TOTAL = 0.001 # 0.1% Binance con BNB aprox entrada+salida ya
TP_PORC = 0.25
SL_PORC = 0.8

estado = {
  "BTCUSDT": {"precio": 78368, "entry": 78368, "pnl": 0.0, "en_posicion": False},
  "BNBUSDT": {"precio": 749.06, "entry": 749.06, "pnl": 0.0, "en_posicion": False},
  "cuenta": {"balance": 200.0, "ganancia": 0.0, "ops": 0}, # $100 + $100 = $200
  "historial": []
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
<h3>🐺 LOBO V28.6 $100 BTC + $100 BNB NETO</h3>
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

                    monto = MONTO_BTC if s == "BTCUSDT" else MONTO_BNB
                    tp_neto = monto * (TP_PORC/100) - monto * COMISION_TOTAL # $0.15
                    sl_neto = monto * (SL_PORC/100) + monto * COMISION_TOTAL # $0.90

                    if estado[s]["pnl"] >= TP_PORC:
                        estado["cuenta"]["balance"] += tp_neto
                        estado["cuenta"]["ganancia"] += tp_neto
                        estado["cuenta"]["ops"] += 1
                        msg = f"✅ TP +{TP_PORC}% {s} ${p:.2f} +${tp_neto:.2f} NETO Bal ${estado['cuenta']['balance']:.2f}"
                        tg(msg)
                        estado["historial"].append(msg)
                        estado[s]["entry"] = p
                        estado[s]["pnl"] = 0
                        tg(f"🔄 RECOMPRA TP {s} ${p:.2f}")

                    if estado[s]["pnl"] <= -SL_PORC:
                        estado["cuenta"]["balance"] -= sl_neto
                        estado["cuenta"]["ganancia"] -= sl_neto
                        estado["cuenta"]["ops"] += 1
                        msg = f"❌ SL -{SL_PORC}% {s} ${p:.2f} -${sl_neto:.2f} NETO Bal ${estado['cuenta']['balance']:.2f}"
                        tg(msg)
                        estado["historial"].append(msg)
                        estado[s]["entry"] = p
                        estado[s]["pnl"] = 0
                        tg(f"🔄 RECOMPRA SL {s} ${p:.2f}")

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
                        tg(f"🟢 COMPRA V28.6\nBTC ${estado['BTCUSDT']['precio']:.2f} ($100)\nBNB ${estado['BNBUSDT']['precio']:.2f} ($100)\nTP +0.25% SL -0.8% NETO")
                    if "/balance" in txt:
                        tg(f"🏦 V28.6 $100+$100\nBal ${estado['cuenta']['balance']:.2f} Neta ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}\nBTC {estado['BTCUSDT']['pnl']:+.2f}% BNB {estado['BNBUSDT']['pnl']:+.2f}%\nTP neto +$0.15 SL neto -$0.90")
                    if "/historial" in txt:
                        if not estado["historial"]:
                            tg("📜 Todavía no hay ops Lobo 🐺")
                        else:
                            ultimos = estado["historial"][-10:]
                            texto = "📜 ÚLTIMOS 10 OPS V28.6 NETO:\n\n" + "\n".join(ultimos)
                            tg(texto)
        except Exception as e:
            print(e)
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
