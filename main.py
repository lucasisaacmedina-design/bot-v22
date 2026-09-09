import os, time, requests, threading, json
from flask import Flask, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

# --- CONFIG V29 ALFA ASESINO ---
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
        "modo": {"name":"LOBO 🐺", "tp":0.30, "sl":0.70, "emoji":"🐺"}
    }
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r") as f:
                data = json.load(f)
                if "cuenta" not in data and "balance" in data:
                    default["cuenta"]["balance"] = float(data.get("balance",200))
                    default["cuenta"]["ganancia"] = float(data.get("ganancia",0))
                    default["cuenta"]["ops"] = int(data.get("ops",0))
                    return default
                if data.get("cuenta",{}).get("balance",200) < 199:
                    default["cuenta"] = data.get("cuenta", default["cuenta"])
                    return default
                return data
        except:
            pass
    return default

def guardar_estado():
    try:
        os.makedirs("/data", exist_ok=True)
        with open(ARCHIVO_ESTADO, "w") as f:
            json.dump(estado, f)
    except Exception as e:
        print(f"Error guardando: {e}")

estado = cargar_estado()

def get_precio(s):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}", timeout=5).json()
        return float(r["price"])
    except:
        return None

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except:
        pass

# === CEREBRO 1: INTERPRETE ===
def get_modo_alfa(symbol="BTCUSDT"):
    try:
        klines = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=30", timeout=5).json()
        cierres = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        if len(cierres) < 15:
            return "LATERAL", {"name":"LOBO 🐺","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"🐺"}, 0.3
        tr = [highs[i]-lows[i] for i in range(1,len(cierres))]
        atr = sum(tr[-14:])/14
        atr_pct = (atr / cierres[-1]) * 100

        if atr_pct < 0.25:
            return f"LATERAL LINEAL ({atr_pct:.2f}%)", {"name":"RATA SCALPER 🐀","tp":0.20,"sl":0.40,"cooldown":300,"emoji":"🐀"}, atr_pct
        elif atr_pct < 0.60:
            return f"TENDENCIA SUAVE ({atr_pct:.2f}%)", {"name":"LOBO 🐺","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"🐺"}, atr_pct
        else:
            return f"EXPLOSIVO 🔥 ({atr_pct:.2f}%)", {"name":"ALFA ASESINO 🦁💀","tp":0.90,"sl":0.50,"cooldown":0,"emoji":"🦁"}, atr_pct
    except:
        return "NORMAL", {"name":"LOBO 🐺","tp":0.30,"sl":0.70,"cooldown":600,"emoji":"🐺"}, 0.3

HTML = """<html><head><meta name="viewport" content="width=device-width"><script src="https://s3.tradingview.com/tv.js"></script></head>
<body style="background:#0a0a0a;color:#fff;font-family:Arial;padding:10px">
<div style="background:#1a1a1a;padding:12px;border-radius:12px;max-width:900px;margin:auto">
<h3>🐺LOBO V29 ALFA ASESINO $100+$100</h3>
<div>Bal ${{ "%.2f"|format(cuenta.balance) }} | Neta ${{ "%+.2f"|format(cuenta.ganancia) }} | Ops {{ cuenta.ops }}</div>
<div style="margin-top:6px;background:#222;padding:8px;border-radius:8px;border-left:4px solid #f5a623">
<div>MERCADO: {{ mercado }} | MODO: {{ modo.name }} {{ modo.emoji }}</div>
<div style="font-size:12px">TP +{{ modo.tp }}% | SL -{{ modo.sl }}% | ATR {{ "%.2f"|format(atr) }}%</div>
</div>
<div style="margin-top:8px">BTC ${{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% {{ '🟢EN POS' if btc.en_posicion else '🔴ESPERA' }} | BNB ${{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}%</div>
</div>
<div style="max-width:900px;margin:10px auto"><div id="tv_btc" style="height:400px"></div></div>
<div style="max-width:900px;margin:10px auto"><div id="tv_bnb" style="height:400px"></div></div>
<script>
new TradingView.widget({"autosize":true,"height":400,"symbol":"BINANCE:BTCUSDT","interval":"5","theme":"dark","container_id":"tv_btc"});
new TradingView.widget({"autosize":true,"height":400,"symbol":"BINANCE:BNBUSDT","interval":"5","theme":"dark","container_id":"tv_bnb"});
</script></body></html>"""

app = Flask(__name__)

@app.route("/")
def home():
    return render_template_string(HTML, btc=estado["BTCUSDT"], bnb=estado["BNBUSDT"], cuenta=estado["cuenta"], mercado=estado.get("mercado","..."), modo=estado.get("modo",{"name":"LOBO","tp":0.30,"sl":0.70,"emoji":"🐺"}), atr=estado.get("atr",0))

def loop():
    last_update_id = 0
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
    except: pass
    while True:
        # INTERPRETA MERCADO CADA CICLO
        mercado, modo, atr_pct = get_modo_alfa("BTCUSDT")
        estado["mercado"] = mercado
        estado["modo"] = modo
        estado["atr"] = atr_pct
        PAUSA_SL_SEG = modo["cooldown"]
        TP_PORC = modo["tp"]
        SL_PORC = modo["sl"]

        en_pausa = (time.time() - estado["ultimo_sl"]) < PAUSA_SL_SEG
        for s in ["BTCUSDT", "BNBUSDT"]:
            p = get_precio(s)
            if p:
                estado[s]["precio"] = p
                if estado[s]["en_posicion"] and not en_pausa:
                    estado[s]["pnl"] = ((p - estado[s]["entry"]) / estado[s]["entry"]) * 100
                    monto = MONTO_BTC if s == "BTCUSDT" else MONTO_BNB
                    tp_neto = monto * (TP_PORC/100) - monto * COMISION_TOTAL
                    sl_neto = monto * (SL_PORC/100) + monto * COMISION_TOTAL
                    if estado[s]["pnl"] >= TP_PORC:
                        estado["cuenta"]["balance"] += tp_neto
                        estado["cuenta"]["ganancia"] += tp_neto
                        estado["cuenta"]["ops"] += 1
                        msg = f"✅TP {modo['emoji']} +{TP_PORC}% {s} ${p:.2f} +${tp_neto:.2f} NETO | {mercado} Bal ${estado['cuenta']['balance']:.2f}"
                        tg(msg)
                        estado["historial"].append(msg)
                        estado[s]["entry"] = p
                        estado[s]["pnl"] = 0
                        guardar_estado()
                    if estado[s]["pnl"] <= -SL_PORC:
                        estado["cuenta"]["balance"] -= sl_neto
                        estado["cuenta"]["ganancia"] -= sl_neto
                        estado["cuenta"]["ops"] += 1
                        estado["ultimo_sl"] = time.time()
                        msg = f"❌SL {modo['emoji']} -{SL_PORC}% {s} ${p:.2f} -${sl_neto:.2f} NETO | {mercado} Bal ${estado['cuenta']['balance']:.2f}"
                        tg(msg)
                        estado["historial"].append(msg)
                        estado[s]["entry"] = p
                        estado[s]["pnl"] = 0
                        guardar_estado()
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=5", timeout=10).json()
            for upd in r.get("result", []):
                last_update_id = upd["update_id"]
                txt = upd.get("message", {}).get("text", "")
                if txt.startswith("/start"):
                    tg(f"🐺 LOBO V29 ALFA ACTIVO\n{estado['mercado']} | {estado['modo']['name']}\nBal ${estado['cuenta']['balance']:.2f} Neto ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}\n/balance")
                elif txt.startswith("/balance"):
                    tg(f"🏦 V29 ALFA\n{estado['mercado']}\nMODO {estado['modo']['name']} TP +{estado['modo']['tp']}% SL -{estado['modo']['sl']}%\nBal ${estado['cuenta']['balance']:.2f} Neto ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}\nBTC {estado['BTCUSDT']['pnl']:+.2f}% BNB {estado['BNBUSDT']['pnl']:+.2f}%")
        except:
            pass
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
