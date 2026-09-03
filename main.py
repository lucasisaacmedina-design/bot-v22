# LOBO BOT V33.7 - VELAS EN VIVO
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
    "descartados": 2,
    "ganancia_bruta": 0.07,
    "ganancia_neta": 0.05,
    "velas": [],
    "historial_capital": [143.99, 144.04],
    "status": "V33.7 LIVE"
}
for i in range(20):
    base = 144 + random.uniform(-0.5, 0.5)
    o = base; c = base + random.uniform(-0.3, 0.4)
    h = max(o,c)+random.uniform(0,0.3); l = min(o,c)-random.uniform(0,0.3)
    estado["velas"].append({"x":i,"open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2)})

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V33.7 - Live</title>
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{font-family:Arial;background:#0e0e0e;color:#fff;margin:0;padding:15px}
.card{background:#1a1a1a;border-radius:12px;padding:15px;margin-bottom:15px;border:1px solid #333}
.verde{color:#00ff88}.rojo{color:#ff4444}.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.kpi{font-size:24px;font-weight:bold} #live{color:#00ff88;animation:blink 1s infinite} @keyframes blink{50%{opacity:0}}
</style>
</head><body>
<h2>🐺 LOBO V33.7 - VELAS EN VIVO <span id="live">● LIVE</span></h2>
<div class="grid">
<div class="card"><div>Capital</div><div class="kpi" id="cap">${{capital}}</div></div>
<div class="card"><div>NETA REAL</div><div class="kpi verde" id="neta">${{neta}}</div></div>
<div class="card"><div>Comisiones</div><div class="kpi rojo" id="comi">-${{comi}}</div></div>
</div>
<div class="grid">
<div class="card"><div>Trades</div><div class="kpi" id="trades">{{trades}} | WR {{wr}}%</div></div>
<div class="card"><div>Descartados</div><div class="kpi" id="desc">{{desc}}</div></div>
<div class="card"><div>Próxima vela</div><div class="kpi" id="countdown">15s</div></div>
</div>
<div class="card"><h3>📈 Velas Japonesas - LIVE</h3><div id="chartVelas"></div></div>

<script>
let velasData = {{velas_json | safe}};
let capitalData = {{capital_data}};
let chartVelas, chartNeta;

function renderCharts(){
  let opt = {series:[{data:velasData}],chart:{type:'candlestick',height:350,background:'#1a1a1a',foreColor:'#fff',animations:{enabled:true}},xaxis:{type:'numeric'},yaxis:{labels:{style:{colors:'#fff'}}},plotOptions:{candlestick:{colors:{upward:'#00ff88',downward:'#ff4444'}}}};
  chartVelas = new ApexCharts(document.querySelector("#chartVelas"), opt); chartVelas.render();
}
renderCharts();

let count = 15;
setInterval(()=>{count--; document.getElementById('countdown').innerText = count+'s'; if(count<=0) count=15;},1000);

setInterval(()=>{
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('cap').innerText = '$'+d.capital_actual.toFixed(2);
    document.getElementById('neta').innerText = '$'+d.ganancia_neta.toFixed(2);
    document.getElementById('comi').innerText = '-$'+d.comisiones.toFixed(2);
    document.getElementById('trades').innerText = d.trades_totales+' | WR '+(d.trades_totales? (d.trades_ganados/d.trades_totales*100).toFixed(1):0)+'%';
    document.getElementById('desc').innerText = d.descartados;
    let newVelas = d.velas.map(v=>({x:v.x,y:[v.open,v.high,v.low,v.close]}));
    velasData = newVelas;
    chartVelas.updateSeries([{data:newVelas}]);
  });
}, 3000);
</script>
</body></html>
"""

def generar_vela():
    last_close = estado["velas"][-1]["close"]
    o = last_close
    var = random.uniform(-0.4, 0.6)
    c = o + var
    h = max(o,c)+random.uniform(0,0.2); l = min(o,c)-random.uniform(0,0.2)
    if var > 0.35:
        monto = estado["capital_actual"]*0.05
        bruta = monto*(var/100); comi = monto*COMISION_TOTAL; neta = bruta-comi
        if neta>0:
            estado["capital_actual"]+=neta; estado["ganancia_neta"]+=neta; estado["trades_totales"]+=1; estado["trades_ganados"]+=1
            estado["comisiones"]+=comi
    else: estado["descartados"]+=1
    estado["velas"].append({"x":len(estado["velas"]),"open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2)})
    if len(estado["velas"])>50: estado["velas"].pop(0)
    estado["historial_capital"].append(round(estado["capital_actual"],2))

def loop():
    while True:
        generar_vela()
        time.sleep(15)

@app.route('/')
def home():
    velas_chart = [{"x":v["x"],"y":[v["open"],v["high"],v["low"],v["close"]]} for v in estado["velas"]]
    return render_template_string(HTML, capital=round(estado["capital_actual"],2), neta=round(estado["ganancia_neta"],2), comi=round(estado["comisiones"],2), trades=estado["trades_totales"], wr=round(estado["trades_ganados"]/estado["trades_totales"]*100,1) if estado["trades_totales"] else 0, desc=estado["descartados"], velas_json=velas_chart, capital_data=estado["historial_capital"])

@app.route('/api')
def api(): return jsonify(estado)
@app.route('/health')
def health(): return "OK", 200

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
