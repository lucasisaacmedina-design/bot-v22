import os, time, requests, threading, json
from flask import Flask, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

# --- CONFIG V28.7 SEGURA PARA SOCIOS ---
MONTO_BTC = 100.0
MONTO_BNB = 100.0
COMISION_TOTAL = 0.001
TP_PORC = 0.30
SL_PORC = 0.70
PAUSA_SL_SEG = 600
ARCHIVO_ESTADO = "/data/estado.json"

def cargar_estado():
    default = {
        "BTCUSDT": {"precio": 78368, "entry": 78368, "pnl": 0.0, "en_posicion": False},
        "BNBUSDT": {"precio": 749.06, "entry": 749.06, "pnl": 0.0, "en_posicion": False},
        "cuenta": {"balance": 200.0, "ganancia": 0.0, "ops": 0},
        "historial": [],
        "ultimo_sl": 0
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
        if s == "BTCUSDT":
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5).json()
            return float(r["bitcoin"]["usd"])
        else:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd", timeout=5).json()
            return float(r["binancecoin"]["usd"])
    except:
        return None

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except:
        pass

# --- TU HTML CON GRAFICOS INTACTO ---
HTML = """<html><head><meta name="viewport" content="width=device-width"><script src="https://s3.tradingview.com/tv.js"></script></head>
<body style="background:#0a0a0a;color:#fff;font-family:Arial;padding:10px">
<div style="background:#1a1a1a;padding:12px;border-radius:12px;max-width:900px;margin:auto">
<h3>🐺LOBO V28.7 $100 BTC + $100 BNB NETO</h3>
<div>Bal ${{ "%.2f"|format(cuenta.balance) }} | Neta ${{ "%+.2f"|format(cuenta.ganancia) }} | Ops {{ cuenta.ops }}</div>
<div>BTC ${{ "%.2f"|format(btc.precio) }} {{ "%+.2f"|format(btc.pnl) }}% {{ '🟢EN POS' if btc.en_posicion else '🔴ESPERANDO' }} | BNB ${{ "%.2f"|format(bnb.precio) }} {{ "%+.2f"|format(bnb.pnl) }}%</div>
<div style="font-size:12px;color:#aaa;margin-top:6px">TP +0.30% (+$0.20 neto) | SL -0.70% (-$0.80 neto) | Pausa 10min anti-doble-SL</div>
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
    return render_template_string(HTML, btc=estado["BTCUSDT"], bnb=estado["BNBUSDT"], cuenta=estado["cuenta"])

def loop():
    last_update_id = 0
    # Borra webhook viejo para que funcione /start
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
    except:
        pass

    while True:
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
                        msg = f"✅TP +{TP_PORC}% {s} ${p:.2f} +${tp_neto:.2f} NETO Bal ${estado['cuenta']['balance']:.2f}"
                        tg(msg)
                        estado["historial"].append(msg)
                        estado[s]["entry"] = p
                        estado[s]["pnl"] = 0
                        tg(f"🔄RECOMPRA TP {s} ${p:.2f}")
                        guardar_estado()

                    if estado[s]["pnl"] <= -SL_PORC:
                        estado["cuenta"]["balance"] -= sl_neto
                        estado["cuenta"]["ganancia"] -= sl_neto
                        estado["cuenta"]["ops"] += 1
                        estado["ultimo_sl"] = time.time()
                        msg = f"❌SL -{SL_PORC}% {s} ${p:.2f} -${sl_neto:.2f} NETO Bal ${estado['cuenta']['balance']:.2f} ⏸Pausa 10min"
                        tg(msg)
                        estado["historial"].append(msg)
                        estado[s]["entry"] = p
                        estado[s]["pnl"] = 0
                        tg(f"🔄RECOMPRA SL {s} ${p:.2f} - Esperando 10min")
                        guardar_estado()

        # --- TELEGRAM ARREGLADO ---
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=5", timeout=10).json()
            for upd in r.get("result", []):
                last_update_id = upd["update_id"]
                txt = upd.get("message", {}).get("text", "")
                if txt.startswith("/start"):
                    tg(f"🐺 LOBO V28.7 ACTIVO\nBal ${estado['cuenta']['balance']:.2f} Neto ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}\nComandos: /balance")
                elif txt.startswith("/balance"):
                    btc_var = estado["BTCUSDT"]["pnl"]
                    bnb_var = estado["BNBUSDT"]["pnl"]
                    tg(f"🏦 V28.7 $100+$100\nBal ${estado['cuenta']['balance']:.2f} Neto ${estado['cuenta']['ganancia']:+.2f} Ops {estado['cuenta']['ops']}\nBTC {btc_var:+.2f}% BNB {bnb_var:+.2f}%\nTP +$0.20 neto SL -$0.80 neto")
        except:
            pass

        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
