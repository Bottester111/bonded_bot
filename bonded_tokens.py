
import requests
import time
import os
from datetime import datetime
from telegram import Bot

# ENV variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

bot = Bot(token=TELEGRAM_TOKEN)

MOONSHOT_FACTORY = "0x0d6848e39114abe69054407452b8aab82f8a44ba"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/pairs/abstract"

THRESHOLD_FDV = 5000
SCAN_INTERVAL = 5  # seconds

seen_tokens = set()

def fetch_tokens():
    try:
        response = requests.get(DEXSCREENER_API)
        if response.status_code != 200:
            print(f"[ERROR] Dexscreener returned {response.status_code}")
            return []
        data = response.json()
        return data.get("pairs", [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch tokens: {e}")
        return []

def get_factory_address(pair_address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pair/abstract/{pair_address}"
        response = requests.get(url)
        data = response.json()
        if "pair" in data:
            return data["pair"].get("factoryAddress", "").lower()
    except Exception as e:
        print(f"[ERROR] Factory fetch error for {pair_address}: {e}")
    return None

def alert_token(pair):
    try:
        msg = f"🚀 *New Bonded Token Alert!*

"               f"🪙 *{pair['baseToken']['name']}* (`{pair['baseToken']['symbol']}`)
"               f"📈 FDV: ${int(pair['fdv'])}
"               f"🔗 [View on Dexscreener]({pair['url']})"
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")
        print(f"[ALERT SENT] {pair['pairAddress']}")
    except Exception as e:
        print(f"[ERROR] Failed to send alert: {e}")

def monitor_bonded_tokens():
    print("🔧 Bonded bot is starting...")
    while True:
        print(f"🔍 Scanning for Moonshot tokens...")
        pairs = fetch_tokens()
        print(f"🔍 Found {len(pairs)} pairs")

        for pair in pairs:
            pair_address = pair.get("pairAddress", "").lower()
            if pair_address in seen_tokens:
                continue

            fdv = pair.get("fdv", 0)
            if fdv is None or fdv < THRESHOLD_FDV:
                continue

            factory = get_factory_address(pair_address)
            if factory != MOONSHOT_FACTORY:
                continue

            alert_token(pair)
            seen_tokens.add(pair_address)

        print(f"⏱ Sleeping for {SCAN_INTERVAL} seconds...\n")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    monitor_bonded_tokens()
