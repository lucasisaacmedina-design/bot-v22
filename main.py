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

def get_precio_testnet(symbol):
    try:
        r=requests.get(f"{BINANCE_URL}/api/v3/ticker/price?symbol={symbol}", timeout=5).json()
        return float(r["price"])
    except:
        try: # fallback binance real
            r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()
            return float(r["price"])
        except: return None

def binance_comprar_forzado(symbol, usdt=30):
    # ESTA COMPRA NO FALLA POR RSI, COMPRA SI O SI
    try:
        if not BINANCE_KEY: return {"msg": "FALTA API KEY en Render"}
        params={"symbol":symbol,"side":"BUY","type":"MARKET","quoteOrderQty":usdt,"timestamp":int(time.time()*1000)}
        headers={"X-MBX-APIKEY": BINANCE_KEY}
        url=f"{BINANCE_URL}/api/v3/order?{binance_firma(params)}"
        r=requests.post(url, headers=headers, timeout=15)
        return r.json()
    except Exception as e: return {"msg": f"ERROR {e}"}

def enviar_telegram(texto):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":texto}, timeout=10)
    except: pass

def actualizar(symbol, forzar_compra=False):
    precio=get_precio_testnet(symbol)
    if not precio: return
    d=estado_global[symbol]; d["precio"]=precio; d["historial"].append(precio)
    if len(d["historial"])>50: d["historial"].pop(0)
    d["ema"]=sum(d["historial"][-20:])/len(d["historial"][-20:]);
    if d["en_posicion"]: d["pnl"]=((precio-d["entry"])/d["entry"])*100

    # COMPRA FORZADA por /comprar
    if forzar_compra or (not d["en_posicion"] and 45 < d["rsi"] < 65):
        res=binance_comprar_forzado(symbol, 30)
        d["entry"]=precio; d["en_posicion"]=True; d["pnl"]=0.0
        enviar_telegram(f"🟢 COMPRA FORZADA {symbol}\n💵 ${precio:.2f} | $30 USDT\nResp: {str(res)[:300]}")
        print(f"COMPRA {symbol} {res}")

    # VENTA TP +0.6% SL -0.6%
    if d["en_posicion"] and (d["pnl"]>=0.6 or d["pnl"]<=-0.6):
        ganancia=30*0.006 if d["pnl"]>=0.6 else 30*-0.006
        estado_global["cuenta"]["balance"]+=ganancia; estado_global["cuenta"]["ganancia_dia"]+=ganancia
        estado_global["cuenta"]["operaciones"].append({"hora":datetime.datetime.now().strftime("%H:%M"),"symbol":symbol,"pnl":d["pnl"],"ganancia":ganancia})
        enviar_telegram(f"{'✅ TP +0.6% VENDIDO' if ganancia>0 else '❌ SL -0.6% VENDIDO'} {symbol}\n💰 ${ganancia:+.2f} | Bal ${estado_global['cuenta']['balance']:.2f}")
        d["en_posicion"]=False; d["entry"]=precio; d["pnl"]=0.0

HTML_TEMPLATE="""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOBO V28.1</title><style>body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:10px}.card{background:#1a1a1a;border-radius:12px;padding:12px;border:1px solid #333;max-width:900px;margin:10px auto}</style><script src="https://s3.tradingview.com/tv.js"></script></head><body><div class="card"><h3>🐺 LOBO V28.1 FIX - AUTO TESTNET</h3><div>🏦 Bal ${{ "%.2f"|format(cuenta.balance) }} | Neta ${{ "%+.2f"|format(cuenta.ganancia_dia) }} | Ops {{ cuenta.operaciones|length }}</div><div>BTC ${{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% {{ "EN POS" if btc.en_posicion else "ESPERANDO" }} | BNB ${{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}% {{ "EN POS" if bnb.en_posicion else "ESPERANDO" }}</div><div style="color:#00ff88;margin-top:6px;">✅ Fix: Precio via Testnet + /comprar forzado</div></div><div class="card"><div id="tv_btc" style="height:350px;"></div></div><div class="card"><div id="tv_bnb" style="height:350px;"></div></div><script>new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","style":"1","locale":"es","container_id":"tv_btc"});new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","style":"1","locale":"es","container_id":"tv_bnb"});</script></body></html>"""

app=Flask(__name__)
@app.route("/")
def home(): return render_template_string(HTML_TEMPLATE, btc=estado_global["BTCUSDT"], bnb=estado_global["BNBUSDT"], cuenta=estado_global["cuenta"])

def loop():
    last=0
    while True:
        try:
            if estado_global["cuenta"]["fecha"]!=datetime.date.today().isoformat(): estado_global["cuenta"]["ganancia_dia"]=0.0; estado_global["cuenta"]["operaciones"]=[]; estado_global["cuenta"]["fecha"]=datetime.date.today().isoformat()
            for s in SYMBOLS_LIST: actualizar(s)
            r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last+1}&timeout=3", timeout=10).json()
            if r.get("ok"):
                for u in r["result"]:
                    last=u["update_id"]
                    if "message" not in u: continue
                    if str(u["message"]["chat"]["id"])!=str(CHAT_ID): continue
                    txt=u["message"].get("text","").lower()
                    print(f"CMD RECIBIDO: {txt}")
                    if "/comprar" in txt:
                        enviar_telegram("⏳ Forzando compra $30 BTC y $30 BNB en Testnet...")
                        for s in SYMBOLS_LIST: actualizar(s, forzar_compra=True); time.sleep(1)
                    if "/balance" in txt:
                        c=estado_global["cuenta"]; msg=f"🏦 V28.1 BALANCE\nBal ${c['balance']:.2f} | Neta ${c['ganancia_dia']:+.2f}\n"
                        for op in c['operaciones'][-10:]: msg+=f"{op['hora']} {op['symbol']} {op['pnl']:+.2f}% ${op['ganancia']:+.2f}\n"
                        if not c['operaciones']: msg+="Sin ops, listo para /comprar"
                        enviar_telegram(msg)
        except Exception as e: print(f"LOOP ERR {e}")
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
