import os
import time
import threading
import requests
from flask import Flask, render_template_string
import ccxt

# --- CONFIGURACION LOBO V22 FINAL ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "TU_CHAT_ID_AQUI")
STRATEGY_NAME = "V22 Cazadora"
BUY_DROP = -1.0
SELL_PROFIT = 1.5
STOP_LOSS = -3.0  # CAMBIADO A -3%
COMMISSION = 0.001
CAPITAL_INICIAL = 30.0

# --- ESTADO ---
estado = {
    "capital_usdt": 15.00,
    "btc_amount": 0.000189,
    "buy_price": 79146.0,
    "trades": 1,
    "max_price": 79146.0,
    "last_price": 79071.0
}

def enviar_telegram(mensaje):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
        requests.post(url, data=data, timeout=10)
        print(f"Telegram enviado: {mensaje}")
    except Exception as e:
        print(f"Error Telegram: {e}")

# --- FLASK ---
app = Flask(__name__)

HTML = """
<html><head><title>Lobo V22</title><meta http-equiv="refresh" content="30"></head>
<body style="background:#0e0e0e;color:white;font-family:Arial;text-align:center;padding-top:30px">
<h1>🐺 Lobo V22 - {{strategy}}</h1>
<h2>💰 Capital: ${{capital}}</h2>
<h2>₿ BTC: {{btc}} (Precio: ${{price}})</h2>
<h2>💵 Total: ${{total}}</h2>
<h2 style="color:{{color}}">📊 Beneficio: ${{benef}} ({{perc}}%)</h2>
<hr>
<h3>Trades: {{trades}} | Compra: ${{buy}} | Max: ${{max}}</h3>
<h3>Estrategia: Compra {{buy_drop}}% / Venta +{{sell}}% / SL {{sl}}%</h3>
<p>Modo: ENTRENO | Actualiza cada 30s | Telegram Activo: {{tg}}</p>
</body></html>
"""

@app.route("/")
def dashboard():
    price = estado["last_price"]
    try:
        binance = ccxt.binance()
        ticker = binance.fetch_ticker('BTC/USDT')
        price = ticker['last']
        estado["last_price"] = price
    except:
        pass
    
    if price > estado["max_price"]:
        estado["max_price"] = price
    
    total_btc_usd = estado["btc_amount"] * price
    total = estado["capital_usdt"] + total_btc_usd
    beneficio = total - CAPITAL_INICIAL
    perc = (beneficio / CAPITAL_INICIAL) * 100
    color = "#00ff00" if beneficio >= 0 else "#ff4444"
    tg_status = "✅ SI" if BOT_TOKEN != "TU_TOKEN_AQUI" else "❌ NO CONFIGURADO"
    
    return render_template_string(HTML, 
        strategy=STRATEGY_NAME, capital=round(estado["capital_usdt"],2),
        btc=estado["btc_amount"], price=round(price,2), total=round(total,2),
        benef=round(beneficio,2), perc=round(perc,2), trades=estado["trades"],
        buy=round(estado["buy_price"],2), max=round(estado["max_price"],2),
        buy_drop=BUY_DROP, sell=SELL_PROFIT, sl=STOP_LOSS, color=color, tg=tg_status)

def loop_caza():
    enviar_telegram(f"🐺 *Lobo V22 Iniciado*\nEstrategia: Compra {BUY_DROP}% / Venta +{SELL_PROFIT}% / SL {STOP_LOSS}%\nModo ENTRENO activo")
    while True:
        time.sleep(30)
        # Logica real iria aqui
        pass

threading.Thread(target=loop_caza, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
