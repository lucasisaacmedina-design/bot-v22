import os, time, requests
from flask import Flask
import threading

SYMBOL = "BTCUSDT"
CAPITAL_INICIAL = 105.0
TP = 0.006
SL = 0.006

app = Flask(__name__)
estado = {
    "capital": 100.0,
    "btc": 0.0,
    "total": 100.0,
    "beneficio": 0.0,
    "beneficio_pct": 0.0,
    "victorias": 0,
    "trades": 0,
    "entry": 0.0,
    "precio": 78490.0
}

def get_price():
    try:
        url = "https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT"
        p = float(requests.get(url, timeout=10).json()["price"])
        estado["precio"] = p
        return p
    except:
        return estado["precio"]

@app.route('/')
def dashboard():
    precio = get_price()
    win_rate = (estado["victorias"]/estado["trades"]*100) if estado["trades"] else 0
    
    if estado["btc"] > 0 and estado["entry"] > 0:
        vendiendo_pct = ((precio - estado["entry"]) / estado["entry"] * 100)
        objetivo = estado["entry"] * 1.006
        stop = estado["entry"] * 0.994
        texto_vendiendo = f"Vendiendo: {vendiendo_pct:+.2f}%<br>Objetivo: ${objetivo:.0f} (+0.6%)<br>SL: ${stop:.0f} (-0.6%)"
    else:
        texto_vendiendo = f"Esperando entrada...<br>Objetivo +0.6% | SL -0,6%<br>RSI < 42"

    total_color = "red" if estado["total"] < CAPITAL_INICIAL else "green"
    benef_color = "red" if estado["beneficio"] < 0 else "green"

    return f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Lobo Scalping</title>
    <style>
    body{{background:#0e0e0e;color:white;font-family:Arial;margin:0;padding:8px}}
    .grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px}}
    .card{{background:#1c1c1c;border-radius:12px;padding:12px}}
    .card span{{color:#aaa;font-size:13px}} .card b{{font-size:18px;display:block;margin-top:4px}}
    .red{{color:#ff5555}} .green{{color:#00ff88}}
    .timebar{{display:flex;gap:8px;padding:8px;background:#1c1c1c;border-radius:10px;margin-bottom:8px}}
    .timebar div{{padding:6px 10px;border-radius:8px;background:#2a2a2a;font-size:13px}} .active{{background:#3a3a3a !important}}
    .chartbox{{background:#1c1c1c;border-radius:12px;height:750px;overflow:hidden}}
    #tv{{height:750px}}
    </style></head><body>
    <div class="grid">
      <div class="card"><span>Capital</span><b>${estado['capital']:.2f}</b></div>
      <div class="card"><span>BTC</span><b>{estado['btc']:.6f}</b></div>
      <div class="card"><span>Total</span><b class="{total_color}">${estado['total']:.2f}</b></div>
      <div class="card"><span>Beneficio</span><b class="{benef_color}">${estado['beneficio']:.2f} ({estado['beneficio_pct']:.2f}%)</b></div>
    </div>
    <div class="grid">
      <div class="card"><span>📈 Porcentaje de victorias: <b class="green">{win_rate:.0f}% ({estado['victorias']}/{estado['trades']})</b></span></div>
      <div class="card"><span>🎯 Próxima 💰<br><b>{texto_vendiendo}</b></span></div>
    </div>
    <div class="timebar"><div>1m</div><div>30m</div><div>1h</div><div class="active">5m</div><div>▼</div><div style="margin-left:auto">SCALPING 0.6% $100+$5</div></div>
    
    <div class="chartbox">
      <div id="tv"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "BINANCE:BTCUSDT",
        "interval": "5",
        "timezone": "America/Argentina/Buenos_Aires",
        "theme": "dark",
        "style": "1",
        "locale": "es",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "container_id": "tv",
        "height": 750,
        "width": "100%"
      }});
      </script>
    </div>

    <div class="card" style="margin-top:8px"><b>📜 ÚLTIMOS TRADES - V24 SCALPING 0.6%</b><br>
    <span style="font-size:12px">Entrada: ${estado['entry']:.2f} | Actual: ${precio:.2f} | TP: +0.6% | SL: -0.6%</span></div>
    <div style="text-align:center;color:#555;font-size:11px;margin-top:10px">Lobo V24 SCALPING • Gráfico Grande ✅</div>
    <meta http-equiv="refresh" content="60">
    </body></html>
    """

def loop_scalping():
    while True:
        try:
            precio = get_price()
            if estado["btc"] > 0:
                if precio >= estado["entry"]*1.006 or precio <= estado["entry"]*0.994:
                    estado["capital"] = estado["btc"] * precio
                    estado["total"] = estado["capital"] + 5.0
                    estado["beneficio"] = estado["total"] - CAPITAL_INICIAL
                    estado["beneficio_pct"] = estado["beneficio"]/CAPITAL_INICIAL*100
                    estado["btc"] = 0
                    estado["trades"] += 1
                    if estado["beneficio"] > 0: estado["victorias"] += 1
            time.sleep(30)
        except: time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=loop_scalping, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
