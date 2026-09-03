# LOBO V41 - TESTNET REAL - SDE CAPITAL - CORRE 7 DIAS
# Dinero ficticio de Binance Testnet + Precio real + Comision real 0.2%

import os
import time
from flask import Flask, render_template_string, jsonify
from binance.client import Client
from binance.exceptions import BinanceAPIException

app = Flask(__name__)

# LEE DE RENDER - NO HARDCODEADO
API_KEY = os.environ.get("BINANCE_TESTNET_API_KEY")
API_SECRET = os.environ.get("BINANCE_TESTNET_API_SECRET")

client = None
MODO = "MODO DEMO"
BALANCE_INICIAL = 145.81

def conectar():
    global client, MODO
    if API_KEY and API_SECRET:
        try:
            client = Client(API_KEY, API_SECRET, testnet=True)
            client.API_URL = 'https://testnet.binance.vision/api'
            client.get_account() # prueba conexion
            MODO = "TESTNET CONECTADO - DINERO FICTICIO"
            print("TESTNET OK")
        except Exception as e:
            MODO = f"ERROR TESTNET: {str(e)[:60]}"
            client = None
    else:
        MODO = "MODO DEMO - FALTA KEY EN RENDER"

conectar()

# Memoria simple para esta semana
estado = {"balance": BALANCE_INICIAL, "bruta": 0.0, "comision": 0.0, "trades": []}

HTML = """
<!DOCTYPE html>
<html><head>
<title>Lobo V41 Testnet</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{margin:0;background:#0f0f0f;color:#fff;font-family:Arial}
.top{background:#ffcc00;color:#000;text-align:center;padding:6px;font-weight:900;font-size:11px}
.header{padding:12px;text-align:center;background:#000;border-bottom:3px solid #f7931a}
.card{background:#1a1a1a;margin:8px;border-radius:10px;padding:10px;border:1px solid #333}
table{width:100%;font-size:11px;border-collapse:collapse} th{color:#888;padding:6px;border-bottom:1px solid #333} td{padding:6px;border-bottom:1px solid #222}
.verde{color:#00ff88} .rojo{color:#ff4444}
</style>
</head><body>
<div class="top">🧪 {{modo}} • TESTNET BINANCE • CORRE 7 DIAS • COMISION REAL 0.2%</div>
<div class="header"><div style="font-weight:900">🦁 LOBO V41 TESTNET - SDE CAPITAL</div><div style="font-size:9px;color:#aaa">PRECIO REAL - BALANCE FICTICIO TESTNET - SIMPLE Y HUMILDE</div></div>
<div class="card" style="display:flex;justify-content:space-around;text-align:center;border:1px solid #f7931a">
<div><div style="font-size:8px;color:#888">BALANCE TESTNET</div><div style="font-size:16px;font-weight:900" id="bal">{{bal}} USDT</div></div>
<div><div style="font-size:8px;color:#888">GANANCIA BRUTA</div><div class="verde" id="bruta">+$0.00</div></div>
<div><div style="font-size:8px;color:#888">COMISIONES</div><div class="rojo" id="com">-$0.00</div></div>
<div><div style="font-size:8px;color:#888">NETA REAL</div><div style="font-size:18px;font-weight:900" class="verde" id="neta">+$0.00</div></div>
</div>
<div class="card" style="padding:0;height:400px"><div id="tv" style="height:400px"></div></div>
<div class="card"><table><tr><th>Hora</th><th>Par</th><th>Tipo</th><th>Bruta</th><th>Comision</th><th>Neta</th></tr><tbody id="trades"></tbody></table></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
new TradingView.widget({"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","container_id":"tv"});
function cargar(){fetch('/api/data').then(r=>r.json()).then(d=>{document.getElementById('bal').innerText=d.balance+' USDT';document.getElementById('bruta').innerText='+$'+d.bruta;document.getElementById('com').innerText='-$'+d.comision;document.getElementById('neta').innerText='+$'+d.neta;let h='';d.trades.forEach(t=>{h+=`<tr><td>${t.hora}</td><td>${t.par}</td><td>${t.tipo}</td><td class="verde">+${t.bruta}</td><td class="rojo">-${t.com}</td><td class="verde">${t.neta}</td></tr>`});document.getElementById('trades').innerHTML=h;});}
setInterval(cargar,5000);cargar();
</script>
</body></html>
"""

@app.route('/')
def home():
    bal = estado["balance"]
    if client:
        try:
            b = client.get_asset_balance(asset='USDT')
            bal = float(b['free'])
            estado["balance"] = bal
        except: pass
    return render_template_string(HTML, bal=round(bal,2), modo=MODO)

@app.route('/api/data')
def data():
    if client:
        try:
            b = client.get_asset_balance(asset='USDT')
            estado["balance"] = float(b['free'])
        except: pass
    return jsonify({
        "balance": round(estado["balance"],2),
        "bruta": round(estado["bruta"],2),
        "comision": round(estado["comision"],2),
        "neta": round(estado["bruta"]-estado["comision"],2),
        "trades": estado["trades"][-20:]
    })

@app.route('/health')
def health(): return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
