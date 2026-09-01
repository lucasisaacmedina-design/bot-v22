import os
import threading
import time
import requests
from flask import Flask

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_ID = os.environ.get("TELEGRAM_ID")
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET")

app = Flask(__name__)

@app.route('/')
def home():
    return "Lobo V22 Live - Bot Telegram Activo"

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_ID:
        print("Falta TOKEN o ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

def telegram_polling():
    print("Iniciando polling Telegram...")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"timeout": 30, "offset": offset}
            r = requests.get(url, params=params, timeout=35)
            data = r.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")
                    if str(chat_id) == str(TELEGRAM_ID):
                        if text.lower() in ["/start", "hola", "Hola"]:
                            send_telegram("🐺 *Lobo, Bot V22 iniciado...*\n\n✅ Conectado a Render + Telegram\n\nMandá /estado para ver estado.")
                        elif "/estado" in text.lower():
                            send_telegram(f"✅ Bot V22 Activo\nRender: Live\nTelegram ID: {TELEGRAM_ID}\nBinance: {'Conectado' if BINANCE_API_KEY else 'No'}")
                        else:
                            send_telegram(f"Recibido: {text}\nEscribí /estado")
        except Exception as e:
            print(f"Error polling: {e}")
            time.sleep(5)
        time.sleep(1)

# Iniciar hilo de Telegram al arrancar
threading.Thread(target=telegram_polling, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
