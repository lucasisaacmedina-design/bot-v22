import os, time, requests, threading
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
URL_BOT = "https://bot-v22.onrender.com"

TP = 0.006 # 0.6% SCALPING
SL = 0.006

app = Flask(__name__)
estado = {"capital":0.0,"btc":0.000189,"total":15.0,"beneficio":-0.04,"beneficio_pct":-0.27,"trades":1,"victorias":1,"entry":80000,"precio":79149,"rsi":38,"ema200":80200}

def get_price_and_indicadores():
    try:
        # precio
        p = float(requests.get("https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT", timeout=10).json()["price"])
        estado["precio"] = p
        # klines para EMA200 + RSI
        klines = requests.get("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=250", timeout=10).json()
        closes = [float(k[4]) for k in klines]
        # EMA 200
        ema = closes[0]
        k = 2/(200+1)
        for c in closes[1:]: ema = c*k + ema*(1-k)
        estado["ema200"] = ema
        # RSI 14 simple
        gains = []; losses = []
        for i in range(1,15):
            diff = closes[-i] - closes[-i-1]
            if diff>0: gains.append(diff)
            else: losses.append(abs(diff))
        rs = (sum(gains)/14) / (sum(losses)/14 + 0.00001)
        rsi = 100 - (100/(1+rs))
        estado["rsi"] = rsi
        estado["total"] = estado["capital"] + (estado["btc"]*p)
        return p, ema, rsi
    except:
        return estado["precio"], estado["ema200"], estado["rsi"]

def formato_vendiendo():
    precio, ema, rsi = estado["precio"], estado["ema200"], estado["rsi"]
    entry = estado["entry"]
    pct = ((precio - entry)/entry*100) if entry else 0
    objetivo = entry * (1+TP)
    stop = entry * (1-SL)
    return f"💰 Vendiendo: {pct:+.2f}% -> Objetivo +0.6% (${objetivo:.0f}) | SL -0.6%\nTP +0.6% | SL -0.6% | EMA200 + RSI ({rsi:.0f})\n🔗 {URL_BOT}"

def send_msg(text):
    if not BOT_TOKEN or not CHAT_ID: return
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":text}, timeout=10)
    except: pass

def telegram_loop():
    last = 0
    while True:
        try:
            precio, ema, rsi = get_price_and_indicadores()
            # /estado
            try:
                upd = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last+1}&timeout=5", timeout=10).json()
                for u in upd.get("result",[]):
                    last = u["update_id"]
                    if u.get("message",{}).get("text") == "/estado":
                        txt = f"""💰 ESTADO LOBO V24 SCALPING 0.6%

💵 Capital: ${estado['capital']:.2f}
₿ BTC: {estado['btc']:.6f}
📈 BTC: ${precio:,.0f} | EMA200: ${ema:,.0f}
💼 Total: ${estado['total']:.2f}
📊 P&L: ${estado['beneficio']:.2f} ({estado['beneficio_pct']:.2f}%) | RSI: {rsi:.0f}
🔄 Trades: {estado['trades']} | Win: {int(estado['victorias']/estado['trades']*100) if estado['trades'] else 0}%

{formato_vendiendo()}"""
                        send_msg(txt)
            except: pass

            # auto cada 5 min
            if int(time.time()) % 300 < 5:
                send_msg(formato_vendiendo())
                time.sleep(20)
            time.sleep(5)
        except: time.sleep(5)

@app.route('/')
def dash():
    precio = estado["precio"]
    return f"""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>
    body{{background:#0e0e0e;color:white;font-family:Arial;padding:8px;margin:0}}.chart{{height:750px}}#tv{{height:750px}}</style></head><body>
    <h3>🐺 LOBO V24 SCALPING 0.6% | BTC ${precio:.0f} | RSI {estado['rsi']:.0f}</h3>
    <div class="chart"><div id="tv"></div></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({{"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"tv","height":750}})</script>
    </body></html>"""

if __name__ == "__main__":
    threading.Thread(target=telegram_loop, daemon=True).start()
    send_msg("🐺 LoboBot22 V24 SCALPING 0.6% + Formato Lindo - VIVO")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
