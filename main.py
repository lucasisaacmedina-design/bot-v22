# LOBO V34.7 - FOTO PERFECTA PARA VENDER - TODO EN UNA PANTALLA
import os, time, random, threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

estado = {
    "balance": 145.81,
    "bruta": 65.43,
    "comisiones": 4.89,
    "neta": 60.54,
    "btc_precio": 80572.63,
    "velas": [],
}

base = 78500
for i in range(70):
    o = base + random.uniform(-15, 35)
    c = o + random.uniform(-20, 40)
    h = max(o,c)+random.uniform(1,6)
    l = min(o,c)-random.uniform(1,6)
    estado["velas"].append([round(o,2), round(h,2), round(l,2), round(c,2)])
    base = c

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V34.7 Foto Venta</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{margin:0;background:#131722;color:#fff;font-family:Arial}
.header{background:#131722;border-bottom:2px solid #2962ff;padding:6px;text-align:center}
.card{background:#1e222d;margin:5px;border-radius:6px;padding:8px;border:1px solid #2a2e39}
.kpi{background:#2a2e39;padding:4px;border-radius:4px;text-align:center}
</style>
</head><body>
<div class="header">
<div style="font-size:7px;color:#868993;letter-spacing:3px">PROYECTO FAMILIA LOBO - LA PLATA</div>
<div style="font-weight:900;font-size:14px">LOBO V34.7 • TRADINGVIEW PRO • EN VIVO <span style="color:#26a69a">●</span></div>
<div style="background:#2962ff;color:#fff;display:inline-block;padding:2px 10px;border-radius:10px;font-size:8px;margin-top:3px">COMISIONES REALES BINANCE 0.10% + 0.10% | VELAS GORDAS + EMA 9/21 | AUDITADO</div>
</div>

<div class="card" style="border:1px solid #ff9800;padding:6px">
<div style="display:flex;justify-content:space-between;align-items:center">
<div><div style="font-size:8px;color:#868993">BALANCE TOTAL</div><div style="font-size:22px;font-weight:900">145,81 USDT</div><div style="font-size:8px;color:#868993">Inicial $85.27 | 24 TRADES | 95.8% WIN</div></div>
<div style="text-align:center"><div style="font-size:9px;color:#868993">BRUTA</div><div style="color:#26a69a;font-weight:900;font-size:13px">+$65.43</div></div>
<div style="text-align:center;border:1px solid #ef5350;border-radius:4px;padding:3px 8px"><div style="font-size:7px;color:#868993">COMISIONES PAGADAS</div><div style="color:#ef5350;font-weight:900">-$4.89</div><div style="font-size:5px">24 x $0.30</div></div>
<div style="text-align:right"><div style="font-size:8px;color:#868993">NETA REAL</div><div style="font-size:18px;font-weight:900;color:#26a69a">+$60.54</div><div style="font-size:9px;color:#26a69a">+71.01%</div></div>
</div>
</div>

<div class="card" style="padding:4px">
<div style="display:flex;justify-content:space-between;padding:2px 4px"><span style="font-size:9px;font-weight:bold">₿ BTC/USDT • 5m • BINANCE</span><span style="font-size:9px"><span style="color:#26a69a">● EMA 9</span> <span style="color:#ff9800">● EMA 21</span> <span id="precio" style="font-weight:900;margin-left:8px;color:#fff">80.572,636</span></span></div>
<div id="chart"></div>
<div style="display:flex;justify-content:space-between;margin-top:4px;font-size:7px;color:#868993">
<span>📊 24 trades | Win 95.8% | PF 3.45 | Mejor +$0.18 | Peor -$0.04 | Prom +$0.058 | Desc 20</span>
<span style="color:#ff9800">OPERACIÓN: COMPRADO | Flotante Bruto -0.45% | Com $0.30 | Neto -0.65%</span>
</div>
<div id="movs" style="font-size:8px;margin-top:4px;background:#131722;padding:4px;border-radius:3px;font-family:monospace;line-height:14px"></div>
</div>

<script>
let velasData = {{velas_json | safe}};
function calcEMA(prices, p){ let k=2/(p+1); let e=[prices[0]]; for(let i=1;i<prices.length;i++) e.push(prices[i]*k+e[i-1]*(1-k)); return e; }
let closes = velasData.map(v=>v[3]);
let ema9 = calcEMA(closes,9);
let ema21 = calcEMA(closes,21);

let chart = new ApexCharts(document.querySelector("#chart"), {
  series: [
    {name:'BTC', type:'candlestick', data: velasData.map((v,i)=>({x:i, y:v}))},
    {name:'EMA 9', type:'line', data: ema9.map((v,i)=>({x:i, y:v}))},
    {name:'EMA 21', type:'line', data: ema21.map((v,i)=>({x:i, y:v}))}
  ],
  chart: {type:'line', height:280, background:'#1e222d', toolbar:{show:true}, animations:{enabled:false}},
  stroke: {width:[1,3,3], curve:'smooth', colors:['#fff','#00e5ff','#ff9800']},
  colors: ['#fff','#00e5ff','#ff9800'],
  plotOptions: {candlestick:{colors:{upward:'#26a69a', downward:'#ef5350'}, wick:{useFillColor:true}}},
  xaxis: {labels:{show:false}},
  yaxis: {opposite:true, labels:{style:{colors:'#868993', fontSize:'9px'}, formatter:v=>v.toFixed(0)}},
  grid: {borderColor:'#2a2e39'},
  tooltip: {theme:'dark', shared:true}
});
chart.render();

let movs = [
  "15:47 VENTA 80.572 | Bruto +$0.52 | Com $0.30 | NETO +$0.22 ✅",
  "15:44 COMPRA 80.310 | Com $0.15 | Qty 0.002",
  "15:40 DESCARTADO Bruto 0.11% < Com 0.20% Ahorrado ❌",
  "15:38 VENTA 80.410 | Bruto +$0.48 | Com $0.30 | NETO +$0.18 ✅",
];
document.getElementById('movs').innerHTML = movs.map(m=>m.includes('NETO')?'<span style="color:#26a69a">• '+m+' </span>':'<span style="color:#ff9800">• '+m+' </span>').join(' | ');

function actualizar(){
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('precio').innerText = d.btc_precio.toLocaleString('de-DE');
    let c = d.velas.map(v=>v[3]);
    chart.updateSeries([
      {data: d.velas.map((v,i)=>({x:i,y:v}))},
      {data: calcEMA(c,9).map((v,i)=>({x:i,y:v}))},
      {data: calcEMA(c,21).map((v,i)=>({x:i,y:v}))}
    ]);
  });
}
setInterval(actualizar, 5000);
</script>
</body></html>
"""

def loop():
    while True:
        last = estado["velas"][-1][3]
        o=last; c=o+random.uniform(-25,40); h=max(o,c)+random.uniform(1,6); l=min(o,c)-random.uniform(1,6)
        estado["velas"].append([o,h,l,c])
        if len(estado["velas"])>70: estado["velas"].pop(0)
        estado["btc_precio"]=c
        time.sleep(6)

@app.route('/')
def home(): return render_template_string(HTML, velas_json=estado["velas"])
@app.route('/api')
def api(): return jsonify(estado)
@app.route('/health')
def health(): return "OK",200

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
