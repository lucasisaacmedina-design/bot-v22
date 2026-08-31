import time
import requests
from datetime import datetime
import os
import threading
from flask import Flask

# --- WEB PARA RENDER (NO TOCAR) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "BOT V22 LIVE 24/7"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

# --- TU BOT V22 ---
MONEDA = "BTCUSDT"
CAIDA_COMPRA = 1.0
SUBIDA_VENTA = 1.5
STOP_LOSS = -2.0

precio_maximo = 0
en_compra = False
precio_compra = 0

def obtener_precio():
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={MONEDA}"
    return float(requests.get(url, timeout=10).json()['price'])

print("BOT V22 RENTABLE INICIADO 24/7")

while True:
    try:
        precio_actual = obtener_precio()
        ahora = datetime.now().strftime("%H:%M:%S")
        
        if not en_compra:
            if precio_actual > precio_maximo:
                precio_maximo = precio_actual
            caida = ((precio_actual - precio_maximo) / precio_maximo) * 100 if precio_maximo > 0 else 0
            print(f"[{ahora}] Precio: {precio_actual} | Caida: {caida:.2f}%")
            if caida <= -CAIDA_COMPRA:
                en_compra = True
                precio_compra = precio_actual
                print(f"--- COMPRA en {precio_compra} ---")
        else:
            ganancia = ((precio_actual - precio_compra) / precio_compra) * 100
            print(f"[{ahora}] EN COMPRA | Ganancia: {ganancia:.2f}%")
            if ganancia >= SUBIDA_VENTA or ganancia <= STOP_LOSS:
                print(f"--- VENTA en {precio_actual} Ganancia: {ganancia:.2f}% ---")
                en_compra = False
                precio_maximo = precio_actual
        time.sleep(10)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
