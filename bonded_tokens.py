
import asyncio
import aiohttp
import time
from datetime import datetime
import logging

# --- CONFIG ---
MOONSHOT_DEPLOYER = "0x0D6848e39114abE69054407452b8aaB82f8a44BA".lower()
ABSCAN_API = "https://api.abscan.io/api"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/pairs/abstract"
SCAN_INTERVAL = 1  # seconds
FDV_THRESHOLD = 4000

# --- SETUP LOGGER ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# --- HELPERS ---
async def fetch_json(session, url):
    async with session.get(url) as resp:
        return await resp.json()

async def get_recent_moonshot_creations(session):
    url = f"{ABSCAN_API}?module=account&action=txlist&address={MOONSHOT_DEPLOYER}&sort=desc"
    data = await fetch_json(session, url)
    txs = data.get("result", [])
    token_creations = [tx for tx in txs if tx.get("functionName", "").lower().startswith("creat") and tx.get("contractAddress")]
    return token_creations

async def check_dexscreener_for_token(session, token_address):
    url = f"{DEXSCREENER_API}/{token_address}?chain=abstract"
    data = await fetch_json(session, url)
    pair = data.get("pair", {})
    if not pair:
        return False
    fdv = float(pair.get("fdv", 0)) / 1e18
    return fdv >= FDV_THRESHOLD

# --- MAIN ---
async def main():
    seen_tokens = set()
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                creations = await get_recent_moonshot_creations(session)
                for tx in creations:
                    contract = tx["contractAddress"]
                    if contract not in seen_tokens:
                        seen_tokens.add(contract)
                        logging.info(f"[TRACKING] New token created: {contract}")
                        bonded = await check_dexscreener_for_token(session, contract)
                        if bonded:
                            logging.info(f"[BONDED] {contract} has crossed ${FDV_THRESHOLD} FDV!")
            except Exception as e:
                logging.error(f"[ERROR] {e}")
            await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
