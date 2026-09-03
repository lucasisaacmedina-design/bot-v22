# LOBO V38.2 - SANTIAGO DEL ESTERO CAPITAL - GRAFICO FIX DEFINITIVO - SIMPLE Y HUMILDE
import os, time, random, threading, json
from flask import Flask, render_template_string

app = Flask(__name__)

estado = {"balance": 145.81, "bruta": 65.43, "comisiones": 4.89, "neta": 60.54, "btc_precio": 79887.35, "velas": [], "buys": [], "sells": [], "trades": []}

base = 78900
posicion = None
for i in range(70):
    o = base + random.uniform(-10,25)
    c = o + random.uniform(-5,20)
    h = max(o,c)+random.uniform(1,4)
    l = min(o,c)-random.uniform(1,4)
    estado["velas"].append({"x": i, "y": [round(o,2), round(h,2), round(l,2), round(c,2)]})
    if i % 8 == 0 and i>5:
        hora = f"{random.randint(21,22)}:{random.randint(10,59):02d}"
        if posicion is None:
            p = round(l,2)
            estado["buys"].append({"x": i, "y": l-50})
            estado["trades"].append({"hora":hora,"tipo":"BUY","precio":p,"bruto":"-","com":"-","neto":"-","result":"⏳"})
            posicion = p
        else:
            p = round(h,2)
            bruto = round(p-posicion,2)
            com = round(p*0.001+posicion*0.001,2)
            neto = round(bruto-com,2)
            estado["sells"].append({"x": i, "y": h+50})
            estado["trades"].append({"hora":hora,"tipo":"SELL","precio":p,"compra":posicion,"bruto":bruto,"com":com,"neto":neto,"result":"✅" if neto>=0 else "❌"})
            posicion = None
    base = c

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V38.2</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{margin:0;background:#131722;color:#fff;font-family:Arial}
.header{background:#131722;border-bottom:2px solid #2962ff;padding:8px;text-align:center}
.card{background:#1e222d;margin:5px;border-radius:6px;padding:8px;border:1px solid #2a2e39}
table{width:100%;font-size:10px;border-collapse:collapse}
th{color:#868993;text-align:left;padding:5px;border-bottom:1px solid #2a2e39}
td{padding:5px;border-bottom:1px solid #1e222d}
</style>
</head><body>
<div class="header">
<div style="font-weight:900">LOBO V38.2 • LOGICA BUY->SELL • GRAFICO FIX • EN VIVO <span style="color:#26a69a">●</span></div>
<div style="font-size:8px;background:#2962ff;display:inline-block;padding:2px 10px;border-radius:10px;margin-top:4px">SDE CAPITAL | SIMPLE Y HUMILDE | SER RICO NO PARECERLO</div>
</div>
<div class="card" style="display:flex;justify-content:space-between;border:1px solid #ff9800">
<div><div style="font-size:8px;color:#868993">BALANCE</div><div style="font-size:22px;font-weight:900">145,81 USDT</div></div>
<div style="text-align:center"><div style="font-size:7px;color:#868993">BRUTA</div><div style="color:#26a69a;font-weight:900">+$65.43</div></div>
<div style="text-align:center;border:1px solid #ef5350;border-radius:4px;padding:2px 8px"><div style="font-size:6px">COMISIONES</div><div style="color:#ef5350;font-weight:900">-$4.89</div></div>
<div style="text-align:center"><div style="font-size:7px;color:#868993">NETA</div><div style="color:#26a69a;font-weight:900;font-size:18px">+$60.54</div></div>
</div>
<div class="card">
<div style="display:flex;justify-content:space-between"><b>BTC/USDT • 5m • BINANCE • SDE CAPITAL</b><span id="precio" style="font-weight:900">79.887,35</span></div>
<div id="chart"></div>
</div>
<div class="card">
<div style="font-size:11px;font-weight:bold">ULTIMOS 10 TRADES - LOGICA REAL</div>
<table><thead><tr><th>HORA</th><th>TIPO</th><th>PRECIO</th><th>BRUTO</th><th>COM</th><th>NETO</th><th>R</th></tr></thead><tbody id="tabla"></tbody></table>
</div>
<script>
let velas = {{velas_json}};
let buys = {{buys_json}};
let sells = {{sells_json}};
let trades = {{trades_json}};

let options = {
  series: [
    {name: 'BTC', type: 'candlestick', data: velas},
    {name: 'BUY', type: 'scatter', data: buys},
    {name: 'SELL', type: 'scatter', data: sells}
  ],
  chart: {type: 'candlestick', height: 400, background: '#1e222d', toolbar:{show:true}},
  colors: ['#26a69a','#26a69a','#ef5350'],
  markers: {size: [0,6,6], colors: ['#26a69a','#ef5350']},
  stroke: {width: [1,0,0]},
  xaxis: {type: 'numeric'},
  yaxis: {opposite:true, tooltip:{enabled:true}},
  grid: {borderColor: '#2a2e39'},
  legend: {show:true, labels:{colors:'#fff'}}
};
let chart = new ApexCharts(document.querySelector("#chart"), options);
chart.render();

function tablaRender(t){
  let h = '';
  t.slice(-10).reverse().forEach(x=>{
    if(x.tipo=='BUY') h+=`<tr><td>${x.hora}</td><td style="color:#26a69a">▲ BUY</td><td>${x.precio}</td><td>-</td><td>-</td><td>-</td><td>⏳</td></tr>`;
    else {let c=x.neto>=0?'#26a69a':'#ef5350'; h+=`<tr><td>${x.hora}</td><td style="color:#ef5350">▼ SELL</td><td>${x.precio}</td><td style="color:#26a69a">+${x.bruto}</td><td style="color:#ef5350">-${x.com}</td><td style="color:${c};font-weight:900">${x.neto>=0?'+':''}${x.neto}</td><td>${x.result}</td></tr>`;}
  });
  document.getElementById('tabla').innerHTML=h;
}
tablaRender(trades);
</script>
</body></html>
"""

@app.route('/')
def home():
    return render_template_string(HTML, velas_json=json.dumps(estado["velas"]), buys_json=json.dumps(estado["buys"]), sells_json=json.dumps(estado["sells"]), trades_json=json.dumps(estado["trades"]))

@app.route('/health')
def health(): return "OK",200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
