from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home():
    return "Lobo Bot V22 - VIVO y operando!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web, daemon=True).start()
import time, requests, os, threading
from datetime import datetime
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home():
    return "BOT V25 LOBO - LIVE 24/7"

def obtener_precio():
    try:
        # Kraken no banea nunca y es gratis
        url = "https://api.kraken.com/0/public/Ticker?pair=BTCUSD"
        r = requests.get(url, timeout=10).json()
        precio = float(r['result']['XXBTZUSD']['c'][0])
        return precio
    except Exception as e:
        print(f"Error Kraken: {e}", flush=True)
        # Si falla Kraken, intenta Binance
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10).json()
            return float(r['price'])
        except:
            return 0

def bot_trading():
    precio_maximo = 0
    print("BOT V25 LOBO INICIADO - RENTABLE 24/7", flush=True)
    while True:
        try:
            precio_actual = obtener_precio()
            if precio_actual == 0:
                time.sleep(15)
                continue
            ahora = datetime.now().strftime("%H:%M:%S")
            if precio_actual > precio_maximo:
                precio_maximo = precio_actual
            caida = ((precio_actual - precio_maximo) / precio_maximo) * 100 if precio_maximo > 0 else 0
            print(f"[{ahora}] BTC: {precio_actual} | Caida: {caida:.2f}% | MAX: {precio_maximo}", flush=True)
            time.sleep(20) # Ahora cada 20 seg para que no te banee
        except Exception as e:
            print(f"Error loop: {e}", flush=True)
            time.sleep(20)

threading.Thread(target=bot_trading, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
