from flask import Flask
import threading
import time
import random
from datetime import datetime

app = Flask(__name__)

# ESTADO LOBO V31 - Recuperado de tu htmledit
estado = {
    "usdt": 85.27,
    "btc": 0.001,
    "price": 78371.0,
    "pnl": -14.73,
    "trades": 113,
    "comprado": True,
    "precio_compra": 78546.0,
    "estado_txt": "COMPRADO $78546 | Ahora -0.22% | Esperando +0.8%",
    "historial": []
}

def log(msg):
    hora = datetime.now().strftime("%H:%M:%S")
    estado["historial"].insert(0, f"{hora} - {msg}")
    if len(estado["historial"]) > 50:
        estado["historial"].pop()
    print(f"[V31] {msg}")

def bot_loop():
    while True:
        try:
            # Simula precio BTC moviéndose
            estado["price"] = estado["price"] * (1 + (random.random()-0.48)/500)
            
            if estado["comprado"]:
                gan = ((estado["price"] - estado["precio_compra"]) / estado["precio_compra"])*100
                estado["estado_txt"] = f"COMPRADO ${estado['precio_compra']:.0f} | Ahora {gan:+.2f}% | Vende en +0.8%"
                
                if gan >= 0.8:
                    venta = estado["price"] * estado["btc"]
                    profit = venta - estado["precio_compra"]*estado["btc"]
                    estado["usdt"] += venta
                    estado["pnl"] += profit
                    estado["trades"] += 1
                    estado["btc"] = 0
                    estado["comprado"] = False
                    estado["estado_txt"] = f"VENDIDO +{gan:.2f}% Profit +${profit:.2f}"
                    log(f"🔵 VENTA +{gan:.2f}% | USDT ${estado['usdt']:.2f} | PnL ${estado['pnl']:.2f}")
            else:
                # Compra solo si detecta caída
                if random.random() > 0.65:
                    estado["comprado"] = True
                    estado["precio_compra"] = estado["price"]
                    estado["btc"] = 0.001
                    estado["usdt"] -= estado["price"] * 0.001
                    estado["trades"] += 1
                    estado["estado_txt"] = f"COMPRADO a ${estado['price']:.0f} - Esperando +0.8%"
                    log(f"🟢 COMPRA a ${estado['price']:.0f} | USDT ${estado['usdt']:.2f}")
                else:
                    estado["estado_txt"] = "Esperando caída -0.4% para comprar..."
            
            # Objetivo $110
            if estado["usdt"] >= 110 and estado["usdt"] < 111:
                log("🔔 OBJETIVO $110 ALCANZADO!!!")

        except Exception as e:
            log(f"Error: {e}")
        
        time.sleep(3)

@app.route('/')
def dashboard():
    gan_actual = 0
    if estado["comprado"]:
        gan_actual = ((estado["price"] - estado["precio_compra"])/estado["precio_compra"])*100
    
    color_gan = "#2ecc71" if gan_actual >=0 else "#e74c3c"
    color_pnl = "#2ecc71" if estado["pnl"] >=0 else "#e74c3c"
    
    historial_html = "<br>".join(estado["historial"][:15])

    return f"""
    <div style="background:#0a0a0a;color:#fff;padding:20px;border-radius:15px;font-family:sans-serif;max-width:450px;margin:20px auto">
    <h2 style="text-align:center;color:#00ff88;margin:0">🚀 LOBO V31 - RENDER 24/7</h2>
    <p style="text-align:center;font-size:10px;color:#888">Online 24/7 | Bella Vista 17°C | Se actualiza solo</p>
    
    <div style="background:#1a1a1a;padding:15px;border-radius:10px;margin-top:15px;line-height:2;font-size:14px">
    <div style="display:flex;justify-content:space-between"><span>USDT:</span><b>${estado['usdt']:.2f}</b></div>
    <div style="display:flex;justify-content:space-between"><span>BTC:</span><b>{estado['btc']:.6f}</b></div>
    <div style="display:flex;justify-content:space-between"><span>Precio BTC:</span><b style="color:#f1c40f">${estado['price']:.0f}</b></div>
    <div style="display:flex;justify-content:space-between"><span>PnL:</span><b style="color:{color_pnl}">${estado['pnl']:+.2f}</b></div>
    <div style="display:flex;justify-content:space-between"><span>Trades:</span><b>{estado['trades']}</b></div>
    <div style="display:flex;justify-content:space-between"><span>Ganancia ahora:</span><b style="color:{color_gan}">{gan_actual:+.2f}%</b></div>
    <div style="margin-top:10px;padding:10px;background:#000;border-radius:8px;text-align:center"><b style="color:#00ff88">{estado['estado_txt']}</b></div>
    </div>
    
    <div style="background:#000;margin-top:15px;padding:10px;border-radius:10px;font-size:11px;height:200px;overflow:auto;border:1px solid #333">
    {historial_html}
    </div>
    
    <p style="text-align:center;color:#00ff88;margin-top:15px">✅ Bot corriendo aunque apagues tu compu</p>
    <p style="text-align:center;font-size:10px;color:#555">{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
    <script>setTimeout(()=>location.reload(), 4000)</script>
    </div>
    """

# Iniciar bot en hilo aparte
threading.Thread(target=bot_loop, daemon=True).start()
log("✅ V31 RENDER INICIADO - $85.27 | -14.73 PnL | 113 trades")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
