
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os
import re

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ABSCAN_API_KEY = os.getenv("ABSCAN_API_KEY")

if not TELEGRAM_TOKEN or " " in TELEGRAM_TOKEN or ":" not in TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN is missing or malformed. Please check your Railway variables.")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

MOONSHOT_DEPLOYER = "0x0d6848e39114abe69054407452b8aab82f8a44ba"
FDV_THRESHOLD_USD = 4000
CHECK_INTERVAL = 1  # seconds

tracked_tokens = set()

def log(msg):
    print(msg)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        print("[Telegram Error]", e)

def get_token_data_from_dexscreener(contract_address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/abstract/{contract_address}"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        if 'pair' not in data:
            return None
        pair_data = data['pair']
        fdv = float(pair_data.get("fdvUsd") or 0)
        return fdv
    except Exception:
        return None

def get_new_tokens():
    url = f"https://api.abscan.io/api?module=account&action=txlist&address={MOONSHOT_DEPLOYER}&sort=desc&apikey={ABSCAN_API_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        txs = res.get("result", [])
        new_tokens = []
        for tx in txs:
            input_data = tx.get("input", "")
            match = re.search(r"0x60.*", input_data)  # matches contract creation calldata
            if match and tx.get("to") == "":
                contract = tx.get("contractAddress")
                if contract and contract not in tracked_tokens:
                    new_tokens.append(contract)
        return new_tokens
    except Exception:
        return []

def main_loop():
    while True:
        new_contracts = get_new_tokens()
        for contract in new_contracts:
            tracked_tokens.add(contract)

        for contract in list(tracked_tokens):
            fdv = get_token_data_from_dexscreener(contract)
            if fdv is not None and fdv >= FDV_THRESHOLD_USD:
                log(f"🚀 Token `{contract}` reached *${int(fdv)} FDV*!
https://dexscreener.com/abstract/{contract}")
                tracked_tokens.remove(contract)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    print("🟢 Bonded Bot is live...")
    main_loop()
