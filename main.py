# LOBO V33.1 - VELAS FIX
from flask import Flask
import threading, time, random, os
from datetime import datetime

app = Flask(__name__)

USDT_INICIAL = 85.27
BTC = 0.001
PNL = 55.73
PRECIO_COMPRA = 152753
TRADES = 267
PRECIO_ACTUAL = 151270
ESTADO = "COMPRADO"
HISTORIAL = ["13:24:01 COMPRA $152753","13:23:37 VENTA +0.80% | +$1.20","13:09:06 VENTA +0.86% | +$1.15"]

def bot_loop():
    global PNL, PRECIO_COMPRA, TRADES, PRECIO_ACTUAL, ESTADO, HISTORIAL
    while True:
        try:
            PRECIO_ACTUAL *= (1 + random.uniform(-0.003, 0.003))
            if ESTADO=="COMPRADO":
                g=(PRECIO_ACTUAL-PRECIO_COMPRA)/PRECIO_COMPRA
                if g>=0.008:
                    PNL+=1.2; TRADES+=1
                    HISTORIAL.insert(0,f"{datetime.now().strftime('%H:%M:%S')} VENTA +{g*100:.2f}%")
                    HISTORIAL=HISTORIAL[:6]; ESTADO="VENDIDO"
            else:
                if random.random()>0.7:
                    PRECIO_COMPRA=PRECIO_ACTUAL; TRADES+=1
                    HISTORIAL.insert(0,f"{datetime.now().strftime('%H:%M:%S')} COMPRA ${PRECIO_ACTUAL:.0f}")
                    HISTORIAL=HISTORIAL[:6]; ESTADO="COMPRADO"
            time.sleep(3)
        except: time.sleep(5)

@app.route('/')
def home():
    g=(PRECIO_ACTUAL-PRECIO_COMPRA)/PRECIO_COMPRA*100 if ESTADO=="COMPRADO" else 0
    usdt=USDT_INICIAL+PNL+(PRECIO_ACTUAL-PRECIO_COMPRA)*0.001 if ESTADO=="COMPRADO" else USDT_INICIAL+PNL
    color="#00c853" if g>=0 else "#ff1744"; bg="#e8f5e9" if g>=0 else "#ffebee"
    barra=max(5,min(100,(g+3)/3.8*100)); badge="COMPRADO" if ESTADO=="COMPRADO" else "ESPERANDO"
    precio_actual_js = int(PRECIO_ACTUAL)
    historial_html = "<br>".join(HISTORIAL)
    return """
<html><head><meta http-equiv="refresh" content="5"><meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/lightweight-charts@4.0.1/dist/lightweight-charts.standalone.production.js"></script>
<style>body{font-family:-apple-system,sans-serif;background:#f5f7fb;margin:0;padding:10px}
.card{background:white;border-radius:16px;padding:16px;max-width:420px;margin:8px auto;box-shadow:0 2px 12px rgba(0,0,0,0.08)}
.demo{background:#fff3cd;color:#856404;padding:8px;border-radius:8px;text-align:center;font-size:12px;font-weight:bold;margin-bottom:10px;border:1px solid #ffeaa7}
.big{font-size:30px;font-weight:900}.sub{font-size:13px;color:#666}
.row{display:flex;justify-content:space-between;margin:8px 0}.badge{padding:4px 10px;border-radius:20px;font-weight:bold;font-size:12px}
#chart{width:100%;height:220px;border-radius:12px;background:#fff;margin:10px 0;border:1px solid #eee}
.bar{background:#eee;height:8px;border-radius:10px;overflow:hidden}.fill{height:100%;transition:width 0.5s}
</style></head><body>
<div class="card"><div style="text-align:center"><div style="font-size:12px;color:#666">PROYECTO FAMILIA LOBO</div><div style="font-weight:800">LOBO V33.1 - VELAS PRO</div></div>
<div class="demo">MODO DEMO - SIN DINERO REAL</div>
<div style="background:#f8f9ff;padding:12px;border-radius:12px;border:1px solid #e0e7ff">
<div class="sub">Balance Total</div><div class="big">$""" + f"{usdt:.2f}" + """ USDT</div>
<div class="row"><span class="sub">Inicial: $85.27</span><span style="color:#00c853;font-weight:bold">+$""" + f"{PNL:.2f}" + """</span></div>
</div>
<div id="chart"></div>
<div class="row"><span class="sub">Operacion</span><span class="badge" style="background:""" + bg + """;color:""" + color + """">""" + badge + """</span></div>
<div class="row"><span>BTC: 0.00100</span><span>$""" + f"{PRECIO_ACTUAL:.0f}" + """</span></div>
<div class="row"><span class="sub">Flotante</span><span class="badge" style="background:""" + bg + """;color:""" + color + """">""" + f"{g:+.2f}%" + """</span></div>
<div class="bar"><div class="fill" style="width:""" + f"{barra:.0f}" + """%;background:""" + color + """"></div></div>
<div style="margin-top:12px"><div class="sub" style="font-weight:bold">Ultimos movimientos</div><div style="font-size:12px;color:#555;line-height:1.6">""" + historial_html + """</div></div>
</div>
<script>
const chart=LightweightCharts.createChart(document.getElementById('chart'),{layout:{background:{color:'#fff'},textColor:'#333'},grid:{vertLines:{color:'#f0f0f0'},horzLines:{color:'#f0f0f0'}}},width:document.getElementById('chart').clientWidth,height:220});
const candleSeries=chart.addCandlestickSeries();
fetch('https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=50').then(r=>r.json()).then(data=>{
 let candles=data.map(d=>({time:d[0]/1000,open:+d[1],high:+d[2],low:+d[3],close:+d[4]}));
 candleSeries.setData(candles); chart.timeScale().fitContent();
}).catch(()=>{
 let base=""" + str(precio_actual_js) + """; let data=[]; for(let i=50;i>0;i--){let o=base+(Math.random()-0.5)*200; let c=o+(Math.random()-0.5)*300; data.push({time:Math.floor(Date.now()/1000)-i*60,open:o,high:Math.max(o,c)+100,low:Math.min(o,c)-100,close:c});}
 candleSeries.setData(data);
});
</script></body></html>
"""
threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
