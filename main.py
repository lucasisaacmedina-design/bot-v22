import os, time, requests, threading, io, datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string

# CONFIGURACION LOBO V25 DUAL COMPLETO 227 LINEAS
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
URL_BOT = "https://bot-v22.onrender.com"

TP_PORCENTAJE = 0.006 # 0.6% SCALPING
SL_PORCENTAJE = 0.006 # 0.6% STOP LOSS
EMA_PERIODO = 50
RSI_PERIODO = 14
SYMBOLS_LIST = ["BTCUSDT", "BNBUSDT"]

app = Flask(__name__)

# ESTADO GLOBAL DUAL
estado_global = {
    "BTCUSDT": {
        "entry": 78085.0,
        "qty": 0.000189,
        "capital": 14.76,
        "trades": 1,
        "wins": 1,
        "pnl": -0.04,
        "pnl_pct": -0.27,
        "precio": 78830.0,
        "ema": 78452.0,
        "rsi": 74.0,
        "closes": [78830]*100
    },
    "BNBUSDT": {
        "entry": 640.0,
        "qty": 0.02,
        "capital": 12.80,
        "trades": 1,
        "wins": 1,
        "pnl": 0.10,
        "pnl_pct": 0.15,
        "precio": 756.0,
        "ema": 751.0,
        "rsi": 79.0,
        "closes": [756]*100
    }
}

def obtener_klines_binance(symbol, limit=200):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=5m&limit={limit}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        closes = [float(k[4]) for k in data]
        return closes
    except Exception as e:
        print(f"Error klines {symbol}: {e}")
        return [estado_global[symbol]["precio"]]*limit

def calcular_ema_lobo(closes, periodo):
    try:
        ema = closes[0]
        k = 2 / (periodo + 1)
        for c in closes[1:]:
            ema = c * k + ema * (1 - k)
        return ema
    except:
        return closes[-1]

def calcular_rsi_lobo(closes, periodo=14):
    try:
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-periodo:]]
        losses = [-d if d < 0 else 0 for d in deltas[-periodo:]]
        avg_gain = sum(gains) / periodo
        avg_loss = sum(losses) / periodo + 0.000001
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except:
        return 50.0

def actualizar_datos_simbolo(symbol):
    closes = obtener_klines_binance(symbol, 200)
    precio_actual = closes[-1]
    ema_actual = calcular_ema_lobo(closes, EMA_PERIODO)
    rsi_actual = calcular_rsi_lobo(closes, RSI_PERIODO)
    estado_global[symbol]["precio"] = precio_actual
    estado_global[symbol]["ema"] = ema_actual
    estado_global[symbol]["rsi"] = rsi_actual
    estado_global[symbol]["closes"] = closes
    return closes, precio_actual, ema_actual, rsi_actual

def crear_grafico_estilo_lobo(symbol, closes, ema_val, precio_val, rsi_val):
    plt.figure(figsize=(8, 4.5), facecolor='#000000')
    ax = plt.gca()
    ax.set_facecolor('#000000')
    plt.plot(closes[-100:], color='#00ff88', linewidth=1.9, label=f'Precio {symbol}')
    ema_line = []
    e = closes[0]
    k = 2 / (EMA_PERIODO + 1)
    for c in closes:
        e = c * k + e * (1 - k)
        ema_line.append(e)
    plt.plot(ema_line[-100:], color='#ffaa00', linestyle='--', linewidth=1.3, label=f'EMA{EMA_PERIODO}')
    pct_actual = ((precio_val - estado_global[symbol]["entry"]) / estado_global[symbol]["entry"] * 100)
    plt.title(f'{symbol} ${precio_val:.2f} | EMA{EMA_PERIODO} ${ema_val:.0f} | RSI {rsi_val:.0f} | {pct_actual:+.2f}%', color='white', fontsize=10, fontweight='bold')
    plt.legend(facecolor='#1a1a1a', edgecolor='#333333', fontsize=7, labelcolor='white', loc='upper left')
    plt.tick_params(colors='#888888', labelsize=7)
    plt.grid(color='#222222', linestyle='--', linewidth=0.4, alpha=0.6)
    plt.xlabel('Velas 5m', color='gray', fontsize=7)
    plt.ylabel('Precio USDT', color='gray', fontsize=7)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='#000000', bbox_inches='tight', dpi=150)
    plt.close()
    buf.seek(0)
    return buf

def enviar_texto_telegram(texto):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": texto, "parse_mode": "HTML"}
        requests.post(url, data=payload, timeout=15)
    except Exception as e:
        print(f"Error telegram texto: {e}")

def enviar_foto_telegram(buf, caption_text):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {"photo": ("grafico_lobo.png", buf, "image/png")}
        data = {"chat_id": CHAT_ID, "caption": caption_text}
        requests.post(url, data=data, files=files, timeout=25)
    except Exception as e:
        print(f"Error telegram foto: {e}")

def loop_principal_lobo():
    last_update_id = 0
    print("LOOP LOBO V25 DUAL 227 LINEAS INICIADO")
    while True:
        try:
            for sym in SYMBOLS_LIST:
                actualizar_datos_simbolo(sym)
            try:
                url_updates = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=8"
                resp = requests.get(url_updates, timeout=12).json()
                for upd in resp.get("result", []):
                    last_update_id = upd["update_id"]
                    mensaje_texto = upd.get("message", {}).get("text", "")
                    if "/estado" in mensaje_texto:
                        hora_now = datetime.datetime.now().strftime('%H:%M:%S')
                        texto_respuesta = f"💰 ESTADO LOBO V25 DUAL COMPLETO 227 LINEAS - {hora_now}\n\n"
                        total_cuenta = 0.0
                        for s in SYMBOLS_LIST:
                            d = estado_global[s]
                            precio = d["precio"]
                            entry = d["entry"]
                            pct = ((precio - entry) / entry * 100) if entry else 0
                            objetivo_tp = entry * (1 + TP_PORCENTAJE)
                            objetivo_sl = entry * (1 - SL_PORCENTAJE)
                            total_cuenta += d["qty"] * precio
                            texto_respuesta += f"--- {s} ---\n"
                            texto_respuesta += f"💵 Capital: ${d['capital']:.2f}\n"
                            texto_respuesta += f"₿ Qty: {d['qty']}\n"
                            texto_respuesta += f"📈 Precio: ${precio:.2f} | EMA{EMA_PERIODO}: ${d['ema']:.0f} | RSI: {d['rsi']:.0f}\n"
                            texto_respuesta += f"💼 Entry: ${entry:.2f} | P&L: {pct:+.2f}%\n"
                            texto_respuesta += f"💰 Vendiendo: {pct:+.2f}% -> Objetivo +0.6% (${objetivo_tp:.2f}) | SL -0.6% (${objetivo_sl:.2f})\n\n"
                        texto_respuesta += f"💼 Total Cuenta: ${total_cuenta:.2f}\n"
                        texto_respuesta += f"TP +0.6% | SL -0.6% | EMA{EMA_PERIODO}+RSI SCALPING DUAL\n"
                        texto_respuesta += f"🔗 {URL_BOT}"
                        enviar_texto_telegram(texto_respuesta)
            except Exception as e:
                print(f"Error check telegram: {e}")
            if int(time.time()) % 300 < 12:
                for s in SYMBOLS_LIST:
                    d = estado_global[s]
                    closes = d.get("closes", [d["precio"]]*100)
                    pct = ((d["precio"] - d["entry"]) / d["entry"] * 100) if d["entry"] else 0
                    objetivo = d["entry"] * (1 + TP_PORCENTAJE)
                    buf_img = crear_grafico_estilo_lobo(s, closes, d["ema"], d["precio"], d["rsi"])
                    caption_final = f"📈 LOBO V25 DUAL 227L - {s}\n💵 ${d['precio']:.2f} | EMA{EMA_PERIODO} ${d['ema']:.0f} | RSI {d['rsi']:.0f}\n💰 Vendiendo: {pct:+.2f}% -> Objetivo +0.6% (${objetivo:.2f}) | SL -0.6%\nTP +0.6% | SL -0.6% | SCALPING DUAL\n🔗 {URL_BOT}"
                    enviar_foto_telegram(buf_img, caption_final)
                time.sleep(40)
            time.sleep(4)
        except Exception as e:
            print(f"Error loop principal: {e}")
            time.sleep(10)

HTML_DASHBOARD_COMPLETO = """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lobo V25 Dual 227L</title>
<style>
body{background:#0e0e0e;color:white;font-family:Arial;margin:0;padding:12px}
.card{background:#1a1a1a;border:1px solid #333;padding:12px;border-radius:12px;margin-bottom:12px}
.badge{padding:4px 10px;border-radius:8px;font-size:11px;font-weight:bold}
.green{background:#00ff8844;color:#00ff88;border:1px solid #00ff88}
.orange{background:#ffaa0044;color:#ffaa00;border:1px solid #ffaa00}
.chart{height:750px;border:1px solid #333;border-radius:12px;overflow:hidden;margin-top:10px;background:#000}
#tv{height:750px}
h2{color:#00ff88}
</style></head><body>
<h2>🐺 LOBO V25 DUAL 227 LINEAS - SCALPING 0.6% BTC+BNB</h2>
<div style="display:flex;gap:12px;flex-wrap:wrap">
{% for sym,data in estado.items() %}
<div class="card">
<b style="font-size:16px">{{sym}}</b> <span class="badge green">SCALPING 0.6%</span> <span class="badge orange">EMA{{ema}}+RSI</span><br><br>
💵 Capital: ${{ "%.2f"|format(data.capital) }}<br>
₿ Qty: {{data.qty}}<br>
📈 Precio: ${{ "%.2f"|format(data.precio) }} | EMA{{ema}}: ${{ "%.0f"|format(data.ema) }} | RSI: {{ "%.0f"|format(data.rsi) }}<br>
💼 Entry: ${{ data.entry }} | P&L: {{ "%.2f"|format(((data.precio-data.entry)/data.entry*100)) }}%<br>
💰 Vendiendo: {{ "%.2f"|format(((data.precio-data.entry)/data.entry*100)) }}% -> Objetivo +0.6% (${{ "%.2f"|format(data.entry*1.006) }}) | SL -0.6%<br>
</div>
{% endfor %}
</div>
<div class="chart"><div id="tv"></div></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"tv","height":750,"style":"1","timezone":"America/Argentina/Buenos_Aires"})
</script>
<p style="color:gray;font-size:12px">🔗 {{url}} | Actualizado: {{hora}} | V25 227L DUAL COMPLETO</p>
</body></html>
"""

@app.route('/')
def dashboard_completo():
    hora_str = datetime.datetime.now().strftime("%H:%M:%S")
    return render_template_string(HTML_DASHBOARD_COMPLETO, estado=estado_global, ema=EMA_PERIODO, url=URL_BOT, hora=hora_str)

threading.Thread(target=loop_principal_lobo, daemon=True).start()

if __name__ == "__main__":
    enviar_texto_telegram("🐺 LoboBot V25 DUAL 227 LINEAS COMPLETO BTC+BNB SCALPING 0.6% + GRAFICO NEGRO LINEA VERDE + DASH 750PX - VIVO")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
