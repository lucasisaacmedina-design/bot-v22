import os, time, requests, threading, io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN","")
CHAT_ID = os.environ.get("CHAT_ID","")
URL_BOT = "https://bot-v22.onrender.com"
TP = 0.006
SL = 0.006

app = Flask(__name__)

estado = {
 "BTC": {"symbol":"BTCUSDT","entry":78085,"qty":0.000189},
 "BNB": {"symbol":"BNBUSDT","entry":640,"qty":0.02}
}

def get_data(symbol):
    k = requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=1m&limit=100", timeout=10).json()
    closes = [float(x[4]) for x in k]
    precio = closes[-1]
    ema = closes[0]
    mult = 2/(50+1)
    for c in closes[1:]: ema = c*mult + ema*(1-mult)
    return closes, precio, ema

def grafico(closes, ema, symbol, precio):
    plt.figure(figsize=(6,3), facecolor='black')
    ax = plt.gca(); ax.set_facecolor('black')
    plt.plot(closes, color='#00ff88', lw=1.5)
    plt.axhline(ema, color='orange', ls='--', lw=0.8)
    plt.title(f'{symbol} {precio:.2f} | EMA50 {ema:.2f} | SCALP 0.6%', color='white', fontsize=8)
    plt.tick_params(colors='gray')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='black', bbox_inches='tight')
    plt.close(); buf.seek(0); return buf

def send_text(t):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":t}, timeout=10)
    except: pass

def send_photo(buf,caption):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHAT_ID,"caption":caption}, files={"photo":buf}, timeout=20)
    except: pass

def loop():
    last = 0
    while True:
        try:
            # /estado
            try:
                r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last+1}&timeout=5", timeout=10).json()
                for u in r.get("result",[]):
                    last = u["update_id"]
                    if "/estado" in u.get("message",{}).get("text",""):
                        txt = "💰 ESTADO LOBO V25 DUAL SCALPING 0.6%\n\n"
                        for k,v in estado.items():
                            _, precio, ema = get_data(v["symbol"])
                            pct = (precio-v["entry"])/v["entry"]*100
                            txt += f"💵 {k}: ${precio:.2f} | EMA50 {ema:.0f} | {pct:+.2f}%\n"
                        txt += f"\n🔗 {URL_BOT}"
                        send_text(txt)
            except: pass

            if int(time.time()) % 300 < 10:
                for k,v in estado.items():
                    closes, precio, ema = get_data(v["symbol"])
                    pct = (precio-v["entry"])/v["entry"]*100
                    objetivo = v["entry"]*(1+TP)
                    buf = grafico(closes, ema, k, precio)
                    cap = f"📈 LOBO V25 {k} SCALPING\n💰 Vendiendo: {pct:+.2f}% -> Objetivo +0.6% (${objetivo:.2f}) | SL -0.6%\n{k} ${precio:.2f} EMA50 {ema:.0f}\n{URL_BOT}"
                    send_photo(buf, cap)
                time.sleep(30)
            time.sleep(3)
        except Exception as e:
            print(e); time.sleep(5)

@app.route('/')
def home():
    return f"<h1>Lobo V25 DUAL BTC+BNB VIVO</h1><a href='{URL_BOT}'>Dashboard</a>"

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    send_text("🐺 Lobo V25 DUAL BTC+BNB SCALPING 0.6% - VIVO Y FIJO")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
