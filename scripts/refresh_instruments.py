"""Refresh `instruments` collection from Zerodha Kite.

Run on demand:
    PYTHONPATH=. uv run python scripts/refresh_instruments.py

Or via cron on EC2 (daily at 3 AM IST):
    0 3 * * *  cd /home/ubuntu/ai-stock-advisor && \\
               /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py \\
               >> /home/ubuntu/instruments-refresh.log 2>&1
"""

import logging
import sys

from app.services.instrument_service import refresh_from_nse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> int:
    try:
        result = refresh_from_nse()
        print(f"\nRefresh result: {result}")
        if result.get("status") == "ok":
            print("✅ Success")
            return 0
        print("⚠️  Refresh did not complete cleanly")
        return 1
    except Exception:
        logging.exception("Instruments refresh failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())
