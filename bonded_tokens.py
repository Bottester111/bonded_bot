
import time
import requests
from datetime import datetime

# === CONFIG ===
BOT_TOKEN = '7681851699:AAH5tosSVfN7jQnaZXj8_hWY7XWsXWjQ0os'
CHAT_ID = '-1002614749658'
FDV_THRESHOLD = 4000  # Alert when FDV crosses this

# === Token Store Simulation ===
tokens = [
    {
        "name": "TestToken1",
        "contract": "0xabc1...",
        "deployed_time": int(time.time()) - 120,
        "fdv": 2500,
        "holders": 100
    },
    {
        "name": "TestToken2",
        "contract": "0xabc2...",
        "deployed_time": int(time.time()) - 300,
        "fdv": 5000,
        "holders": 120
    }
]

alerted_contracts = set()

def send_alert(name, contract, fdv, deployed_time, bonded_time, holders):
    time_to_bond = bonded_time - deployed_time
    message = (
        f"🚀 *{name}* just bonded!\n"
        f"*Contract:* `{contract}`\n"
        f"*FDV:* ${int(fdv):,}\n"
        f"*Time Hit FDV:* {datetime.utcfromtimestamp(bonded_time).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"*Deployed:* {datetime.utcfromtimestamp(deployed_time).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"*Time to Bond:* {int(time_to_bond // 60)}m {int(time_to_bond % 60)}s\n"
        f"*Holders:* {holders}\n"
        f"[View on Abscan](https://abscan.org/token/{contract})"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    print(f"Sent alert for {name}: {response.status_code}")

def monitor_tokens():
    while True:
        for token in tokens:
            contract = token["contract"]
            if contract in alerted_contracts:
                continue

            fdv = token["fdv"]
            if fdv >= FDV_THRESHOLD:
                send_alert(
                    name=token["name"],
                    contract=contract,
                    fdv=fdv,
                    deployed_time=token["deployed_time"],
                    bonded_time=int(time.time()),
                    holders=token["holders"]
                )
                alerted_contracts.add(contract)

        time.sleep(10)

monitor_tokens()
