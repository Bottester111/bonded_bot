
import asyncio
import aiohttp
import time
from datetime import datetime
import os
import json

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

seen_contracts = set()
contract_deploy_times = {}

async def fetch_json(session, url):
    async with session.get(url) as response:
        return await response.json()

async def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload)

async def get_token_data(session, contract):
    abscan_url = f"https://api.abscan.io/api?module=token&action=tokeninfo&contractaddress={contract}"
    data = await fetch_json(session, abscan_url)
    return data.get("result", {})

async def get_holder_count(session, contract):
    url = f"https://api.abscan.io/api?module=token&action=tokenholdercount&contractaddress={contract}"
    data = await fetch_json(session, url)
    return int(data.get("result", 0))

async def track_tokens():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                url = "https://api.abscan.io/api?module=token&action=recenttokens"
                data = await fetch_json(session, url)

                for entry in data.get("result", []):
                    contract = entry.get("contractAddress")
                    fdv = float(entry.get("fdv", 0))
                    name = entry.get("name", "Unknown")
                    deploy_time_unix = int(entry.get("timeStamp", time.time()))
                    deployed_time = datetime.utcfromtimestamp(deploy_time_unix).strftime('%Y-%m-%d %H:%M:%S UTC')
                    bond_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

                    if contract in seen_contracts:
                        continue

                    if fdv >= 4000:
                        seen_contracts.add(contract)

                        time_to_bond = str(datetime.utcnow() - datetime.utcfromtimestamp(deploy_time_unix)).split('.')[0]
                        holder_count = await get_holder_count(session, contract)

                        message = (
                            f"🚀 *{name}* just bonded!

"
                            f"🔹 *Contract:* `{contract}`
"
                            f"🔹 *FDV:* ${int(fdv):,}
"
                            f"🔹 *Holders:* {holder_count}
"
                            f"🔹 *Deployed:* {deployed_time}
"
                            f"🔹 *Bonded:* {bond_time}
"
                            f"⏱️ *Time to Bond:* {time_to_bond}

"
                            f"📎 [View on Abscan](https://abscan.org/token/{contract})"
                        )

                        await send_telegram_message(message)

            except Exception as e:
                print(f"Error: {e}")

            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(track_tokens())
