import time, requests, os
from flask import Flask, render_template_string
import threading

app = Flask(__name__)

CAPITAL_INICIAL = 30.0
CAPITAL = CAPITAL_INICIAL
BTC = 0.0
TRADES = []
PROFIT_TOTAL = 0.0
LAST_PRICE = 79200.0

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
    global LAST_PRICE
    # Intento 1: Binance
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=4)
        data = r.json()
        if 'price' in data:
            LAST_PRICE = float(data['price'])
            return LAST_PRICE
    except:
        pass
    # Intento 2: CoinGecko
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=4)
        LAST_PRICE = float(r.json()['bitcoin']['usd'])
        return LAST_PRICE
    except:
        pass
    # Si falla todo, devuelve el último precio guardado, nunca 0
    return LAST_PRICE

def estrategia_lobo(price):
    global CAPITAL, BTC, PROFIT_TOTAL
    if not TRADES:
        btc_c = (CAPITAL * 0.5) / price
        BTC = btc_c
        CAPITAL -= btc_c * price
        TRADES.append({"tipo":"COMPRA","precio":price,"profit":0,"hora":time.strftime("%H:%M")})
        send_telegram(f"🐺 LoboBot22 REAL INICIADO\n🟢 COMPRA 50%\nPrecio: ${price:,.2f}\nBTC: {btc_c:.6f}")
        return

    ultimo = TRADES[-1]['precio']

    # STOP LOSS 3%
    if BTC > 0 and price < ultimo * 0.97:
        btc_v = BTC
        perdida = btc_v * price - btc_v * ultimo
        CAPITAL += btc_v * price
        BTC = 0
        PROFIT_TOTAL += perdida
        TRADES.append({"tipo":"STOP LOSS -3%","precio":price,"profit":perdida,"hora":time.strftime("%H:%M")})
        send_telegram(f"🐺 LoboBot22\n🛑 STOP LOSS -3%\nVendido a ${price:,.2f}\nPerdida: ${perdida:.2f}")
        return

    # COMPRA -1%
    if price < ultimo * 0.99 and CAPITAL > 5:
        btc_c = (CAPITAL * 0.3) / price
        BTC += btc_c
        CAPITAL -= btc_c * price
        TRADES.append({"tipo":"COMPRA -1%","precio":price,"profit":0,"hora":time.strftime("%H:%M")})
        send_telegram(f"🐺 LoboBot22\n🟢 COMPRA -1%\nPrecio: ${price:,.2f}")

    # VENTA +1.5%
    elif price > ultimo * 1.015 and BTC > 0.00001:
        btc_v = BTC * 0.5
        ganancia = btc_v * price - btc_v * ultimo
        CAPITAL += btc_v * price
        BTC -= btc_v
        PROFIT_TOTAL += ganancia
        TRADES.append({"tipo":"VENTA +1.5%","precio":price,"profit":ganancia,"hora":time.strftime("%H:%M")})
        send_telegram(f"🐺 LoboBot22\n🔴 VENTA +1.5%\nPrecio: ${price:,.2f}\nProfit: ${ganancia:.2f}\nTotal: ${PROFIT_TOTAL:.2f}")

def loop_caza():
    send_telegram("🐺 LoboBot22 V22 TradingView PRO Iniciado ✅\nEstrategia -1% / +1.5% / Stop -3%\nNunca más $0.00")
    while True:
        price = get_btc_price()
        estrategia_lobo(price)
        time.sleep(30)

threading.Thread(target=loop_caza, daemon=True).start()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { background:#131722; color:white; font-family:Arial; margin:0; }
.header { background:#1e222d; padding:12px; display:flex; justify-content:space-between; align-items:center; }
.card { background:#1e222d; margin:5px; padding:10px; border-radius:8px; display:inline-block; min-width:105px; }
.green { color:#26a69a; } .red { color:#ef5350; }
table { width:100%; font-size:12px; border-collapse:collapse; }
th { background:#2a2e39; padding:6px; } td { padding:6px; border-bottom:1px solid #2a2e39; text-align:center; }
</style>
</head>
<body>
<div class="header">
<b>🐺 LoboBot22 V22 PRO</b>
<span>BTC: ${{price}}</span>
</div>

<div style="padding:5px">
<div class="card">Capital<br><b>${{capital}}</b></div>
<div class="card">BTC<br><b>{{btc}}</b></div>
<div class="card">Total<br><b class="{{'green' if total>=30 else 'red'}}">${{total}}</b></div>
<div class="card">Beneficio<br><b class="{{'green' if profit>=0 else 'red'}}">${{profit}} ({{pct}}%)</b></div>
</div>

<div class="tradingview-widget-container" style="height:500px">
  <div id="tradingview_chart" style="height:500px"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({
    "autosize": true,
    "symbol": "BINANCE:BTCUSDT",
    "interval": "5",
    "timezone": "America/Argentina/Buenos_Aires",
    "theme": "dark",
    "style": "1",
    "locale": "es",
    "toolbar_bg": "#131722",
    "enable_publishing": false,
    "hide_top_toolbar": false,
    "save_image": false,
    "container_id": "tradingview_chart"
  });
  </script>
</div>

<div style="padding:10px">
<b>📈 Intercambios Lobo ({{trades|length}})</b>
<table>
<tr><th>Hora</th><th>Tipo</th><th>Precio</th><th>Profit</th></tr>
{% for t in trades[::-1] %}
<tr>
<td>{{t.hora}}</td>
<td style="color:{{'#26a69a' if 'COMPRA' in t.tipo else '#ef5350'}}">{{t.tipo}}</td>
<td>${{t.precio}}</td>
<td class="{{'green' if t.profit>0 else 'red' if t.profit<0 else ''}}">${{"%.2f"|format(t.profit)}}</td>
</tr>
{% endfor %}
</table>
<p style="font-size:11px; color:#888; margin-top:10px">Estrategia: Compra -1% / Venta +1.5% / Stop Loss -3% | Papel Real</p>
</div>
</body>
</html>
"""

@app.route("/")
def home():
    price = get_btc_price()
    total = CAPITAL + BTC * price
    pct = ((total - CAPITAL_INICIAL)/CAPITAL_INICIAL*100) if CAPITAL_INICIAL else 0
    return render_template_string(HTML, price=f"{price:,.2f}", capital=round(CAPITAL,2), btc=round(BTC,6), profit=round(PROFIT_TOTAL,2), total=round(total,2), pct=round(pct,2), trades=TRADES[-20:])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
