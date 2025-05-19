
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ABSCAN_API_KEY = os.getenv("ABSCAN_API_KEY")

if not TELEGRAM_TOKEN or " " in TELEGRAM_TOKEN or ":" not in TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN is missing or malformed. Please check your Railway variables.")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

MOONSHOT_DEPLOYER = "0x0d6848e39114abe69054407452b8aab82f8a44ba"
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

def fetch_recent_tokens(backfill=False):
    try:
        url = f"https://api.abscan.org/api?module=account&action=txlist&address={MOONSHOT_DEPLOYER}&sort=desc&apikey={ABSCAN_API_KEY}"
        if backfill:
            url += "&startblock=0"

        response = requests.get(url)
        print("[Raw Abscan response]", response.text[:300])
        response.raise_for_status()

        txs = response.json().get("result", [])
        new_tokens = []

        for tx in txs:
            if tx.get("from", "").lower() != MOONSHOT_DEPLOYER:

                continue
            contract = tx.get("contractAddress")
            if not contract:

                continue
            if contract in tracked_tokens:
                continue
            tracked_tokens.add(contract)
            new_tokens.append(contract)

        return new_tokens
    except Exception as e:
        print("[Fetch Token Error]", e)
        return []

def process_tokens(tokens):
    for token in tokens:
        print(f"[Scan] Checking token: {token}")
        price = get_token_price(token)
        if price is None:

            continue
        if price < PRICE_THRESHOLD:

            continue
        print(f"[PASS] {token} passed FDV threshold with price ${price}")
        msg = (
            f"🚨 New Moonshot Token\n"
            f"📈 *Token:* [{token}]({BASE_URL}/{token})\n"
            f"💵 *Price:* ${price}\n"
            f"🔥 *FDV est:* ${price * 1_000_000_000:,.0f}"
        )
        log(msg)

def main():
    log("🟢 Bonded Bot is live...")

    print("[Startup] Running backfill scan for recent tokens...")
    backfill_tokens = fetch_recent_tokens(backfill=True)
    process_tokens(backfill_tokens)

    while True:
        try:
            new_tokens = fetch_recent_tokens()
            process_tokens(new_tokens)
            print(f"Checked {len(new_tokens)} tokens. Sleeping {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print("[Main Loop Error]", e)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
