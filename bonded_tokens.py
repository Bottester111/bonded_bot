import time
import requests
import os
from telegram import Bot
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

print("🔧 Bonded bot is starting...")

posted_tokens = set()

def get_token_data():
    try:
        response = requests.get("https://api.dexscreener.com/latest/dex/search/?q=abstract")
        if response.status_code == 200:
            all_tokens = response.json().get("pairs", [])
            moonshot_tokens = [
                token for token in all_tokens
                if "moonshot" in token.get("url", "").lower() and token.get("marketCap", 0) >= 5000
            ]
            return moonshot_tokens
        return []
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def format_token_message(token):
    name = token.get("baseToken", {}).get("name", "Unknown")
    symbol = token.get("baseToken", {}).get("symbol", "Unknown")
    address = token.get("pairAddress", "N/A")
    price = token.get("priceUsd", "N/A")
    market_cap = token.get("fdv", "N/A")
    liquidity = token.get("liquidity", {}).get("usd", "N/A")
    volume = token.get("volume", {}).get("h24", "N/A")
    created_at = token.get("pairCreatedAt", None)
    ds_link = f"https://dexscreener.com/abstract/{address}"
    
    # Time since launch
    try:
        minutes_since_launch = int((time.time() - created_at) / 60)
        age = f"{minutes_since_launch // 60}h{minutes_since_launch % 60}m"
    except:
        age = "N/A"

    tax_warning = ""
    try:
        tax_data = requests.get(f"https://api.definder.tools/taxCheck?network=abstract&address={address}").json()
        buy_tax = tax_data.get("buyTax", 0)
        sell_tax = tax_data.get("sellTax", 0)
        if buy_tax > 10 or sell_tax > 10:
            tax_warning = f"\n⚠️ Tax Alert: Buy {buy_tax}%, Sell {sell_tax}%"
    except:
        pass

    return f"""🚀 ${symbol} Bonded
• Name: {name}
• CA: {address}
• 🔗 DS - ({ds_link})
• 💸 Price: ${price}
• 💰 FDV: ${market_cap}
• 💵 Liquidity: ${liquidity}
• ⏳ Pair Age: {age}
• 📊 Volume (24h): ${volume}{tax_warning}
"""

def check_new_bonds():
    global posted_tokens
    tokens = get_token_data()
    for token in tokens:
        try:
            address = token.get("pairAddress")
            market_cap = float(token.get("fdv", 0))
            if address not in posted_tokens and market_cap >= 46000:
                message = format_token_message(token)
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                posted_tokens.add(address)
                print(f"Posted ${token.get('baseToken', {}).get('symbol', '')}")
        except Exception as e:
            print(f"Error processing token: {e}")

while True:
    check_new_bonds()
    time.sleep(1)