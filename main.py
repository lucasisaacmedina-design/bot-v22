import os
from flask import Flask
from binance.client import Client
import requests
import time
from datetime import datetime

app = Flask(__name__)

API_KEY = os.environ.get("BINANCE_API_KEY")
API_SECRET = os.environ.get("BINANCE_API_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_ID = os.environ.get("TELEGRAM_ID")

client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_ID, "text": msg})
    except: pass

@app.route("/")
def home():
    try:
        ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        precio = float(ticker['price'])
        bal = client.get_asset_balance(asset='USDT')
        saldo = float(bal['free']) if bal else 100.0
        hora = datetime.now().strftime("%H:%M:%S 2/9/2026")

        html = f"""
        <div style="background:#111;color:white;padding:20px;font-family:sans-serif;border-radius:15px">
        <h2>🔴 LOBO V28 - TESTNET REAL ACTIVO</h2>
        <p>Fecha inicio: 2 Sept 2026 - SIN CULPA 40</p>
        <p>BTC Precio REAL Binance: ${precio:,.2f}</p>
        <p>Saldo Testnet USDT: ${saldo:.2f}</p>
        <p>PnL: ${saldo-100:.2f}</p>
        <p>Estado: CONECTADO A BINANCE TESTNET</p>
        <p>Actualizado: {hora}</p>
        <p style="color:#2ecc71">¡Bot conectado a claves que ya pegaste en Render!</p>
        </div>
        <script>setTimeout(()=>location.reload(), 10000)</script>
        """
        return html
    except Exception as e:
        return f"<h1>Error conectando</h1><p>{e}</p><p>Revisá que las keys de testnet sigan activas en testnet.binance.vision</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
