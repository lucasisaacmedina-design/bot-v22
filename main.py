import time, requests, os
from flask import Flask, render_template_string
import threading

app = Flask(__name__)

CAPITAL_INICIAL = 30.0
CAPITAL = CAPITAL_INICIAL
BTC = 0.0
TRADES = []
PROFIT_TOTAL = 0.0

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_ID = os.environ.get("TELEGRAM_ID")

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_ID, "text": msg}, timeout=5)
    except:
        pass

def get_btc_price():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5)
        return float(r.json()['price'])
    except:
        return None

def estrategia_lobo(price):
    global CAPITAL, BTC, PROFIT_TOTAL
    if not TRADES:
        btc_c = (CAPITAL * 0.5) / price
        BTC = btc_c
        CAPITAL -= btc_c * price
        TRADES.append({"tipo":"COMPRA","precio":price,"profit":0})
        send_telegram(f"🐺 LoboBot22 REAL INICIADO\n🟢 COMPRA 50%\nPrecio: ${price:,.2f}")
        return

    ultimo = TRADES[-1]['precio']
    
    # STOP LOSS 3% - salvavidas
    if BTC > 0 and price < ultimo * 0.97:
        btc_v = BTC
        perdida = btc_v * price - btc_v * ultimo
        CAPITAL += btc_v * price
        BTC = 0
        PROFIT_TOTAL += perdida
        TRADES.append({"tipo":"STOP LOSS 3%","precio":price,"profit":perdida})
        send_telegram(f"🐺 LoboBot22\n🛑 STOP LOSS -3%\nVendido todo a ${price:,.2f}\nPerdida: ${perdida:.2f}\nTotal: ${PROFIT_TOTAL:.2f}")
        return

    # COMPRA -1%
    if price < ultimo * 0.99 and CAPITAL > 5:
        btc_c = (CAPITAL * 0.3) / price
        BTC += btc_c
        CAPITAL -= btc_c * price
        TRADES.append({"tipo":"COMPRA -1%","precio":price,"profit":0})
        send_telegram(f"🐺 LoboBot22\n🟢 COMPRA -1%\nPrecio: ${price:,.2f}")
    
    # VENTA +1.5%
    elif price > ultimo * 1.015 and BTC > 0.00001:
        btc_v = BTC * 0.5
        ganancia = btc_v * price - btc_v * ultimo
        CAPITAL += btc_v * price
        BTC -= btc_v
        PROFIT_TOTAL += ganancia
        TRADES.append({"tipo":"VENTA +1.5%","precio":price,"profit":ganancia})
        send_telegram(f"🐺 LoboBot22\n🔴 VENTA +1.5%\nPrecio: ${price:,.2f}\nProfit: ${ganancia:.2f}\nTotal: ${PROFIT_TOTAL:.2f}")

def loop_caza():
    send_telegram("🐺 LoboBot22 PAPEL REAL V22\nEstrategia: Compra -1% / Venta +1.5% / Stop -3%\nPrecio REAL Binance. Iniciado ✅")
    while True:
        price = get_btc_price()
        if price:
            estrategia_lobo(price)
        time.sleep(30)

threading.Thread(target=loop_caza, daemon=True).start()

HTML = """
<h1>LoboBot22 V22 REAL</h1>
<p>Estrategia: -1% / +1.5% / Stop -3%</p>
<p>BTC REAL: ${{price}} | Capital: ${{capital}} | BTC: {{btc}} | Profit: ${{profit}} | Total: ${{total}}</p>
<p>{{trades}}</p>
"""

@app.route("/")
def home():
    price = get_btc_price() or 0
    total = CAPITAL + BTC * price
    return render_template_string(HTML, price=price, capital=round(CAPITAL,2), btc=round(BTC,6), profit=round(PROFIT_TOTAL,2), total=round(total,2), trades=TRADES[-15:])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
