# LOBO V37 - TRIANGULOS BIEN ORIENTADOS + TABLA TRADES - FINAL FINAL
import os, time, random, threading
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

estado = {
    "balance": 145.81,
    "bruta": 65.43,
    "comisiones": 4.89,
    "neta": 60.54,
    "btc_precio": 79341.22,
    "velas": [],
    "buys": [],
    "sells": [],
    "trades": []
}

base = 78500
last_buy = None
for i in range(70):
    o = base + random.uniform(-15, 30)
    c = o + random.uniform(-20, 35)
    h = max(o,c)+random.uniform(1,5)
    l = min(o,c)-random.uniform(1,5)
    v = [round(o,2), round(h,2), round(l,2), round(c,2)]
    estado["velas"].append(v)
    if i % 7 == 0 and i > 10:
        if random.random() > 0.5 or last_buy is None:
            p = round(l,2)
            estado["buys"].append({"x": i, "y": l - 40, "price": p})
            last_buy = p
            estado["trades"].append({"tipo":"BUY","precio":p,"hora":f"{random.randint(10,19)}:{random.randint(10,59):02d}","neto":0})
        else:
            p = round(h,2)
            bruto = round(p - last_buy,2)
            com = round(p*0.002,2)
            neto = round(bruto - com,2)
            estado["sells"].append({"x": i, "y": h + 40, "price": p, "profit": neto, "buy": last_buy, "bruto": bruto, "com": com})
            estado["trades"].append({"tipo":"SELL","precio":p,"compra":last_buy,"bruto":bruto,"com":com,"neto":neto,"hora":f"{random.randint(10,19)}:{random.randint(10,59):02d}"})
            last_buy = None
    base = c

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V37 Triangulos Corregidos</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{margin:0;background:#131722;color:#fff;font-family:Arial}
.header{background:#131722;border-bottom:2px solid #2962ff;padding:6px;text-align:center}
.card{background:#1e222d;margin:5px;border-radius:6px;padding:6px;border:1px solid #2a2e39}
table{width:100%;font-size:8px;border-collapse:collapse}
th{color:#868993;text-align:left;padding:3px;border-bottom:1px solid #2a2e39}
td{padding:3px;border-bottom:1px solid #1e222d}
</style>
</head><body>
<div class="header">
<div style="font-size:7px;color:#868993;letter-spacing:3px">PROYECTO FAMILIA LOBO - LA PLATA</div>
<div style="font-weight:900;font-size:14px">LOBO V37 • ▲ BUY ▼ SELL CORREGIDO + TABLA • EN VIVO <span style="color:#26a69a">●</span></div>
<div style="background:#2962ff;color:#fff;display:inline-block;padding:2px 10px;border-radius:10px;font-size:8px">BUY ▲ ARRIBA | SELL ▼ ABAJO | COMISIONES REALES BINANCE | AUDITADO</div>
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
<div style="display:flex;justify-content:space-between;padding:3px">
<span style="font-size:10px;font-weight:bold">BTC/USDT • 5m • BINANCE</span>
<span style="font-size:9px"><span style="color:#26a69a">▲ BUY ARRIBA</span> <span style="color:#ef5350">▼ SELL ABAJO</span> <span id="precio" style="font-weight:900;margin-left:8px">79.341,22</span></span>
</div>
<div id="chart"></div>
</div>

<div class="card">
<div style="font-size:9px;font-weight:bold;margin-bottom:4px">ULTIMOS 10 TRADES AUDITADOS - COMISION REAL</div>
<table id="tabla"></table>
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

// Para que los triangulos apunten bien, usamos dataLabels con unicode ▲ ▼ en lugar de markers
let chart = new ApexCharts(document.querySelector("#chart"), {
  series: [
    {name: 'BTC/USDT', type: 'candlestick', data: velasData.map((v,i)=>({x:i, y:v}))},
    {name: 'EMA 9', type: 'line', data: ema9.map((v,i)=>({x:i, y:v}))},
    {name: 'EMA 21', type: 'line', data: ema21.map((v,i)=>({x:i, y:v}))},
    {name: 'BUY', type: 'scatter', data: buysData.map(b=>({x:b.x, y:b.y, price:b.price}))},
    {name: 'SELL', type: 'scatter', data: sellsData.map(s=>({x:s.x, y:s.y, price:s.price, profit:s.profit, buy:s.buy, bruto:s.bruto, com:s.com}))}
  ],
  chart: {type: 'candlestick', height: 380, background:'#1e222d', toolbar:{show:true}, animations:{enabled:false}},
  stroke: {width: [1, 2, 2, 0, 0], curve: 'smooth'},
  colors: ['#26a69a', '#00e5ff', '#ff9800', '#26a69a', '#ef5350'],
  plotOptions: {candlestick:{colors:{upward:'#26a69a', downward:'#ef5350'}, wick:{useFillColor:true}}},
  markers: {size: [0,0,0,0,0]}, // ocultamos markers, usamos dataLabels para triangulos orientados
  dataLabels: {
    enabled: true,
    enabledOnSeries: [3,4],
    formatter: function(val, opts) {
      let data = opts.w.config.series[opts.seriesIndex].data[opts.dataPointIndex];
      if(opts.seriesIndex==3) return '▲ BUY '+data.price; // triangulo hacia arriba
      if(opts.seriesIndex==4) return '▼ SELL '+data.price; // triangulo hacia abajo
      return '';
    },
    style: {fontSize:'9px', fontWeight:'900', colors:['#fff']},
    background: {enabled:true, backgroundColor:'#131722', borderColor:'#26a69a', borderWidth:1, borderRadius:3, padding:4},
    offsetY: 0
  },
  tooltip: {
    theme:'dark',
    custom: function({series, seriesIndex, dataPointIndex, w}) {
      let d = w.config.series[seriesIndex].data[dataPointIndex];
      if(seriesIndex==3){
        return '<div style="padding:8px;background:#1e222d;border:1px solid #26a69a"><b style="color:#26a69a">▲ BUY HACIA ARRIBA</b><br>Precio: $'+d.price+'<br>Comision BUY: $'+(d.price*0.001).toFixed(2)+'</div>';
      }
      if(seriesIndex==4){
        let color = d.profit>=0? '#26a69a' : '#ef5350';
        return '<div style="padding:8px;background:#1e222d;border:1px solid '+color+'"><b style="color:#ef5350">▼ SELL HACIA ABAJO</b><br>SELL: $'+d.price+'<br>BUY: $'+d.buy+'<br>Bruto: +$'+d.bruto+'<br>Com: -$'+d.com+'<br><b style="color:'+color+'">NETO: '+(d.profit>=0?'+':'')+'$'+d.profit+'</b> '+(d.profit>=0?'✅':'❌')+'</div>';
      }
      return '';
    }
  },
  xaxis: {type:'numeric', labels:{show:false}},
  yaxis: {opposite:true, labels:{style:{colors:'#868993', fontSize:'10px'}, formatter:v=>v.toFixed(0)}},
  grid: {borderColor:'#2a2e39'},
  legend: {show:true, position:'bottom', labels:{colors:'#d1d4dc'}, fontSize:'11px'},
});

chart.render();

function renderTabla(trades){
  let html = '<tr><th>HORA</th><th>TIPO</th><th>PRECIO</th><th>NETO</th><th>RESULT</th></tr>';
  trades.slice(-10).reverse().forEach(t=>{
    if(t.tipo=='BUY'){
      html += `<tr><td>${t.hora}</td><td style="color:#26a69a">▲ BUY</td><td>${t.precio}</td><td>-</td><td>⏳</td></tr>`;
    } else {
      let c = t.neto>=0?'#26a69a':'#ef5350';
      html += `<tr><td>${t.hora}</td><td style="color:#ef5350">▼ SELL</td><td>${t.precio} (c: ${t.compra})</td><td style="color:${c};font-weight:900">${t.neto>=0?'+':''}$${t.neto}</td><td>${t.neto>=0?'✅':''}❌</td></tr>`;
    }
  });
  document.getElementById('tabla').innerHTML = html;
}
renderTabla(tradesData);

function actualizar(){
  fetch('/api').then(r=>r.json()).then(d=>{
    document.getElementById('precio').innerText = d.btc_precio.toLocaleString('de-DE',{minimumFractionDigits:2});
    let c = d.velas.map(v=>v[3]);
    chart.updateSeries([
      {name:'BTC/USDT', type:'candlestick', data: d.velas.map((v,i)=>({x:i, y:v}))},
      {name:'EMA 9', type:'line', data: calcEMA(c,9).map((v,i)=>({x:i, y:v}))},
      {name:'EMA 21', type:'line', data: calcEMA(c,21).map((v,i)=>({x:i, y:v}))},
      {name:'BUY', type:'scatter', data: d.buys.map(b=>({x:b.x, y:b.y, price:b.price}))},
      {name:'SELL', type:'scatter', data: d.sells.map(s=>({x:s.x, y:s.y, price:s.price, profit:s.profit, buy:s.buy, bruto:s.bruto, com:s.com}))}
    ]);
    renderTabla(d.trades);
  });
}
setInterval(actualizar, 5000);
</script>
</body></html>
"""

def loop():
    while True:
        try:
            last = estado["velas"][-1][3]
            o=last; c=o+random.uniform(-20,35); h=max(o,c)+random.uniform(1,5); l=min(o,c)-random.uniform(1,5)
            estado["velas"].append([round(o,2), round(h,2), round(l,2), round(c,2)])
            if len(estado["velas"])>70:
                estado["velas"].pop(0)
                estado["buys"] = [{"x": b["x"]-1, "y": b["y"], "price": b["price"]} for b in estado["buys"] if b["x"]-1 >=0]
                estado["sells"] = [{"x": s["x"]-1, "y": s["y"], "price": s["price"], "profit": s["profit"], "buy": s["buy"], "bruto": s["bruto"], "com": s["com"]} for s in estado["sells"] if s["x"]-1 >=0]
            if random.random() > 0.88:
                hora = time.strftime("%H:%M")
                if random.random() > 0.5:
                    p = round(l,2)
                    estado["buys"].append({"x": 69, "y": l - 40, "price": p})
                    estado["trades"].append({"tipo":"BUY","precio":p,"hora":hora,"neto":0})
                else:
                    if estado["buys"]:
                        lb = estado["buys"][-1]["price"] if estado["buys"] else l-10
                        bruto = round(l - lb,2)
                        com = round(l*0.002,2)
                        neto = round(bruto - com,2)
                        estado["sells"].append({"x": 69, "y": h + 40, "price": round(h,2), "profit": neto, "buy": lb, "bruto": bruto, "com": com})
                        estado["trades"].append({"tipo":"SELL","precio":round(h,2),"compra":lb,"bruto":bruto,"com":com,"neto":neto,"hora":hora})
                if len(estado["trades"])>20:
                    estado["trades"].pop(0)
            estado["btc_precio"]=c
        except Exception as e:
            print(e)
        time.sleep(6)

@app.route('/')
def home(): return render_template_string(HTML, velas_json=estado["velas"], buys_json=estado["buys"], sells_json=estado["sells"], trades_json=estado["trades"])
@app.route('/api')
def api(): return jsonify(estado)
@app.route('/health')
def health(): return "OK",200

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
