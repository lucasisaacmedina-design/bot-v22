import os, time, requests
from flask import Flask, send_file
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- CONFIG FINAL LOBO - V23 135 LINEAS LIVIANO ---
CAPITAL_BTC = 100.0
CAPITAL_BNB = 5.0
TP_PCT = 0.006 # 0.6% SCALPING
SL_PCT = 0.006 # 0.6% SCALPING
SYMBOL = "BTCUSDT"
TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://bot-v22.onrender.com")

app = Flask(__name__)
estado = {"capital": CAPITAL_BTC, "btc": 0.0, "entry": 0.0, "total": CAPITAL_BTC, "pnl": 0.0}

def get_closes(limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval=1m&limit={limit}"
    data = requests.get(url, timeout=10).json()
    return [float(c[4]) for c in data]

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
    ax.plot(data, color='#00FF88', linewidth=2, label='BTC')
    # Lineas de objetivo y SL si esta comprado
    if estado["entry"] > 0:
        objetivo = estado["entry"] * (1 + TP_PCT)
        sl = estado["entry"] * (1 - SL_PCT)
        ax.axhline(estado["entry"], color='white', linestyle='--', label=f'Entrada {estado["entry"]:.2f}')
        ax.axhline(objetivo, color='#00FF00', linestyle=':', label=f'Objetivo +0.6% {objetivo:.2f}')
        ax.axhline(sl, color='#FF3333', linestyle=':', label=f'SL -0.6% {sl:.2f}')
    ax.set_title(f'LOBO SCALPING V23 - BTC {closes[-1]:.2f}', color='white')
    ax.legend(facecolor='black', edgecolor='white', labelcolor='white')
    ax.tick_params(colors='white')
    plt.tight_layout()
    plt.savefig("chart.png", facecolor='black', dpi=120)
    plt.close()

def enviar_telegram(precio, rsi, ema9, ema20, ema200):
    if not TG_TOKEN: return
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

💵 *BNB Comisiones:* ${CAPITAL_BNB} (para 25% descuento)
🔗 *Grafico:* {RENDER_URL}/chart
"""
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=10)
    except: pass

@app.route('/')
def home():
    # Pagina que SI muestra el grafico como querias
    return f"""
    <html><head><title>LoboBot V23</title><meta http-equiv='refresh' content='60'></head>
    <body style='background:black;color:white;text-align:center;font-family:Arial'>
    <h2>LoboBot22 GRAFICO - VIVO - SCALPING 0.6% - ${CAPITAL_BTC} + ${CAPITAL_BNB} BNB</h2>
    <h3>Total: ${estado['total']:.2f} | P&L: ${estado['pnl']:.2f}</h3>
    <img src='/chart?v={time.time()}' style='width:95%;max-width:1000px;border:2px solid #00FF88;border-radius:10px'>
    <p><a href='/chart' style='color:#00FF88'>Ver imagen directa</a> - Se actualiza cada 60s</p>
    </body></html>
    """

@app.route('/chart')
def chart():
    closes = get_closes()
    generar_grafico(closes)
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
            print(f"Error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    import threading
    threading.Thread(target=loop_trading, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
