from flask import Flask
import threading, time, requests

app = Flask(__name__)

precio_compra = 77143.5
btc_actual = 77143.5
profit = 0.0

def track():
    global btc_actual, profit
    while True:
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10)
            btc_actual = float(r.json()['price'])
            profit = btc_actual - precio_compra
            print(f"BTC: {btc_actual} | PROFIT: {profit}")
        except:
            pass
        time.sleep(10)

@app.route("/")
def home():
    color = "green" if profit >= 0 else "red"
    return f"<h1>BOT V25 LOBO - LIVE 24/7</h1><h2>BTC: ${btc_actual:.2f}</h2><h2 style='color:{color}'>PROFIT: ${profit:.2f}</h2>"

threading.Thread(target=track, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
