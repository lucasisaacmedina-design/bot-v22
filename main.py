import os, time, requests, threading, json
from flask import Flask, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
MONTO_BTC = 100.0
MONTO_BNB = 100.0
COMISION_TOTAL = 0.001
ARCHIVO_ESTADO = "/data/estado.json"

def cargar_estado():
    default = {
        "BTCUSDT": {"precio": 78254, "entry": 78254, "pnl": 0.0, "en_posicion": True},
        "BNBUSDT": {"precio": 749.06, "entry": 749.06, "pnl": 0.0, "en_posicion": True},
        "cuenta": {"balance": 200.0, "ganancia": 0.0, "ops": 0},
        "historial": [], "ultimo_sl": 0,
        "mercado": "ANALIZANDO...",
        "modo": {"name":"LOBO","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"\U0001F43A"},
        "atr": 0.30, "ultimo_modo_name": "LOBO",
        "activo": False,
        "primera_vez": True
    }
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r") as f:
                data = json.load(f)
                for k,v in default.items():
                    if k not in data: data[k]=v
                return data
        except: pass
    return default

def guardar_estado():
    try:
        os.makedirs("/data", exist_ok=True)
        with open(ARCHIVO_ESTADO, "w") as f: json.dump(estado, f)
    except: pass

estado = cargar_estado()

def get_precio(s):
    try: return float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}", timeout=5).json()["price"])
    except: return None

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except: pass

def get_modo_alfa(symbol="BTCUSDT"):
    try:
        klines = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=30", timeout=5).json()
        cierres = [float(k[4]) for k in klines]; highs = [float(k[2]) for k in klines]; lows = [float(k[3]) for k in klines]
        if len(cierres) < 15: return "LATERAL LINEAL (0.30%)", {"name":"LOBO","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"\U0001F43A"}, 0.3
        tr = [highs[i]-lows[i] for i in range(1,len(cierres))]; atr = sum(tr[-14:])/14; atr_pct = (atr / cierres[-1]) * 100
        if atr_pct < 0.25: return f"LATERAL LINEAL ({atr_pct:.2f}%)", {"name":"RATA SCALPER","tp":0.20,"sl":0.40,"cooldown":300,"emoji":"\U0001F400"}, atr_pct
        elif atr_pct < 0.60: return f"NORMAL ({atr_pct:.2f}%)", {"name":"LOBO","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"\U0001F43A"}, atr_pct
        else: return f"EXPLOSIVO ({atr_pct:.2f}%)", {"name":"ALFA ASESINO","tp":0.90,"sl":0.50,"cooldown":0,"emoji":"\U0001F981"}, atr_pct
    except: return "NORMAL (0.30%)", {"name":"LOBO","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"\U0001F43A"}, 0.3

def set_menu():
    try:
        cmds = [
            {"command":"introduccion","description":"1 introduccion para novatos"},
            {"command":"estrategias","description":"2 estrategias las que usamos nosotros"},
            {"command":"start","description":"3 start se inicia el bot"},
            {"command":"modo","description":"4 modo que modo se esta usando"},
            {"command":"balance","description":"5 balance"},
            {"command":"historial","description":"6 historial de las operaciones de cada dia"},
            {"command":"help","description":"7 help"},
            {"command":"stop","description":"8 stop"}
        ]
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands", json={"commands":cmds}, timeout=10)
    except: pass

HTML = """<html><head><meta name="viewport" content="width=device-width"><script src="https://s3.tradingview.com/tv.js"></script></head><body style="background:#0a0a0a;color:#fff;font-family:Arial;padding:10px"><div style="background:#1a1a1a;padding:12px;border-radius:12px;max-width:900px;margin:auto"><h3>LOBO V31 EMBUDO</h3><div>Estado: {{ "CAZANDO" if activo else "PAUSADO" }}</div><div>Bal ${{ "%.2f"|format(cuenta.balance) }} | Neta ${{ "%+.2f"|format(cuenta.ganancia) }} | Ops {{ cuenta.ops }}</div><div style="margin-top:6px;background:#222;padding:8px;border-radius:8px;border-left:4px solid {{ "#00ff00" if activo else "#ff0000" }}"><div>MERCADO: {{ mercado }} | MODO: {{ modo.name }} {{ modo.emoji }}</div><div>TP +{{ modo.tp }}% | SL -{{ modo.sl }}% | ATR {{ "%.2f"|format(atr) }}%</div></div><div style="margin-top:8px">BTC ${{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% | BNB ${{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}%</div></div><div style="max-width:900px;margin:10px auto"><div id="tv_btc" style="height:350px"></div></div><div style="max-width:900px;margin:10px auto"><div id="tv_bnb" style="height:350px"></div></div><div style="max-width:900px;margin:15px auto;background:#151515;padding:12px;border-radius:12px"><h4>HISTORIAL DEL DIA</h4>{% for h in historial[-10:][::-1] %}<div style="font-size:13px;padding:6px;border-bottom:1px solid #222">{{ h }}</div>{% endfor %}</div><script>new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"tv_btc"});new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","container_id":"tv_bnb"});</script></body></html>"""
app = Flask(__name__)
@app.route("/")
def home(): return render_template_string(HTML, btc=estado["BTCUSDT"], bnb=estado["BNBUSDT"], cuenta=estado["cuenta"], mercado=estado.get("mercado","..."), modo=estado.get("modo",{"name":"LOBO","tp":0.30,"sl":0.70,"emoji":"\U0001F43A"}), atr=estado.get("atr",0), historial=estado.get("historial",[]), activo=estado.get("activo",False))

def loop():
    last_update_id = 0
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5); set_menu()
    except: pass
    while True:
        mercado, modo, atr_pct = get_modo_alfa("BTCUSDT")
        if modo["name"]!= estado.get("ultimo_modo_name"):
            if estado.get("ultimo_modo_name") and estado.get("activo"):
                if estado.get("ultimo_modo_name")!= modo["name"]:
                    tg(f"🔄 CAMBIO DE MODO\nAntes: {estado.get('ultimo_modo_name')}\nAhora: {modo['name']} {modo['emoji']}\n{mercado}")
            estado["ultimo_modo_name"] = modo["name"]; guardar_estado()
        estado["mercado"] = mercado; estado["modo"] = modo; estado["atr"] = atr_pct
        if estado.get("activo"):
            en_pausa = (time.time() - estado["ultimo_sl"]) < modo["cooldown"]
            for s in ["BTCUSDT", "BNBUSDT"]:
                p = get_precio(s)
                if p:
                    estado[s]["precio"] = p
                    if estado[s]["en_posicion"] and not en_pausa:
                        estado[s]["pnl"] = ((p - estado[s]["entry"]) / estado[s]["entry"]) * 100
                        monto = MONTO_BTC if s == "BTCUSDT" else MONTO_BNB
                        tp_neto = monto * (modo["tp"]/100) - monto * COMISION_TOTAL
                        sl_neto = monto * (modo["sl"]/100) + monto * COMISION_TOTAL
                        if estado[s]["pnl"] >= modo["tp"]:
                            estado["cuenta"]["balance"] += tp_neto; estado["cuenta"]["ganancia"] += tp_neto; estado["cuenta"]["ops"] += 1
                            msg = f"✅TP {modo['emoji']} +{modo['tp']}% {s} ${p:.2f} +${tp_neto:.2f} NETO Bal ${estado['cuenta']['balance']:.2f}"; tg(msg)
                            estado["historial"].append(f"{time.strftime('%d/%m %H:%M')} {msg}"); estado[s]["entry"] = p; estado[s]["pnl"] = 0; guardar_estado()
                        if estado[s]["pnl"] <= -modo["sl"]:
                            estado["cuenta"]["balance"] -= sl_neto; estado["cuenta"]["ganancia"] -= sl_neto; estado["cuenta"]["ops"] += 1; estado["ultimo_sl"] = time.time()
                            msg = f"❌SL {modo['emoji']} -{modo['sl']}% {s} ${p:.2f} -${sl_neto:.2f} NETO Bal ${estado['cuenta']['balance']:.2f}"; tg(msg)
                            estado["historial"].append(f"{time.strftime('%d/%m %H:%M')} {msg}"); estado[s]["entry"] = p; estado[s]["pnl"] = 0; guardar_estado()
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=5", timeout=10).json()
            for upd in r.get("result", []):
                last_update_id = upd["update_id"]; txt = upd.get("message", {}).get("text", ""); low = txt.lower()

                if low.startswith("/introduccion"):
                    tg("""📚 1 INTRODUCCION PARA NOVATOS\n\n1. BTC es oro por internet\n2. BNB es moneda de Binance\n3. EXCHANGE es casa de cambio\n4. TRADING es comprar barato y vender caro\n5. VELAS verde sube rojo baja\n6. TENDENCIA alcista sube bajista baja\n7. MERCADO lateral normal explosivo\n8. SCALPING muchos cortes chiquitos\n9. TP es donde cobro SL es seguro\n10. Con $200 trabaja $100 BTC + $100 BNB solo\n\nSiguiente: /estrategias""")

                elif low.startswith("/estrategias"):
                    tg(f"""🧠 2 ESTRATEGIAS LAS QUE USAMOS NOSOTROS\n\n🐀 RATA SCALPER lateral 0.10-0.25%\nTP +0.20% SL -0.40%\n\n🐺 LOBO normal 0.25-0.60% - 80% del tiempo\nTP +0.30% SL -0.70%\n\n🦁 ALFA ASESINO explosivo +0.60%\nTP +0.90% SL -0.50%\n\nHOY: {estado['mercado']} -> {estado['modo']['name']} {estado['modo']['emoji']}\n\nSiguiente: /start para prender el bot""")

                elif low.startswith("/start"):
                    # EMBUDO: PRIMERA VEZ NO PRENDE, ENSEÑA
                    if estado.get("primera_vez", True):
                        estado["primera_vez"] = False; guardar_estado()
                        tg(f"""👋 ¡BIENVENIDO SOCIO AL LOBO V22!

Veo que es tu primera vez, te explico en 1 minuto antes de prender el bot:

📚 1 INTRODUCCION PARA NOVATOS
BTC es oro por internet
BNB es moneda de Binance
Trading es comprar barato y vender caro
Con $200 trabajamos $100 BTC + $100 BNB solo

🧠 2 ESTRATEGIAS QUE USAMOS
🐀 RATA: mercado lateral TP +0.20%
🐺 LOBO: mercado normal TP +0.30% (80% del tiempo)
🦁 ALFA: mercado explosivo TP +0.90%

HOY ESTAMOS EN: {estado['mercado']}
MODO: {estado['modo']['name']} {estado['modo']['emoji']}

Si querés ver todo en detalle:
👉 /introduccion
👉 /estrategias

¿Entendiste todo? Ahora sí, toca de nuevo /start para PRENDER EL BOT y empezar a cazar. 🟢""")
                    else:
                        # SEGUNDA VEZ SI PRENDE
                        estado["activo"] = True; guardar_estado()
                        tg(f"""🟢 3 START SE INICIA EL BOT\n\n✅ LOBO PRENDIDO AUTOMATICAMENTE\nEl socio inicio el bot. Ya esta cazando BTC y BNB solo.\n\n📊 MODO HOY: {estado['modo']['name']} {estado['modo']['emoji']}\nMercado: {estado['mercado']}\nATR: {estado['atr']:.2f}% | TP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%\n\nBalance: ${estado['cuenta']['balance']:.2f} | Neto: {estado['cuenta']['ganancia']:+.2f} | Ops: {estado['cuenta']['ops']}\n\nSiguiente: /modo""")

                elif low.startswith("/modo"):
                    tg(f"""📊 4 MODO QUE MODO SE ESTA USANDO\n\n{estado['mercado']}\nActivo: {estado['modo']['name']} {estado['modo']['emoji']}\nATR {estado['atr']:.2f}%\nTP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%\nBot: {'🟢 PRENDIDO' if estado['activo'] else '🔴 PAUSADO - Pone /start'}\n\nSiguiente: /balance""")

                elif low.startswith("/balance"):
                    tg(f"""🏦 5 BALANCE\n\nBot: {'🟢 PRENDIDO' if estado['activo'] else '🔴 PAUSADO'}\n{estado['mercado']}\n{estado['modo']['name']} {estado['modo']['emoji']} TP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%\n\nBal ${estado['cuenta']['balance']:.2f} Neto ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}\nBTC {estado['BTCUSDT']['pnl']:+.2f}% BNB {estado['BNBUSDT']['pnl']:+.2f}%\n\nSiguiente: /historial""")

                elif low.startswith("/historial"):
                    hoy = time.strftime('%d/%m')
                    if not estado["historial"]: tg("📜 6 HISTORIAL DE LAS OPERACIONES DE CADA DIA\n\nAun sin operaciones hoy. Prende el bot con /start")
                    else:
                        ult = "\n".join(estado["historial"][-15:][::-1]); tg(f"📜 6 HISTORIAL DE LAS OPERACIONES DE CADA DIA\n\nHOY {hoy}:\n{ult}\n\nTotal Ops: {estado['cuenta']['ops']} | Neto: ${estado['cuenta']['ganancia']:+.2f}\n\nSiguiente: /help")

                elif low.startswith("/help"):
                    tg(f"""❓ 7 HELP\n\nBot: {'🟢 PRENDIDO' if estado['activo'] else '🔴 PAUSADO'}\n\n1 /introduccion para novatos\n2 /estrategias las que usamos nosotros\n3 /start se inicia el bot\n4 /modo que modo se esta usando\n5 /balance\n6 /historial de las operaciones de cada dia\n7 /help ayuda\n8 /stop pausar bot\n\nESTADO HOY:\n{estado['mercado']} | {estado['modo']['name']} {estado['modo']['emoji']}\nBalance: ${estado['cuenta']['balance']:.2f}""")

                elif low.startswith("/stop"):
                    estado["activo"] = False; estado["primera_vez"] = True; guardar_estado()
                    tg(f"""🔴 8 STOP - BOT PAUSADO\n\nBot pausado. No tradea mas hasta /start.\n\nBalance final: ${estado['cuenta']['balance']:.2f} | Neto: ${estado['cuenta']['ganancia']:+.2f} | Ops: {estado['cuenta']['ops']}\n\nPara prender de nuevo: /start (vas a pasar por la bienvenida otra vez)""")

        except: pass
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
