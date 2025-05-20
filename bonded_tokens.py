
import time
import requests
from datetime import datetime
from telegram import Bot

# --- CONFIG ---
FDV_THRESHOLD = 4000
DEPLOYER_ADDRESS = "0xYOUR_DEPLOYER"
TOKEN = "7681851699:AAH5tosSVfN7jQnaZXj8_hWY7XWsXWjQ0os"
CHAT_ID = "-1002614749658"
SCAN_INTERVAL = 1  # seconds

bot = Bot(token=TOKEN)
seen_alerts = set()
tracked_tokens = {}

def fetch_deployments():
    response = requests.get(f"https://api.abscan.io/api?module=account&action=txlist&address={DEPLOYER_ADDRESS}&sort=desc")
    result = response.json().get("result", [])
    return [tx for tx in result if tx["to"] == ""]

def fetch_token_info(contract):
    try:
        url = f"https://api.abscan.io/api?module=token&action=tokeninfo&contractaddress={contract}"
        response = requests.get(url)
        data = response.json().get("result", {})
        fdv = float(data.get("fdv", 0))
        name = data.get("name", "Unknown")
        holders = data.get("holders", "Unknown")
        return fdv, name, holders
    except:
        return 0, "Unknown", "Unknown"

def get_human_timestamp(unix):
    return datetime.utcfromtimestamp(int(unix)).strftime("%Y-%m-%d %H:%M:%S")

def alert(contract, fdv, name, holders, deployed_time, hit_time):
    time_to_bond = hit_time - deployed_time
    msg = (
        f"🚀 *{name}* just bonded!

"
        f"*Contract:* `{contract}`
"
        f"*FDV:* ${int(fdv):,}
"
        f"*Holders:* {holders}
"
        f"*Deployed:* {deployed_time.strftime('%Y-%m-%d %H:%M:%S')}
"
        f"*Hit FDV:* {hit_time.strftime('%Y-%m-%d %H:%M:%S')}
"
        f"*Time to Bond:* {str(time_to_bond)}
"
        f"[View on Abscan](https://abscan.org/token/{contract})"
    )
    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")

while True:
    try:
        txs = fetch_deployments()
        for tx in txs:
            contract = tx["contractAddress"] if "contractAddress" in tx else tx["hash"]
            if contract not in tracked_tokens:
                tracked_tokens[contract] = int(tx["timeStamp"])

        now = datetime.utcnow()
        for contract, deploy_ts in tracked_tokens.items():
            if contract in seen_alerts:
                continue
            fdv, name, holders = fetch_token_info(contract)
            if fdv >= FDV_THRESHOLD:
                deployed_time = datetime.utcfromtimestamp(deploy_ts)
                alert(contract, fdv, name, holders, deployed_time, now)
                seen_alerts.add(contract)
        time.sleep(SCAN_INTERVAL)
    except Exception as e:
        print(f"[ERROR] {e}")
        time.sleep(5)
