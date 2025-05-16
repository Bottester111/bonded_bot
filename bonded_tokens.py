# Required packages:
# pip install beautifulsoup4 requests python-telegram-bot==13.15

import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or " " in TELEGRAM_TOKEN or ":" not in TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN is missing or malformed. Please check your Railway variables.")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

MOONSHOT_DEPLOYER = "0x0d6848e39114abe69054407452b8aab82f8a44ba"
ETHERSCAN_API = os.getenv("ETHERSCAN_API_KEY")
FDV_THRESHOLD_USD = 4100
PRICE_THRESHOLD = 0.0000041
CHECK_INTERVAL = 1  # seconds
BASE_URL = "https://dexscreener.com/abstract"

tracked_tokens = set()

def log(msg):
    print(msg)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        print("[Telegram Error]", e)

def fetch_recent_tokens():
    try:
        ABSCAN_API_KEY = os.getenv("ABSCAN_API_KEY")
        # Get latest block
        try:
            latest_block_res = requests.get(f"https://api.abscan.org/api?module=proxy&action=eth_blockNumber&apikey={ABSCAN_API_KEY}")
            latest_block = int(latest_block_res.json().get("result", "0x0"), 16)
            start_block = latest_block - 50
        except Exception as e:
            print("[Block Fetch Error]", e)
            start_block = 0

        url = f"https://api.abscan.org/api?module=account&action=tokentx&address={MOONSHOT_DEPLOYER}&startblock={start_block}&sort=desc&apikey={ABSCAN_API_KEY}"
        response = requests.get(url)
        print("[Raw Abscan response]", response.text[:500])  # Always print raw response
        response.raise_for_status()

        try:
            data = response.json()
            if not isinstance(data, dict):
                print("[JSON Type Error] Expected dict, got:", type(data))
                print("[Raw JSON Response]", repr(data)[:300])
                return []
            txs = data.get("result", [])
        except Exception as e:
            print("[JSON Parse Error]", e)
            print("[Raw Abscan Response]", response.text[:300])
            return []

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
    try:
        ABSCAN_API_KEY = os.getenv("ABSCAN_API_KEY")
        # Get latest block
        try:
            latest_block_res = requests.get(f"https://api.abscan.org/api?module=proxy&action=eth_blockNumber&apikey={ABSCAN_API_KEY}")
            latest_block = int(latest_block_res.json().get("result", "0x0"), 16)
            start_block = latest_block - 50
        except Exception as e:
            print("[Block Fetch Error]", e)
            start_block = 0

        url = f"https://api.abscan.org/api?module=account&action=tokentx&address={MOONSHOT_DEPLOYER}&startblock={start_block}&sort=desc&apikey={ABSCAN_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()

        try:
            data = response.json()
        except Exception as e:
            print("[JSON Parse Error]", e)
            print("[Raw Response]", response.text[:300])
            return []

        txs = data.get("result", [])
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
                print(f"[Scan] Checking token: {token}")
                price = get_token_price(token)
                if price and price >= PRICE_THRESHOLD:
                    print(f"[PASS] {token} passed FDV threshold with price ${price}")
                    msg = (
                        f"🚨 New Moonshot Token\n"
                        f"📈 *Token:* [{token}]({BASE_URL}/{token})\n"
                        f"💵 *Price:* ${price}\n"
                        f"🔥 *FDV est:* ${price * 1_000_000_000:,.0f}"
                    )
                    log(msg)
            print(f"Checked {len(new_tokens)} tokens. Sleeping {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print("[Main Loop Error]", e)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
