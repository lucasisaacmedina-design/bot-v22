import requests, time, os, threading
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "LoboBot22 VIVO", 200
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}"
def tg(m):
    try: requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except Exception as e: print(f"TG Error {e}")

tg("🐺 FIX USA - VIVO 10:15")
print("BOT INICIADO - esperando 60s para primer envio")

time.sleep(60) # Primer envio a los 60s para que lo veas rapido

while True:
    try:
        print("Pidiendo precio BTC...")
        # Intenta Binance US, si falla usa CoinGecko
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10).json()
            btc = float(r['price'])
        except:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10).json()
            btc = float(r['bitcoin']['usd'])
            print("Usando CoinGecko fallback")

        print(f"BTC {btc} - enviando a TG")
        tg(f"📈 BTC ${btc:.0f} | Bot USA OK | Grafico viene en prox version")
        time.sleep(300)
    except Exception as e:
        print(f"ERROR LOOP: {e}")
        tg(f"❌ Error loop: {e}")
        time.sleep(30)
