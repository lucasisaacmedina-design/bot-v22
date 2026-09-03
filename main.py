# LOBO BOT V33.3 - REAL NETO CON COMISIONES - PLATA FICTICIA
# Filosofía: Ser rico, no parecerlo.

import time
import random
from datetime import datetime

# --- CONFIG REAL BINANCE ---
COMISION_BINANCE = 0.001  # 0.1% maker/taker spot real
CAPITAL_FICTICIO_INICIAL = 144.00  # Partimos de donde estás ahora
OBJETIVO_DIARIO = 15.00 # Objetivo neto real

capital_actual = CAPITAL_FICTICIO_INICIAL
capital_inicial_hoy = CAPITAL_FICTICIO_INICIAL
comisiones_totales = 0.0
trades_totales = 0
trades_ganados = 0

def ejecutar_trade_ficticio():
    global capital_actual, comisiones_totales, trades_totales, trades_ganados
    
    # Simulación de tu estrategia momentum scalper
    # Entra chiquito como vos querés
    monto_trade = capital_actual * 0.05  # 5% por trade
    
    precio_entrada = 65842.31
    variacion = random.uniform(-0.008, 0.012)  # Tu edge del V33.2
    precio_salida = precio_entrada * (1 + variacion)
    
    ganancia_bruta = (precio_salida - precio_entrada) / precio_entrada * monto_trade
    
    # --- ACA ESTA LA POSTA: COMISION REAL ---
    comision = monto_trade * COMISION_BINANCE * 2  # Entrada + Salida
    ganancia_neta = ganancia_bruta - comision
    
    comisiones_totales += comision
    capital_actual += ganancia_neta
    trades_totales += 1
    if ganancia_neta > 0:
        trades_ganados += 1
    
    return ganancia_bruta, comision, ganancia_neta

def monitor_anti_sueno():
    ganancia_dia_neta = capital_actual - capital_inicial_hoy
    profit_factor = (trades_ganados / trades_totales * 100) if trades_totales > 0 else 0
    
    print(f"\n--- LOBO V33.3 | {datetime.now().strftime('%H:%M:%S')} ---")
    print(f"Capital Actual: ${capital_actual:.2f} USDT (FICTICIO)")
    print(f"Ganancia BRUTA hoy: ${ganancia_dia_neta + comisiones_totales:.2f}")
    print(f"Comisiones pagadas a Binance: -${comisiones_totales:.2f}")
    print(f"Ganancia NETA REAL hoy: ${ganancia_dia_neta:.2f}")
    print(f"Trades: {trades_totales} | Ganados: {profit_factor:.1f}%")
    print(f"Objetivo: ${OBJETIVO_DIARIO:.2f} | Falta: ${OBJETIVO_DIARIO - ganancia_dia_neta:.2f}")
    
    if ganancia_dia_neta >= OBJETIVO_DIARIO:
        print("🔔 ¡OBJETIVO CUMPLIDO! Campana Anti-Sueño: Podés irte a dormir tranquilo Lobo.")
        # Acá iría tu envío de comprobante por WhatsApp
        return True
    return False

# --- BUCLE 24/7 ---
print(f"Iniciando V33.3 con ${CAPITAL_FICTICIO_INICIAL} FICTICIOS...")
print("Contando COMISIONES REALES. Mostrando solo NETA.")
while True:
    bruta, comi, neta = ejecutar_trade_ficticio()
    print(f"Trade #{trades_totales}: Bruta ${bruta:.3f} | Comi -${comi:.3f} | NETA ${neta:.3f}")
    
    if monitor_anti_sueno():
        break
    
    time.sleep(5)  # En real es cada 3-5 min, acá acelerado para prueba
