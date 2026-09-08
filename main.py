import requests, time, os, io, threading
from flask import Flask
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# TRUCO PARA RENDER WEB SERVICE
app = Flask(__name__)
@app.route('/')
def home(): return "LoboBot22 VIVO", 200
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}"

capital = 100.0
btc_bag = 0.0
comprado_en = 0

def tg_texto(msg): requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
def tg_foto(buf, cap): requests.post(f"{API}/sendPhoto", data={"chat_id": CHAT_ID, "caption": cap}, files={"photo": buf})

def get_klines(sym="BTCUSDT", lim=200):
    data = requests.get(f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1m&limit={lim}", timeout=10).json()
    return [float(x[4]) for x in data]

def calc_ema(closes, period=200):
    k = 2 / (period + 1)
    ema = closes[0]
    for p in closes: ema = p * k + ema * (1 - k)
    return ema

def calc_rsi(closes, period=14):
    g = l = 0
    for i in range(1, period+1):
        d = closes[-i] - closes[-i-1]
        if d>0: g+=d
        else: l+=abs(d)
    if l==0: return 70
    return 100 - (100 / (1 + g/l))

tg_texto("🐺 LoboBot22 FIX WEB - VIVO")

while True:
    try:
        closes = get_klines()
        btc = closes[-1]
        ema200 = calc_ema(closes, 200)
        rsi = calc_rsi(closes, 14)

        if btc_bag==0 and btc < ema200 and rsi < 35:
            btc_bag = capital/btc
            comprado_en = btc
            tg_texto(f"🟢 COMPRA BTC ${btc:.0f} | RSI {rsi:.1f}")

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6,3))
        ax.plot(closes[-50:], color='#00ff88', linewidth=2)
        ax.axhline(ema200, color='orange', linestyle='--')
        ax.set_title(f"BTC ${btc:.0f} | RSI {rsi:.0f}", color='white')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='black', bbox_inches='tight')
        buf.seek(0); plt.close()
        tg_foto(buf, f"LOBO V22 FIX\nBTC ${btc:.0f}\nRSI {rsi:.1f} EMA {ema200:.0f}")
        time.sleep(300)
    except Exception as e:
        print(e); time.sleep(30)
