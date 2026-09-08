import os, time, requests, threading, io, random, datetime, hmac, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
BINANCE_KEY = os.environ.get("BINANCE_TESTNET_API_KEY", "")
BINANCE_SECRET = os.environ.get("BINANCE_TESTNET_API_SECRET", "")
URL_BOT = "https://bot-v22.onrender.com"
SYMBOLS_LIST = ["BTCUSDT", "BNBUSDT"]
BINANCE_URL = "https://testnet.binance.vision"

def crear_historial(base, n=50):
    h=[base]
    for _ in range(n-1): h.append(h[-1]+random.uniform(-base*0.0005, base*0.0005))
    return h

estado_global = {
    "BTCUSDT": {"precio":78645,"entry":78645,"ema":78645,"rsi":54,"pnl":0.0,"historial":crear_historial(78645), "en_posicion": False},
    "BNBUSDT": {"precio":753.67,"entry":753.67,"ema":753.67,"rsi":55,"pnl":0.0,"historial":crear_historial(753.67), "en_posicion": False},
    "cuenta": {"balance":1000.0,"inicial":1000.0,"ganancia_dia":0.0,"operaciones":[],"fecha":datetime.date.today().isoformat()}
}

def binance_firma(params):
    query = "&".join([f"{k}={v}" for k,v in params.items()])
    sig = hmac.new(BINANCE_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    return query + f"&signature={sig}"

def binance_comprar(symbol, usdt=30):
    if not BINANCE_KEY: return None
    try:
        params={"symbol":symbol,"side":"BUY","type":"MARKET","quoteOrderQty":usdt,"timestamp":int(time.time()*1000)}
        headers={"X-MBX-APIKEY": BINANCE_KEY}
        r=requests.post(f"{BINANCE_URL}/api/v3/order?{binance_firma(params)}", headers=headers, timeout=10).json()
        return r
    except Exception as e: print(e); return None

def binance_vender(symbol, qty=None):
    if not BINANCE_KEY: return None
    try:
        # obtener balance real si no hay qty
        if not qty:
            params={"timestamp":int(time.time()*1000)}; headers={"X-MBX-APIKEY": BINANCE_KEY}
            bal=requests.get(f"{BINANCE_URL}/api/v3/account?{binance_firma(params)}", headers=headers, timeout=10).json()
            for b in bal.get("balances",[]):
                if b["asset"]==symbol.replace("USDT",""): qty=float(b["free"]); break
        params={"symbol":symbol,"side":"SELL","type":"MARKET","quantity":round(qty,6),"timestamp":int(time.time()*1000)}
        headers={"X-MBX-APIKEY": BINANCE_KEY}
        r=requests.post(f"{BINANCE_URL}/api/v3/order?{binance_firma(params)}", headers=headers, timeout=10).json()
        return r
    except Exception as e: print(e); return None

def enviar_foto(symbol, extra=""):
    try:
        d=estado_global[symbol]; fig, ax=plt.subplots(figsize=(6,2.6)); fig.patch.set_facecolor('black'); ax.set_facecolor('black')
        ax.plot(d["historial"], color='#00ff88', linewidth=1.8); ema=[sum(d["historial"][max(0,i-20):i+1])/len(d["historial"][max(0,i-20):i+1]) for i in range(len(d["historial"]))]
        ax.plot(ema, color='#ffaa00', linestyle='--', linewidth=1.1)
        ax.set_title(f'{symbol} {d["precio"]:.2f} | {d["pnl"]:+.2f}%', color='white', fontsize=8); ax.tick_params(colors='white', labelsize=6); ax.grid(True, alpha=0.08, color='white')
        buf=io.BytesIO(); plt.tight_layout(); plt.savefig(buf, format='png', facecolor='black', dpi=120); plt.close(fig); buf.seek(0)
        c=estado_global["cuenta"]; cap=f"📈 LOBO V28 AUTO TESTNET - {symbol}\n💵 ${d['precio']:.2f} | {d['pnl']:+.2f}% -> Obj ${d['entry']*1.006:.2f}\n🏦 Bal ${c['balance']:.2f} | Neta Hoy ${c['ganancia_dia']:+.2f}\n{extra}\n🔗 {URL_BOT}"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHAT_ID,"caption":cap}, files={"photo":buf}, timeout=15)
    except Exception as e: print(e)

def actualizar(symbol):
    try:
        precio=float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()["price"])
        d=estado_global[symbol]; d["precio"]=precio; d["historial"].append(precio)
        if len(d["historial"])>50: d["historial"].pop(0)
        d["ema"]=sum(d["historial"][-20:])/len(d["historial"][-20:]); d["pnl"]=((precio-d["entry"])/d["entry"])*100 if d["en_posicion"] else 0.0

        # ENTRADA AUTOMATICA si no estoy en posicion
        if not d["en_posicion"] and d["rsi"]>45 and d["rsi"]<65:
            res=binance_comprar(symbol, usdt=30)
            d["entry"]=precio; d["en_posicion"]=True; d["pnl"]=0.0
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":f"🟢 COMPRA AUTO TESTNET {symbol}\n💵 ${precio:.2f} con $30 USDT\nTx {str(res)[:100]}"}, timeout=10)
            enviar_foto(symbol, "🟢 COMPRA REALIZADA TESTNET")

        # SALIDA AUTOMATICA TP +0.6% o SL -0.6%
        if d["en_posicion"] and (d["pnl"]>=0.6 or d["pnl"]<=-0.6):
            ganancia=estado_global["cuenta"]["balance"]*0.006 if d["pnl"]>=0.6 else estado_global["cuenta"]["balance"]*-0.006
            binance_vender(symbol)
            estado_global["cuenta"]["balance"]+=ganancia; estado_global["cuenta"]["ganancia_dia"]+=ganancia
            estado_global["cuenta"]["operaciones"].append({"hora":datetime.datetime.now().strftime("%H:%M"),"symbol":symbol,"pnl":d["pnl"],"ganancia":ganancia,"precio":precio})
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":f"{'✅ TP +0.6% VENDIDO REAL' if ganancia>0 else '❌ SL -0.6% VENDIDO'} {symbol}\n💰 ${ganancia:+.2f} | Bal ${estado_global['cuenta']['balance']:.2f}"}, timeout=10)
            enviar_foto(symbol, f"{'✅ TP REAL' if ganancia>0 else '❌ SL REAL'}")
            d["en_posicion"]=False; d["entry"]=precio; d["pnl"]=0.0
    except Exception as e: print(f"Err {symbol} {e}")

HTML_TEMPLATE="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOBO V28 AUTO</title><style>body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:10px}.card{background:#1a1a1a;border-radius:12px;padding:12px;border:1px solid #333;max-width:800px;margin:10px auto}.pos{color:#00ff88}.neg{color:#ff4444}</style><script src="https://s3.tradingview.com/tv.js"></script></head><body><div class="card"><h3>🐺 LOBO V28 AUTO TESTNET REAL</h3><div>🏦 Bal ${{ "%.2f"|format(cuenta.balance) }} | Neta Hoy <span class="{{ 'pos' if cuenta.ganancia_dia>=0 else 'neg' }}">${{ "%+.2f"|format(cuenta.ganancia_dia) }}</span> | Ops {{ cuenta.operaciones|length }}</div><div>BTC {{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% {{ "EN POS" if btc.en_posicion else "ESPERANDO" }} | BNB {{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}% {{ "EN POS" if bnb.en_posicion else "ESPERANDO" }}</div></div><div class="card"><div id="tv_btc" style="height:350px;"></div></div><div class="card"><div id="tv_bnb" style="height:350px;"></div></div><script>new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","style":"1","locale":"es","studies":["EMA@tv-basicstudies","RSI@tv-basicstudies"],"container_id":"tv_btc"});new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","style":"1","locale":"es","studies":["EMA@tv-basicstudies","RSI@tv-basicstudies"],"container_id":"tv_bnb"});</script></body></html>"""

app=Flask(__name__)
@app.route("/")
def home(): return render_template_string(HTML_TEMPLATE, btc=estado_global["BTCUSDT"], bnb=estado_global["BNBUSDT"], cuenta=estado_global["cuenta"])

def loop():
    last=0
    while True:
        if estado_global["cuenta"]["fecha"]!=datetime.date.today().isoformat(): estado_global["cuenta"]["ganancia_dia"]=0.0; estado_global["cuenta"]["operaciones"]=[]; estado_global["cuenta"]["fecha"]=datetime.date.today().isoformat()
        for s in SYMBOLS_LIST: actualizar(s)
        try:
            r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last+1}&timeout=2", timeout=10).json()
            if r.get("ok"):
                for u in r["result"]:
                    last=u["update_id"]
                    if str(u["message"]["chat"]["id"])!=str(CHAT_ID): continue
                    txt=u["message"].get("text","").lower()
                    if "/estado" in txt:
                        for s in SYMBOLS_LIST: enviar_foto(s); time.sleep(1)
                    if "/balance" in txt:
                        c=estado_global["cuenta"]; msg=f"🏦 LOBO V28 AUTO BALANCE\n💰 Bal ${c['balance']:.2f} | Neta ${c['ganancia_dia']:+.2f} ({len(c['operaciones'])} ops)\n";
                        for op in c['operaciones'][-15:]: msg+=f"{op['hora']} {op['symbol']} {op['pnl']:+.2f}% -> ${op['ganancia']:+.2f}\n"
                        if not c['operaciones']: msg+="Sin ops hoy - esperando señal RSI"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg}, timeout=10)
                    if "/comprar" in txt:
                        for s in SYMBOLS_LIST: actualizar(s) # fuerza compra
        except: pass
        time.sleep(6)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
