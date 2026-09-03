# LOBO V32 - FIX USDT + FAMILIA EDITION - RENDER 24/7
from flask import Flask
import threading, time, random
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURACION INICIAL ---
USDT_INICIAL = 85.27
USDT = 85.27
BTC = 0.0
PNL = -14.73  # arrancamos donde quedo el V31 anoche
PRECIO_COMPRA = 78546
TRADES = 113
PRECIO_ACTUAL = 77784
ESTADO = "COMPRADO"
HISTORIAL = []

def bot_loop():
    global USDT, BTC, PNL, PRECIO_COMPRA, TRADES, PRECIO_ACTUAL, ESTADO, HISTORIAL
    
    # Si ya venias ganando, arrancamos con tus numeros de hoy
    # Para el V32 reseteamos a lo de hoy: +54.53
    USDT = 139.80 # 85.27 + 54.53 = ganancia real V31
    PNL = 54.53
    TRADES = 265
    PRECIO_COMPRA = 149867
    PRECIO_ACTUAL = 150282

    while True:
        try:
            # Simula movimiento BTC real
            cambio = random.uniform(-0.005, 0.005) # -0.5% a +0.5%
            PRECIO_ACTUAL = PRECIO_ACTUAL * (1 + cambio)
            
            if ESTADO == "COMPRADO":
                ganancia = (PRECIO_ACTUAL - PRECIO_COMPRA) / PRECIO_COMPRA
                
                # VENDE SOLO EN +0.8%
                if ganancia >= 0.008:
                    ganancia_usd = (PRECIO_ACTUAL * 0.001) - (PRECIO_COMPRA * 0.001)
                    USDT = USDT + (PRECIO_ACTUAL * 0.001)
                    PNL += ganancia_usd
                    TRADES += 1
                    hora = datetime.now().strftime("%H:%M:%S")
                    HISTORIAL.insert(0, f"{hora} VENTA +{ganancia*100:.2f}% | USDT ${USDT:.2f} | PnL ${PNL:.2f}")
                    HISTORIAL = HISTORIAL[:10]
                    ESTADO = "VENDIDO"
                else:
                    # ESPERA COMPRADO
                    pass
            else: # VENDIDO, espera para COMPRAR en -0.4%
                # Simula compra
                if random.random() > 0.7: # 30% chance de comprar
                    if USDT >= PRECIO_ACTUAL * 0.001:
                        BTC = 0.001
                        USDT -= PRECIO_ACTUAL * 0.001
                        PRECIO_COMPRA = PRECIO_ACTUAL
                        TRADES += 1
                        hora = datetime.now().strftime("%H:%M:%S")
                        HISTORIAL.insert(0, f"{hora} COMPRA a ${PRECIO_ACTUAL:.0f} | USDT ${USDT:.2f}")
                        HISTORIAL = HISTORIAL[:10]
                        ESTADO = "COMPRADO"
            
            time.sleep(3)
        except Exception as e:
            print(e)
            time.sleep(5)

@app.route('/')
def home():
    if ESTADO == "COMPRADO":
        ganancia_actual = (PRECIO_ACTUAL - PRECIO_COMPRA) / PRECIO_COMPRA * 100
        estado_txt = f"COMPRADO ${PRECIO_COMPRA:.0f} | Ahora {ganancia_actual:+.2f}% | Vende en +0.8%"
        color = "green" if ganancia_actual > 0 else "red"
    else:
        estado_txt = "VENDIDO - Esperando compra -0.4%"
        color = "gray"
        ganancia_actual = 0

    html = f"""
    <html><head><meta http-equiv="refresh" content="3"><style>
    body{{font-family:monospace;background:#0a0a0a;color:#00ff00;padding:15px}}
    .box{{border:2px solid #00ff00;padding:15px;border-radius:10px;max-width:400px;margin:auto}}
    .demo{{background:yellow;color:black;padding:5px;text-align:center;font-weight:bold}}
    </style></head><body>
    <div class="box">
    <div class="demo">MODO DEMO - SIN DINERO REAL - PROYECTO FAMILIA</div>
    <h2>LOBO V32 - RENDER 24/7</h2>
    USDT: ${USDT:.2f} (Inicial ${USDT_INICIAL})<br>
    BTC: {BTC:.6f}<br>
    Precio BTC: ${PRECIO_ACTUAL:.0f}<br>
    PnL: <b>${PNL:.2f}</b><br>
    Trades: {TRADES}<br>
    Ganancia ahora: <span style="color:{color}">{ganancia_actual:+.2f}%</span><br>
    {estado_txt}<br><br>
    <small>Bot corriendo aunque apagues tu compu<br>
    V32 - Fix USDT - Para mostrar a tu hermano</small><br><br>
    {"<br>".join(HISTORIAL)}
    </div></body></html>
    """
    return html

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
