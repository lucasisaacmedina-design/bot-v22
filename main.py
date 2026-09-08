import os, time, requests, threading, io, random, datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
URL_BOT = "https://bot-v22.onrender.com"
SYMBOLS_LIST = ["BTCUSDT", "BNBUSDT"]

def crear_historial(base, n=50):
    h = [base]
    for _ in range(n-1):
        h.append(h[-1] + random.uniform(-base*0.0005, base*0.0005))
    return h

estado_global = {
    "BTCUSDT": {"precio": 78645, "entry": 78645, "ema": 78645, "rsi": 54, "pnl": 0.0, "historial": crear_historial(78645)},
    "BNBUSDT": {"precio": 753.67, "entry": 753.67, "ema": 753.67, "rsi": 55, "pnl": 0.0, "historial": crear_historial(753.67)},
    "cuenta": {"balance": 1000.0, "inicial": 1000.0, "ganancia_dia": 0.0, "operaciones": [], "fecha": datetime.date.today().isoformat()}
}

def enviar_foto(symbol):
    try:
        d = estado_global[symbol]
        fig, ax = plt.subplots(figsize=(6, 2.6))
        fig.patch.set_facecolor('black'); ax.set_facecolor('black')
        ax.plot(d["historial"], color='#00ff88', linewidth=1.8)
        ema = [sum(d["historial"][max(0,i-20):i+1])/len(d["historial"][max(0,i-20):i+1]) for i in range(len(d["historial"]))]
        ax.plot(ema, color='#ffaa00', linestyle='--', linewidth=1.1)
        ax.set_title(f'{symbol} {d["precio"]:.2f} | EMA {d["ema"]:.0f} | {d["pnl"]:+.2f}%', color='white', fontsize=8)
        ax.tick_params(colors='white', labelsize=6); ax.grid(True, alpha=0.08, color='white')
        buf = io.BytesIO(); plt.tight_layout(); plt.savefig(buf, format='png', facecolor='black', dpi=120); plt.close(fig); buf.seek(0)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        cuenta = estado_global["cuenta"]
        caption = f"📈 LOBO V27 - {symbol}\n💵 ${d['precio']:.2f} | EMA ${d['ema']:.0f} | RSI {d['rsi']}\n💰 {d['pnl']:+.2f}% -> Obj ${d['entry']*1.006:.2f}\n🏦 Balance ${cuenta['balance']:.2f} | Neta Hoy +${cuenta['ganancia_dia']:.2f}\n🔗 {URL_BOT}"
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": buf}, timeout=15)
    except Exception as e: print(e)

def actualizar(symbol):
    try:
        precio = float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()["price"])
        d = estado_global[symbol]
        d["precio"]=precio; d["historial"].append(precio)
        if len(d["historial"])>50: d["historial"].pop(0)
        d["ema"]=sum(d["historial"][-20:])/len(d["historial"][-20:])
        d["pnl"]=((precio - d["entry"])/d["entry"])*100

        if d["pnl"] >= 0.6 or d["pnl"] <= -0.6:
            # REGISTRO DE GANANCIA
            ganancia = (estado_global["cuenta"]["balance"] * 0.006) if d["pnl"]>=0.6 else (estado_global["cuenta"]["balance"] * -0.006)
            estado_global["cuenta"]["balance"] += ganancia
            estado_global["cuenta"]["ganancia_dia"] += ganancia
            op = {"hora": datetime.datetime.now().strftime("%H:%M"), "symbol": symbol, "pnl": d["pnl"], "ganancia": ganancia, "precio": precio}
            estado_global["cuenta"]["operaciones"].append(op)
            # Avisar en Telegram
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            txt = f"{'✅ TP +0.6%' if ganancia>0 else '❌ SL -0.6%'} {symbol}\n💰 Ganancia ${ganancia:+.2f}\n🏦 Balance ${estado_global['cuenta']['balance']:.2f} | Neta Hoy ${estado_global['cuenta']['ganancia_dia']:+.2f}\nUsa /balance para ver todo"
            requests.post(url, data={"chat_id": CHAT_ID, "text": txt}, timeout=10)
            d["entry"]=precio; d["pnl"]=0.0
    except Exception as e: print(e)

HTML_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOBO V27</title><style>
body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0;padding:10px}
.card{background:#1a1a1a;border-radius:12px;padding:12px;border:1px solid #333;max-width:800px;margin:10px auto}
.obj{color:#ffaa00}.pos{color:#00ff88}.neg{color:#ff4444}
</style><script src="https://s3.tradingview.com/tv.js"></script></head><body>
<div class="card">
<h3>🐺 LOBO V27 - REGISTRO Y NETA</h3>
<div>🏦 Balance ${{ "%.2f"|format(cuenta.balance) }} | Inicial ${{ "%.2f"|format(cuenta.inicial) }} | <span class="{{ 'pos' if cuenta.ganancia_dia>=0 else 'neg' }}">Neta Hoy ${{ "%+.2f"|format(cuenta.ganancia_dia) }}</span> | Ops {{ cuenta.operaciones|length }}</div>
<div style="margin-top:6px">BTC ${{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% -> Obj ${{ "%.2f"|format(btc.entry*1.006) }} | BNB ${{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}% -> Obj ${{ "%.2f"|format(bnb.entry*1.006) }}</div>
{% if cuenta.operaciones %}
<div style="margin-top:8px; font-size:12px; max-height:90px; overflow:auto; background:#000; padding:6px; border-radius:6px">
{% for op in cuenta.operaciones[::-1][:10] %}<div>{{op.hora}} {{op.symbol}} {{ "%+.2f"|format(op.pnl) }}% -> ${{ "%+.2f"|format(op.ganancia) }}</div>{% endfor %}
</div>
{% endif %}
</div>
<div class="card"><div id="tv_btc" style="height:350px;"></div></div>
<div class="card"><div id="tv_bnb" style="height:350px;"></div></div>
<script>
new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BTCUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","studies":["EMA@tv-basicstudies","RSI@tv-basicstudies"],"container_id":"tv_btc"});
new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BNBUSDT","interval":"5","timezone":"America/Argentina/Buenos_Aires","theme":"dark","style":"1","locale":"es","studies":["EMA@tv-basicstudies","RSI@tv-basicstudies"],"container_id":"tv_bnb"});
</script></body></html>
"""

app = Flask(__name__)
@app.route("/")
def home(): return render_template_string(HTML_TEMPLATE, btc=estado_global["BTCUSDT"], bnb=estado_global["BNBUSDT"], cuenta=estado_global["cuenta"])

def loop():
    last=0
    while True:
        # Reset dia
        if estado_global["cuenta"]["fecha"]!= datetime.date.today().isoformat():
            estado_global["cuenta"]["ganancia_dia"]=0.0; estado_global["cuenta"]["operaciones"]=[]; estado_global["cuenta"]["fecha"]=datetime.date.today().isoformat()
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
                        c=estado_global["cuenta"]
                        msg=f"🏦 LOBO V27 BALANCE\n💰 Balance ${c['balance']:.2f}\n📅 Inicial ${c['inicial']:.2f}\n📈 Neta Hoy ${c['ganancia_dia']:+.2f} ({len(c['operaciones'])} ops)\n\n"
                        for op in c['operaciones'][-15:]: msg+=f"{op['hora']} {op['symbol']} {op['pnl']:+.2f}% -> ${op['ganancia']:+.2f}\n"
                        if not c['operaciones']: msg+="Sin operaciones hoy"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        except: pass
        time.sleep(4)

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
