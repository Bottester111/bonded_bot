
import time
import requests

TELEGRAM_BOT_TOKEN = "7681851699:AAH5tosSVfN7jQnaZXj8_hWY7XWsXWjQ0os"
TELEGRAM_CHAT_ID = "-1002614749658"
FDV_THRESHOLD = 4000

# Simulate previously tracked contracts for example
tracked_contracts = {"0x123...abc": 3900, "0x456...def": 3999}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

while True:
    # Simulate checking FDV for each tracked token
    for contract, current_fdv in tracked_contracts.items():
        current_fdv += 2  # fake FDV increase
        tracked_contracts[contract] = current_fdv
        if current_fdv >= FDV_THRESHOLD:
            print(f"🚀 Token `{contract}` reached *${int(current_fdv)} FDV*!")
            send_telegram_message(f"🚀 Token `{contract}` reached *${int(current_fdv)} FDV*!")
            del tracked_contracts[contract]
    time.sleep(1)
