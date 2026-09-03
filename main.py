# LOBO V32.1 FIX - PROLIJO
from flask import Flask
import threading, time, random, os
from datetime import datetime
app = Flask(__name__)
USDT_INICIAL = 85.27
USDT = 138.12
BTC = 0.001
PNL = 55.73
PRECIO_COMPRA = 152753
TRADES = 267
PRECIO_ACTUAL = 150067
ESTADO = "COMPRADO"
HISTORIAL = [
    "13:24:01 COMPRA a $152753 | Ganancia acumulada $55.73",
    "13:23:37 VENTA +0.80% | Ganancia +$1.20",
    "13:09:06 VENTA +0.86% | Ganancia +$1.15",
    "13:02:34 VENTA +0.81% | Ganancia +$1.10"
]
def bot_loop():
    global USDT, BTC, PNL, PRECIO_COMPRA, TRADES, PRECIO_ACTUAL, ESTADO, HISTORIAL
    while True:
        try:
            cambio = random.uniform(-0.004, 0.004)
            PRECIO_ACTUAL = PRECIO_ACTUAL * (1 + cambio)
            if ESTADO == "COMPRADO":
                ganancia = (PRECIO_ACTUAL - PRECIO_COMPRA) / PRECIO_COMPRA
                if ganancia >= 0.008:
                    PNL += 1.2
                    TRADES += 1
                    hora = datetime.now().strftime("%H:%M:%S")
                    HISTORIAL.insert(0, f"{hora} VENTA +{ganancia*100:.2f}% | +$1.20")
                    HISTORIAL = HISTORIAL[:5]
                    ESTADO = "VENDIDO"
            else:
                if random.random() > 0.7:
                    PRECIO_COMPRA = PRECIO_ACTUAL
                    TRADES += 1
                    hora = datetime.now().strftime("%H:%M:%S")
                    HISTORIAL.insert(0, f"{hora} COMPRA a ${PRECIO_ACTUAL:.0f}")
                    HISTORIAL = HISTORIAL[:5]
                    ESTADO = "COMPRADO"
            time.sleep(4)
        except:
            time.sleep(5)
@app.route('/')
def home():
    if ESTADO == "COMPRADO":
        g = (PRECIO_ACTUAL - PRECIO_COMPRA) / PRECIO_COMPRA * 100
        usdt_mostrado = USDT_INICIAL + PNL + (PRECIO_ACTUAL - PRECIO_COMPRA)*0.001
    else:
        g = 0
        usdt_mostrado = USDT_INICIAL + PNL
    color = "green" if g >=0 else "red"
    estado_txt = f"COMPRADO ${PRECIO_COMPRA:.0f} | Ahora {g:+.2f}% | Vende en +0.8%" if ESTADO=="COMPRADO" else "VENDIDO - Buscando compra"
    return f"""<html><head><meta http-equiv="refresh" content="3"><style>body{{font-family:monospace;background:#0a0a0a;color:#00ff00;padding:15px}}.box{{border:2px solid #00ff00;padding:15px;border-radius:10px;max-width:420px;margin:auto}}.demo{{background:yellow;color:black;padding:6px;text-align:center;font-weight:bold;font-size:13px}}</style></head><body><div class="box"><div class="demo">MODO DEMO - SIN DINERO REAL - PROYECTO FAMILIA LOBO</div><h2>LOBO V32.1 - RENDER 24/7</h2>USDT: ${usdt_mostrado:.2f} (Inicial ${USDT_INICIAL})<br>BTC: {BTC:.6f}<br>Precio BTC: ${PRECIO_ACTUAL:.0f}<br>PnL: <b>${PNL:.2f}</b><br>Trades: {TRADES}<br>Ganancia ahora: <span style="color:{color}">{g:+.2f}%</span><br>{estado_txt}<br><br><small>Bot corriendo aunque apagues tu compu - 24/7<br>Estrategia propia - Sin terceros</small><br><br>{"<br>".join(HISTORIAL)}</div></body></html>"""
threading.Thread(target=bot_loop, daemon=True).start()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
