# LOBO BOT V33.3 - main.py COMPLETO PARA RENDER
# Plata ficticia, comisiones reales, puerto abierto 24/7
# Filosofía: Ser rico, no parecerlo.

import os
import time
import random
import threading
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

# --- CONFIG REAL ---
COMISION_BINANCE = 0.001  # 0.1% real Binance Spot
CAPITAL_FICTICIO_INICIAL = 144.00
OBJETIVO_DIARIO_NETO = 15.00

# Estado global del bot
estado = {
    "capital_actual": CAPITAL_FICTICIO_INICIAL,
    "capital_inicial_hoy": CAPITAL_FICTICIO_INICIAL,
    "comisiones_totales": 0.0,
    "trades_totales": 0,
    "trades_ganados": 0,
    "ganancia_bruta_hoy": 0.0,
    "ganancia_neta_hoy": 0.0,
    "ultimo_trade": None,
    "status": "INICIANDO",
    "objetivo_cumplido": False
}

def ejecutar_trade():
    monto_trade = estado["capital_actual"] * 0.05
    
    # Simula tu estrategia (acá va tu lógica real después)
    variacion = random.uniform(-0.008, 0.012) 
    ganancia_bruta = monto_trade * variacion
    
    comision = monto_trade * COMISION_BINANCE * 2
    ganancia_neta = ganancia_bruta - comision
    
    estado["capital_actual"] += ganancia_neta
    estado["comisiones_totales"] += comision
    estado["ganancia_bruta_hoy"] += ganancia_bruta
    estado["ganancia_neta_hoy"] += ganancia_neta
    estado["trades_totales"] += 1
    if ganancia_neta > 0:
        estado["trades_ganados"] += 1
    
    estado["ultimo_trade"] = {
        "hora": datetime.now().strftime("%H:%M:%S"),
        "bruta": round(ganancia_bruta, 4),
        "comision": round(comision, 4),
        "neta": round(ganancia_neta, 4)
    }
    
    print(f"[Trade #{estado['trades_totales']}] NETA: ${ganancia_neta:.4f} | Bruta: ${ganancia_bruta:.4f} | Comi: -${comision:.4f} | Capital: ${estado['capital_actual']:.2f}")

def loop_bot():
    estado["status"] = "TRABAJANDO EN SILENCIO"
    print(f"--- LOBO V33.3 INICIADO con ${CAPITAL_FICTICIO_INICIAL} FICTICIOS ---")
    while True:
        ejecutar_trade()
        
        if estado["ganancia_neta_hoy"] >= OBJETIVO_DIARIO_NETO and not estado["objetivo_cumplido"]:
            estado["objetivo_cumplido"] = True
            estado["status"] = "OBJETIVO CUMPLIDO - CAMPANA"
            print(f"🔔 OBJETIVO NETO DE ${OBJETIVO_DIARIO_NETO} CUMPLIDO! NETA HOY: ${estado['ganancia_neta_hoy']:.2f}")
        
        time.sleep(10)  # Un trade cada 10 seg para test rápido. En real poné 180 (3 min)

# --- RUTAS PARA QUE RENDER NO TE APAGUE ---
@app.route('/')
def home():
    profit_pct = (estado["trades_ganados"] / estado["trades_totales"] * 100) if estado["trades_totales"] > 0 else 0
    return jsonify({
        "mensaje": "Lobo V33.3 trabajando en silencio",
        "filosofia": "Ser rico, no parecerlo",
        "capital_actual_ficticio": round(estado["capital_actual"], 2),
        "ganancia_bruta_hoy": round(estado["ganancia_bruta_hoy"], 2),
        "comisiones_pagadas": round(estado["comisiones_totales"], 2),
        "ganancia_neta_real": round(estado["ganancia_neta_hoy"], 2),
        "trades": estado["trades_totales"],
        "win_rate": f"{profit_pct:.1f}%",
        "status": estado["status"],
        "ultimo_trade": estado["ultimo_trade"]
    })

@app.route('/health')
def health():
    return "OK - Lobo vivo", 200

# Iniciar bot en hilo separado
threading.Thread(target=loop_bot, daemon=True).start()

# --- ESTO ES LO QUE TE FALTABA PARA RENDER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
