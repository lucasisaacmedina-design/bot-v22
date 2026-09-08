import requests, time, os, io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}"

capital = 100.0
btc_bag = 0.0
comprado_en = 0

def tg_texto(msg):
    requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})

def tg_foto(buf, cap):
    requests.post(f"{API}/sendPhoto", data={"chat_id": CHAT_ID, "caption": cap}, files={"photo": buf})

def get_klines(sym="BTCUSDT", lim=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1m&limit={lim}"
    data = requests.get(url, timeout=10).json()
    return [float(x[4]) for x in data] # cierres

def calc_ema(closes, period=200):
    # EMA sin pandas
    k = 2 / (period + 1)
    ema = closes[0]
    for price in closes:
        ema = price * k + ema * (1 - k)
    return ema

def calc_rsi(closes, period=14):
    # RSI sin pandas
    gains = losses = 0
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
        if diff > 0: gains += diff
        else: losses += abs(diff)
    if losses == 0: return 70
    rs = gains / losses
    return 100 - (100 / (1 + rs))

# INICIO
tg_texto("🐺 LoboBot22 DUAL sin pandas - EMA200+RSI REAL - VIVO")

while True:
    try:
        closes = get_klines()
        btc = closes[-1]
        ema200 = calc_ema(closes, 200)
        rsi = calc_rsi(closes, 14)

        # LOGICA 0.8%
        if btc_bag == 0 and btc < ema200 and rsi < 35:
            btc_bag = capital / btc
            comprado_en = btc
            tg_texto(f"🟢 COMPRA BTC ${btc:.0f} | RSI {rsi:.1f} <35 | EMA200 ${ema200:.0f}")
        elif btc_bag > 0:
            if btc >= comprado_en * 1.008:
                capital = btc_bag * btc
                tg_texto(f"💰 TP +0.8% HIT | VENDIDO ${btc:.0f} | Capital ${capital:.2f}")
                btc_bag = 0
            elif btc <= comprado_en * 0.985:
                capital = btc_bag * btc
                tg_texto(f"🔴 SL -1.5% | VENDIDO ${btc:.0f}")
                btc_bag = 0

        # GRAFICO NEGRO
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6,3))
        ax.plot(closes[-50:], color='#00ff88', linewidth=2)
        ax.axhline(ema200, color='orange', linestyle='--', label=f'EMA200 {ema200:.0f}')
        ax.set_title(f"BTC ${btc:.0f} | RSI {rsi:.0f} | EMA200", color='white')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='black', bbox_inches='tight')
        buf.seek(0)
        plt.close()

        total = capital if btc_bag==0 else btc_bag*btc
        pnl = (total/100-1)*100
        cap_txt = f"💰 LOBO V23 RENTABLE\nCapital: ${total:.2f}\nBTC: ${btc:.0f}\nP&L: {pnl:.2f}%\nRSI: {rsi:.1f} | EMA: {ema200:.0f}\nTP +0.8% | SL -1.5%"
        tg_foto(buf, cap_txt)

        time.sleep(300)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(30)
