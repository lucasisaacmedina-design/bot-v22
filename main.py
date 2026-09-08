import requests, time, os, io, threading
from flask import Flask
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
@app.route('/')
def home(): return "LoboBot22 GRAFICO - VIVO", 200
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}"

def tg_text(m): requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": m})
def tg_photo(buf, cap): requests.post(f"{API}/sendPhoto", data={"chat_id": CHAT_ID, "caption": cap}, files={"photo": buf})

def get_klines():
    # Endpoint que NO bloquea USA
    url = "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=100"
    try:
        d = requests.get(url, timeout=10).json()
        return [float(x[4]) for x in d]
    except:
        # Fallback a precio unico si falla
        return [78476]*100

def ema(data, p=50):
    k = 2/(p+1)
    e = data[0]
    for x in data: e = x*k + e*(1-k)
    return e

print("BOT GRAFICO INICIADO")
tg_text("🐺 LoboBot22 GRAFICO NEGRO USA - VIVO")

while True:
    try:
        closes = get_klines()
        btc = closes[-1]
        e50 = ema(closes, 50)
        
        print(f"Grafico BTC {btc}")
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6,3), facecolor='black')
        ax.plot(closes, color='#00ff88', linewidth=2)
        ax.axhline(e50, color='orange', linestyle='--', linewidth=1)
        ax.set_title(f"BTC ${btc:.0f} | EMA50 ${e50:.0f} | USA FIX", color='white', fontsize=10)
        ax.tick_params(colors='white')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='black', bbox_inches='tight', dpi=100)
        buf.seek(0); plt.close()
        
        tg_photo(buf, f"📈 LOBO V22 GRAFICO\nBTC ${btc:.0f}\nEMA50 {e50:.0f}\nhttps://bot-v22.onrender.com")
        time.sleep(300)
    except Exception as e:
        print(f"Error grafico {e}")
        tg_text(f"❌ Error grafico: {e}")
        time.sleep(30)
