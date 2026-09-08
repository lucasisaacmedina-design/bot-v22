import os, time, requests, math
from flask import Flask, send_file
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import deque

# --- CONFIG LOBO V23 LIVIANO - SIN PANDAS ---
CAPITAL_BTC = 100.0
CAPITAL_BNB = 5.0
TP_PCT = 0.006
SL_PCT = 0.006
SYMBOL_BTC = "BTCUSDT"
SYMBOL_BNB = "BNBUSDT"
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://tu-bot.onrender.com")

app = Flask(__name__)
estado = {"capital": CAPITAL_BTC, "btc": 0.0, "entry": 0, "total": CAPITAL_BTC, "pnl": 0, "prices": deque(maxlen=200)}

def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    return float(requests.get(url, timeout=10).json()["price"])

def get_klines_close(symbol, limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit={limit}"
    data = requests.get(url, timeout=10).json()
    closes = [float(c[4]) for c in data]
    return closes

def calc_rsi(prices, period=14):
    if len(prices) < period+1: return 50
    gains, losses = 0, 0
    for i in range(1, period+1):
        diff = prices[-i] - prices[-i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    if losses == 0: return 100
    rs = (gains/period) / (losses/period)
    return 100 - (100 / (1 + rs))

def calc_ema(prices, span):
    if len(prices) < span: return prices[-1]
    k = 2 / (span + 1)
    ema = prices[0]
    for p in prices[1:]: ema = p * k + ema * (1 - k)
    return ema

def generar_grafico_negro(closes, symbol):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(8,4), facecolor='black')
    ax.set_facecolor('black')
    ax.plot(closes[-100:], color='#00FF88', linewidth=2)
    ax.set_title(f"{symbol} LOBO SCALPING 0.6%", color='white', fontsize=12)
    ax.tick_params(colors='white')
    plt.tight_layout()
    plt.savefig(f"{symbol}_chart.png", facecolor='black', dpi=100)
    plt.close()

def enviar_telegram(precio, rsi, ema9, ema20, ema200, objetivo, sl):
    pnl_pct = ((estado["total"] - CAPITAL_BTC) / CAPITAL_BTC) * 100 if CAPITAL_BTC else 0
    mensaje = f"""
🐺 *LOBO SCALPING V23 - LIVIANO*

💰 Capital: ${estado['capital']:.2f}
₿ BTC: {estado['btc']:.6f}
📊 Total: ${estado['total']:.2f}
📈 P&L: ${estado['pnl']:.2f} ({pnl_pct:.2f}%)

🎯 Vendiendo:
   Objetivo: ${objetivo:.2f} (+0.6%)
   SL: ${sl:.2f} (-0.6%)

📉 Indicadores:
   RSI: {rsi:.1f}
   EMA9: {ema9:.2f}
   EMA20: {ema20:.2f}
   EMA200: {ema200:.2f}

💵 BNB Comisiones: ${CAPITAL_BNB}
🔗 Grafico: {RENDER_URL}/chart
"""
    if not TELEGRAM_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"})

@app.route('/')
def home():
    return f"LOBO SCALPING 0.6% - ${CAPITAL_BTC} BTC + ${CAPITAL_BNB} BNB OK - <a href='/chart'>Ver Grafico</a>"

@app.route('/chart')
def chart():
    closes = get_klines_close(SYMBOL_BTC)
    generar_grafico_negro(closes, SYMBOL_BTC)
    return send_file("BTCUSDT_chart.png", mimetype='image/png')

def loop():
    while True:
        try:
            closes = get_klines_close(SYMBOL_BTC)
            precio = closes[-1]
            estado["prices"] = closes
            rsi = calc_rsi(closes)
            ema9 = calc_ema(closes, 9)
            ema20 = calc_ema(closes, 20)
            ema200 = calc_ema(closes, 200)

            if estado["btc"] == 0 and ema9 > ema20 and rsi < 40:
                estado["btc"] = estado["capital"] / precio
                estado["entry"] = precio
                estado["capital"] = 0

            if estado["btc"] > 0:
                objetivo = estado["entry"] * (1 + TP_PCT)
                sl = estado["entry"] * (1 - SL_PCT)
                generar_grafico_negro(closes, SYMBOL_BTC)
                enviar_telegram(precio, rsi, ema9, ema20, ema200, objetivo, sl)
                if precio >= objetivo or precio <= sl:
                    estado["capital"] = estado["btc"] * precio
                    estado["total"] = estado["capital"] + CAPITAL_BNB
                    estado["pnl"] = estado["total"] - (CAPITAL_BTC + CAPITAL_BNB)
                    estado["btc"] = 0
            time.sleep(60)
        except Exception as e:
            print(f"Error loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    import threading
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
