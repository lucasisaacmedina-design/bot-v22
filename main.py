import os
import time
import threading
import requests
from flask import Flask, render_template_string
import ccxt

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "TU_ID")
STRATEGY_NAME = "V22 Cazadora"
BUY_DROP = -1.0
SELL_PROFIT = 1.5
STOP_LOSS = -3.0
CAPITAL_INICIAL = 30.0

estado = {
    "capital_usdt": 15.0,
    "btc_amount": 0.000189,
    "buy_price": 79146.0,
    "trades": 1,
    "max_price": 79146.0,
    "last_price": 79071.0
}

def enviar_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

app = Flask(__name__)

HTML = """
<html><head><title>Lobo V22</title><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{background:#0e0e0e;color:white;font-family:Arial;text-align:center;margin:0;padding:15px}</style>
</head>
<body>
<h1>🐺 Lobo V22 - {{strategy}}</h1>
<h2>💰 Capital: ${{capital}} | ₿ BTC: {{btc}} (${{price}})</h2>
<h2>💵 Total: ${{total}} | <span style="color:{{color}}">Beneficio: ${{benef}} ({{perc}}%)</span></h2>
<h3>Trades: {{trades}} | Compra: ${{buy}} | Max: ${{max}}</h3>
<h3>Estrategia: Compra {{buy_drop}}% / Venta +{{sell}}% / SL {{sl}}%</h3>
<p>Modo: ENTRENO | Telegram: ✅ SI</p>
<hr>
<h2>📈 Gráfico BTC/USDT - TradingView</h2>
<!-- TradingView Widget -->
<div style="height:500px">
<div class="tradingview-widget-container">
  <div id="tradingview_chart" style="height:500px"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({
    "autosize": true,
    "symbol": "BINANCE:BTCUSDT",
    "interval": "15",
    "timezone": "America/Argentina/Buenos_Aires",
    "theme": "dark",
    "style": "1",
    "locale": "es",
    "toolbar_bg": "#f1f3f6",
    "enable_publishing": false,
    "hide_side_toolbar": false,
    "allow_symbol_change": true,
    "container_id": "tradingview_chart"
  });
  </script>
</div>
</div>
<p style="margin-top:20px;color:#888">Actualiza cada 30s - https://bot-v22.onrender.com</p>
</body></html>
"""

@app.route("/")
def dashboard():
    price = estado["last_price"]
    try:
        price = ccxt.binance().fetch_ticker('BTC/USDT')['last']
        estado["last_price"] = price
    except: pass
    if price > estado["max_price"]: estado["max_price"] = price
    total = estado["capital_usdt"] + (estado["btc_amount"] * price)
    benef = total - CAPITAL_INICIAL
    perc = (benef / CAPITAL_INICIAL)*100
    color = "#00ff00" if benef >=0 else "#ff4444"
    return render_template_string(HTML, strategy=STRATEGY_NAME, capital=round(estado["capital_usdt"],2),
        btc=estado["btc_amount"], price=round(price,2), total=round(total,2),
        benef=round(benef,2), perc=round(perc,2), trades=estado["trades"],
        buy=round(estado["buy_price"],2), max=round(estado["max_price"],2),
        buy_drop=BUY_DROP, sell=SELL_PROFIT, sl=STOP_LOSS, color=color)

def loop_caza():
    enviar_telegram(f"🐺 *Lobo V22 con Grafico Iniciado*\nSL: {STOP_LOSS}%")
    while True: time.sleep(30)

threading.Thread(target=loop_caza, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
