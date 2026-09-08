import requests, time, os
from datetime import datetime

# === CONFIG LOBOBOT22 DUAL ===
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BTC_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
BNB_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT"

capital = 100.0
ganancia_por_trade = 0.008  # 0.8%

def enviar_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def get_precio(url):
    r = requests.get(url, timeout=5).json()
    return float(r['price'])

# === LOOP DUAL ===
enviar_telegram("🐺 LoboBot22 DUAL BTC+BNB iniciado - BOT VIVO")

while True:
    try:
        btc = get_precio(BTC_URL)
        bnb = get_precio(BNB_URL)
        hora = datetime.now().strftime("%H:%M:%S")

        # Logica scalper simple
        mensaje = f"🐺 LOBOBOT22 | {hora}\nBTC: ${btc:.2f}\nBNB: ${bnb:.2f}\nCapital: ${capital:.2f}\n✅ BOT VIVO"
        print(mensaje)
        
        # Aca va tu logica de compra/venta 0.8%
        # if condicion: capital *= (1 + ganancia_por_trade)
        
        time.sleep(60) # escanea cada 1 min

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
