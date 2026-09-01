import time, threading
from flask import Flask
import requests

app = Flask(__name__)

btc_actual = 77143.50
precio_entrada = 77143.50
profit = 0.0
trades = []

def get_btc():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5)
        return float(r.json()['price'])
    except:
        return btc_actual

def track():
    global btc_actual, profit, trades, precio_entrada
    while True:
        btc_actual = get_btc()
        profit = btc_actual - precio_entrada
        pct = (profit / precio_entrada) * 100
        trades.append(f"{time.strftime('%H:%M:%S')} BTC ${btc_actual:.2f} | Profit ${profit:.2f}")
        if len(trades) > 20: trades.pop(0)
        print(f"PROFIT ${profit:.2f} ({pct:.2f}%)")
        time.sleep(60)

@app.route("/")
def home():
    pct = (profit / precio_entrada) * 100 if precio_entrada else 0
    color = "green" if profit >= 0 else "red"
    lista_trades = "<br>".join(trades[::-1])
    return f"""
    <html><head><meta http-equiv='refresh' content='30'><style>
    body{{font-family:Arial;background:#0d1117;color:white;padding:20px}}
    .card{{background:#161b22;padding:20px;border-radius:12px;max-width:800px}}
    .profit{{color:{color};font-size:32px;font-weight:bold}}
    </style></head><body>
    <div class=card>
    <h1>🐺 BOT V25.1 LOBO - PANEL PRO</h1>
    <h2>BTC: ${btc_actual:.2f}</h2>
    <div class=profit>GANANCIA: ${profit:.2f} ({pct:.2f}%)</div>
    <p>Entrada: ${precio_entrada:.2f} | Actualizando cada 30 seg</p>
    <hr><h3>📊 Ultimos movimientos:</h3>
    <p>{lista_trades}</p>
    <p>🔴 LIVE 24/7 en Render</p>
    </div></body></html>
    """

threading.Thread(target=track, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
