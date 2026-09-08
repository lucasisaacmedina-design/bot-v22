import os, time, requests
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from flask import Flask, send_file

# --- CONFIG FINAL LOBO SCALPING ---
CAPITAL_BTC = 100.0  # USD en BTC
CAPITAL_BNB = 5.0    # USD en BNB para comisiones
TP_PCT = 0.006  # +0.6% SCALPING
SL_PCT = 0.006  # -0.6% SCALPING
SYMBOL_BTC = "BTCUSDT"
SYMBOL_BNB = "BNBUSDT"

TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://tu-bot.onrender.com")

app = Flask(__name__)
estado = {"capital": CAPITAL_BTC, "btc": 0.0, "entry": 0, "total": CAPITAL_BTC, "pnl": 0}

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=200"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=["t","o","h","l","c","v","ct","qv","n","tb","tq","i"])
    df["c"] = df["c"].astype(float)
    return df

def get_rsi_ema(df):
    # RSI 14
    delta = df["c"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    # EMAs para scalping
    ema9 = df["c"].ewm(span=9).mean().iloc[-1]
    ema20 = df["c"].ewm(span=20).mean().iloc[-1]
    ema200 = df["c"].ewm(span=200).mean().iloc[-1]
    return rsi.iloc[-1], ema9, ema20, ema200

def generar_grafico_negro(df, symbol):
    plt.style.use('dark_background')
    df_plot = df.tail(100).copy()
    df_plot.index = pd.to_datetime(df_plot["t"], unit='ms')
    # Grafico negro que te gustaba
    fig, ax = plt.subplots(figsize=(8,4), facecolor='black')
    ax.set_facecolor('black')
    ax.plot(df_plot.index, df_plot["c"], color='#00FF88', label=symbol)
    ax.set_title(f"{symbol} - LOBO SCALPING 0.6%", color='white')
    ax.tick_params(colors='white')
    plt.savefig(f"{symbol}_chart.png", facecolor='black')
    plt.close()

def enviar_telegram_formato_lindo(precio, rsi, ema9, ema20, ema200, objetivo, sl):
    pnl_pct = ((estado["total"] - CAPITAL_BTC) / CAPITAL_BTC) * 100
    # FORMATO ENTENDIBLE QUE TE GUSTABA
    mensaje = f"""
🐺 **LOBO SCALPING V23 - 135 LINEAS**

💰 **Capital:** ${estado['capital']:.2f}
₿ **BTC:** {estado['btc']:.6f}
📊 **Total:** ${estado['total']:.2f}
📈 **P&L:** ${estado['pnl']:.2f} ({pnl_pct:.2f}%)

🎯 **Vendiendo:**
   Objetivo: ${objetivo:.2f} (+0.6%)
   SL: ${sl:.2f} (-0.6%)

📉 **Indicadores:**
   RSI: {rsi:.1f}
   EMA9: {ema9:.2f}
   EMA20: {ema20:.2f}
   EMA200: {ema200:.2f}

💵 **BNB Comisiones:** ${CAPITAL_BNB} (25% OFF)
🔗 **Gráfico:** {RENDER_URL}/chart
"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"})

@app.route('/')
def home():
    return f"LOBO SCALPING 0.6% - BTC ${CAPITAL_BTC} + BNB ${CAPITAL_BNB} OK - <a href='/chart'>Ver Grafico</a>"

@app.route('/chart')
def chart():
    df = get_klines(SYMBOL_BTC)
    generar_grafico_negro(df, SYMBOL_BTC)
    return send_file("BTCUSDT_chart.png", mimetype='image/png')

def loop_trading():
    while True:
        try:
            df_btc = get_klines(SYMBOL_BTC)
            df_bnb = get_klines(SYMBOL_BNB)
            precio_btc = df_btc["c"].iloc[-1]
            precio_bnb = df_bnb["c"].iloc[-1]
            
            rsi, ema9, ema20, ema200 = get_rsi_ema(df_btc)
            
            # LOGICA SCALPING
            if estado["btc"] == 0 and ema9 > ema20 and rsi < 40:
                # COMPRAR
                estado["btc"] = estado["capital"] / precio_btc
                estado["entry"] = precio_btc
                estado["capital"] = 0
            
            if estado["btc"] > 0:
                objetivo = estado["entry"] * (1 + TP_PCT)
                sl = estado["entry"] * (1 - SL_PCT)
                
                generar_grafico_negro(df_btc, SYMBOL_BTC)
                enviar_telegram_formato_lindo(precio_btc, rsi, ema9, ema20, ema200, objetivo, sl)
                
                if precio_btc >= objetivo or precio_btc <= sl:
                    estado["capital"] = estado["btc"] * precio_btc
                    estado["total"] = estado["capital"] + CAPITAL_BNB
                    estado["pnl"] = estado["total"] - (CAPITAL_BTC + CAPITAL_BNB)
                    estado["btc"] = 0
            
            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    import threading
    threading.Thread(target=loop_trading, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
