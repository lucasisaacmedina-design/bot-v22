import requests, threading, time
from flask import Flask
app = Flask(__name__)

# --- CONFIG ---
TOKEN = "AQUI_TU_TOKEN_DE_TELEGRAM"
CHAT_ID = "AQUI_TU_CHAT_ID"
TP = 0.25 # FAST 0.25% para vender rapido
BALANCE = 1000.0
MONEDAS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","ADAUSDT"]
estado = {m: {"en_pos": False, "compra": 0, "pnl": 0, "ops": 0, "neta": 0} for m in MONEDAS}
estado["balance"] = BALANCE

def send(msg):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except: pass

def get_price(sym):
    try:
        # API NUEVA QUE NO BLOQUEA - data-api.binance.vision
        r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={sym}", timeout=4).json()
        return float(r["price"])
    except: return None

def bot_loop():
    send(f"🐺 LOBO V28.3 FAST {TP}% - 87L AUTO ON\nBal ${BALANCE} - Esperando compra...")
    while True:
        for sym in MONEDAS:
            price = get_price(sym)
            if not price: continue

            if not estado[sym]["en_pos"]:
                estado[sym]["en_pos"] = True
                estado[sym]["compra"] = price
                estado[sym]["pnl"] = 0
                send(f"🟢 COMPRA {sym} ${price:.2f} TP +{TP}% ON")
            else:
                compra = estado[sym]["compra"]
                pnl = ((price - compra) / compra) * 100
                estado[sym]["pnl"] = pnl

                if pnl >= TP:
                    ganancia = (BALANCE * TP / 100) * 0.2 # aprox
                    estado[sym]["ops"] += 1
                    estado[sym]["neta"] += ganancia
                    estado["balance"] += ganancia
                    estado[sym]["en_pos"] = False
                    send(f"✅ TP +{TP}% {sym} ${price:.2f} +${ganancia:.2f}\nOps: {estado[sym]['ops']} Neta: ${estado[sym]['neta']:.2f}")
        time.sleep(3) # chequea cada 3 seg para ser mas rapido

def telegram_loop():
    offset = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=20", timeout=25).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                txt = u["message"]["text"]
                if "/balance" in txt:
                    msg = f"🐺 LOBO V28.3 FAST {TP}%\nBal ${estado['balance']:.2f}\n"
                    for s in MONEDAS:
                        e = estado[s]
                        st = f"🟢 EN POS {e['pnl']:.2f}%" if e["en_pos"] else "⚪ ESPERANDO"
                        msg += f"{s}: {st} Ops:{e['ops']}\n"
                    send(msg)
                if "/comprar" in txt:
                    for s in MONEDAS: estado[s]["en_pos"] = False
                    send("🔄 Reiniciado - Comprando ahora...")
        except: time.sleep(2)

@app.route("/")
def home():
    html = f"<h2>LOBO V28.3 FAST {TP}% - 87L</h2>Bal ${estado['balance']:.2f}<br>"
    for s in MONEDAS:
        e = estado[s]
        html += f"{s}: {'EN POS' if e['en_pos'] else 'ESPERA'} {e['pnl']:.2f}% Ops:{e['ops']}<br>"
    return html

threading.Thread(target=bot_loop, daemon=True).start()
threading.Thread(target=telegram_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
