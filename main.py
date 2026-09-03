# LOBO BOT V33.4 - RENTABLE NETO REAL - FILTRO ANTI-COMISION
# Objetivo: Solo trades que dejen ganancia DESPUES de Binance

import os, time, random, threading
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

COMISION_TOTAL = 0.002  # 0.1% x 2 (ida y vuelta) = 0.2%
CAPITAL_INICIAL = 143.99 # Donde quedaste
TP_MINIMO_BRUTO = 0.005  # 0.5% bruto = 0.3% neto real. Si no da eso, NO ENTRA
OBJETIVO_NETO = 15.00

estado = {
    "capital_actual": CAPITAL_INICIAL,
    "capital_inicial_hoy": CAPITAL_INICIAL,
    "comisiones_totales": 0.0,
    "trades_totales": 0,
    "trades_ganados": 0,
    "trades_descartados_por_comision": 0,
    "ganancia_bruta_hoy": 0.0,
    "ganancia_neta_hoy": 0.0,
    "ultimo_trade": None,
    "status": "V33.4 FILTRANDO"
}

def ejecutar_trade_inteligente():
    # Simula señal de tu estrategia
    variacion_potencial = random.uniform(-0.008, 0.012)

    # --- FILTRO CLAVE V33.4: ANTI-COMISION ---
    if variacion_potencial < TP_MINIMO_BRUTO:
        estado["trades_descartados_por_comision"] += 1
        print(f"[DESCARTADO] Señal de {variacion_potencial*100:.2f}% es muy chica, no cubre comisión. No entro.")
        return None

    # Si pasó el filtro, recién ahí entro
    monto_trade = estado["capital_actual"] * 0.05
    ganancia_bruta = monto_trade * variacion_potencial
    comision = monto_trade * COMISION_TOTAL
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
        "senal": f"{variacion_potencial*100:.2f}%",
        "bruta": round(ganancia_bruta, 4),
        "comision": round(comision, 4),
        "neta": round(ganancia_neta, 4)
    }
    print(f"[ACEPTADO] NETA: ${ganancia_neta:.4f} | Bruta: ${ganancia_bruta:.4f} | Comi: -${comision:.4f}")
    return ganancia_neta

def loop_bot():
    print(f"--- LOBO V33.4 INICIADO - Solo trades >{TP_MINIMO_BRUTO*100}% ---")
    while True:
        ejecutar_trade_inteligente()
        # Ahora cada 3 min como tu bot real, no cada 10 seg
        time.sleep(180) 

@app.route('/')
def home():
    win_rate = (estado["trades_ganados"] / estado["trades_totales"] * 100) if estado["trades_totales"] > 0 else 0
    return jsonify({
        "version": "V33.4 RENTABLE",
        "filosofia": "Ser rico, no parecerlo",
        "capital_actual_ficticio": round(estado["capital_actual"], 2),
        "ganancia_bruta_hoy": round(estado["ganancia_bruta_hoy"], 2),
        "comisiones_pagadas": round(estado["comisiones_totales"], 2),
        "ganancia_neta_real": round(estado["ganancia_neta_hoy"], 2),
        "trades_ejecutados": estado["trades_totales"],
        "trades_descartados_para_no_perder": estado["trades_descartados_por_comision"],
        "win_rate": f"{win_rate:.1f}%",
        "status": estado["status"],
        "ultimo_trade": estado["ultimo_trade"],
        "filtro_actual": f"Solo entra si gana >{TP_MINIMO_BRUTO*100}% bruto"
    })

@app.route('/health')
def health(): return "OK", 200

threading.Thread(target=loop_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
