# LOBO BOT V33.5 - DASHBOARD CON GRAFICOS REALES
import os, time, random, threading
from datetime import datetime
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

COMISION_TOTAL = 0.002
CAPITAL_INICIAL = 143.99
TP_MINIMO_BRUTO = 0.005

estado = {
    "capital_actual": CAPITAL_INICIAL,
    "capital_inicial_hoy": CAPITAL_INICIAL,
    "comisiones_totales": 0.0,
    "trades_totales": 0,
    "trades_ganados": 0,
    "trades_descartados": 0,
    "ganancia_bruta_hoy": 0.0,
    "ganancia_neta_hoy": 0.0,
    "historial_capital": [CAPITAL_INICIAL],
    "historial_neta": [0.0],
    "ultimo_trade": None,
    "status": "V33.5 FILTRANDO"
}

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
<title>Lobo V33.5 - Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:Arial;background:#0e0e0e;color:#fff;margin:0;padding:20px}
.card{background:#1a1a1a;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #333}
.verde{color:#00ff88}.rojo{color:#ff4444}.gris{color:#999}
h1{margin:0 0 10px 0} .kpi{font-size:28px;font-weight:bold}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style>
<meta http-equiv="refresh" content="10">
</head>
<body>
<h1>🐺 LOBO BOT V33.5 <span class="gris" style="font-size:14px">Ser rico, no parecerlo</span></h1>
<p>Status: {{status}} | Actualizado: {{hora}} | Auto-refresh 10s</p>

<div class="grid">
<div class="card"><div>Capital Ficticio</div><div class="kpi">${{capital}}</div></div>
<div class="card"><div>Ganancia NETA REAL (después comisiones)</div><div class="kpi {{'verde' if neta>=0 else 'rojo'}}">${{neta}}</div></div>
<div class="card"><div>Comisiones pagadas a Binance</div><div class="kpi rojo">-${{comisiones}}</div></div>
</div>

<div class="grid">
<div class="card"><div>Trades Ejecutados</div><div class="kpi">{{trades}}</div><div class="gris">Win rate: {{winrate}}% | Bruta: ${{bruta}}</div></div>
<div class="card"><div>Trades Descartados (salvados)</div><div class="kpi">{{descartados}}</div><div class="gris">Señales chicas que te harían perder</div></div>
<div class="card"><div>Filtro Actual</div><div class="kpi" style="font-size:16px">Solo entra si gana >0.5% bruto</div><div class="gris">0.3% neto real minimo</div></div>
</div>

<div class="card">
<h3>Gráfico Capital y Ganancia Neta</h3>
<canvas id="chartCapital"></canvas>
</div>

<div class="card">
<p>Último trade: {{ultimo}}</p>
<p><a href="/api" style="color:#00ff88">Ver API JSON crudo</a></p>
</div>

<script>
const ctx = document.getElementById('chartCapital');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: {{labels}},
    datasets: [
      {label: 'Capital', data: {{data_capital}}, borderColor: '#00ff88', tension: 0.3},
      {label: 'Ganancia Neta Acum', data: {{data_neta}}, borderColor: '#ffaa00', tension: 0.3}
    ]
  },
  options: {responsive:true, plugins:{legend:{labels:{color:'#fff'}}}, scales:{x:{ticks:{color:'#888'}}, y:{ticks:{color:'#888'}}}}
});
</script>
</body>
</html>
"""

def ejecutar_trade():
    variacion = random.uniform(-0.008, 0.012)
    if variacion < TP_MINIMO_BRUTO:
        estado["trades_descartados"] += 1
        return
    monto = estado["capital_actual"] * 0.05
    bruta = monto * variacion
    comi = monto * COMISION_TOTAL
    neta = bruta - comi
    estado["capital_actual"] += neta
    estado["comisiones_totales"] += comi
    estado["ganancia_bruta_hoy"] += bruta
    estado["ganancia_neta_hoy"] += neta
    estado["trades_totales"] += 1
    if neta > 0: estado["trades_ganados"] += 1
    estado["historial_capital"].append(round(estado["capital_actual"],2))
    estado["historial_neta"].append(round(estado["ganancia_neta_hoy"],2))
    if len(estado["historial_capital"]) > 50: 
        estado["historial_capital"].pop(0)
        estado["historial_neta"].pop(0)
    estado["ultimo_trade"] = f"{datetime.now().strftime('%H:%M:%S')} NETA ${neta:.4f}"

def loop_bot():
    while True:
        ejecutar_trade()
        time.sleep(60)

@app.route('/')
def home():
    winrate = round(estado["trades_ganados"]/estado["trades_totales"]*100,1) if estado["trades_totales"]>0 else 0
    return render_template_string(HTML_DASHBOARD,
        status=estado["status"],
        hora=datetime.now().strftime("%H:%M:%S"),
        capital=round(estado["capital_actual"],2),
        neta=round(estado["ganancia_neta_hoy"],2),
        comisiones=round(estado["comisiones_totales"],2),
        trades=estado["trades_totales"],
        descartados=estado["trades_descartados"],
        winrate=winrate,
        bruta=round(estado["ganancia_bruta_hoy"],2),
        ultimo=estado["ultimo_trade"] or "Ninguno aun, filtrando...",
        labels=list(range(len(estado["historial_capital"]))),
        data_capital=estado["historial_capital"],
        data_neta=estado["historial_neta"]
    )

@app.route('/api')
def api():
    return jsonify(estado)

@app.route('/health')
def health(): return "OK", 200

threading.Thread(target=loop_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
