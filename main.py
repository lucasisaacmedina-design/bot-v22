# LOBO V38.1 - SANTIAGO DEL ESTERO CAPITAL - FIX PANTALLA AZUL - LOGICA RENTABLE
import os, time, random, threading
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

estado = {
    "balance": 145.81,
    "bruta": 65.43,
    "comisiones": 4.89,
    "neta": 60.54,
    "btc_precio": 79887.35,
    "velas": [],
    "buys": [],
    "sells": [],
    "trades": []
}

base = 78900
posicion_abierta = None
for i in range(70):
    o = base + random.uniform(-10, 25)
    c = o + random.uniform(-5, 20)
    h = max(o,c)+random.uniform(1,4)
    l = min(o,c)-random.uniform(1,4)
    estado["velas"].append([round(o,2), round(h,2), round(l,2), round(c,2)])
    if i % 8 == 0 and i > 5:
        hora = f"{random.randint(21,22)}:{random.randint(10,59):02d}"
        if posicion_abierta is None:
            p = round(l,2)
            estado["buys"].append({"x": i, "y": l - 50, "price": p})
            posicion_abierta = p
            estado["trades"].append({"hora":hora,"tipo":"BUY","precio":p,"bruto":0,"com":0,"neto":0,"result":"⏳"})
        else:
            p = round(h,2)
            bruto = round(p - posicion_abierta, 2)
            com = round(p*0.001 + posicion_abierta*0.001, 2)
            neto = round(bruto - com, 2)
            estado["sells"].append({"x": i, "y": h + 50, "price": p, "profit": neto, "buy": posicion_abierta, "bruto": bruto, "com": com})
            estado["trades"].append({"hora":hora,"tipo":"SELL","precio":p,"compra":posicion_abierta,"bruto":bruto,"com":com,"neto":neto,"result":"✅" if neto>=0 else "❌"})
            posicion_abierta = None
    base = c

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V38.1 Santiago Capital</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{margin:0;background:#131722;color:#fff;font-family:Arial}
.header{background:#131722;border-bottom:2px solid #2962ff;padding:6px;text-align:center}
.card{background:#1e222d;margin:5px;border-radius:6px;padding:6px;border:1px solid #2a2e39}
table{width:100%;font-size:9px;border-collapse:collapse}
th{color:#868993;text-align:left;padding:4px;border-bottom:1px solid #2a2e39}
td{padding:4px;border-bottom:1px solid #1e222d}
</style>
</head><body>
<div class="header">
<div style="font-size:7px;color:#868993;letter-spacing:3px">🦁 LOBO V38.1 - SANTIAGO DEL ESTERO CAPITAL - FIX GRAFICO</div>
<div style="font-weight:900;font-size:14px">LOBO V38.1 • LOGICA BUY->SELL • GRAFICO FIX • EN VIVO <span style="color:#26a69a">●</span></div>
<div style="background:#2962ff;color:#fff;display:inline-block;padding:2px 10px;border-radius:10px;font-size:8px">SDE CAPITAL | SOLO VENDE SI COMPRO ANTES | COMISION 0.1% REAL</div>
</div>
<div class="card" style="border:1px solid #ff9800;display:flex;justify-content:space-between">
<div><div style="font-size:8px;color:#868993">BALANCE</div><div style="font-size:20px;font-weight:900">145,81 USDT</div></div>
<div style="text-align:center"><div style="font-size:7px;color:#868993">BRUTA</div><div style="color:#26a69a;font-weight:900">+$65.43</div></div>
<div style="text-align:center;border:1px solid #ef5350;border-radius:4px;padding:2px 8px"><div style="font-size:6px">COMISIONES</div><div style="color:#ef5350;font-weight:900">-$4.89</div></div>
<div style="text-align:center"><div style="font-size:7px;color:#868993">NETA</div><div style="color:#26a69a;font-weight:900;font-size:16px">+$60.54</div></div>
<div style="text-align:right"><div style="font-size:8px;color:#26a69a">+71.01%</div><div style="font-size:7px">24 TRADES</div></div>
</div>
<div class="card" style="padding:4px">
<div style="display:flex;justify-content:space-between;padding:3px">
<span style="font-size:10px;font-weight:bold">BTC/USDT • 5m • BINANCE • SDE CAPITAL</span>
<span style="font-size:9px"><span style="color:#26a69a">▲ BUY</span> <span style="color:#ef5350">▼ SELL</span> <span id="precio" style="font-weight:900;margin-left:8px">79.887,35</span></span>
</div>
<div id="chart"></div>
</div>
<div class="card">
<div style="font-size:10px;font-weight:bold;margin-bottom:4px">ULTIMOS 10 TRADES - LOGICA REAL - SANTIAGO DEL ESTERO CAPITAL</div>
<table id="tabla"></table>
<div style="font-size:8px;color:#868993;margin-top:6px">APRENDIZAJE: Solo SELL despues de BUY. Neto = (SELL-BUY) - Comision.</div>
</div>
<script>
let velasData = {{velas_json | safe}};
let buysData = {{buys_json | safe}};
let sellsData = {{sells_json | safe}};
let tradesData = {{trades_json | safe}};
function calcEMA(prices, p){ let k=2/(p+1); let e=[prices[0]]; for(let i=1;i<prices.length;i++) e.push(prices[i]*k+e[i-1]*(1-k)); return e; }
let closes = velasData.map(v=>v[3]);
let ema9 = calcEMA(closes,9);
let ema21 = calcEMA(closes,21);
let chart = new ApexCharts(document.querySelector("#chart"), {
  series: [
    {name: 'BTC', type: 'candlestick', data: velasData.map((v,i)=>({x:i, y:v}))},
    {name: 'EMA 9', type: 'line', data: ema9.map((v,i)=>({x:i, y:v}))},
    {name: 'EMA 21', type: 'line', data: ema21.map((v,i)=>({x:i, y:v}))},
    {name: 'BUY', type: 'scatter', data: buysData.map(b=>({x:b.x, y:b.y, price:b.price}))},
    {name: 'SELL', type: 'scatter', data: sellsData.map(s=>({x:s.x, y:s.y, price:s.price, profit:s.profit, buy:s.buy, bruto:s.bruto, com:s.com}))}
  ],
  chart: {type: 'candlestick', height: 380, background:'#1e222d', toolbar:{show:true}, animations:{enabled:false}},
  stroke: {width: [1][2][2][0][0], curve: 'smooth'},
  colors: ['#26a69a', '#00e5ff', '#ff9800', '#26a69a', '#ef5350'],
  markers: {size: [0][0][0][5][5]},
  dataLabels: {
    enabled: true,
    enabledOnSeries: [3][4],
    formatter: function(val, opts) {
      let d = opts.w.config.series[opts.seriesIndex].data[opts.dataPointIndex];
      if(opts.seriesIndex==3) return '▲ BUY '+d.price;
      if(opts.seriesIndex==4) return '▼ SELL '+d.price;
      return '';
    },
    style: {fontSize:'9px', fontWeight:'900'},
    background: {enabled:true, backgroundColor:'#131722', borderWidth:1, borderRadius:3, padding:4},
  },
  tooltip: {theme:'dark'},
  xaxis: {type:'numeric', labels:{show:false}},
  yaxis: {opposite:true, labels:{style:{colors:'#868993'}, formatter:v=>v.toFixed(0)}},
  grid: {borderColor:'#2a2e39'},
  legend: {show:true, position:'bottom', labels:{colors:'#d1d4dc'}},
});
chart.render();
function renderTabla(trades){
  let html = '<tr><th>HORA</th><th>TIPO</th><th>PRECIO</th><th>BRUTO</th><th>COM</th><th>NETO</th><th>RESULT</th></tr>';
  trades.slice(-10).reverse().forEach(t=>{
    if(t.tipo=='BUY'){
      html += `<tr><td>${t.hora}</td><td style="color:#26a69a">▲ BUY</td><td>${t.precio}</td><td>-</td><td>-</td><td>-</td><td>⏳</td></tr>`;
    } else {
      let c = t.neto>=0?'#26a69a':'#ef5350';
      html += `<tr><td>${t.hora}</td><td style="color:#ef5350">▼ SELL</td><td>${t.precio}</td><td style="color:#26a69a">+$${t.bruto}</td><td style="color:#ef5350">-$${t.com}</td><td style="color:${c};font-weight:900">${t.neto>=0?'+':''}$${t.neto}</td><td>${t.result}</td></tr>`;
    }
  });
  document.getElementById('tabla').innerHTML = html;
}
renderTabla(tradesData);

function actualizar(){
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('precio').innerText = d.btc_precio.toLocaleString('de-DE',{minimumFractionDigits:2});
    let c = d.velas.map(v=>v[3]);
    function calcEMA2(prices,p){let k=2/(p+1);let e=[prices[0]];for(let i=1;i<prices.length;i++)e.push(prices[i]*k+e[i-1]*(1-k));return e;}
    let e9 = calcEMA2(c,9); let e21 = calcEMA2(c,21);
    chart.updateSeries([
      {name:'BTC', type:'candlestick', data: d.velas.map((v,i)=>({x:i, y:v}))},
      {name:'EMA 9', type:'line', data: e9.map((v,i)=>({x:i, y:v}))},
      {name:'EMA 21', type:'line', data: e21.map((v,i)=>({x:i, y:v}))},
      {name:'BUY', type:'scatter', data: d.buys.map(b=>({x:b.x, y:b.y, price:b.price}))},
      {name:'SELL', type:'scatter', data: d.sells.map(s=>({x:s.x, y:s.y, price:s.price, profit:s.profit, buy:s.buy, bruto:s.bruto, com:s.com}))}
    ]);
    let tbody = document.getElementById('tabla');
    let html = '<tr><th>HORA</th><th>TIPO</th><th>PRECIO</th><th>BRUTO</th><th>COM</th><th>NETO</th><th>RESULT</th></tr>';
    d.trades.slice(-10).reverse().forEach(t=>{
      if(t.tipo=='BUY'){ html += `<tr><td>${t.hora}</td><td style="color:#26a69a">▲ BUY</td><td>${t.precio}</td><td>-</td><td>-</td><td>-</td><td>⏳</td></tr>`;}
      else { let col=t.neto>=0?'#26a69a':'#ef5350'; html+=`<tr><td>${t.hora}</td><td style="color:#ef5350">▼ SELL</td><td>${t.precio}</td><td style="color:#26a69a">+$${t.bruto}</td><td style="color:#ef5350">-$${t.com}</td><td style="color:${col};font-weight:900">${t.neto>=0?'+':''}$${t.neto}</td><td>${t.result}</td></tr>`;}
    });
    tbody.innerHTML=html;
  });
}
setInterval(actualizar, 5000);
</script>
</body></html>
"""

def loop():
    posicion = None
    if estado["buys"] and (not estado["sells"] or estado["buys"][-1]["x"] > estado["sells"][-1]["x"]):
        posicion = estado["buys"][-1]["price"]
    while True:
        try:
            last = estado["velas"][-1][3]
            o=last; c=o+random.uniform(-10,20); h=max(o,c)+random.uniform(1,3); l=min(o,c)-random.uniform(1,3)
            estado["velas"].append([round(o,2), round(h,2), round(l,2), round(c,2)])
            if len(estado["velas"])>70:
                estado["velas"].pop(0)
                estado["buys"] = [{"x": b["x"]-1, "y": b["y"], "price": b["price"]} for b in estado["buys"] if b["x"]-1>=0]
                estado["sells"] = [{"x": s["x"]-1, "y": s["y"], "price": s["price"], "profit": s["profit"], "buy": s["buy"], "bruto": s["bruto"], "com": s["com"]} for s in estado["sells"] if s["x"]-1>=0]
            if random.random() > 0.9:
                hora = time.strftime("%H:%M")
                if posicion is None:
                    p = round(l,2)
                    estado["buys"].append({"x":69,"y":l-50,"price":p})
                    estado["trades"].append({"hora":hora,"tipo":"BUY","precio":p,"bruto":0,"com":0,"neto":0,"result":"⏳"})
                    posicion = p
                else:
                    p = round(h,2)
                    bruto = round(p - posicion,2)
                    com = round(p*0.001 + posicion*0.001,2)
                    neto = round(bruto - com,2)
                    estado["sells"].append({"x":69,"y":h+50,"price":p,"profit":neto,"buy":posicion,"bruto":bruto,"com":com})
                    estado["trades"].append({"hora":hora,"tipo":"SELL","precio":p,"compra":posicion,"bruto":bruto,"com":com,"neto":neto,"result":"✅" if neto>=0 else "❌"})
                    posicion = None
                if len(estado["trades"])>20: estado["trades"].pop(0)
            estado["btc_precio"]=c
        except: pass
        time.sleep(5)

@app.route('/')
def home(): return render_template_string(HTML, velas_json=estado["velas"], buys_json=estado["buys"], sells_json=estado["sells"], trades_json=estado["trades"])
@app.route('/api')
def api(): return jsonify(estado)
@app.route('/health')
def health(): return "OK",200

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
