from flask import Flask
import threading, time, random
from datetime import datetime

app = Flask(__name__)

ganancia_total = 0.0
capital = 200.0

def bot_lobo():
    global ganancia_total
    print("=== LOBO TRADER V24 - 30 DIAS - 2 SEPT ===")
    while True:
        resultado = random.choice(["TP","TP","TP","SL"])
        if resultado == "TP":
            ganancia_total += 3.0
        else:
            ganancia_total -= 4.0
        print(f"Total: ${ganancia_total:.2f}")
        time.sleep(60)

@app.route('/')
def home():
    return f"<h1>LOBO TRADER V24 ACTIVO</h1><p>Desde 2 Sept 2026</p><h2>Ganancia acumulada: ${ganancia_total:.2f}</h2><p>Capital prueba: $200 - Estrategia -2% / +1.5%</p><p>Link de respaldo 30 dias</p>"

threading.Thread(target=bot_lobo, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
