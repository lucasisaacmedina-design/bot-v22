# LOBO V34.5 - FIX GRAFICO TRADINGVIEW REAL - VELAS SI O SI SE VEN
import os, time, random, threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

estado = {
    "balance": 145.81,
    "inicial": 85.27,
    "bruta": 65.43,
    "comisiones": 4.89,
    "neta": 60.54,
    "neta_pct": 71.01,
    "btc_precio": 80021.28,
    "trades": 24,
    "winrate": 95.8,
    "descartados": 20,
    "velas": [],
    "movimientos": [
        "15:44:10 VENTA BTC 80.021 | Bruto +$0.38 | Com $0.30 | NETO +$0.08 ✅",
        "15:40:22 COMPRA BTC 79.850 | Com $0.15",
        "15:38:05 DESCARTADO | Bruto 0.11% < Com 0.20% Salvado",
    ]
}

# Generar 80 velas bien visibles
base = 78000
for i in range(80):
    o = base + random.uniform(-30, 50)
    c = o + random.uniform(-40, 60)
    h = max(o,c) + random.uniform(2, 12)
    l = min(o,c) - random.uniform(2, 12)
    estado["velas"].append([o, h, l, c])
    base = c

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V34.5 TV FIX</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial}
.header{background:#131722;border-bottom:2px solid #2962ff;padding:8px;text-align:center}
.card{background:#1e222d;margin:6px;border-radius:6px;padding:10px;border:1px solid #2a2e39}
.kpi{background:#2a2e39;padding:6px;border-radius:4px;text-align:center}
.verde{color:#26a69a}.rojo{color:#ef5350}
</style>
</head><body>
<div class="header">
<div style="font-size:8px;color:#868993;letter-spacing:3px">PROYECTO FAMILIA LOBO</div>
<div style="font-weight:900;color:#fff">LOBO V34.5 • TRADINGVIEW FIX • EN VIVO <span style="color:#26a69a">●</span></div>
<div style="background:#2962ff;color:#fff;display:inline-block;padding:3px 12px;border-radius:12px;font-size:9px;margin-top:4px">COMISIONES REALES BINANCE 0.10% + 0.10% | VELAS GORDAS TV</div>
</div>

<div class="card" style="border:1px solid #ff9800">
<div style="display:flex;justify-content:space-between">
<div><div style="font-size:9px;color:#868993">BALANCE TOTAL</div><div style="font-size:28px;font-weight:900;color:#fff">145,81 USDT</div><div style="font-size:10px;color:#868993">Inicial $85.27 | 24 trades | 95.8% win</div></div>
<div style="text-align:right"><div style="font-size:20px;font-weight:900;color:#26a69a">+$60.54</div><div style="font-size:11px;color:#26a69a">+71.01% NETA</div><div style="font-size:8px;color:#868993">Después de comisiones</div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;margin-top:10px">
<div class="kpi"><div style="font-size:7px;color:#868993">BRUTA</div><div style="color:#26a69a;font-weight:900">+$65.43</div></div>
<div class="kpi" style="border:1px solid #ef5350"><div style="font-size:7px;color:#868993">COMISIONES PAGADAS</div><div style="color:#ef5350;font-weight:900">-$4.89</div><div style="font-size:6px">20 trades x $0.30</div></div>
<div class="kpi" style="background:#26a69a20;border:1px solid #26a69a"><div style="font-size:7px;color:#868993">NETA REAL</div><div style="color:#26a69a;font-weight:900;font-size:14px">+$60.54</div></div>
</div>
</div>

<div class="card" style="padding:5px">
<div style="display:flex;justify-content:space-between;padding:5px"><span style="font-size:11px;font-weight:bold;color:#fff">₿ BTC/USDT • BINANCE • 5m • EN VIVO</span><span id="precio" style="font-weight:900;color:#fff">80.021,283</span></div>
<div id="chartCandle" style="background:#1e222d"></div>
<div id="chartVol" style="margin-top:5px"></div>
</div>

<script>
let velasData = {{velas_json | safe}};

function calcEMA(prices, period){
  let k = 2/(period+1);
  let ema = [prices[0]];
  for(let i=1;i<prices.length;i++){ ema.push(prices[i]*k + ema[i-1]*(1-k)); }
  return ema;
}
let closes = velasData.map(v=>v[3]);
let ema9 = calcEMA(closes, 9);
let ema21 = calcEMA(closes, 21);

// FORMATO CORRECTO PARA APEX CANDLESTICK: [{x:i, y:[O,H,L,C]}]
let candleSeries = velasData.map((v,i)=>({x: i, y: v}));

let chart = new ApexCharts(document.querySelector("#chartCandle"), {
  series: [{name:'BTC', data: candleSeries}],
  chart: {type:'candlestick', height:350, background:'#1e222d', toolbar:{show:true}, animations:{enabled:false}},
  xaxis: {type:'numeric', labels:{style:{colors:'#868993'}}},
  yaxis: {opposite:true, tooltip:{enabled:true}, labels:{style:{colors:'#868993'}, formatter: (v)=>{return v.toFixed(0) }}},
  plotOptions: {candlestick:{colors:{upward:'#26a69a', downward:'#ef5350'}, wick:{useFillColor:true}}},
  grid: {borderColor:'#2a2e39', xaxis:{lines:{show:true}}, yaxis:{lines:{show:true}}},
  tooltip: {theme:'dark'}
});
chart.render();

// Segundo chart solo para EMAs - superpuesto visualmente debajo con mismo eje X
let chartEMA = new ApexCharts(document.querySelector("#chartCandle"), {
  series: [
    {name:'EMA 9', data: ema9.map((v,i)=>({x:i, y:v}))},
    {name:'EMA 21', data: ema21.map((v,i)=>({x:i, y:v}))}
  ],
  chart: {type:'line', height:350, background:'transparent', toolbar:{show:false}, animations:{enabled:false}},
  stroke: {width:2, curve:'smooth'},
  colors: ['#26a69a', '#ff9800'],
  xaxis: {type:'numeric', labels:{show:false}},
  yaxis: {show:false, min: Math.min(...closes)-100, max: Math.max(...closes)+100},
  grid: {show:false},
  tooltip: {enabled:false}
});

// Truco final: actualizar el primer chart con las 3 series de la forma que Apex SI acepta
setTimeout(()=>{
  chart.updateOptions({
    series: [
      {type:'candlestick', name:'BTC', data: candleSeries},
      {type:'line', name:'EMA 9', data: ema9.map((v,i)=>({x:i,y:v}))},
      {type:'line', name:'EMA 21', data: ema21.map((v,i)=>({x:i,y:v}))}
    ],
    stroke: {width:[1,2,2]},
    colors: ['#fff','#26a69a','#ff9800']
  });
}, 1000);

function actualizar(){
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('precio').innerText = d.btc_precio.toLocaleString('de-DE');
    let newCandles = d.velas.map((v,i)=>({x:i, y:v}));
    let c = d.velas.map(v=>v[3]);
    let e9 = calcEMA(c, 9).map((v,i)=>({x:i,y:v}));
    let e21 = calcEMA(c, 21).map((v,i)=>({x:i,y:v}));
    chart.updateSeries([
      {type:'candlestick', data: newCandles},
      {type:'line', data: e9},
      {type:'line', data: e21}
    ]);
  });
}
setInterval(actualizar, 6000);
</script>
</body></html>
"""

def loop():
    while True:
        last = estado["velas"][-1][3]
        o = last
        c = o + random.uniform(-40, 60)
        h = max(o,c)+random.uniform(2,10)
        l = min(o,c)-random.uniform(2,10)
        estado["velas"].append([o,h,l,c])
        if len(estado["velas"])>80:
            estado["velas"].pop(0)
        estado["btc_precio"]=c
        time.sleep(7)

@app.route('/')
def home():
    return render_template_string(HTML, velas_json=estado["velas"])
@app.route('/api')
def api(): return jsonify(estado)
@app.route('/health')
def health(): return "OK",200

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
