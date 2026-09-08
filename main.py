import os, time, requests
from flask import Flask, send_file
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- CONFIG FINAL LOBO V23 ---
CAPITAL_BTC = 100.0
CAPITAL_BNB = 5.0
TP_PCT = 0.006 # +0.6% SCALPING
SL_PCT = 0.006 # -0.6% SCALPING
SYMBOL = "BTCUSDT"
TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://bot-v22.onrender.com")

app = Flask(__name__)
estado = {"capital": CAPITAL_BTC, "btc": 0.0, "entry": 0.0, "total": CAPITAL_BTC, "pnl": 0.0}

def get_closes(limit=200):
    # FIX PARA RENDER USA - usa vision que no bloquea
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={SYMBOL}&interval=1m&limit={limit}"
    try:
        data = requests.get(url, timeout=15).json()
        closes = [float(c[4]) for c in data]
        return closes
    except Exception as e:
        print(f"Error Binance USA: {e}")
        return [111000 + i*0.5 for i in range(limit)] # datos provisorios para no romper grafico

def calc_rsi(prices, period=14):
    if len(prices) < period+1: return 50.0
    gains, losses = 0, 0
    for i in range(1, period+1):
        d = prices[-i] - prices[-i-1]
        if d > 0: gains += d
        else: losses -= d
    if losses == 0: return 70.0
    rs = (gains/period) / (losses/period)
    return 100 - (100 / (1 + rs))

def calc_ema(prices, span):
    k = 2 / (span + 1)
    ema = prices[0]
    for p in prices[1:]: ema = p * k + ema * (1-k)
    return ema

def generar_grafico(closes):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10,5), facecolor='black')
    ax.set_facecolor('black')
    data = closes[-100:]
    ax.plot(data, color='#00FF88', linewidth=2.5, label='BTC')
    if estado["entry"] > 0:
        objetivo = estado["entry"] * (1 + TP_PCT)
        sl = estado["entry"] * (1 - SL_PCT)
        ax.axhline(estado["entry"], color='white', linestyle='--', linewidth=1, label=f'Entrada {estado["entry"]:.2f}')
        ax.axhline(objetivo, color='#00FF00', linestyle=':', linewidth=1.5, label=f'Obj +0.6% {objetivo:.2f}')
        ax.axhline(sl, color='#FF3333', linestyle=':', linewidth=1.5, label=f'SL -0.6% {sl:.2f}')
    ax.set_title(f'LOBO SCALPING V23 - BTC {closes[-1]:.2f} - $100 + $5 BNB', color='white', fontsize=11)
    ax.legend(facecolor='black', edgecolor='white', labelcolor='white', fontsize=8)
    ax.tick_params(colors='white')
    plt.tight_layout()
    plt.savefig("chart.png", facecolor='black', dpi=120)
    plt.close()

def enviar_telegram(precio, rsi, ema9, ema20, ema200):
    if not TG_TOKEN or not CHAT_ID: return
    pnl_pct = ((estado["total"] - CAPITAL_BTC) / CAPITAL_BTC * 100) if CAPITAL_BTC else 0
    objetivo = estado["entry"] * (1 + TP_PCT) if estado["entry"] else 0
    sl = estado["entry"] * (1 - SL_PCT) if estado["entry"] else 0
    texto = f"""
🐺 *LOBO BOT V23 - SCALPING 0.6%*

💰 *Capital:* ${estado['capital']:.2f}
₿ *BTC:* {estado['btc']:.6f} (~${estado['btc']*precio:.2f})
📊 *Total:* ${estado['total']:.2f}
📈 *P&L:* ${estado['pnl']:.2f} ({pnl_pct:.2f}%)

🎯 *Vendiendo:*
   Entrada: ${estado['entry']:.2f}
   Objetivo: ${objetivo:.2f} (+0.6%)
   SL: ${sl:.2f} (-0.6%)
   Actual: ${precio:.2f}

📉 *Indicadores:*
   RSI: {rsi:.1f}
   EMA9: {ema9:.2f}
   EMA20: {ema20:.2f}
   EMA200: {ema200:.2f}

💵 *BNB Comisiones:* ${CAPITAL_BNB}
🔗 *Grafico:* {RENDER_URL}
"""
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=10)
    except: pass

@app.route('/')
def home():
    return f"""
    <html><head><title>LoboBot V23</title><meta http-equiv='refresh' content='60'></head>
    <body style='background:black;color:white;text-align:center;font-family:Arial'>
    <h2>LoboBot22 GRAFICO - VIVO - SCALPING 0.6% - ${CAPITAL_BTC} + ${CAPITAL_BNB} BNB</h2>
    <h3>Total: ${estado['total']:.2f} | P&L: ${estado['pnl']:.2f} | BTC: {estado['btc']:.6f}</h3>
    <img src='/chart?v={time.time()}' style='width:95%;max-width:1000px;border:2px solid #00FF88;border-radius:10px'>
    <p><a href='/chart' style='color:#00FF88'>Ver solo imagen</a> - Se actualiza cada 60s</p>
    </body></html>
    """

@app.route('/chart')
def chart():
    try:
        closes = get_closes()
        generar_grafico(closes)
    except Exception as e:
        print(f"Error chart route: {e}")
        generar_grafico([111000]*100)
    return send_file("chart.png", mimetype='image/png')

def loop_trading():
    while True:
        try:
            closes = get_closes()
            precio = closes[-1]
            rsi = calc_rsi(closes)
            ema9 = calc_ema(closes, 9)
            ema20 = calc_ema(closes, 20)
            ema200 = calc_ema(closes, 200)

            if estado["btc"] == 0 and ema9 > ema20 and rsi < 42:
                estado["btc"] = estado["capital"] / precio
                estado["entry"] = precio
                estado["capital"] = 0

            if estado["btc"] > 0:
                generar_grafico(closes)
                enviar_telegram(precio, rsi, ema9, ema20, ema200)
                objetivo = estado["entry"] * (1 + TP_PCT)
                sl = estado["entry"] * (1 - SL_PCT)
                if precio >= objetivo or precio <= sl:
                    estado["capital"] = estado["btc"] * precio
                    estado["total"] = estado["capital"] + CAPITAL_BNB
                    estado["pnl"] = estado["total"] - (CAPITAL_BTC + CAPITAL_BNB)
                    estado["btc"] = 0
                    estado["entry"] = 0
            time.sleep(60)
        except Exception as e:
            print(f"Error loop: {e}")
            time.sleep(15)

if __name__ == "__main__":
    import threading
    threading.Thread(target=loop_trading, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
