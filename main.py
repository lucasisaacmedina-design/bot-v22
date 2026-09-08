import os, time, threading, requests, math
from flask import Flask, render_template_string
import ccxt, datetime

BOT_TOKEN=os.environ.get("TELEGRAM_TOKEN","")
CHAT_ID=os.environ.get("TELEGRAM_CHAT_ID","")
DASHBOARD_URL = "https://bot-v22.onrender.com"
INITIAL_CAP = 15.0

# --- ESTRATEGIA V23 RENTABLE ---
TP_PCT = 0.015 # +1.5%
SL_PCT = 0.015 # -1.5%
BUY_DROP = 0.01 # -1.0% para comprar
TRAIL_START = 0.008 # +0.8% activa trailing
TRAIL_SL = 0.003 # -0.3% desde maximo

ESTADO={
 "cap":0.0,
 "btc":0.000189,
 "buy":79014.0,
 "trades":1,
 "max":79456.0,
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
   data={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"},timeout=10)
 except: pass

def get_price():
 try:
  p=ccxt.binance().fetch_ticker('BTC/USDT')['last']
  ESTADO["price"]=p
  if p>ESTADO["max"]: ESTADO["max"]=p
  return p
 except: return ESTADO["price"]

def get_indicators():
 try:
  ex=ccxt.binance()
  ohlcv=ex.fetch_ohlcv('BTC/USDT','1h',limit=210)
  closes=[c[4] for c in ohlcv]
  # EMA 200
  ema=closes[0]
  k=2/(200+1)
  for price in closes[1:]: ema=price*k+ema*(1-k)
  # RSI 14
  gains=losses=0
  for i in range(1,15):
   d=closes[-i]-closes[-i-1]
   if d>0: gains+=d
   else: losses+=-d
  rs=gains/(losses+1e-9)
  rsi=100-(100/(1+rs))
  return ema, rsi
 except:
  return None, None

def get_next_action(p):
 if ESTADO["btc"] > 0.000001:
  pnl = (p-ESTADO["buy"])/ESTADO["buy"]
  tp_price = ESTADO["buy"]*(1+TP_PCT)
  sl_price = ESTADO["buy"]*(1-SL_PCT)
  if pnl >= TRAIL_START:
   return f"💰 TRAILING +{pnl*100:.2f}% | TP ${tp_price:.0f} | SL ${sl_price:.0f} | Max ${ESTADO['max']:.0f}"
  else:
   return f"💰 Vendiendo: +{pnl*100:.2f}% -> Objetivo +1.5% (${tp_price:.0f}) | SL -1.5%"
 else:
  ema, rsi = get_indicators()
  if ema and rsi:
   return f"🎯 Cazando -1.0% | EMA200 ${ema:.0f} | RSI {rsi:.0f} | Actual ${p:.0f}"
  return f"🎯 Comprando: Esperando caída -1.0% (actual {p:.0f})"

# --- LOOP DE TRADING RENTABLE (PAPEL) ---
def trading_loop():
 while True:
  try:
   p=get_price()
   ema, rsi = get_indicators()
   # Lógica de VENTA rentable
   if ESTADO["btc"] > 0:
    if p >= ESTADO["buy"]*(1+TP_PCT) or p <= ESTADO["buy"]*(1-SL_PCT):
     # VENTA
     ESTADO["cap"] = ESTADO["btc"]*p*0.999 # con comisión 0.1%
     profit = p-ESTADO["buy"]
     ESTADO["btc"]=0
     ESTADO["history"].append({"time":datetime.datetime.now().strftime("%H:%M"),"tipo":"VENTA","price":int(p),"btc":ESTADO["cap"]/p,"pnl":f"{profit/p*100:.2f}%"})
     ESTADO["trades"]+=1
     if profit>0: ESTADO["win_trades"]+=1
     enviar(f"✅ *VENTA V23* @ ${p:.0f}\nP&L {profit/ESTADO['buy']*100:.2f}%\nTotal ${ESTADO['cap']:.2f}")
     ESTADO["max"]=p
    # Trailing
    elif p>ESTADO["max"]: ESTADO["max"]=p
    elif ESTADO["max"]>0 and p < ESTADO["max"]*(1-TRAIL_SL) and (p-ESTADO["buy"])/ESTADO["buy"]>=TRAIL_START:
     ESTADO["cap"]=ESTADO["btc"]*p*0.999
     ESTADO["btc"]=0
     enviar(f"✅ *TRAILING VENTA* @ ${p:.0f} (max ${ESTADO['max']:.0f})")
   # Lógica de COMPRA rentable
   else:
    if ema and rsi:
     cond_precio = p < ESTADO["max"]* (1-BUY_DROP)
     cond_tendencia = p > ema # solo en tendencia alcista
     cond_rsi = rsi < 45
     if cond_precio and cond_tendencia and cond_rsi:
      btc_amount = (ESTADO["cap"]*0.999)/p if ESTADO["cap"]>0 else INITIAL_CAP*0.999/p
      ESTADO["btc"]=btc_amount
      ESTADO["buy"]=p
      ESTADO["cap"]=0
      ESTADO["max"]=p
      ESTADO["history"].append({"time":datetime.datetime.now().strftime("%H:%M"),"tipo":"COMPRA","price":int(p),"btc":btc_amount,"pnl":"--"})
      enviar(f"🐺 *COMPRA V23 RENTABLE* @ ${p:.0f}\nEMA ${ema:.0f} RSI {rsi:.0f}\n₿ {btc_amount}")

  except Exception as e: print(e)
  time.sleep(60)

def telegram_loop():
 offset=0
 enviar(f"🐺 *LoboBot V23 RENTABLE CONECTADO* ✅\nEstrategia +1.5%/-1.5% + EMA+RSI\n📊 {DASHBOARD_URL}")
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
     ben=total-INITIAL_CAP; perc=ben/INITIAL_CAP*100
     win_rate = int(ESTADO["win_trades"]/ESTADO["trades"]*100) if ESTADO["trades"]>0 else 0
     msg = f"💰 *ESTADO LOBO V23 RENTABLE*\n\n💵 Capital: ${ESTADO['cap']:.2f}\n₿ BTC: {ESTADO['btc']}\n📈 BTC: ${p:,.0f}\n💼 Total: ${total:.2f}\n📊 P&L: ${ben:.2f} ({perc:.2f}%)\n🔁 Trades: {ESTADO['trades']} | Win: {win_rate}%\n\n{get_next_action(p)}\n\nTP +1.5% | SL -1.5% | EMA200 + RSI\n🔗 {DASHBOARD_URL}"
     enviar(msg)
  except: time.sleep(5)

app=Flask(__name__)
HTML="""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>LoboBot V23 RENTABLE</title><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0e0e12;color:#fff;font-family:system-ui}.top{height:48px;background:#1a1a1f;display:flex;justify-content:space-between;align-items:center;padding:0 14px;border-bottom:1px solid #222}.top b{font-size:15px}.top a{color:#38bdf8;font-size:12px;text-decoration:none;border:1px solid #38bdf8;padding:4px 8px;border-radius:6px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px}.card{background:#1c1c21;border-radius:12px;padding:10px 12px}.card.t{color:#888;font-size:12px;text-transform:uppercase}.card.v{font-size:17px;font-weight:700;margin-top:2px}.red{color:#ff4d4d}.green{color:#2ecc71}.stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:0 10px 10px}.stat{background:#13131a;border:1px solid #222;border-radius:10px;padding:8px 12px;font-size:12px;color:#aaa}.stat b{color:#fff}.chart{margin:0 10px;background:#13131a;border-radius:12px;overflow:hidden;border:1px solid #222}#tv{height:50vh}.history{margin:10px;background:#1c1c21;border-radius:12px;overflow:hidden}.h-head{padding:10px 12px;font-size:12px;font-weight:700;border-bottom:1px solid #222;display:flex;justify-content:space-between}.row{display:flex;justify-content:space-between;padding:8px 12px;font-size:12px;border-bottom:1px solid #1a1a1a}.buy{color:#2ecc71}.sell{color:#ff4d4d}.foot{padding:12px;text-align:center;color:#444;font-size:10px}</style></head><body><div class="top"><b>🐺 LoboBot V23 RENTABLE</b><a href="{{dash_url}}" target="_blank">🔗 COMPARTIR</a><span style="font-size:13px">BTC: ${{price}}</span></div><div class="grid"><div class="card"><div class="t">Capital</div><div class="v">${{cap}}</div></div><div class="card"><div class="t">BTC</div><div class="v">{{btc}}</div></div><div class="card"><div class="t">Total</div><div class="v {{cls}}">${{total}}</div></div><div class="card"><div class="t">Beneficio</div><div class="v {{cls}}">{{sign}}${{abs_b}} ({{perc}}%)</div></div></div><div class="stats"><div class="stat">📈 Win Rate <b style="color:#2ecc71">{{win_rate}}% ({{win}}/{{trades}})</b></div><div class="stat">🎯 Próxima <b>{{next_action}}</b></div></div><div class="chart"><div id="tv"></div></div><script src="https://s3.tradingview.com/tv.js"></script><script>new TradingView.widget({autosize:true,symbol:"BINANCE:BTCUSDT",interval:"5",theme:"dark",style:"1",locale:"es",toolbar_bg:"#13131a",hide_side_toolbar:true,backgroundColor:"#13131a",container_id:"tv"});</script><div class="history"><div class="h-head"><span>📜 ÚLTIMOS TRADES</span><span style="color:#555">V23 Rentable TP1.5/SL1.5</span></div>{% for h in history %}<div class="row"><span>{{h.time}} <b class="{{'buy' if h.tipo=='COMPRA' else 'sell'}}">{{h.tipo}}</b> @ ${{h.price}}</span><span>{{h.btc}} BTC <b>{{h.pnl}}</b></span></div>{% endfor %}<div class="row"><span style="color:#666">SL Activo</span><span style="color:#ff4d4d"><b>-1.5%</b> • Venta emergencia</span></div></div><div class="foot">Lobo V23 RENTABLE • {{dash_url}} • Telegram Activo ✅</div></body></html>"""

@app.route("/")
def dash():
 p=get_price(); total=ESTADO["cap"]+ESTADO["btc"]*p; ben=total-INITIAL_CAP; perc=ben/INITIAL_CAP*100
 win_rate=int(ESTADO["win_trades"]/ESTADO["trades"]*100) if ESTADO["trades"]>0 else 0
 return render_template_string(HTML, price=f"{p:,.0f}", cap=f"{ESTADO['cap']:.2f}", btc=ESTADO["btc"], total=f"{total:.2f}", abs_b=f"{abs(ben):.2f}", sign="+" if ben>=0 else "-", perc=f"{perc:.2f}", cls="green" if ben>=0 else "red", trades=ESTADO["trades"], win=ESTADO["win_trades"], win_rate=win_rate, next_action=get_next_action(p), history=ESTADO["history"][::-1][:5], dash_url=DASHBOARD_URL)

threading.Thread(target=telegram_loop,daemon=True).start()
threading.Thread(target=trading_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
