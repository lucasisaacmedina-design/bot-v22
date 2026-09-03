# LOBO V40.1 - SDE CAPITAL - SIMPLE, HONESTO, CON COMISION - EL QUE VENDE
import os
from flask import Flask, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Lobo V40.1 - Simple y Humilde</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{margin:0;background:#0f0f0f;color:#fff;font-family:Arial}
.header{padding:12px;text-align:center;background:#000;border-bottom:3px solid #f7931a}
.card{background:#1a1a1a;margin:8px;border-radius:10px;padding:10px;border:1px solid #333}
table{width:100%;font-size:11px;border-collapse:collapse}
th{color:#888;padding:8px;border-bottom:1px solid #333;text-align:left;font-size:10px}
td{padding:8px;border-bottom:1px solid #222;text-align:left}
.verde{color:#00ff88;font-weight:900}
.rojo{color:#ff4444}
</style>
</head>
<body>
<div class="header">
<div style="font-weight:900;font-size:17px">🦁 LOBO V40.1 • SDE CAPITAL</div>
<div style="font-size:9px;color:#aaa;margin-top:3px">SIMPLE Y HUMILDE • CON COMISION REAL • SER RICO NO PARECERLO ● EN VIVO</div>
</div>

<div class="card" style="display:flex;justify-content:space-around;text-align:center;border:1px solid #f7931a">
<div><div style="font-size:8px;color:#888">BALANCE</div><div style="font-size:20px;font-weight:900">145,81 USDT</div></div>
<div><div style="font-size:8px;color:#888">BRUTA HOY</div><div style="color:#00ff88;font-weight:900">+$65.43</div></div>
<div style="border:1px solid #ff4444;border-radius:6px;padding:2px 8px"><div style="font-size:7px;color:#888">COMISIONES BINANCE</div><div class="rojo" style="font-weight:900">-$4.89</div><div style="font-size:6px;color:#666">0.1%+0.1% REAL</div></div>
<div><div style="font-size:8px;color:#888">NETA REAL</div><div style="font-size:22px;font-weight:900;color:#00ff88">+$60.54</div></div>
</div>

<div class="card" style="padding:0;overflow:hidden">
<div style="height:380px" id="tv"></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"tv","height":380});
</script>
</div>

<div class="card">
<div style="font-weight:900;font-size:12px;margin-bottom:6px">ULTIMOS 10 TRADES - TODO A LA VISTA</div>
<table>
<tr><th>HORA</th><th>TIPO</th><th>BRUTO</th><th>COMISION</th><th>NETO REAL</th><th>R</th></tr>
<tr><td>19:32</td><td style="color:#00ff88">▲ BUY 78.922</td><td>-</td><td>-</td><td>-</td><td>⏳</td></tr>
<tr><td>19:45</td><td style="color:#ff4444">▼ SELL 79.105</td><td class="verde">+183.00</td><td class="rojo">-158.02</td><td class="verde">+24.98</td><td>✅</td></tr>
<tr><td>20:10</td><td style="color:#00ff88">▲ BUY 79.010</td><td>-</td><td>-</td><td>-</td><td>⏳</td></tr>
<tr><td>20:28</td><td style="color:#ff4444">▼ SELL 79.220</td><td class="verde">+210.00</td><td class="rojo">-158.23</td><td class="verde">+51.77</td><td>✅</td></tr>
<tr><td>21:05</td><td style="color:#00ff88">▲ BUY 79.150</td><td>-</td><td>-</td><td>-</td><td>⏳</td></tr>
</table>
<div style="font-size:8px;color:#666;margin-top:8px">Lobo no te miente: Bruto - Comisión Binance (0.2% total) = Neto Real que te queda. A veces se pierde, la mayoría se gana.</div>
</div>

<div class="card" style="text-align:center">
<button style="background:#f7931a;color:#000;padding:12px 25px;border-radius:25px;font-weight:900;border:none;width:90%;font-size:15px">EMPEZAR CON $20 - SIMPLE Y HUMILDE</button>
<div style="font-size:8px;color:#888;margin-top:5px">Santiago del Estero Capital • Sin humo • Solo números reales</div>
</div>

</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/health')
def health(): return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
