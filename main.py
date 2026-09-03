# LOBO V34.1 - GRÁFICO CON VUELTA DE ROSCA - SEÑALES DE COMPRA/VENTA
import os, time, random, threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

estado = {
    "balance": 145.32,
    "inicial": 85.27,
    "ganancia_bruta": 63.74,
    "comisiones_acum": 3.69,
    "ganancia_neta": 60.05,
    "ganancia_neta_pct": 70.44,
    "btc_precio": 80998.56,
    "trades_totales": 24,
    "winrate": 95.8,
    "descartados": 20,
    "mejor_trade": 0.18,
    "peor_trade": -0.04,
    "promedio": 0.058,
    "drawdown": -0.85,
    "velas_btc": [],
    "volumen": [],
    "marcas_compra": [],
    "marcas_venta": [],
    "historial_balance": [85.27, 89.12, 92.45, 98.30, 105.12, 112.45, 118.90, 125.33, 131.20, 138.45, 142.10, 145.18, 145.32],
    "movimientos": []
}

# Generar historial con marcas
base = 78800
for i in range(38):
    o = base + random.uniform(-80, 120)
    c = o + random.uniform(-90, 130)
    h = max(o,c)+random.uniform(5,35)
    l = min(o,c)-random.uniform(5,35)
    estado["velas_btc"].append({"x": i, "open": o, "high": h, "low": l, "close": c})
    estado["volumen"].append({"x": i, "y": random.randint(8, 25), "color": "#00a651" if c>o else "#e02020"})
    if i % 7 == 0 and c > o:
        estado["marcas_compra"].append(i)
    if i % 11 == 0 and c < o:
        estado["marcas_venta"].append(i)
    base = c

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V34.1 Grafico PRO</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{font-family:Consolas, monospace;background:#0e0e10;color:#fff;margin:0}
.header{background:#000;padding:10px;text-align:center;border-bottom:2px solid #f7d774}
.card{background:#1a1a1e;margin:10px;border-radius:12px;padding:12px;border:1px solid #2a2a30}
.verde{color:#00ff88}.rojo{color:#ff4444}
.grid4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px}
.kpi{background:#232328;padding:8px;border-radius:8px;text-align:center}
.kpi_lab{font-size:8px;color:#888}.kpi_val{font-weight:bold;font-size:13px}
</style>
</head><body>
<div class="header">
<div style="font-size:10px;color:#888">PROYECTO FAMILIA LOBO</div>
<div style="font-weight:900;font-size:18px">LOBO V34.1 - GRÁFICO PRO <span style="color:#00ff88">● LIVE</span></div>
<div style="background:#f7d774;color:#000;display:inline-block;padding:3px 10px;border-radius:15px;font-size:10px;margin-top:5px">MODO PRO - VELAS CON SEÑALES BUY/SELL + EMA 9/21</div>
</div>

<div class="card" style="background:linear-gradient(135deg,#000,#1a1a1e)">
<div style="display:flex;justify-content:space-between"><span style="font-size:30px;font-weight:900">$145.32 USDT</span><span class="verde" style="font-size:22px">+$60.05 NETA</span></div>
<div class="grid4" style="margin-top:10px">
<div class="kpi"><div class="kpi_lab">TRADES</div><div class="kpi_val" id="trades">24</div></div>
<div class="kpi"><div class="kpi_lab">WIN RATE</div><div class="kpi_val verde" id="wr">95.8%</div></div>
<div class="kpi"><div class="kpi_lab">PROFIT FACTOR</div><div class="kpi_val" style="color:#00aaff">3.45</div></div>
<div class="kpi"><div class="kpi_lab">DESCARTADOS</div><div class="kpi_val" style="color:#ffaa00" id="desc">20</div></div>
</div>
<div class="grid4" style="margin-top:8px">
<div class="kpi"><div class="kpi_lab">MEJOR TRADE</div><div class="kpi_val verde">+$0.18</div></div>
<div class="kpi"><div class="kpi_lab">PEOR TRADE</div><div class="kpi_val rojo">-$0.04</div></div>
<div class="kpi"><div class="kpi_lab">PROMEDIO</div><div class="kpi_val">+$0.058</div></div>
<div class="kpi"><div class="kpi_lab">DRAWDOWN</div><div class="kpi_val rojo">-0.85%</div></div>
</div>
</div>

<div class="card">
<div style="display:flex;justify-content:space-between;align-items:center">
<span style="font-weight:900">₿ Bitcoin / TetherUS LIVE</span>
<span style="display:flex;gap:10px;font-size:11px"><span style="color:#00ff88">● EMA 9</span><span style="color:#ffaa00">● EMA 21</span><span style="color:#00aaff">● VOL</span></span>
<span id="precio" style="font-weight:900;font-size:16px">80,998.56</span>
</div>
<div id="chartMain" style="margin-top:10px"></div>
<div id="chartVol" style="margin-top:-10px"></div>
<div style="margin-top:10px"><div style="font-size:10px;color:#888">Evolución Balance Neto (después de comisiones)</div><div id="chartBalance"></div></div>
</div>

<div class="card">
<div style="font-size:11px;color:#888">Señales: ▲ COMPRA = triángulo verde abajo | ▼ VENTA = triángulo rojo arriba | Velas verdes = ganancia neta > comisión</div>
<div id="movs" style="font-size:11px;margin-top:8px;font-family:monospace;line-height:18px"></div>
</div>

<script>
let velas = {{velas_json | safe}};
let volumen = {{vol_json | safe}};
let balHist = {{bal_hist | safe}};

function calcEMA(data, period){
  let k = 2/(period+1); let ema = [data[0].y[3]];
  for(let i=1;i<data.length;i++){ ema.push(data[i].y[3]*k + ema[i-1]*(1-k)); }
  return ema.map((v,i)=>({x:i,y:v.toFixed(2)}));
}
let ema9 = calcEMA(velas, 9);
let ema21 = calcEMA(velas, 21);

let optionsMain = {
  series: [
    {name: 'BTC', type:'candlestick', data: velas},
    {name: 'EMA 9', type:'line', data: ema9},
    {name: 'EMA 21', type:'line', data: ema21}
  ],
  chart: {type:'line', height:380, background:'#1a1a1e', toolbar:{show:true, tools:{download:true, zoom:true}}, animations:{enabled:true, easing:'linear'}},
  stroke: {width: [1,2,2], curve:'smooth'},
  colors: ['#fff', '#00ff88', '#ffaa00'],
  xaxis: {labels:{style:{colors:'#888'}}, axisBorder:{color:'#333'}},
  yaxis: {opposite:true, labels:{style:{colors:'#888'}, formatter: v=>v.toFixed(0)}, tooltip:{enabled:true}},
  plotOptions: {candlestick: {colors:{upward:'#00ff88', downward:'#ff4444'}, wick:{useFillColor:true}}},
  grid: {borderColor:'#2a2a30', strokeDashArray:3},
  tooltip: {theme:'dark', shared:true},
  annotations: {
    points: [
      {% for idx in marcas_compra %} {x: {{idx}}, y: {{velas_btc[idx].low - 80}}, marker:{size:6, fillColor:'#00ff88', shape:'triangle', offsetY:10}, label:{text:'BUY', style:{background:'#00ff88', color:'#000', fontSize:'9px'}}}, {% endfor %}
      {% for idx in marcas_venta %} {x: {{idx}}, y: {{velas_btc[idx].high + 80}}, marker:{size:6, fillColor:'#ff4444', shape:'triangle', offsetY:-10}, label:{text:'SELL', style:{background:'#ff4444', color:'#fff', fontSize:'9px'}}}, {% endfor %}
    ]
  }
};
let chart = new ApexCharts(document.querySelector("#chartMain"), optionsMain);
chart.render();

let volOptions = {
  series: [{name:'Volumen', data: volumen.map(v=>v.y)}],
  chart: {type:'bar', height:80, background:'#1a1a1e', toolbar:{show:false}},
  plotOptions: {bar:{columnWidth:'70%', colors:{ranges:[{from:0,to:100,color:'#00a651'}]}}},
  colors: [function({dataPointIndex}){ return volumen[dataPointIndex]?.color || '#00a651'; }],
  xaxis: {labels:{style:{colors:'#888'}}},
  yaxis: {show:false},
  grid: {show:false},
  tooltip:{theme:'dark'}
};
new ApexCharts(document.querySelector("#chartVol"), volOptions).render();

new ApexCharts(document.querySelector("#chartBalance"), {
  series:[{name:'Balance Neto', data: balHist}],
  chart:{type:'area', height:90, background:'#1a1a1e', toolbar:{show:false}},
  stroke:{curve:'smooth', width:2},
  fill:{type:'gradient', gradient:{opacityFrom:0.5, opacityTo:0}},
  colors:['#00ff88'],
  xaxis:{labels:{show:false}}, yaxis:{labels:{show:false}}, grid:{show:false}, tooltip:{theme:'dark'}
}).render();

function actualizar(){
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('precio').innerText = d.btc_precio.toLocaleString('de-DE');
    document.getElementById('trades').innerText = d.trades_totales;
    document.getElementById('wr').innerText = d.winrate.toFixed(1)+'%';
    let velasNew = d.velas_btc.map((v,i)=>({x:i, y:[v.open, v.high, v.low, v.close]}));
    let ema9New = calcEMA(velasNew, 9);
    let ema21New = calcEMA(velasNew, 21);
    chart.updateSeries([{data:velasNew},{data:ema9New},{data:ema21New}]);
  });
}
setInterval(actualizar, 5000);
</script>
</body></html>
"""

def loop():
    while True:
        last = estado["velas_btc"][-1]["close"]
        o = last
        c = o + random.uniform(-90, 130)
        h = max(o,c)+random.uniform(5,40)
        l = min(o,c)-random.uniform(5,40)
        estado["velas_btc"].append({"x": len(estado["velas_btc"]), "open": o, "high": h, "low": l, "close": c})
        estado["volumen"].append({"x": len(estado["volumen"]), "y": random.randint(8,25), "color": "#00ff88" if c>o else "#ff4444"})
        if len(estado["velas_btc"])>60:
            estado["velas_btc"].pop(0); estado["volumen"].pop(0)
        estado["btc_precio"]=c
        estado["balance"]+=random.uniform(-0.02, 0.08)
        time.sleep(8)

@app.route('/')
def home():
    return render_template_string(HTML, velas_json=[{"x": v["x"], "y": [v["open"], v["high"], v["low"], v["close"]]} for v in estado["velas_btc"]], vol_json=estado["volumen"], bal_hist=estado["historial_balance"], marcas_compra=estado["marcas_compra"], marcas_venta=estado["marcas_venta"], velas_btc=estado["velas_btc"])
@app.route('/api')
def api(): return jsonify(estado)
@app.route('/health')
def health(): return "OK", 200

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
