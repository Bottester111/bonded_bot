
import time
import requests
import logging
from web3 import Web3
from telegram import Bot
from datetime import datetime

# === Config ===
TELEGRAM_BOT_TOKEN = '7681851699:AAH5tosSVfN7jQnaZXj8_hWY7XWsXWjQ0os'
TELEGRAM_CHAT_ID = '-1002614749658'
RPC_URL = "https://api.mainnet.abs.xyz"
FACTORY_RAW = "0x59fc79d625380f803a1fc5028fc3dc7c8b3c3f1e"
FDV_THRESHOLD = 5000
SCAN_INTERVAL = 1  # seconds

# === Setup ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

bot = Bot(token=TELEGRAM_BOT_TOKEN)
w3 = Web3(Web3.HTTPProvider(RPC_URL))
FACTORY_ADDRESS = Web3.to_checksum_address(FACTORY_RAW)

factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=[{
    "anonymous": False,
    "inputs": [
        {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
        {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
        {"indexed": False, "internalType": "address", "name": "pair", "type": "address"}
    ],
    "name": "PairCreated",
    "type": "event"
}])

seen_pairs = {}
alerted_pairs = set()
last_block = w3.eth.block_number

def send_alert(name, contract, fdv, deployed_time):
    message = (
        f"🚀 *{name}* just bonded!\n"
        f"*Contract:* `{contract}`\n"
        f"*FDV:* ${int(fdv):,}\n"
        f"*Time Hit FDV:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"*Deployed:* {datetime.utcfromtimestamp(deployed_time).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"*Time to Bond:* {int((time.time() - deployed_time) // 60)}m {int((time.time() - deployed_time) % 60)}s\n"
        f"[View on Dexscreener](https://dexscreener.com/abstract/{contract})"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)
    logging.info(f"🚨 Alert sent for {name} at FDV ${fdv:,}")

def fetch_new_pairs():
    global last_block
    current_block = w3.eth.block_number
    events = factory.events.PairCreated().get_logs(fromBlock=last_block + 1, toBlock=current_block)
    for event in events:
        pair_address = event["args"]["pair"]
        if pair_address not in seen_pairs:
            seen_pairs[pair_address] = int(time.time())  # Store deployment time
            logging.info(f"👀 New pair detected: {pair_address}")
    last_block = current_block

def check_all_pairs():
    for pair_address, deployed_time in seen_pairs.items():
        if pair_address in alerted_pairs:
            continue
        url = f"https://api.dexscreener.com/latest/dex/pairs/abstract/{pair_address}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json().get("pair", {})
                if "priceUsd" in data and data["priceUsd"]:
                    price = float(data["priceUsd"])
                    fdv = price * 1_000_000_000
                    if fdv >= FDV_THRESHOLD:
                        name = data.get("baseToken", {}).get("symbol", "UnknownToken")
                        send_alert(name, pair_address, fdv, deployed_time)
                        alerted_pairs.add(pair_address)
        except Exception as e:
            logging.warning(f"⚠️ Error fetching {pair_address}: {e}")

def monitor():
    while True:
        try:
            fetch_new_pairs()
            check_all_pairs()
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            logging.error(f"🛑 Error in monitor loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor()
