# LOBO V33.2 - VELAS TRADINGVIEW
from flask import Flask
import threading, time, random, os
from datetime import datetime
app=Flask(__name__)
USDT_INICIAL=85.27; BTC=0.001; PNL=55.73; PRECIO_COMPRA=152753; TRADES=267; PRECIO_ACTUAL=151270; ESTADO="COMPRADO"
HISTORIAL=["13:24:01 COMPRA $152753","13:23:37 VENTA +0.80% | +$1.20","13:09:06 VENTA +0.86% | +$1.15"]
def bot_loop():
    global PNL, PRECIO_COMPRA, TRADES, PRECIO_ACTUAL, ESTADO, HISTORIAL
    while True:
        try:
            PRECIO_ACTUAL*=(1+random.uniform(-0.003,0.003))
            if ESTADO=="COMPRADO":
                g=(PRECIO_ACTUAL-PRECIO_COMPRA)/PRECIO_COMPRA
                if g>=0.008: PNL+=1.2; TRADES+=1; HISTORIAL.insert(0,f"{datetime.now().strftime('%H:%M:%S')} VENTA +{g*100:.2f}%"); HISTORIAL=HISTORIAL[:6]; ESTADO="VENDIDO"
            else:
                if random.random()>0.7: PRECIO_COMPRA=PRECIO_ACTUAL; TRADES+=1; HISTORIAL.insert(0,f"{datetime.now().strftime('%H:%M:%S')} COMPRA ${PRECIO_ACTUAL:.0f}"); HISTORIAL=HISTORIAL[:6]; ESTADO="COMPRADO"
            time.sleep(3)
        except: time.sleep(5)
@app.route('/')
def home():
    g=(PRECIO_ACTUAL-PRECIO_COMPRA)/PRECIO_COMPRA*100 if ESTADO=="COMPRADO" else 0
    usdt=USDT_INICIAL+PNL+(PRECIO_ACTUAL-PRECIO_COMPRA)*0.001 if ESTADO=="COMPRADO" else USDT_INICIAL+PNL
    color="#00c853" if g>=0 else "#ff1744"; bg="#e8f5e9" if g>=0 else "#ffebee"
    barra=max(5,min(100,(g+3)/3.8*100)); badge="COMPRADO" if ESTADO=="COMPRADO" else "ESPERANDO"
    return f"""
<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="30">
<style>body{{font-family:-apple-system,sans-serif;background:#f5f7fb;margin:0;padding:10px}}
.card{{background:white;border-radius:16px;padding:16px;max-width:420px;margin:8px auto;box-shadow:0 2px 12px rgba(0,0,0,0.08)}}
.demo{{background:#fff3cd;color:#856404;padding:8px;border-radius:8px;text-align:center;font-size:12px;font-weight:bold;margin-bottom:10px}}
.big{{font-size:30px;font-weight:900}}.sub{{font-size:13px;color:#666}}.row{{display:flex;justify-content:space-between;margin:8px 0}}
.badge{{padding:4px 10px;border-radius:20px;font-weight:bold;font-size:12px}}.bar{{background:#eee;height:8px;border-radius:10px;overflow:hidden}}.fill{{height:100%}}
</style></head><body>
<div class="card">
<div style="text-align:center"><div style="font-size:12px;color:#666">PROYECTO FAMILIA LOBO</div><div style="font-weight:800">LOBO V33.2 - VELAS PRO</div></div>
<div class="demo">MODO DEMO - SIN DINERO REAL</div>
<div style="background:#f8f9ff;padding:12px;border-radius:12px;border:1px solid #e0e7ff">
<div class="sub">Balance Total</div><div class="big">${usdt:.2f} USDT</div>
<div class="row"><span class="sub">Inicial: $85.27</span><span style="color:#00c853;font-weight:bold">+${PNL:.2f}</span></div>
</div>
<!-- VELAS JAPONESAS TRADINGVIEW -->
<div style="margin:12px 0;border-radius:12px;overflow:hidden;border:1px solid #eee">
<div class="tradingview-widget-container">
<iframe src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_123&symbol=BINANCE:BTCUSDT&interval=1&hidesidetoolbar=1&symboledit=0&saveimage=0&toolbarbg=f1f3f6&studies=[]&theme=light&style=1&timezone=America/Argentina/Buenos_Aires&studies_overrides={{}}&overrides={{}}&enabled_features=[]&disabled_features=[]&locale=es&colorTheme=light&isTransparent=0&autosize=1" style="width:100%;height:260px;border:0"></iframe>
</div>
</div>
<div class="row"><span class="sub">Operacion</span><span class="badge" style="background:{bg};color:{color}">{badge}</span></div>
<div class="row"><span>BTC: 0.00100</span><span>${PRECIO_ACTUAL:.0f}</span></div>
<div class="row"><span class="sub">Flotante</span><span class="badge" style="background:{bg};color:{color}">{g:+.2f}%</span></div>
<div class="bar"><div class="fill" style="width:{barra:.0f}%;background:{color}"></div></div>
<div style="margin-top:12px"><div class="sub" style="font-weight:bold">Ultimos movimientos</div><div style="font-size:12px;color:#555;line-height:1.6">{"<br>".join(HISTORIAL)}</div></div>
<div style="text-align:center;font-size:11px;color:#999;margin-top:10px">Velas BTC/USDT en vivo • TradingView • Bot 24/7</div>
</div></body></html>
"""
threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
