
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
SCAN_INTERVAL = 3

# === Setup ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
bot = Bot(token=TELEGRAM_BOT_TOKEN)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

FACTORY_ADDRESS = Web3.to_checksum_address(FACTORY_RAW)
create_fn_sig = w3.keccak(text="createMoonshotTokenAndBuy(...)").hex()[:10]
create_fn_sig_bytes = bytes.fromhex(create_fn_sig[2:])

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
    send_log("✅ Bonded bot is now watching Moonshot factory txs and FDV...")

    while True:
        try:
            current_block = w3.eth.block_number
            for block_num in range(last_block + 1, current_block + 1):
                block = w3.eth.get_block(block_num, full_transactions=True)
                for tx in block.transactions:
                    if tx.to and tx.to.lower() == FACTORY_ADDRESS.lower():
                        if isinstance(tx.input, str):
                            tx_input_bytes = bytes.fromhex(tx.input[2:])
                        else:
                            tx_input_bytes = tx.input
                        if tx_input_bytes.startswith(create_fn_sig_bytes):
                            send_log(f"🆕 Detected Moonshot token creation tx:\n🔗 https://abscan.org/tx/{tx.hash.hex()}")
            last_block = current_block
            time.sleep(SCAN_INTERVAL)

        except Exception as e:
            send_log(f"🛑 Monitor error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor()
