# LOBO V32.2 - VISTA PRO
from flask import Flask
import threading, time, random, os
from datetime import datetime

app = Flask(__name__)

USDT_INICIAL = 85.27
BTC = 0.001
PNL = 55.73
PRECIO_COMPRA = 152753
TRADES = 267
PRECIO_ACTUAL = 150067
ESTADO = "COMPRADO"
HISTORIAL = [
    "13:24:01 COMPRA a $152753",
    "13:23:37 VENTA +0.80% | +$1.20",
    "13:09:06 VENTA +0.86% | +$1.15",
    "13:02:34 VENTA +0.81% | +$1.10"
]

def bot_loop():
    global PNL, PRECIO_COMPRA, TRADES, PRECIO_ACTUAL, ESTADO, HISTORIAL
    while True:
        try:
            PRECIO_ACTUAL *= (1 + random.uniform(-0.004, 0.004))
            if ESTADO == "COMPRADO":
                g = (PRECIO_ACTUAL - PRECIO_COMPRA) / PRECIO_COMPRA
                if g >= 0.008:
                    PNL += 1.2
                    TRADES += 1
                    h = datetime.now().strftime("%H:%M:%S")
                    HISTORIAL.insert(0, f"{h} VENTA +{g*100:.2f}%")
                    HISTORIAL = HISTORIAL[:6]
                    ESTADO = "VENDIDO"
            else:
                if random.random() > 0.7:
                    PRECIO_COMPRA = PRECIO_ACTUAL
                    TRADES += 1
                    h = datetime.now().strftime("%H:%M:%S")
                    HISTORIAL.insert(0, f"{h} COMPRA ${PRECIO_ACTUAL:.0f}")
                    HISTORIAL = HISTORIAL[:6]
                    ESTADO = "COMPRADO"
            time.sleep(4)
        except:
            time.sleep(5)

@app.route('/')
def home():
    if ESTADO == "COMPRADO":
        g = (PRECIO_ACTUAL - PRECIO_COMPRA) / PRECIO_COMPRA * 100
        usdt = USDT_INICIAL + PNL + (PRECIO_ACTUAL - PRECIO_COMPRA)*0.001
        barra = max(0, min(100, (g + 3) / 3.8 * 100))
    else:
        g = 0
        usdt = USDT_INICIAL + PNL
        barra = 0
    color_g = "#00c853" if g >= 0 else "#ff1744"
    bg_g = "#e8f5e9" if g >= 0 else "#ffebee"
    estado_badge = "🟢 COMPRADO" if ESTADO=="COMPRADO" else "🟡 ESPERANDO COMPRA"

    return f"""
    <html><head><meta http-equiv="refresh" content="3"><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;background:#f5f7fb;margin:0;padding:12px}}
    .card{{background:white;border-radius:16px;padding:16px;max-width:400px;margin:10px auto;box-shadow:0 2px 12px rgba(0,0,0,0.08)}}
    .header{{text-align:center;padding:10px}}
    .demo{{background:#fff3cd;color:#856404;padding:8px;border-radius:8px;text-align:center;font-size:12px;font-weight:bold;margin-bottom:12px;border:1px solid #ffeaa7}}
    .big{{font-size:28px;font-weight:800;color:#1a1a1a}}
    .sub{{font-size:13px;color:#666}}
    .row{{display:flex;justify-content:space-between;margin:10px 0}}
    .badge{{background:{bg_g};color:{color_g};padding:4px 10px;border-radius:20px;font-weight:bold;font-size:13px}}
    .bar{{background:#eee;height:8px;border-radius:10px;overflow:hidden;margin:8px 0}}
    .fill{{background:{color_g};height:100%;width:{barra:.0f}%;transition:width 0.5s}}
    .hist{{font-size:12px;color:#555;line-height:1.6}}
    .footer{{text-align:center;font-size:11px;color:#999;margin-top:10px}}
    </style></head><body>
    <div class="card"><div class="header"><div style="font-size:14px;color:#666">PROYECTO FAMILIA LOBO</div><div style="font-weight:800;font-size:18px">LOBO V32.2 PRO</div></div>
    <div class="demo">🔒 MODO DEMO - SIN DINERO REAL</div>
    <div class="card" style="margin:0;padding:12px;background:#f8f9ff;border:1px solid #e0e7ff">
        <div class="sub">Balance Total</div>
        <div class="big">${usdt:.2f} USDT</div>
        <div class="row"><span class="sub">Inicial: ${USDT_INICIAL}</span><span style="color:#00c853;font-weight:bold">+${PNL:.2f} ganancia</span></div>
    </div>
    <div class="row" style="margin-top:14px"><span class="sub">Operación actual</span><span class="badge">{estado_badge}</span></div>
    <div class="row"><span>BTC: {BTC:.5f}</span><span>${PRECIO_ACTUAL:.0f}</span></div>
    <div class="row"><span class="sub">Ganancia flotante</span><span class="badge" style="background:{bg_g};color:{color_g}">{g:+.2f}%</span></div>
    <div class="bar"><div class="fill"></div></div>
    <div class="sub" style="text-align:center">Vende automático en +0.80% | {TRADES} trades</div>
    <div style="margin-top:14px"><div class="sub" style="font-weight:bold;margin-bottom:6px">📋 Últimos movimientos</div><div class="hist">{"<br>".join(HISTORIAL)}</div></div>
    <div class="footer">Bot 24/7 en Render • Aunque apagues la compu • Estrategia propia</div>
    </div></body></html>
    """

threading.Thread(target=bot_loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
