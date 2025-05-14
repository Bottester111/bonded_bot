
import time
import requests

def main():
    print("🔧 Bonded bot is starting...")
    while True:
        try:
            response = requests.get("https://api.dexscreener.com/latest/dex/search/?q=abstract")
            data = response.json()

            tokens = data.get("pairs", [])
            print(f"🔍 Checking {len(tokens)} tokens from Dexscreener...")

            for token in tokens:
                name = token.get("baseToken", {}).get("name", "Unknown")
                symbol = token.get("baseToken", {}).get("symbol", "???")
                fdv = token.get("fdv", 0)
                url = token.get("url", "")

                if not url.startswith("https://dexscreener.com/moonshot"):
                    continue

                print(f"- {name} ({symbol}): FDV = ${fdv:,}", end=" ")

                if fdv and fdv >= 5000:
                    print("✅ PASSED — sending alert")
                    print(f"🔔 {name} ({symbol}) has FDV ${fdv:,} — {url}")
                    # Placeholder for Telegram alert logic
                else:
                    print("❌ Below threshold")

            print("⏱ Sleeping for 5 seconds...\n")
            time.sleep(5)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
