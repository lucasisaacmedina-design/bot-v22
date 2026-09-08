import os, time, threading, requests
from flask import Flask, render_template_string
import ccxt
BOT_TOKEN=os.environ.get("TELEGRAM_TOKEN",""); CHAT_ID=os.environ.get("TELEGRAM_CHAT_ID","")
EST={"cap":15.0,"btc":0.000189,"buy":79146.0,"trades":1,"max":79146.0,"price":79149.0}
def tg(m):
 try:
  if BOT_TOKEN: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":m},timeout=5)
 except: pass
app=Flask(__name__)
HTML="""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"><title>LoboBot22 V22 PRO</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{background:#0e0e12;color:white;font-family:system-ui,-apple-system,sans-serif}
.top{height:48px;background:#1a1a1f;display:flex;justify-content:space-between;align-items:center;padding:0 14px;border-bottom:1px solid #222}
.top b{font-size:16px}.top span{font-size:15px;color:#e0e0e0}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:10px;background:#0e0e12}
.card{background:#1c1c21;border-radius:12px;padding:12px 14px}
.card .t{font-size:15px;color:#a0a0b0}.card .v{font-size:19px;font-weight:700;margin-top:2px}
.red{color:#ff3b3b}.green{color:#2ecc71}
.chart{margin:0 10px;background:#13131a;border-radius:12px;overflow:hidden;border:1px solid #222}
#tv{height:62vh}
.foot{padding:12px;text-align:center;color:#555;font-size:11px}
</style></head><body>
<div class="top"><b>🐺 LoboBot22 V22 PRO</b><span>BTC: ${{price}}</span></div>
<div class="grid">
<div class="card"><div class="t">Capital</div><div class="v">${{cap}}</div></div>
<div class="card"><div class="t">BTC</div><div class="v">{{btc}}</div></div>
<div class="card"><div class="t">Total</div><div class="v red">${{total}}</div></div>
<div class="card"><div class="t">Beneficio</div><div class="v green">${{ben}} ({{perc}}%)</div></div>
</div>
<div class="chart"><div id="tv"></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
new TradingView.widget({
"autosize":true,"symbol":"BINANCE:BTCUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires",
"theme":"dark","style":"1","locale":"es","toolbar_bg":"#13131a","enable_publishing":false,
"hide_top_toolbar":false,"hide_side_toolbar":true,"backgroundColor":"#13131a","container_id":"tv"
});
</script></div>
<div class="foot">Intercambios Lobo ({{trades}}) • Compra ${{buy}} • SL -3.0% • /estado en Telegram</div>
</body></html>
"""
@app.route("/")
def dash():
 p=EST["price"]
 try: p=ccxt.binance().fetch_ticker('BTC/USDT')['last']; EST["price"]=p
 except: pass
 total=EST["cap"]+EST["btc"]*p; ben=total-30.0; perc=(ben/30)*100
 return render_template_string(HTML, price=f"{p:,.2f}".replace(",","."), cap=EST["cap"], btc=EST["btc"],
  total=f"{total:.2f}", ben=f"{ben:.1f}", perc=f"{perc:.2f}", trades=EST["trades"], buy=round(EST["buy"],2))
def loop():
 tg("🐺 V25 MOBILE PRO ONLINE")
 while True: time.sleep(30)
threading.Thread(target=loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
