import time, requests, os, threading
from datetime import datetime
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home():
    return "BOT V22 LIVE 24/7 - FUNCIONANDO"

def obtener_precio():
    # Intenta Binance, si falla usa CoinGecko
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        r = requests.get(url, timeout=10).json()
        if 'price' in r:
            return float(r['price'])
    except:
        pass
    # Fallback CoinGecko
    url2 = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    r2 = requests.get(url2, timeout=10).json()
    return float(r2['bitcoin']['usd'])

def bot_trading():
    precio_maximo = 0
    en_compra = False
    precio_compra = 0
    print("BOT V22 RENTABLE INICIADO 24/7", flush=True)
    while True:
        try:
            precio_actual = obtener_precio()
            ahora = datetime.now().strftime("%H:%M:%S")
            if not en_compra:
                if precio_actual > precio_maximo:
                    precio_maximo = precio_actual
                caida = ((precio_actual - precio_maximo) / precio_maximo) * 100 if precio_maximo > 0 else 0
                print(f"[{ahora}] BTC: {precio_actual} | Caida: {caida:.2f}%", flush=True)
                if caida <= -1.0:
                    en_compra = True
                    precio_compra = precio_actual
                    print(f"--- COMPRA en {precio_compra} ---", flush=True)
            else:
                ganancia = ((precio_actual - precio_compra) / precio_compra) * 100
                print(f"[{ahora}] EN COMPRA | Ganancia: {ganancia:.2f}%", flush=True)
                if ganancia >= 1.5 or ganancia <= -2.0:
                    print(f"--- VENTA en {precio_actual} Ganancia: {ganancia:.2f}% ---", flush=True)
                    en_compra = False
                    precio_maximo = precio_actual
            time.sleep(10)
        except Exception as e:
            print(f"Error: {e}", flush=True)
            time.sleep(10)

threading.Thread(target=bot_trading, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
