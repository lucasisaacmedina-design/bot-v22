import os, time, threading, requests
from flask import Flask, render_template_string
import ccxt
BOT=os.environ.get("TELEGRAM_TOKEN",""); CHAT=os.environ.get("TELEGRAM_CHAT_ID","")
E={"cap":15.0,"btc":0.000189,"buy":79146.0,"tr":1,"pr":79149.0}
app=Flask(__name__)
HTML="""<!DOCTYPE html><html><head><meta name=viewport content='width=device-width,initial-scale=1'><style>
body{margin:0;background:#0e0e12;color:#fff;font-family:Arial} .top{height:48px;background:#1a1a1f;display:flex;justify-content:space-between;align-items:center;padding:0 12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:10px} .card{background:#1c1c21;border-radius:12px;padding:12px} .t{color:#888;font-size:14px} .v{font-size:19px;font-weight:700} .red{color:#ff4d4d} .green{color:#2ecc71}
#tv{height:70vh}
</style></head><body>
<div class=top><b>🐺 LoboBot22 V22 PRO</b><span>BTC: ${{pr}}</span></div>
<div class=grid>
<div class=card><div class=t>Capital</div><div class=v>${{cap}}</div></div>
<div class=card><div class=t>BTC</div><div class=v>{{btc}}</div></div>
<div class=card><div class=t>Total</div><div class=v red>${{tot}}</div></div>
<div class=card><div class=t>Beneficio</div><div class=v green>${{be}} ({{pc}}%)</div></div>
</div>
<div id=tv></div>
<script src=https://s3.tradingview.com/tv.js></script>
<script>new TradingView.widget({autosize:true,symbol:"BINANCE:BTCUSDT",interval:"5",theme:"dark",style:"1",locale:"es",container_id:"tv"});</script>
</body></html>"""
@app.route("/")
def h():
 pr=E["pr"]
 try: pr=ccxt.binance().fetch_ticker('BTC/USDT')['last']; E["pr"]=pr
 except: pass
 tot=E["cap"]+E["btc"]*pr; be=tot-30
 return render_template_string(HTML,pr=f"{pr:,.0f}",cap=E["cap"],btc=E["btc"],tot=f"{tot:.2f}",be=f"{be:.2f}",pc=f"{(be/30*100):.2f}")
threading.Thread(target=lambda:[time.sleep(30)],daemon=True).start()
app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
