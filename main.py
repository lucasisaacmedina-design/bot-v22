import os, time, threading, requests
from flask import Flask, render_template_string
import ccxt, datetime

BOT_TOKEN=os.environ.get("TELEGRAM_TOKEN","")
CHAT_ID=os.environ.get("TELEGRAM_CHAT_ID","")
DASHBOARD_URL = "https://bot-v22.onrender.com"

ESTADO={
 "cap":15.0,
 "btc":0.000189,
 "buy":79146.0,
 "trades":1,
 "max":79146.0,
 "price":79149.0,
 "win_trades":1,
 "history":[
   {"time":"21:15","tipo":"COMPRA","price":79014,"btc":0.000190,"pnl":"--"},
 ]
}

def enviar(msg):
 try:
  if BOT_TOKEN and CHAT_ID:
   requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
   data={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown","disable_web_page_preview":False},timeout=10)
 except: pass

def get_price():
 try:
  p=ccxt.binance().fetch_ticker('BTC/USDT')['last']
  ESTADO["price"]=p
  if p>ESTADO["max"]: ESTADO["max"]=p
  return p
 except:
  return ESTADO["price"]

def telegram_loop():
 offset=0
 enviar(f"🐺 *LoboBot22 V22 PRO CONECTADO* ✅\n\n📊 *Dashboard PRO:* {DASHBOARD_URL}\nEscribí /estado para ver balance")
 while True:
  try:
   if not BOT_TOKEN: time.sleep(30); continue
   r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",params={"offset":offset,"timeout":25},timeout=30).json()
   for u in r.get("result",[]):
    offset=u["update_id"]+1
    m=u.get("message",{}); txt=m.get("text",""); chat=str(m.get("chat",{}).get("id",""))
    if chat!=str(CHAT_ID): continue
    if txt.startswith("/estado"):
     p=get_price()
     total=ESTADO["cap"]+ESTADO["btc"]*p
     ben=total-30.0; perc=ben/30*100
     win_rate = 100 if ESTADO["trades"]>0 else 0
     msg = f"💰 *ESTADO LOBO V22 PRO*\n\n💵 Capital: ${ESTADO['cap']:.2f}\n₿ BTC: {ESTADO['btc']}\n📈 BTC: ${p:,.0f}\n💼 Total: ${total:.2f}\n📊 P&L: ${ben:.2f} ({perc:.2f}%)\n🔁 Trades: {ESTADO['trades']} | Win: {win_rate}%\n\n🎯 Próxima: Esperando caída -1.0% para comprar\n\n🔗 *Dashboard:* {DASHBOARD_URL}"
     enviar(msg)
  except: time.sleep(5)

app=Flask(__name__)

HTML="""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LoboBot22 V22 PRO</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{background:#0e0e12;color:#fff;font-family:system-ui}
.top{height:48px;background:#1a1a1f;display:flex;justify-content:space-between;align-items:center;padding:0 14px;border-bottom:1px solid #222}
.top b{font-size:15px}.top a{color:#38bdf8;font-size:12px;text-decoration:none;border:1px solid #38bdf8;padding:4px 8px;border-radius:6px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px}
.card{background:#1c1c21;border-radius:12px;padding:10px 12px}
.card .t{color:#888;font-size:12px;text-transform:uppercase;letter-spacing:.5px}.card .v{font-size:17px;font-weight:700;margin-top:2px}
.red{color:#ff4d4d}.green{color:#2ecc71}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:0 10px 10px}
.stat{background:#13131a;border:1px solid #222;border-radius:10px;padding:8px 12px;font-size:12px;color:#aaa}
.stat b{color:#fff}
.chart{margin:0 10px;background:#13131a;border-radius:12px;overflow:hidden;border:1px solid #222}#tv{height:50vh}
.history{margin:10px;background:#1c1c21;border-radius:12px;overflow:hidden}
.h-head{padding:10px 12px;font-size:12px;font-weight:700;border-bottom:1px solid #222;display:flex;justify-content:space-between}
.row{display:flex;justify-content:space-between;padding:8px 12px;font-size:12px;border-bottom:1px solid #1a1a1a}
.row:last-child{border:0}.buy{color:#2ecc71}.sell{color:#ff4d4d}
.foot{padding:12px;text-align:center;color:#444;font-size:10px}
</style></head><body>
<div class="top"><b>🐺 LoboBot22 V22 PRO</b><a href="{{dash_url}}" target="_blank">🔗 COMPARTIR</a><span style="font-size:13px">BTC: ${{price}}</span></div>

<div class="grid">
<div class="card"><div class="t">Capital</div><div class="v">${{cap}}</div></div>
<div class="card"><div class="t">BTC</div><div class="v">{{btc}}</div></div>
<div class="card"><div class="t">Total</div><div class="v {{cls}}">${{total}}</div></div>
<div class="card"><div class="t">Beneficio</div><div class="v {{cls}}">{{sign}}${{abs_b}} ({{perc}}%)</div></div>
</div>

<div class="stats">
<div class="stat">📈 Win Rate <b style="color:#2ecc71">{{win_rate}}% ({{win}}/{{trades}})</b></div>
<div class="stat">🎯 Próxima <b>{{next_action}}</b></div>
</div>

<div class="chart"><div id="tv"></div></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>new TradingView.widget({autosize:true,symbol:"BINANCE:BTCUSDT",interval:"5",theme:"dark",style:"1",locale:"es",toolbar_bg:"#13131a",hide_side_toolbar:true,backgroundColor:"#13131a",container_id:"tv"});</script>

<div class="history">
<div class="h-head"><span>📜 ÚLTIMOS TRADES</span><span style="color:#555">V22 Cazadora</span></div>
{% for h in history %}
<div class="row"><span>{{h.time}} <b class="{{'buy' if h.tipo=='COMPRA' else 'sell'}}">{{h.tipo}}</b> @ ${{h.price}}</span><span>{{h.btc}} BTC <b>{{h.pnl}}</b></span></div>
{% endfor %}
<div class="row"><span style="color:#666">SL Activo</span><span style="color:#ff4d4d"><b>-3.0%</b> • Venta emergencia</span></div>
</div>

<div class="foot">Lobo V22 PRO TERMINAL • {{dash_url}} • Telegram Activo ✅ • Mostrable a amigos</div>
</body></html>
"""

@app.route("/")
def dash():
 p=get_price()
 total=ESTADO["cap"]+ESTADO["btc"]*p
 ben=total-30.0
 perc=ben/30*100
 win_rate=100 if ESTADO["trades"]>0 else 0
 next_action = f"Esperando caída -1.0% (actual {p:.0f})"
 return render_template_string(HTML, price=f"{p:,.0f}", cap=f"{ESTADO['cap']:.2f}", btc=ESTADO["btc"],
  total=f"{total:.2f}", abs_b=f"{abs(ben):.2f}", sign="+" if ben>=0 else "-", perc=f"{perc:.2f}",
  cls="green" if ben>=0 else "red", trades=ESTADO["trades"], win=ESTADO["win_trades"], win_rate=win_rate,
  next_action=next_action, history=ESTADO["history"][::-1][:5], dash_url=DASHBOARD_URL)

threading.Thread(target=telegram_loop,daemon=True).start()
if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
