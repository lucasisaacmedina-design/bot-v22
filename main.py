import time
import requests
from datetime import datetime

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
        precio = obtener_precio()
        ahora = datetime.now().strftime("%H:%M:%S")
        if precio > precio_maximo:
            precio_maximo = precio
        caida = ((precio_maximo - precio) / precio_maximo * 100) if precio_maximo else 0
        if not en_compra and caida >= CAIDA_COMPRA:
            en_compra = True
            precio_compra = precio
            print(f"[{ahora}] COMPRA BTC a ${precio:.2f} | Caida {caida:.2f}%")
        elif en_compra:
            gan = (precio - precio_compra) / precio_compra * 100
            if gan >= SUBIDA_VENTA:
                print(f"[{ahora}] VENTA +{gan:.2f}% GANANCIA")
                en_compra = False
                precio_maximo = precio
            elif gan <= STOP_LOSS:
                print(f"[{ahora}] STOP {gan:.2f}%")
                en_compra = False
                precio_maximo = precio
        time.sleep(10)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
