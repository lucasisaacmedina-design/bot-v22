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
        "BTCUSDT": {"precio": 78368, "entry": 78368, "pnl": 0.0, "en_posicion": True},
        "BNBUSDT": {"precio": 749.06, "entry": 749.06, "pnl": 0.0, "en_posicion": True},
        "cuenta": {"balance": 200.0, "ganancia": 0.0, "ops": 0},
        "historial": [],
        "ultimo_sl": 0,
        "mercado": "ANALIZANDO...",
        "modo": {"name":"LOBO 🐺", "tp":0.30, "sl":0.70, "cooldown":600,"emoji":"🐺"},
        "atr": 0.30,
        "ultimo_modo_name": "LOBO 🐺"
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

HTML = """
<html><head><meta name="viewport" content="width=device-width"><script src="https://s3.tradingview.com/tv.js"></script></head>
<body style="background:#0a0a0a;color:#fff;font-family:Arial;padding:10px">
<div style="background:#1a1a1a;padding:12px;border-radius:12px;max-width:900px;margin:auto">
<h3>🐺 LOBO V30 SOCIOS PRO $100+$100</h3>
<div>Bal ${{ "%.2f"|format(cuenta.balance) }} | Neta ${{ "%+.2f"|format(cuenta.ganancia) }} | Ops {{ cuenta.ops }}</div>
<div style="margin-top:6px;background:#222;padding:8px;border-radius:8px;border-left:4px solid #f5a623">
<div>MERCADO: {{ mercado }} | MODO: {{ modo.name }} {{ modo.emoji }}</div>
<div style="font-size:12px">TP +{{ modo.tp }}% | SL -{{ modo.sl }}% | ATR {{ "%.2f"|format(atr) }}%</div>
</div>
<div style="margin-top:8px">BTC ${{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% | BNB ${{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}%</div>
</div>
<div style="max-width:900px;margin:10px auto"><div id="tv_btc" style="height:350px"></div></div>
<div style="max-width:900px;margin:10px auto"><div id="tv_bnb" style="height:350px"></div></div>
<div style="max-width:900px;margin:15px auto;background:#151515;padding:12px;border-radius:12px">
<h4>📜 HISTORIAL</h4>{% for h in historial[-5:][::-1] %}<div style="font-size:13px;padding:6px;border-bottom:1px solid #222">{{ h }}</div>{% endfor %}</div>
<script>
new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"tv_btc"});
new TradingView.widget({"autosize":true,"height":350,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","container_id":"tv_bnb"});
</script></body></html>
"""

app = Flask(__name__)
@app.route("/")
def home(): return render_template_string(HTML, btc=estado["BTCUSDT"], bnb=estado["BNBUSDT"], cuenta=estado["cuenta"], mercado=estado.get("mercado","..."), modo=estado.get("modo",{"name":"LOBO","tp":0.30,"sl":0.70,"emoji":"🐺"}), atr=estado.get("atr",0), historial=estado.get("historial",[]))

def loop():
    last_update_id = 0
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
    except: pass
    while True:
        mercado, modo, atr_pct = get_modo_alfa("BTCUSDT")
        if modo["name"]!= estado.get("ultimo_modo_name"):
            if estado.get("ultimo_modo_name") is not None and estado.get("ultimo_modo_name")!="LOBO 🐺" or True:
                if estado.get("ultimo_modo_name")!= modo["name"]:
                    # solo avisa si realmente cambia
                    if estado.get("cuenta",{}).get("ops",0)>0 or True:
                        if estado.get("ultimo_modo_name")!= None:
                            if estado["ultimo_modo_name"]!= modo["name"]:
                                tg(f"🔄 CAMBIO DE MODO DETECTADO!\n\nAntes: {estado.get('ultimo_modo_name')}\nAhora: {modo['name']} {modo['emoji']}\nMercado: {mercado}\nNuevo TP +{modo['tp']}% SL -{modo['sl']}%")
            estado["ultimo_modo_name"] = modo["name"]
            guardar_estado()
        estado["mercado"] = mercado; estado["modo"] = modo; estado["atr"] = atr_pct
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
                        msg = f"✅TP {modo['emoji']} +{modo['tp']}% {s} ${p:.2f} +${tp_neto:.2f} NETO | {mercado} Bal ${estado['cuenta']['balance']:.2f}"; tg(msg)
                        estado["historial"].append(f"{time.strftime('%d/%m %H:%M')} {msg}"); estado[s]["entry"] = p; estado[s]["pnl"] = 0; guardar_estado()
                    if estado[s]["pnl"] <= -modo["sl"]:
                        estado["cuenta"]["balance"] -= sl_neto; estado["cuenta"]["ganancia"] -= sl_neto; estado["cuenta"]["ops"] += 1; estado["ultimo_sl"] = time.time()
                        msg = f"❌SL {modo['emoji']} -{modo['sl']}% {s} ${p:.2f} -${sl_neto:.2f} NETO | {mercado} Bal ${estado['cuenta']['balance']:.2f}"; tg(msg)
                        estado["historial"].append(f"{time.strftime('%d/%m %H:%M')} {msg}"); estado[s]["entry"] = p; estado[s]["pnl"] = 0; guardar_estado()
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=5", timeout=10).json()
            for upd in r.get("result", []):
                last_update_id = upd["update_id"]; txt = upd.get("message", {}).get("text", "")

                if txt.startswith("/introduccion"):
                    tg("""📚 ACADEMIA LOBO - EXPLICADO PARA PRINCIPIANTES (sin saber nada)

👋 Hola socio! Te explico todo como si tuvieras 10 años, sin palabras raras:

1. ¿Qué es BITCOIN (BTC)?
Imaginate que es oro pero por internet. Es la moneda más famosa del mundo. 1 Bitcoin vale hoy ~$78.000. No necesitas comprar 1 entero, podes comprar con $100. Si sube 1%, tus $100 se hacen $101. Eso caza el bot.

2. ¿Qué es BNB?
Es la moneda del Exchange más grande del mundo que se llama BINANCE. Es como comprar acciones de la cueva más grande. Vale ~$740 y se mueve muy rápido, por eso nos sirve para hacer scalping.

3. ¿Qué es un EXCHANGE?
Es como una casa de cambio del centro. Vos llevas pesos y te dan dólares. Acá llevas dólares y te dan Bitcoin. Nosotros usamos BINANCE porque es el más seguro y grande del mundo.

4. ¿Qué es el TRADING?
Es comprar barato y vender caro. Comprás Bitcoin a $78.000 y lo vendés a $78.300. Te quedaste con $300. El bot hace eso solo, pero 20 veces por día con ganancias chiquitas.

5. ¿Qué son las VELAS japonesas?
Son esos palitos verdes y rojos que ves en el gráfico.
Vela VERDE = la gente compró y el precio SUBIÓ 📈
Vela ROJA = la gente vendió y el precio BAJÓ 📉
El bot lee 30 velas por minuto y sabe si tiene que estar tranquilo o atacar.

6. ¿Qué es TENDENCIA ALCISTA y BAJISTA?
ALCISTA 📈 = Todo sube, todos felices, todos compran. Es fácil ganar.
BAJISTA 📉 = Todo baja, todos con miedo y venden. El bot igual gana porque entra y sale en 5 minutos, no guarda nada por meses.

7. ¿Tipos de MERCADO que ve el bot?
LATERAL 😴 = El precio va de costado, aburrido, no pasa nada. Ahí el bot se hace RATITA 🐀 y saca de a 10 centavos para no perder.
NORMAL 😐 = Sube y baja tranquilo. El 80% del tiempo está así. Ahí trabaja el LOBO 🐺.
EXPLOSIVO 🔥 = Se vuelve loco, velas gigantes para arriba y abajo. Ahí se transforma en ALFA ASESINO 🦁 y va a buscar $0.80 neto por operación.

8. ¿Qué es SCALPING? (Nuestra especialidad)
No somos de los que compran Bitcoin y esperan 1 año. Nosotros somos peluqueros: muchos cortes chiquitos.
Entramos, sacamos +0.20% a +0.90% en 5-10 minutos y nos vamos. 10 ganancias de $0.20 es mejor que 1 pérdida grande. Sin riesgo.

9. ¿Qué es TP y SL? (Muy importante)
TP = Take Profit = DONDE COBRAMOS. Ej: si compré y subió +0.30%, vendo y cobro ganancia.
SL = Stop Loss = DONDE CORTAMOS LA PERDIDA. Ej: si me equivoqué y bajó -0.70%, vendo para no perder más. Es el seguro del auto.

10. ¿Qué hace el bot con tus $200?
Pone $100 en BTC y $100 en BNB. Y todo el día hace scalping entre los 3 modos solo. No tenes que tocar nada. Vos solo mirás el balance crecer.

¿Entendiste todo? Perfecto. Ahora poné /start y mirá en qué modo está cazando hoy el LOBO 🐺""")

                elif txt.startswith("/start"):
                    tg(f"""🐺 LOBO V30 ALFA - BOT AUTOMATICO 24HS

Caza BTC y BNB con $100 en cada moneda, con TP/SL neto automático.

🧠 TIENE 3 ESTRATEGIAS Y ELIGE SOLA:

🐀 RATA SCALPER (Lateral 0.10-0.25%)
TP +0.20% (+$0.10 neto) | SL -0.40% | Pausa 5 min
Para no perder en días muertos.

🐺 LOBO (Normal 0.25-0.60%)
TP +0.30% (+$0.20 neto) | SL -0.70% | Pausa 10 min
Base segura, la que usamos siempre.

🦁 ALFA ASESINO (Explosivo +0.60%)
TP +0.90% (+$0.80 neto) | SL -0.50% | Sin pausa
Acá caza fuerte y sin parar.

📊 ESTADO DE HOY:
{estado['mercado']}
MODO ACTIVO: {estado['modo']['name']} {estado['modo']['emoji']}
ATR: {estado['atr']:.2f}% | TP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%

Balance: ${estado['cuenta']['balance']:.2f} | Neto: {estado['cuenta']['ganancia']:+.2f} | Ops: {estado['cuenta']['ops']}

Comandos:
/introduccion - escuela para novatos
/modo - modo de hoy resumido
/balance - PnL en vivo
/historial - últimos cierres
/simulacion - proyección con más capital""")

                elif txt.startswith("/modo"):
                    tg(f"📊 MODO DE HOY\n{estado['mercado']}\nActivo: {estado['modo']['name']} {estado['modo']['emoji']}\nATR {estado['atr']:.2f}%\nTP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}% | Pausa {estado['modo']['cooldown']//60}min\nSe está aplicando {estado['modo']['name']} ahora mismo.")

                elif txt.startswith("/balance"):
                    tg(f"🏦 V30 SOCIOS PRO\n{estado['mercado']}\nMODO {estado['modo']['name']} {estado['modo']['emoji']} TP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%\nBal ${estado['cuenta']['balance']:.2f} Neto ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}\nBTC {estado['BTCUSDT']['pnl']:+.2f}% BNB {estado['BNBUSDT']['pnl']:+.2f}%")

                elif txt.startswith("/historial"):
                    if not estado["historial"]: tg("📜 Aún sin cierres. Cuando cierre un TP/SL aparece acá y en la web.")
                    else:
                        ult = "\n".join(estado["historial"][-10:][::-1])
                        tg(f"📜 ULTIMOS 10 CIERRES\n{ult}\n\nTotal Ops: {estado['cuenta']['ops']} | Neto: ${estado['cuenta']['ganancia']:+.2f}")

                elif txt.startswith("/simulacion"):
                    g = estado["cuenta"]["ganancia"]; ops = max(1, estado["cuenta"]["ops"]); prom = g/ops if ops>0 else 0
                    tg(f"💰 SIMULACION SEGUN RENDIMIENTO ACTUAL\nProm por op: ${prom:.2f}\nOps actuales: {ops} | Neto actual ($200): ${g:+.2f}\n\nSi usaras:\n- $100 total -> ${g*0.5:+.2f} neto\n- $500 total -> ${g*2.5:+.2f} neto\n- $1000 total -> ${g*5:+.2f} neto\n\n*Estimado en base a tus ops reales de hoy. Más capital = más ganancia neta con mismo %.")

        except: pass
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
