# LOBO BOT V33.6 - CON VELAS JAPONESAS
import os, time, random, threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

COMISION_TOTAL = 0.002
CAPITAL_INICIAL = 144.04

estado = {
    "capital_actual": CAPITAL_INICIAL,
    "comisiones": 0.01,
    "trades_totales": 1,
    "trades_ganados": 1,
    "descartados": 1,
    "ganancia_bruta": 0.07,
    "ganancia_neta": 0.05,
    "velas": [], # OHLC
    "historial_capital": [143.99, 144.04],
    "status": "V33.6 VELAS"
}

# Inicializar con 20 velas
for i in range(20):
    base = 144 + random.uniform(-0.5, 0.5)
    open_p = base
    close_p = base + random.uniform(-0.3, 0.4)
    high_p = max(open_p, close_p) + random.uniform(0, 0.3)
    low_p = min(open_p, close_p) - random.uniform(0, 0.3)
    estado["velas"].append({
        "x": i,
        "open": round(open_p, 2),
        "high": round(high_p, 2),
        "low": round(low_p, 2),
        "close": round(close_p, 2)
    })

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Lobo V33.6 - Velas</title>
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{font-family:Arial;background:#0e0e0e;color:#fff;margin:0;padding:15px}
.card{background:#1a1a1a;border-radius:12px;padding:15px;margin-bottom:15px;border:1px solid #333}
.verde{color:#00ff88}.rojo{color:#ff4444}.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.kpi{font-size:24px;font-weight:bold}
</style>
<meta http-equiv="refresh" content="15">
</head>
<body>
<h2>🐺 LOBO V33.6 - VELAS JAPONESAS <span style="color:#666;font-size:12px">Ser rico, no parecerlo</span></h2>

<div class="grid">
<div class="card"><div>Capital</div><div class="kpi">${{capital}}</div></div>
<div class="card"><div>NETA REAL</div><div class="kpi verde">${{neta}}</div></div>
<div class="card"><div>Comisiones</div><div class="kpi rojo">-${{comi}}</div></div>
</div>

<div class="grid">
<div class="card"><div>Trades</div><div class="kpi">{{trades}} | WR {{wr}}%</div></div>
<div class="card"><div>Descartados</div><div class="kpi">{{desc}}</div></div>
<div class="card"><div>Filtro</div><div style="font-size:12px">>0.5% bruto / 0.3% neto</div></div>
</div>

<div class="card">
<h3>📈 Velas Japonesas - Capital (Tiempo Real)</h3>
<div id="chartVelas"></div>
</div>

<div class="card">
<h3>💰 Evolución Ganancia Neta</h3>
<div id="chartNeta"></div>
</div>

<script>
var velasData = {{velas_json | safe}};
var capitalData = {{capital_data}};

var optionsVelas = {
  series: [{data: velasData}],
  chart: {type: 'candlestick', height: 350, background: '#1a1a1a', foreColor: '#fff'},
  xaxis: {type: 'numeric'},
  yaxis: {tooltip: {enabled: true}, labels: {style:{colors:'#fff'}}},
  plotOptions: {candlestick: {colors: {upward: '#00ff88', downward: '#ff4444'}}}
};
new ApexCharts(document.querySelector("#chartVelas"), optionsVelas).render();

var optionsNeta = {
  series: [{name: 'Capital', data: capitalData}],
  chart: {type: 'line', height: 200, background: '#1a1a1a', foreColor: '#fff'},
  stroke: {curve: 'smooth', width: 3, colors: ['#00ff88']},
  xaxis: {labels:{style:{colors:'#888'}}},
  yaxis: {labels:{style:{colors:'#888'}}}
};
new ApexCharts(document.querySelector("#chartNeta"), optionsNeta).render();
</script>

<p style="color:#666;font-size:12px">Último update: {{hora}} | Auto refresh 15s | <a href="/api" style="color:#00ff88">API</a></p>
</body>
</html>
"""

def generar_nueva_vela():
    last_close = estado["velas"][-1]["close"] if estado["velas"] else CAPITAL_INICIAL
    open_p = last_close
    variacion = random.uniform(-0.4, 0.5) # simula movimiento
    close_p = open_p + variacion
    high_p = max(open_p, close_p) + random.uniform(0, 0.2)
    low_p = min(open_p, close_p) - random.uniform(0, 0.2)
    
    # Logica rentable V33.5
    if variacion > 0.5: # solo si es ganadora grande
        monto = estado["capital_actual"] * 0.05
        bruta = monto * (variacion/100)
        comi = monto * COMISION_TOTAL
        neta = bruta - comi
        if neta > 0:
            estado["capital_actual"] += neta
            estado["ganancia_neta"] += neta
            estado["trades_totales"] += 1
            estado["trades_ganados"] += 1
    else:
        estado["descartados"] += 1

    estado["velas"].append({
        "x": len(estado["velas"]),
        "open": round(open_p, 2),
        "high": round(high_p, 2),
        "low": round(low_p, 2),
        "close": round(close_p, 2)
    })
    if len(estado["velas"]) > 50: estado["velas"].pop(0)
    estado["historial_capital"].append(round(estado["capital_actual"],2))

def loop():
    while True:
        generar_nueva_vela()
        time.sleep(60)

@app.route('/')
def home():
    velas_chart = [{"x": v["x"], "y": [v["open"], v["high"], v["low"], v["close"]]} for v in estado["velas"]]
    return render_template_string(HTML,
        capital=round(estado["capital_actual"],2),
        neta=round(estado["ganancia_neta"],2),
        comi=round(estado["comisiones"],2),
        trades=estado["trades_totales"],
        wr=round(estado["trades_ganados"]/estado["trades_totales"]*100,1) if estado["trades_totales"] else 0,
        desc=estado["descartados"],
        velas_json=velas_chart,
        capital_data=estado["historial_capital"],
        hora=datetime.now().strftime("%H:%M:%S")
    )

@app.route('/api')
def api(): return jsonify(estado)

@app.route('/health')
def health(): return "OK", 200

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
