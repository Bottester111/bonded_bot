
import time
import json
from web3 import Web3
from telegram import Bot

# === CONFIG ===
RPC_URL = "https://api.mainnet.abs.xyz"
FACTORY_ADDRESS = "0x566d7510dEE58360a64C9827257cF6D0Dc43985E"
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
WETH_USDC_PAIR = "0x7c72570fda921aac316bcef81c0e683904a72d30"  # <-- Replace with real Chainlink feed if available
TELEGRAM_BOT_TOKEN = "7681851699:AAH5tosSVfN7jQnaZXj8_hWY7XWsXWjQ0os"
TELEGRAM_CHAT_ID = "-1002614749658"
FDV_THRESHOLD = 5000

w3 = Web3(Web3.HTTPProvider(RPC_URL))
bot = Bot(token=TELEGRAM_BOT_TOKEN)
alerted = set()

# ABIs
FACTORY_ABI = json.loads('[{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token0","type":"address"},{"indexed":true,"internalType":"address","name":"token1","type":"address"},{"indexed":false,"internalType":"address","name":"pair","type":"address"},{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"PairCreated","type":"event"}]')

PAIR_ABI = json.loads("""[
    {"constant": true, "inputs": [], "name": "getReserves", "outputs": [{"name": "_reserve0", "type": "uint112"}, {"name": "_reserve1", "type": "uint112"}, {"name": "_blockTimestampLast", "type": "uint32"}], "payable": false, "stateMutability": "view", "type": "function"},
    {"constant": true, "inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "payable": false, "stateMutability": "view", "type": "function"},
    {"constant": true, "inputs": [], "name": "token1", "outputs": [{"name": "", "type": "address"}], "payable": false, "stateMutability": "view", "type": "function"}
]""")

TOKEN_ABI = json.loads('[{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]')

ORACLE_ABI = json.loads('[{"inputs":[],"name":"latestAnswer","outputs":[{"internalType":"int256","name":"","type":"int256"}],"stateMutability":"view","type":"function"}]')

factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)

def get_token_details(token_address):
    token = w3.eth.contract(address=token_address, abi=TOKEN_ABI)
    try:
        supply = token.functions.totalSupply().call()
        if supply == 0 or supply > 1e36:
            return None
        decimals = token.functions.decimals().call()
        return supply / (10 ** decimals)
    except:
        return None

def get_token_price_in_weth(pair_address, token_address):
    try:
        pair = w3.eth.contract(address=pair_address, abi=PAIR_ABI)
        token0 = pair.functions.token0().call()
        token1 = pair.functions.token1().call()
        reserves = pair.functions.getReserves().call()

        if token0.lower() == token_address.lower():
            reserve_token = reserves[0]
            reserve_weth = reserves[1]
        else:
            reserve_token = reserves[1]
            reserve_weth = reserves[0]

        if reserve_token == 0:
            return 0

        return reserve_weth / reserve_token
    except:
        return 0


def get_eth_price_usd():
    try:
        pair = w3.eth.contract(address=WETH_USDC_PAIR, abi=PAIR_ABI)
        token0 = pair.functions.token0().call()
        token1 = pair.functions.token1().call()
        reserves = pair.functions.getReserves().call()

        if token0.lower() == WETH_ADDRESS.lower():
            reserve_weth = reserves[0]
            reserve_usdc = reserves[1]
        else:
            reserve_weth = reserves[1]
            reserve_usdc = reserves[0]

        if reserve_weth == 0:
            return 2000

        return reserve_usdc / reserve_weth
    except:
        return 2000

        price = oracle.functions.latestAnswer().call()
        return int(price) / 1e8
    except:
        return 2000  # fallback

def send_alert(pair_address, token_address, fdv, price):
    msg = f"""🚨 *Bonded Token Detected*

*Pair:* `{pair_address}`
*Token:* `{token_address}`
*Price:* {price:.8f} WETH
*FDV:* ${int(fdv):,}

[📊 View on AbstractScan](https://abscan.org/address/{token_address})"""
    print(f"[ALERT] {msg}")
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        print("Telegram error:", e)

def check_token(pair, token):
    if pair in alerted:
        return

    supply = get_token_details(token)
    if not supply:
        return

    price = get_token_price_in_weth(pair, token)
    eth_price = get_eth_price_usd()
    fdv = supply * price * eth_price

    if fdv >= FDV_THRESHOLD:
        send_alert(pair, token, fdv, price)
        alerted.add(pair)

def scan_historic():
    print("🔁 Scanning historic pairs...")
    event_signature = w3.keccak(text="PairCreated(address,address,address,uint256)").hex()
    latest_block = w3.eth.block_number
    step = 5000
    for start in range(0, latest_block, step):
        end = min(start + step - 1, latest_block)
        try:
            logs = w3.eth.get_logs({
                "fromBlock": start,
                "toBlock": end,
                "address": FACTORY_ADDRESS,
                "topics": [event_signature]
            })
            for log in logs:
                data = factory.events.PairCreated().processLog(log)
                token0 = data.args.token0
                token1 = data.args.token1
                pair = data.args.pair

                if WETH_ADDRESS.lower() not in [token0.lower(), token1.lower()]:
                    continue

                token = token0 if token1.lower() == WETH_ADDRESS.lower() else token1
                check_token(pair, token)
        except Exception as e:
            print(f"Historic block {start}-{end} error:", e)

def monitor_live():
    print("🚀 Watching live pairs...")
    last_block = w3.eth.block_number
    while True:
        latest = w3.eth.block_number
        if latest == last_block:
            time.sleep(1)
            continue

        try:
            logs = w3.eth.get_logs({
                "fromBlock": last_block + 1,
                "toBlock": latest,
                "address": FACTORY_ADDRESS,
                "topics": [w3.keccak(text="PairCreated(address,address,address,uint256)").hex()]
            })

            for log in logs:
                data = factory.events.PairCreated().processLog(log)
                token0 = data.args.token0
                token1 = data.args.token1
                pair = data.args.pair

                if WETH_ADDRESS.lower() not in [token0.lower(), token1.lower()]:
                    continue

                token = token0 if token1.lower() == WETH_ADDRESS.lower() else token1
                check_token(pair, token)

        except Exception as e:
            print("Live monitoring error:", e)

        last_block = latest
        time.sleep(1)

def main():
    scan_historic()
    monitor_live()

if __name__ == "__main__":
    main()
