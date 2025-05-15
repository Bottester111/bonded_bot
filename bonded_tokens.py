
import requests
import time
import os
from telegram import Bot

# Telegram setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

# Constants
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/pairs/abstract"
PAIR_DETAILS_API = "https://api.dexscreener.com/latest/dex/pair/abstract"
MOONSHOT_FACTORY = "0x0d6848e39114abe69054407452b8aab82f8a44ba"
FDV_THRESHOLD = 5000
SCAN_INTERVAL = 5  # seconds

seen = set()

def fetch_pairs():
    try:
        response = requests.get(DEXSCREENER_API)
        if response.status_code != 200:
            print(f"[ERROR] Dexscreener status {response.status_code}")
            return []
        return response.json().get("pairs", [])
    except Exception as e:
        print(f"[ERROR] Fetch pairs failed: {e}")
        return []

def get_factory(pair_address):
    try:
        url = f"{PAIR_DETAILS_API}/{pair_address}"
        res = requests.get(url)
        data = res.json()
        return data.get("pair", {}).get("factoryAddress", "").lower()
    except Exception as e:
        print(f"[ERROR] Factory check failed for {pair_address}: {e}")
        return None

def send_alert(token):
    try:
        msg = (
            f"🚀 *New Bonded Token Alert!*\n"
            f"🔹 Token: {token['baseToken']['name']} ({token['baseToken']['symbol']})\n"
            f"💰 FDV: ${int(token['fdv']):,}\n"
            f"🔗 [View on Dexscreener]({token['url']})"
        )
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")
        print(f"[ALERT] Sent for {token['baseToken']['symbol']}")
    except Exception as e:
        print(f"[ERROR] Sending alert: {e}")

def main():
    print("🟢 Bonded Bot Live...")
    while True:
        tokens = fetch_pairs()
        print(f"🔍 Checking {len(tokens)} tokens...")
        for token in tokens:
            addr = token.get("pairAddress", "").lower()
            if addr in seen:
                continue

            fdv = token.get("fdv", 0)
            if not fdv or fdv < FDV_THRESHOLD:
                continue

            factory = get_factory(addr)
            if factory != MOONSHOT_FACTORY:
                continue

            send_alert(token)
            seen.add(addr)

        print(f"⏱ Sleeping {SCAN_INTERVAL}s...\n")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
