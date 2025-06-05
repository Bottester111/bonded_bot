
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
FACTORY_RAW = "0x0D6848e39114abE69054407452b8aaB82f8a44BA"
FDV_THRESHOLD = 5000
FDV_WARNING = 4000
SCAN_INTERVAL = 3  # seconds

# === Setup ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
bot = Bot(token=TELEGRAM_BOT_TOKEN)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

FACTORY_ADDRESS = Web3.to_checksum_address(FACTORY_RAW)
pair_created_topic = w3.keccak(text="PairCreated(address,address,address)").hex()

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
warned_pairs = set()
last_block = w3.eth.block_number

def send_log(message):
    logging.info(message)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logging.warning(f"Telegram send failed: {e}")

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
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")

def monitor():
    global last_block
    send_log("✅ Bonded bot using correct factory is now live and scanning...")

    while True:
        try:
            current_block = w3.eth.block_number
            logs = w3.eth.get_logs({
                "fromBlock": last_block + 1,
                "toBlock": current_block,
                "address": FACTORY_ADDRESS,
                "topics": [pair_created_topic]
            })

            logging.info(f"🔍 Scanning blocks {last_block + 1} → {current_block}, found {len(logs)} logs")

            for log in logs:
                decoded = factory.events.PairCreated().process_log(log)
                pair = decoded["args"]["pair"]
                if pair not in seen_pairs:
                    seen_pairs[pair] = int(time.time())
                    send_log(f"🧪 New pair detected: {pair}")

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
                            name = data.get("baseToken", {}).get("symbol", "UnknownToken")
                            if fdv >= FDV_WARNING and pair_address not in warned_pairs:
                                send_log(f"⚠️ {name} nearing bond level: FDV ${fdv:,.2f}")
                                warned_pairs.add(pair_address)
                            if fdv >= FDV_THRESHOLD:
                                send_alert(name, pair_address, fdv, deployed_time)
                                alerted_pairs.add(pair_address)
                            else:
                                logging.info(f"📉 {name} FDV: ${fdv:,.2f}")
                except Exception as e:
                    logging.warning(f"Error checking FDV for {pair_address}: {e}")

            last_block = current_block
            time.sleep(SCAN_INTERVAL)

        except Exception as e:
            send_log(f"🛑 Monitor error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor()
