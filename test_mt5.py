# === test_mt5.py (secure version) ===
import MetaTrader5 as mt5
from config import MT5_CREDENTIALS

print("🔐 Using credentials from config.py (environment variables)...")

connected = mt5.initialize(
    login=MT5_CREDENTIALS["login"],
    password=MT5_CREDENTIALS["password"],
    server=MT5_CREDENTIALS["server"]
)

print("Connected?", connected)
print("Error:", mt5.last_error())

if connected:
    info = mt5.account_info()
    print("✅ Connected successfully!")
    print(f"Balance: {info.balance}")
    print(f"Equity: {info.equity}")
    print(f"Leverage: {info.leverage}")
    print(f"Account Name: {info.name}")
    print(f"Account Currency: {info.currency}")

mt5.shutdown()
