
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

MOONSHOT_DEPLOYER = "0x0d6848e39114abe69054407452b8aab82f8a44ba"
ETHERSCAN_API = os.getenv("ETHERSCAN_API_KEY")
FDV_THRESHOLD_USD = 4000
PRICE_THRESHOLD = 0.0000041000
CHECK_INTERVAL = 1  # seconds
BASE_URL = "https://dexscreener.com/abstract"

tracked_tokens = set()

def log(msg):
    print(msg)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
    except Exception as e:
        print("[Telegram Error]", e)

def fetch_recent_tokens():
    try:
        url = f"https://api.abscan.org/api?module=account&action=tokentx&address={MOONSHOT_DEPLOYER}&sort=desc"
        response = requests.get(url)
        response.raise_for_status()
        txs = response.json().get("result", [])
        new_tokens = []

        for tx in txs:
            contract = tx.get("contractAddress")
            if contract and contract not in tracked_tokens:
                tracked_tokens.add(contract)
                new_tokens.append(contract)

        return new_tokens
    except Exception as e:
        print("[Fetch Token Error]", e)
        return []

def get_token_price(contract_address):
    try:
        url = f"{BASE_URL}/{contract_address}"
        headers = {
            "User-Agent": "Mozilla/5.0",
        }
        r = requests.get(url, headers=headers)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        # Dexscreener typically has price in <div>$0.002960</div> for tokens
        price_text = soup.find("div", string=lambda t: t and "$" in t)
        if not price_text:
            return None

        price = price_text.text.strip().replace("$", "")
        return float(price)
    except Exception as e:
        print(f"[Dexscreener Price Error] {contract_address}", e)
        return None

def main():
    log("🟢 Bonded Bot is live...")

    while True:
        try:
            new_tokens = fetch_recent_tokens()
            for token in new_tokens:
                price = get_token_price(token)
                if price and price >= PRICE_THRESHOLD:
                    msg = f"🚨 New Moonshot Token
📈 *Token:* [{token}]({BASE_URL}/{token})
💵 *Price:* ${price}
🔥 *FDV est:* ${price * 1_000_000_000:,.0f}"
                    log(msg)
            print(f"Checked {len(new_tokens)} tokens. Sleeping {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print("[Main Loop Error]", e)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
