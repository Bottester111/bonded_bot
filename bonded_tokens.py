
import asyncio
import aiohttp
from datetime import datetime
import logging

TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"
MOONSHOT_DEPLOYER = "0xf4937e578d14ee1943361fd5c966542070f6595f"
FDV_THRESHOLD = 4000  # $4K threshold
CHECK_INTERVAL = 1  # seconds

tracked_tokens = set()

logging.basicConfig(level=logging.INFO)

async def send_alert(token_address, fdv):
    from telegram import Bot
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    msg = f"🚀 Token {token_address} just hit ${fdv:,} FDV!"
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

async def fetch_deployer_txs(session):
    url = f"https://api.abscan.org/api?module=account&action=txlist&address={MOONSHOT_DEPLOYER}&sort=desc"
    async with session.get(url) as res:
        data = await res.json()
        return data.get("result", [])

async def get_fdv(token_address):
    url = f"https://api.dexscreener.io/latest/dex/pairs/abstract/{token_address}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as res:
                if res.status != 200:
                    return 0
                data = await res.json()
                return float(data.get("pair", {}).get("fdv", 0))
        except:
            return 0

async def monitor_token(token_address):
    while True:
        fdv = await get_fdv(token_address)
        if fdv >= FDV_THRESHOLD:
            await send_alert(token_address, fdv)
            return
        await asyncio.sleep(CHECK_INTERVAL)

async def main():
    async with aiohttp.ClientSession() as session:
        while True:
            txs = await fetch_deployer_txs(session)
            for tx in txs:
                contract = tx.get("contractAddress")
                if contract and contract not in tracked_tokens:
                    tracked_tokens.add(contract)
                    logging.info(f"[TRACKING] {contract}")
                    asyncio.create_task(monitor_token(contract))
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
