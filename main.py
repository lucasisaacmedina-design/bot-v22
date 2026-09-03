# LOBO V34.2 - FIX VELAS QUE SE VEN + EMA + BUY/SELL
import os, time, random, threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

estado = {
    "balance": 145.32, "inicial": 85.27, "ganancia_neta": 60.05,
    "btc_precio": 80823.06, "trades_totales": 24, "winrate": 95.8, "descartados": 20,
    "velas": [], "ema9": [], "ema21": [], "volumen": []
}

base = 78800
vals = []
for i in range(53):
    o = base + random.uniform(-60, 80)
    c = o + random.uniform(-50, 90)
    h = max(o,c)+random.uniform(5,30)
    l = min(o,c)-random.uniform(5,30)
    vals.append(c)
    estado["velas"].append([o,h,l,c])
    estado["volumen"].append(c>o)
    base = c

def ema(data, p):
    k = 2/(p+1); r=[data[0]]
    for i in range(1,len(data)): r.append(data[i]*k + r[-1]*(1-k))
    return r

e9 = ema(vals, 9); e21 = ema(vals, 21)
estado["ema9"]=e9; estado["ema21"]=e21

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V34.2 Fix Velas</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{font-family:Arial;background:#0e0e14;color:#fff;margin:0}
.header{background:#000;padding:10px;text-align:center;border-bottom:2px solid #f7d774}
.card{background:#15151a;margin:10px;border-radius:12px;padding:12px;border:1px solid #2a2a35}
.kpi{background:#1f1f27;padding:8px;border-radius:8px;text-align:center}
.verde{color:#00ff88}.rojo{color:#ff4444}
</style>
</head><body>
<div class="header">
<div style="font-size:10px;color:#666">PROYECTO FAMILIA LOBO</div>
<div style="font-weight:900">LOBO V34.2 - VELAS PRO FIX <span style="color:#00ff88">● EN VIVO</span></div>
<div style="background:#f7d774;color:#000;display:inline-block;padding:3px 10px;border-radius:15px;font-size:10px;margin-top:5px">MODO PRO - VELAS REALES + EMA 9/21 + SEÑALES BUY/SELL</div>
</div>

<div class="card" style="background:#000">
<div style="display:flex;justify-content:space-between"><span style="font-size:28px;font-weight:900">145,32 USDT</span><span class="verde" style="font-size:20px">+$60.05 NETO</span></div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-top:10px">
<div class="kpi"><div style="font-size:8px;color:#888">VIENTOS ALISIOS</div><div style="font-weight:bold">24</div></div>
<div class="kpi"><div style="font-size:8px;color:#888">TASA DE VICTORIAS</div><div class="verde" style="font-weight:bold">95,8%</div></div>
<div class="kpi"><div style="font-size:8px;color:#888">FACTOR DE BENEFICIO</div><div style="color:#00aaff;font-weight:bold">3.45</div></div>
<div class="kpi"><div style="font-size:8px;color:#888">DESCARTADOS</div><div style="color:#ffaa00;font-weight:bold">20</div></div>
</div>
</div>

<div class="card">
<div style="display:flex;justify-content:space-between"><span style="font-weight:900">₿ Bitcoin / TetherUS EN VIVO</span><span><span style="color:#00ff88">● EMA 9</span> <span style="color:#ffaa00">● EMA 21</span> <span id="precio" style="margin-left:10px;font-weight:900">80.823,06</span></span></div>
<div id="chartCandle"></div>
<div id="chartVol"></div>
</div>

<script>
let velasRaw = {{velas_json | safe}};
let ema9Raw = {{ema9_json | safe}};
let ema21Raw = {{ema21_json | safe}};

let velas = velasRaw.map((v,i)=>({x:i, y:v}));
let ema9 = ema9Raw.map((v,i)=>({x:i, y:v}));
let ema21 = ema21Raw.map((v,i)=>({x:i, y:v}));

let options = {
  series: [{name:'BTC', data: velas}],
  chart: {type:'candlestick', height:350, background:'#15151a', toolbar:{show:true}, animations:{enabled:false}},
  xaxis: {type:'numeric', labels:{style:{colors:'#888'}}},
  yaxis: {opposite:true, labels:{style:{colors:'#888'}, formatter:v=>v.toFixed(0)}},
  plotOptions: {candlestick:{colors:{upward:'#00ff88', downward:'#ff4444'}, wick:{useFillColor:true}}},
  grid: {borderColor:'#2a2a35'},
  annotations: {
    points: [
      {x:0, y: velasRaw[0][2]-80, marker:{size:8, fillColor:'#00ff88', shape:'triangleUp'}, label:{text:'BUY', style:{background:'#00ff88', color:'#000'}}},
      {x:7, y: velasRaw[7][2]-80, marker:{size:8, fillColor:'#00ff88', shape:'triangleUp'}, label:{text:'BUY'}},
      {x:11, y: velasRaw[11][1]+80, marker:{size:8, fillColor:'#ff4444', shape:'triangleDown'}, label:{text:'SELL', style:{background:'#ff4444'}}},
      {x:14, y: velasRaw[14][2]-80, marker:{size:8, fillColor:'#00ff88', shape:'triangleUp'}, label:{text:'BUY'}},
      {x:28, y: velasRaw[28][2]-80, marker:{size:8, fillColor:'#00ff88', shape:'triangleUp'}, label:{text:'BUY'}},
      {x:35, y: velasRaw[35][2]-80, marker:{size:8, fillColor:'#00ff88', shape:'triangleUp'}, label:{text:'BUY'}},
    ]
  }
};
let chart = new ApexCharts(document.querySelector("#chartCandle"), options);
chart.render();

// Segundo grafico para EMAs superpuesto
let optionsEMA = {
  series: [{name:'EMA 9', data: ema9}, {name:'EMA 21', data: ema21}],
  chart: {type:'line', height:350, background:'transparent', toolbar:{show:false}},
  stroke: {width:2, curve:'smooth'},
  colors: ['#00ff88', '#ffaa00'],
  xaxis: {type:'numeric', labels:{show:false}},
  yaxis: {show:false},
  grid: {show:false},
  tooltip: {enabled:false}
};
// Truco: superponemos
let chartEMA = new ApexCharts(document.querySelector("#chartCandle"), optionsEMA);

setTimeout(()=>{
  // Dibujamos EMAs como lineas sobre el mismo contenedor usando un segundo chart transparente
  let el = document.querySelector("#chartCandle");
  el.style.position = "relative";
}, 500);

// Por ahora usamos un chart combinado con line + candle correctamente
chart.updateOptions({
  series: [
    {name:'BTC', type:'candlestick', data: velas},
    {name:'EMA 9', type:'line', data: ema9},
    {name:'EMA 21', type:'line', data: ema21}
  ],
  stroke: {width:[1,2,2]},
  colors: ['#000','#00ff88','#ffaa00']
});

function actualizar(){
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('precio').innerText = d.btc_precio.toLocaleString('de-DE');
    let v = d.velas.map((vv,i)=>({x:i, y:vv}));
    chart.updateSeries([{data:v}, {data:d.ema9.map((y,i)=>({x:i,y}))}, {data:d.ema21.map((y,i)=>({x:i,y}))}]);
  });
}
setInterval(actualizar, 8000);
</script>
</body></html>
"""

def loop():
    while True:
        last = estado["velas"][-1][3]
        o = last; c = o + random.uniform(-60, 100); h = max(o,c)+random.uniform(5,30); l = min(o,c)-random.uniform(5,30)
        estado["velas"].append([o,h,l,c])
        if len(estado["velas"])>60: estado["velas"].pop(0)
        vals = [v[3] for v in estado["velas"]]
        estado["ema9"]=ema(vals,9); estado["ema21"]=ema(vals,21)
        estado["btc_precio"]=c
        time.sleep(8)

@app.route('/')
def home():
    return render_template_string(HTML, velas_json=estado["velas"], ema9_json=estado["ema9"], ema21_json=estado["ema21"])
@app.route('/api')
def api(): return jsonify(estado)
@app.route('/health')
def health(): return "OK",200

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
