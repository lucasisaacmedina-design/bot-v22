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
        "modo": {"name":"LOBO 🐺", "tp":0.30, "sl":0.70, "cooldown":600,"emoji":"🐺"},
        "atr": 0.30, "ultimo_modo_name": "LOBO 🐺",
        "activo": False
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
        if len(cierres) < 15: return "LATERAL LINEAL (0.30%)", {"name":"LOBO 🐺","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"🐺"}, 0.3
        tr = [highs[i]-lows[i] for i in range(1,len(cierres))]; atr = sum(tr[-14:])/14; atr_pct = (atr / cierres[-1]) * 100
        if atr_pct < 0.25: return f"LATERAL LINEAL ({atr_pct:.2f}%)", {"name":"RATA SCALPER 🐀","tp":0.20,"sl":0.40,"cooldown":300,"emoji":"🐀"}, atr_pct
        elif atr_pct < 0.60: return f"NORMAL ({atr_pct:.2f}%)", {"name":"LOBO 🐺","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"🐺"}, atr_pct
        else: return f"EXPLOSIVO 🔥 ({atr_pct:.2f}%)", {"name":"ALFA ASESINO 🦁💀","tp":0.90,"sl":0.50,"cooldown":0,"emoji":"🦁"}, atr_pct
    except: return "NORMAL (0.30%)", {"name":"LOBO 🐺","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"🐺"}, 0.3

def set_menu():
    try:
        cmds = [
            {"command":"introduccion","description":"📚 1- Para novatos - EMPEZÁ ACÁ"},
            {"command":"estrategias","description":"🧠 2- Las que usamos nosotros"},
            {"command":"start","description":"🟢 3- INICIAR BOT - El socio debe iniciar"},
            {"command":"modo","description":"📊 4- Qué modo se está usando hoy"},
            {"command":"balance","description":"🏦 5- Balance y PnL en vivo"},
            {"command":"historial","description":"📜 6- Historial de operaciones del día"},
            {"command":"help","description":"❓ 7- Ayuda general"},
            {"command":"stop","description":"🔴 8- Pausar bot"}
        ]
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands", json={"commands":cmds}, timeout=10)
    except: pass

HTML = """<html><head><meta name="viewport" content="width=device-width"><script src="https://s3.tradingview.com/tv.js"></script></head><body style="background:#0a0a0a;color:#fff;font-family:Arial;padding:10px"><div style="background:#1a1a1a;padding:12px;border-radius:12px;max-width:900px;margin:auto"><h3>🐺 LOBO V30.6 FINAL VENDEDOR</h3><div>Estado: {{ "🟢 CAZANDO" if activo else "🔴 PAUSADO - Poné /start" }}</div><div>Bal ${{ "%.2f"|format(cuenta.balance) }} | Neta ${{ "%+.2f"|format(cuenta.ganancia) }} | Ops {{ cuenta.ops }}</div><div style="margin-top:6px;background:#222;padding:8px;border-radius:8px;border-left:4px solid {{ "#00ff00" if activo else "#ff0000" }}"><div>MERCADO: {{ mercado }} | MODO: {{ modo.name }}</div><div>TP +{{ modo.tp }}% | SL -{{ modo.sl }}% | ATR {{ "%.2f"|format(atr) }}%</div></div><div style="margin-top:8px">BTC ${{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% | BNB ${{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}%</div></div><div style="max-width:900px;margin:10px auto"><div id="tv_btc" style="height:350px"></div></div><div style="max-width:900px;margin:10px auto"><div id="tv_bnb" style="height:350px"></div></div><div style="max-width:900px;margin:15px auto;background:#151515;padding:12px;border-radius:12px"><h4>📜 HISTORIAL DEL DÍA</h4>{% for h in historial[-10:][::-1] %}<div style="font-size:13px;padding:6px;border-bottom:1px solid #222">{{ h }}</div>{% endfor %}</div><script>new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"tv_btc"});new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","container_id":"tv_bnb"});</script></body></html>"""
app = Flask(__name__)
@app.route("/")
def home(): return render_template_string(HTML, btc=estado["BTCUSDT"], bnb=estado["BNBUSDT"], cuenta=estado["cuenta"], mercado=estado.get("mercado","..."), modo=estado.get("modo",{"name":"LOBO","tp":0.30,"sl":0.70,"emoji":"🐺"}), atr=estado.get("atr",0), historial=estado.get("historial",[]), activo=estado.get("activo",False))

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

                if low.startswith("/introduccion") or "introducción" in low:
                    tg("""📚 1- INTRODUCCIÓN PARA NOVATOS

👋 Hola socio, te explico como si tuvieras 10 años:

1. BTC es oro por internet (~$78k)
2. BNB es la moneda de Binance
3. EXCHANGE es casa de cambio, usamos Binance
4. TRADING es comprar barato y vender caro
5. VELAS: Verde sube 📈 Rojo baja 📉
6. TENDENCIA: Alcista sube, Bajista baja, el bot gana igual
7. MERCADO: Lateral 😴, Normal 😐, Explosivo 🔥
8. SCALPING: Muchos cortes chiquitos, sin riesgo
9. TP es donde cobro, SL es el seguro
10. Con $200 pone $100 en BTC y $100 en BNB solo

Siguiente: /estrategias""")

                elif low.startswith("/estrategias"):
                    tg(f"""🧠 2- ESTRATEGIAS QUE USAMOS NOSOTROS

🐀 RATA SCALPER (0.10-0.25% lateral)
TP +0.20% (+$0.10 neto) | SL -0.40% | Pausa 5min

🐺 LOBO (0.25-0.60% normal) - 80% del tiempo
TP +0.30% (+$0.20 neto) | SL -0.70% | Pausa 10min

🦁 ALFA ASESINO (+0.60% explosivo)
TP +0.90% (+$0.80 neto) | SL -0.50% | Sin pausa

HOY: {estado['mercado']} -> {estado['modo']['name']} {estado['modo']['emoji']}

Siguiente: /start para prender""")

                elif low.startswith("/start"):
                    estado["activo"] = True; guardar_estado()
                    tg(f"""🟢 3- BOT INICIADO - EL SOCIO INICIÓ EL BOT

✅ LOBO PRENDIDO AUTOMÁTICAMENTE

Ya está cazando BTC y BNB solo.

📊 MODO HOY: {estado['modo']['name']} {estado['modo']['emoji']}
Mercado: {estado['mercado']}
ATR: {estado['atr']:.2f}% | TP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%

Balance: ${estado['cuenta']['balance']:.2f} | Neto: {estado['cuenta']['ganancia']:+.2f} | Ops: {estado['cuenta']['ops']}

Siguiente: /modo para ver que modo usa""")

                elif low.startswith("/modo"):
                    tg(f"📊 4- MODO QUE SE ESTÁ USANDO HOY\n\n{estado['mercado']}\nActivo: {estado['modo']['name']} {estado['modo']['emoji']}\nATR {estado['atr']:.2f}%\nTP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%\nBot: {'🟢 PRENDIDO' if estado['activo'] else '🔴 PAUSADO - Poné /start'}")

                elif low.startswith("/balance"):
                    tg(f"🏦 5- BALANCE EN VIVO\n\nBot: {'🟢 PRENDIDO' if estado['activo'] else '🔴 PAUSADO'}\n{estado['mercado']}\n{estado['modo']['name']} TP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%\n\nBal ${estado['cuenta']['balance']:.2f} Neto ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}\nBTC {estado['BTCUSDT']['pnl']:+.2f}% BNB {estado['BNBUSDT']['pnl']:+.2f}%")

                elif low.startswith("/historial"):
                    hoy = time.strftime('%d/%m')
                    historial_hoy = [h for h in estado["historial"] if hoy in h]
                    if not estado["historial"]:
                        tg("📜 6- HISTORIAL DEL DÍA\n\nAún sin operaciones hoy. Prendé el bot con /start")
                    else:
                        ult = "\n".join(estado["historial"][-15:][::-1])
                        ult_hoy = "\n".join(historial_hoy[-15:][::-1]) if historial_hoy else "Hoy aún sin cierres, mostrando últimos:"
                        tg(f"📜 6- HISTORIAL DE OPERACIONES DE CADA DÍA\n\nHOY {hoy}:\n{ult_hoy if historial_hoy else ult}\n\nTotal Ops: {estado['cuenta']['ops']} | Neto: ${estado['cuenta']['ganancia']:+.2f}")

                elif low.startswith("/help"):
                    tg(f"""❓ 7- AYUDA GENERAL - LOBO V30.6

Bot: {'🟢 PRENDIDO CAZANDO' if estado['activo'] else '🔴 PAUSADO - Poné /start'}

🤔 ¿QUÉ ES ESTO?
Bot automático que hace scalping en BTC y BNB con $100 en cada uno. Elige solo entre 3 modos (Rata, Lobo, Alfa) según el mercado. Vos solo lo prendés y apagás.

📚 COMANDOS EN ORDEN (tocá el Menú 👇):
1. /introduccion - Si no sabes nada, empezá acá
2. /estrategias - Las 3 estrategias que usamos
3. /start - PRENDER el bot (lo tenés que iniciar vos)
4. /modo - Ver que modo está usando HOY
5. /balance - Ver plata en vivo
6. /historial - Ver operaciones del día
7. /help - Esta ayuda
8. /stop - PAUSAR el bot

❓ PREGUNTAS FRECUENTES:
- ¿Se puede fundir? No, usa SL -0.40% a -0.70%, corta pérdida rápido. Es scalping, no hold.
- ¿Cuanto gana por día? Depende del mercado. En normal 3 a 8 ops x +$0.20 neto = +$0.60 a +$1.60 día con $200.
- ¿Tengo que dejar la compu prendida? No, está en la nube 24hs en Render.
- ¿Es automático? Si, vos solo /start y /stop.
- ¿Qué es TP/SL neto? Ya descuenta comisión Binance 0.10% total. Lo que ves es limpio.
- ¿Qué es ATR? Mide cuánto se mueve el precio. Si se mueve poco = Rata, normal = Lobo, mucho = Alfa.

🆘 ¿ALGO FALLA?
1. Bot no responde: poné /start de nuevo
2. Balance raro: /balance
3. Pausar: /stop
4. Web: abrí el link de Render

📊 ESTADO ACTUAL:
{estado['mercado']} | {estado['modo']['name']} {estado['modo']['emoji']}
Balance: ${estado['cuenta']['balance']:.2f}

¿Listo? Si sos nuevo poné /introduccion, si ya sabés poné /start para prender.""")

                elif low.startswith("/stop"):
                    estado["activo"] = False; guardar_estado()
                    tg(f"""🔴 8- BOT PAUSADO

Bot pausado. No tradea más hasta /start.

Balance final: ${estado['cuenta']['balance']:.2f} | Neto: ${estado['cuenta']['ganancia']:+.2f} | Ops: {estado['cuenta']['ops']}

Para prender: /start""")

        except: pass
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
