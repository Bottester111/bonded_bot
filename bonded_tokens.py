
import time
from datetime import datetime

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
    print(message)  # Replace with actual Telegram send

# Example usage
send_alert(
    name="TestToken",
    contract="0x1234567890abcdef1234567890abcdef12345678",
    fdv=4200,
    deployed_time=int(time.time()) - 600,
    bonded_time=int(time.time()),
    holders=123
)
