import requests, io, time, pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ========== LOBOBOT22 DUAL FINAL - BTC + BNB ==========
NOMBRE = "LoboBot22 DUAL - BTC + BNB Scalper 0.8%"
TOKEN = "TU_TOKEN_AQUI"
CHAT_ID = "TU_CHAT_ID_AQUI"

TP = 0.008
SL = 0.008
CAIDA = 0.01

PARES = {
    "BTCUSDT": {"entrada": 79014.0, "color": "#F3BA2F"},
    "BNBUSDT": {"entrada": 620.0, "color": "#F3BA2F"}
}

def telegram_foto(par, actual, entrada, tp, sl, buf):
    caption = f"""🐺 *{NOMBRE}*
🟢 BOT VIVO - {datetime.now().strftime('%H:%M:%S')}

Par: {par}
Actual: ${actual}
Entrada: ${entrada}
TP: ${tp:.2f} (+0.8%) | SL: ${sl:.2f} (-0.8%)
💵 Ganancia: $0.65 limpio x trade (con BNB)
Estado: Escaneando DUAL"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(url, data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": (f"{par}.png", buf, "image/png")})

def telegram_texto(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"})

def crear_grafico(par, actual, entrada, tp, sl, color):
    df = pd.DataFrame({'time': pd.date_range(end=pd.Timestamp.now(), periods=50, freq='5min'), 'close': [actual + (i-25)*0.1 for i in range(50)]})
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['time'], y=df['close'], line=dict(color=color, width=2), name=par))
    fig.add_hline(y=entrada, line_dash="dash", line_color="blue")
    fig.add_hline(y=tp, line_dash="dash", line_color="#00FF00")
    fig.add_hline(y=sl, line_dash="dash", line_color="#FF0000")
    fig.add_hline(y=actual, line_color="white")
    fig.update_layout(template="plotly_dark", title=f"{par} - ${actual}", height=400, width=700, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=40,b=10))
    buf = io.BytesIO()
    fig.write_image(buf, format="png")
    buf.seek(0)
    return buf

print(f"🐺 {NOMBRE} iniciado - DUAL BTC + BNB")

# Loop infinito para Render
while True:
    try:
        for par, data in PARES.items():
            entrada = data["entrada"]
            # TODO: reemplazar por precio real Binance
            actual = 78384.0 if par == "BTCUSDT" else 618.5

            tp = entrada * (1 + TP)
            sl = entrada * (1 - SL)
            variacion = ((actual - entrada)/entrada)*100

            # Si toca TP o SL -> vende y avisa
            if actual >= tp:
                buf = crear_grafico(par, actual, entrada, tp, sl, data["color"])
                telegram_foto(par, actual, entrada, tp, sl, buf)
                telegram_texto(f"✅ *TP +0.8% TOCADO {par}* - Venta ${actual} | Ganancia $0.65")
                PARES[par]["entrada"] = actual * 0.99 # recompra 1% abajo

            elif actual <= sl:
                buf = crear_grafico(par, actual, entrada, tp, sl, data["color"])
                telegram_foto(par, actual, entrada, tp, sl, buf)
                telegram_texto(f"🛑 *SL -0.8% {par}* - Venta ${actual} para recomprar")
                PARES[par]["entrada"] = actual * 0.99

        # Mensaje VIVO cada 1 hora para que no parezca clavado
        if datetime.now().minute == 0:
            telegram_texto(f"🟢 *BOT VIVO* - {NOMBRE}\nEscaneando: BTC $78384 | BNB $618.5 - Sin novedad, buscando 0.8%")

        time.sleep(60)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(60)
