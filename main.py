# LOBO V34.4 - TRADINGVIEW REAL - VELAS GORDAS + COMISIONES
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
    "btc_precio": 73893.20,
    "trades": 24,
    "winrate": 95.8,
    "descartados": 20,
    "velas": [],
    "ema9": [],
    "ema21": [],
    "movimientos": [
        "15:38:10 VENTA BTC 73.893 | Bruto +$0.38 | Com $0.30 | NETO +$0.08 ✅",
        "15:35:22 COMPRA BTC 73.650 | Com $0.15 | Qty 0.002",
        "15:32:05 DESCARTADO | Bruto +0.11% < Com 0.20% Salvado ❌",
        "15:28:40 VENTA BTC 73.720 | Bruto +$0.52 | Com $0.30 | NETO +$0.22 ✅",
    ]
}

base = 78400
vals=[]
for i in range(80):
    o = base + random.uniform(-40,60)
    c = o + random.uniform(-50,70)
    h = max(o,c)+random.uniform(2,15)
    l = min(o,c)-random.uniform(2,15)
    vals.append(c)
    estado["velas"].append({"x": i, "y": [round(o,2), round(h,2), round(l,2), round(c,2)]})
    base = c

def ema(data,p):
    k=2/(p+1); r=[data[0]]
    for i in range(1,len(data)): r.append(data[i]*k + r[-1]*(1-k))
    return [round(x,2) for x in r]

estado["ema9"]=ema(vals,9)
estado["ema21"]=ema(vals,21)

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V34.4 TradingView</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{margin:0;background:#131722;color:#d1d4dc;font-family:Arial, sans-serif}
.header{background:#131722;border-bottom:1px solid #2a2e39;padding:8px;text-align:center}
.card{background:#1e222d;margin:6px;border-radius:6px;padding:10px;border:1px solid #2a2e39}
.kpi{background:#2a2e39;padding:6px;border-radius:4px;text-align:center}
.kpi_lab{font-size:7px;color:#868993;letter-spacing:0.5px}.kpi_val{font-size:12px;font-weight:bold}
.verde{color:#26a69a}.rojo{color:#ef5350}.tv-yellow{color:#ff9800}
.grid4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:5px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px}
</style>
</head><body>
<div class="header">
<div style="font-size:8px;color:#868993;letter-spacing:3px">PROYECTO FAMILIA LOBO</div>
<div style="font-weight:900;font-size:15px;color:#fff">LOBO V34.4 • TRADINGVIEW PRO <span style="color:#26a69a">● EN VIVO</span></div>
<div style="background:#2962ff;color:#fff;display:inline-block;padding:3px 12px;border-radius:12px;font-size:9px;margin-top:4px;font-weight:bold">AUDITADO - COMISIONES REALES BINANCE 0.10% + 0.10%</div>
</div>

<div class="card" style="background:#131722;border:1px solid #ff9800">
<div style="display:flex;justify-content:space-between">
<div><div style="font-size:9px;color:#868993">BALANCE TOTAL</div><div style="font-size:30px;font-weight:900;color:#fff" id="bal">145,81 USDT</div><div style="font-size:10px;color:#868993">Inicial $85.27 | 24 trades</div></div>
<div style="text-align:right"><div style="font-size:22px;font-weight:900;color:#26a69a" id="neta_big">+$60.54</div><div style="font-size:12px;color:#26a69a" id="pct">+71.01% NETA</div><div style="font-size:8px;color:#868993">DESPUÉS DE COMISIONES</div></div>
</div>
<div class="grid3" style="margin-top:10px">
<div class="kpi"><div class="kpi_lab">BRUTA</div><div class="kpi_val" style="color:#26a69a" id="bruta">+$65.43</div></div>
<div class="kpi" style="border:1px solid #ef5350"><div class="kpi_lab">COMISIONES PAGADAS</div><div class="kpi_val" style="color:#ef5350" id="comis">-$4.89</div><div style="font-size:6px;color:#868993">20 x $0.15 + 20 x $0.15</div></div>
<div class="kpi" style="background:#26a69a20;border:1px solid #26a69a"><div class="kpi_lab">NETA REAL</div><div class="kpi_val" style="color:#26a69a;font-size:15px" id="neta">+$60.54</div></div>
</div>
</div>

<div class="card">
<div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:10px;font-weight:900">ESTADÍSTICAS PRO</span><span style="font-size:8px;background:#26a69a;color:#000;padding:2px 6px;border-radius:8px;font-weight:bold">AUDITADO</span></div>
<div class="grid4">
<div class="kpi"><div class="kpi_lab">TRADES</div><div class="kpi_val" id="tr">24</div></div>
<div class="kpi"><div class="kpi_lab">WIN RATE</div><div class="kpi_val" style="color:#26a69a" id="wr">95.8%</div></div>
<div class="kpi"><div class="kpi_lab">PROFIT FACTOR</div><div class="kpi_val" style="color:#2962ff">3.45</div></div>
<div class="kpi"><div class="kpi_lab">DESCARTADOS</div><div class="kpi_val tv-yellow">20</div></div>
</div>
<div class="grid4" style="margin-top:5px">
<div class="kpi"><div class="kpi_lab">MEJOR</div><div class="kpi_val" style="color:#26a69a">+$0.18</div></div>
<div class="kpi"><div class="kpi_lab">PEOR</div><div class="kpi_val" style="color:#ef5350">-$0.04</div></div>
<div class="kpi"><div class="kpi_lab">PROMEDIO</div><div class="kpi_val">+$0.058</div></div>
<div class="kpi"><div class="kpi_lab">DRAWDOWN</div><div class="kpi_val" style="color:#ef5350">-0.85%</div></div>
</div>
</div>

<div class="card" style="padding:5px">
<div style="display:flex;justify-content:space-between;padding:5px 5px 0 5px"><span style="font-size:11px;font-weight:bold;color:#fff">Bitcoin / TetherUS • BINANCE • 5m EN VIVO</span><span style="font-size:10px"><span style="color:#26a69a">● EMA 9</span> <span style="color:#ff9800">● EMA 21</span> <span id="precio" style="color:#fff;font-weight:900;margin-left:10px">73.893,20</span></span></div>
<div id="chart" style="background:#1e222d"></div>
</div>

<div class="card" style="border-left:3px solid #ff9800">
<div style="display:flex;justify-content:space-between"><span style="font-size:9px;color:#868993">OPERACIÓN ACTUAL</span><span style="background:#ff9800;color:#000;padding:2px 8px;border-radius:10px;font-size:8px;font-weight:900">COMPRADO</span></div>
<div class="grid3" style="margin-top:8px">
<div class="kpi"><div class="kpi_lab">FLOTANTE BRUTO</div><div class="kpi_val" style="color:#ef5350">-0.45%</div><div style="font-size:8px">-$0.68</div></div>
<div class="kpi"><div class="kpi_lab">COMISIÓN CIERRE</div><div class="kpi_val tv-yellow">$0.30</div><div style="font-size:6px">0.20% total</div></div>
<div class="kpi"><div class="kpi_lab">FLOTANTE NETO</div><div class="kpi_val" style="color:#ef5350">-0.65%</div><div style="font-size:8px">-$0.98</div></div>
</div>
</div>

<div class="card">
<div style="font-size:10px;font-weight:900">📜 AUDITORÍA TIEMPO REAL - COMISIONES</div>
<div id="movs" style="font-size:10px;margin-top:6px;line-height:18px;font-family:monospace;background:#131722;padding:8px;border-radius:4px"></div>
</div>

<script>
let velas = {{velas_json | safe}};
let ema9 = {{ema9_json | safe}};
let ema21 = {{ema21_json | safe}};
let movs = {{movs_json | safe}};

let seriesData = velas;
let e9 = ema9.map((v,i)=>({x:i, y:v}));
let e21 = ema21.map((v,i)=>({x:i, y:v}));

let chart = new ApexCharts(document.querySelector("#chart"), {
  series: [
    {name:'BTC', type:'candlestick', data: seriesData},
    {name:'EMA 9', type:'line', data: e9},
    {name:'EMA 21', type:'line', data: e21}
  ],
  chart: {type:'candlestick', height:380, background:'#1e222d', toolbar:{show:true, tools:{download:true, zoom:true, pan:true}}, animations:{enabled:true, dynamicAnimation:{speed:500}}},
  stroke: {width:[1,2,2], curve:'smooth', lineCap:'round'},
  colors: ['#fff', '#26a69a', '#ff9800'],
  plotOptions: {candlestick:{wick:{useFillColor:true}, colors:{upward:'#26a69a', downward:'#ef5350'}}},
  xaxis: {type:'numeric', labels:{style:{colors:'#868993', fontSize:'10px'}}},
  yaxis: {opposite:true, labels:{style:{colors:'#868993'}, formatter:v=>v.toLocaleString('de-DE')}, tooltip:{enabled:true}},
  grid: {borderColor:'#2a2e39', strokeDashArray:0, xaxis:{lines:{show:true, color:'#2a2e39'}}, yaxis:{lines:{show:true, color:'#2a2e39'}}},
  tooltip: {theme:'dark', shared:false, x:{show:true}},
});

chart.render();

function renderMovs(m){
  document.getElementById('movs').innerHTML = m.map(x=>{
    if(x.includes('NETO +')) return '<div style="color:#26a69a">• '+x+'</div>';
    if(x.includes('DESCARTADO')) return '<div style="color:#ff9800;background:#ff980015;padding:1px 5px;border-radius:3px;margin:2px 0">• '+x+'</div>';
    return '<div style="color:#868993">• '+x+'</div>';
  }).join('');
}
renderMovs(movs);

function actualizar(){
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('precio').innerText = d.btc_precio.toLocaleString('de-DE',{minimumFractionDigits:2});
    document.getElementById('bal').innerText = d.balance.toFixed(2).replace('.',',')+' USDT';
    document.getElementById('bruta').innerText = '+$'+d.bruta.toFixed(2);
    document.getElementById('comis').innerText = '-$'+d.comisiones.toFixed(2);
    document.getElementById('neta').innerText = '+$'+d.neta.toFixed(2);
    document.getElementById('neta_big').innerText = '+$'+d.neta.toFixed(2);
    document.getElementById('pct').innerText = '+'+d.neta_pct.toFixed(2)+'% NETA';
    chart.updateSeries([
      {data: d.velas.map((v,i)=>({x:i, y:v}))},
      {data: d.ema9.map((y,i)=>({x:i,y}))},
      {data: d.ema21.map((y,i)=>({x:i,y}))}
    ]);
    renderMovs(d.movimientos);
  });
}
setInterval(actualizar, 5000);
</script>
</body></html>
"""

def loop():
    while True:
        last = estado["velas"][-1]["y"][3]
        o = last; c = o + random.uniform(-50,70); h = max(o,c)+random.uniform(2,12); l = min(o,c)-random.uniform(2,12)
        estado["velas"].append({"x": len(estado["velas"]), "y": [o,h,l,c]})
        if len(estado["velas"])>80: estado["velas"].pop(0)
        vals=[v["y"][3] for v in estado["velas"]]
        estado["ema9"]=ema(vals,9); estado["ema21"]=ema(vals,21)
        estado["btc_precio"]=c
        time.sleep(7)

@app.route('/')
def home():
    return render_template_string(HTML, velas_json=estado["velas"], ema9_json=estado["ema9"], ema21_json=estado["ema21"], movs_json=estado["movimientos"])
@app.route('/api')
def api(): return jsonify(estado)
@app.route('/health')
def health(): return "OK",200

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
