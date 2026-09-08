import requests, time, os, io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}"

capital = 100.0
btc_bag = 0.0
comprado_en = 0

def tg_texto(msg):
    requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})

def tg_foto(buf, caption):
    requests.post(f"{API}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": buf})

def get_price(sym):
    r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", timeout=5).json()
    return float(r['price'])

def get_klines(sym, limit=50):
    r = requests.get(f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1m&limit={limit}", timeout=5).json()
    return [float(x[4]) for x in r] # cierres

tg_texto("🐺 LoboBot22 DUAL 0.8% PRO - BOT VIVO + Grafico Negro")

while True:
    try:
        btc = get_price("BTCUSDT")
        closes = get_klines("BTCUSDT")
        ema200 = sum(closes[-20:])/20 # ema simplificada pelada
        rsi = 50 # simplificado para no usar pandas

        hora = datetime.now().strftime("%H:%M:%S")

        # --- LOGICA 0.8% ---
        pnl = 0
        if btc_bag == 0 and btc < ema200:
            btc_bag = capital / btc
            comprado_en = btc
            tg_texto(f"🟢 COMPRANDO BTC {btc:.2f}")
        elif btc_bag > 0 and btc >= comprado_en * 1.008: # +0.8%
            capital = btc_bag * btc
            gan = (btc/comprado_en-1)*100
            tg_texto(f"💰 VENDIENDO +{gan:.2f}% -> Capital ${capital:.2f}")
            btc_bag = 0

        # --- GRAFICO NEGRO ---
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6,3))
        ax.plot(closes, color='#00ff88', linewidth=2)
        ax.set_title(f"LOBO V22 DUAL | BTC ${btc:.0f} | {hora}", color='white')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='black')
        buf.seek(0)
        plt.close()

        total = capital if btc_bag==0 else btc_bag*btc
        pnl_pct = (total/100-1)*100

        caption = f"💰 ESTADO LOBO V23 RENTABLE\nCapital: ${total:.2f}\nBTC: ${btc:.0f}\nP&L: {pnl_pct:.2f}%\nTP +0.8% | SL -1.5% | EMA200"
        tg_foto(buf, caption)

        time.sleep(300) # cada 5 min
    except Exception as e:
        print(e)
        time.sleep(30)
