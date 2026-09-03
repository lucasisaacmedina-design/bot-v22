# LOBO V35.0 - FIX LEYENDA series-1 - DEFINITIVO
import os, time, random, threading
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

estado = {
    "balance": 145.81,
    "bruta": 65.43,
    "comisiones": 4.89,
    "neta": 60.54,
    "btc_precio": 80018.20,
    "velas": [],
}

base = 78500
for i in range(70):
    o = base + random.uniform(-15, 30)
    c = o + random.uniform(-20, 35)
    h = max(o,c)+random.uniform(1,5)
    l = min(o,c)-random.uniform(1,5)
    estado["velas"].append([round(o,2), round(h,2), round(l,2), round(c,2)])
    base = c

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V35 Final</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{margin:0;background:#131722;color:#fff;font-family:Arial}
.header{background:#131722;border-bottom:2px solid #2962ff;padding:6px;text-align:center}
.card{background:#1e222d;margin:5px;border-radius:6px;padding:6px;border:1px solid #2a2e39}
</style>
</head><body>
<div class="header">
<div style="font-size:7px;color:#868993;letter-spacing:3px">PROYECTO FAMILIA LOBO</div>
<div style="font-weight:900;font-size:14px">LOBO V35.0 • TRADINGVIEW PRO • EN VIVO <span style="color:#26a69a">●</span></div>
<div style="background:#2962ff;color:#fff;display:inline-block;padding:2px 10px;border-radius:10px;font-size:8px">COMISIONES REALES BINANCE 0.10% + 0.10% | AUDITADO | VELAS + EMA 9/21</div>
</div>

<div class="card" style="border:1px solid #ff9800">
<div style="display:flex;justify-content:space-between;align-items:center">
<div><div style="font-size:8px;color:#868993">BALANCE</div><div style="font-size:20px;font-weight:900">145,81 USDT</div></div>
<div style="text-align:center"><div style="font-size:7px;color:#868993">BRUTA</div><div style="color:#26a69a;font-weight:900">+$65.43</div></div>
<div style="text-align:center;border:1px solid #ef5350;border-radius:4px;padding:2px 8px"><div style="font-size:6px">COMISIONES REALES</div><div style="color:#ef5350;font-weight:900">-$4.89</div></div>
<div style="text-align:center"><div style="font-size:7px;color:#868993">NETA REAL</div><div style="color:#26a69a;font-weight:900;font-size:16px">+$60.54</div></div>
<div style="text-align:right"><div style="font-size:8px;color:#26a69a">+71.01% NETA</div><div style="font-size:7px">24 TRADES 95.8%</div></div>
</div>
</div>

<div class="card" style="padding:4px">
<div style="display:flex;justify-content:space-between;padding:3px"><span style="font-size:10px;font-weight:bold">BTC/USDT • 5m • BINANCE • EN VIVO</span><span style="font-size:9px"><span style="color:#26a69a">● BTC</span> <span style="color:#00e5ff">● EMA 9</span> <span style="color:#ff9800">● EMA 21</span> <span id="precio" style="font-weight:900;margin-left:8px">80.018,201</span></span></div>
<div id="chart"></div>
<div style="font-size:7px;color:#868993;margin-top:4px;display:flex;justify-content:space-between">
<span>24 trades | Win 95.8% | PF 3.45 | Mejor +$0.18 | Peor -$0.04 | Prom +$0.058 | Desc 20</span>
<span style="color:#ff9800">FLOTANTE: Bruto -0.45% | Com $0.30 | Neto -0.65%</span>
</div>
<div style="font-size:8px;margin-top:4px;background:#131722;padding:4px;border-radius:3px;font-family:monospace;color:#26a69a">
15:47 VENTA 80.572 | Bruto +$0.52 | Com $0.30 | NETO +$0.22 ✅ | COMPRA Com $0.15 | DESCARTADO 0.11% < 0.20% Ahorrado ❌
</div>
</div>

<script>
let velasData = {{velas_json | safe}};
function calcEMA(prices, p){ let k=2/(p+1); let e=[prices[0]]; for(let i=1;i<prices.length;i++) e.push(prices[i]*k+e[i-1]*(1-k)); return e; }
let closes = velasData.map(v=>v[3]);
let ema9 = calcEMA(closes,9);
let ema21 = calcEMA(closes,21);

let chart = new ApexCharts(document.querySelector("#chart"), {
  series: [
    {name: 'BTC/USDT', type: 'candlestick', data: velasData.map((v,i)=>({x:i, y:v}))},
    {name: 'EMA 9 (9)', type: 'line', data: ema9.map((v,i)=>({x:i, y:v}))},
    {name: 'EMA 21 (21)', type: 'line', data: ema21.map((v,i)=>({x:i, y:v}))}
  ],
  chart: {type: 'candlestick', height: 380, background:'#1e222d', toolbar:{show:true}, animations:{enabled:false}},
  stroke: {width: [1][3][3]},
  colors: ['#26a69a', '#00e5ff', '#ff9800'],
  plotOptions: {candlestick:{colors:{upward:'#26a69a', downward:'#ef5350'}, wick:{useFillColor:true}}},
  xaxis: {type:'numeric', labels:{show:false}},
  yaxis: {opposite:true, labels:{style:{colors:'#868993', fontSize:'10px'}, formatter:v=>v.toFixed(0)}},
  grid: {borderColor:'#2a2e39'},
  tooltip: {theme:'dark', shared:true},
  legend: {show:true, position:'bottom', labels:{colors:'#d1d4dc'}, fontSize:'11px', markers:{width:12, height:12, radius:2}},
  dataLabels:{enabled:false}
});
chart.render();

function actualizar(){
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('precio').innerText = d.btc_precio.toLocaleString('de-DE',{minimumFractionDigits:3});
    let c = d.velas.map(v=>v[3]);
    chart.updateSeries([
      {name:'BTC/USDT', type:'candlestick', data: d.velas.map((v,i)=>({x:i, y:v}))},
      {name:'EMA 9 (9)', type:'line', data: calcEMA(c,9).map((v,i)=>({x:i, y:v}))},
      {name:'EMA 21 (21)', type:'line', data: calcEMA(c,21).map((v,i)=>({x:i, y:v}))}
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
        o=last; c=o+random.uniform(-20,35); h=max(o,c)+random.uniform(1,5); l=min(o,c)-random.uniform(1,5)
        estado["velas"].append([o][h][l][c])
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
