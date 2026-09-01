import os
import threading
import time
import requests
from flask import Flask

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_ID = os.environ.get("TELEGRAM_ID")

print(f"TOKEN: {'OK' if TELEGRAM_TOKEN else 'NO'} ID: {TELEGRAM_ID}")

app = Flask(__name__)

@app.route('/')
def home():
    return f"Bot V22 OK - Token: {'OK' if TELEGRAM_TOKEN else 'FALTA'} - ID: {TELEGRAM_ID}"

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)

def polling():
    print(">>> POLLING INICIADO <<<")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            r = requests.get(url, params={"timeout": 20, "offset": offset}, timeout=25)
            j = r.json()
            for upd in j.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                print(f"Msg {chat_id}: {text}")
                if "start" in text.lower() or "hola" in text.lower():
                    send_telegram(chat_id, "🐺 *Lobo, Bot V22 iniciado...*\n✅ AHORA SI ESTOY VIVO!")
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

threading.Thread(target=polling, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
