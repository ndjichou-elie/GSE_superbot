# === log.py ===
from datetime import datetime

def log(message: str):
    """Unified logging function with timestamp."""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {message}")
