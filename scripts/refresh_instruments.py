"""Refresh `instruments` collection from the NSE EQUITY_L.csv master.

Delegates to app.services.instrument_service.refresh_from_nse, which
downloads the official NSE master CSV and upserts the instruments
collection.

Run on demand:

    PYTHONPATH=. uv run python scripts/refresh_instruments.py

Or via cron on EC2 (daily at 3 AM IST):

    0 3 * * *  cd /home/ubuntu/ai-stock-advisor-backend && \\
               /home/ubuntu/.local/bin/uv run python scripts/refresh_instruments.py \\
               >> /home/ubuntu/cron-instruments.log 2>&1
"""

import logging
import sys

from app.services.cron_heartbeat_service import cron_run
from app.services.instrument_service import refresh_from_nse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> int:
    try:
        with cron_run("refresh_instruments") as hb:
            result = refresh_from_nse()
            hb.metadata["result"] = result
            print(f"\nRefresh result: {result}")
            if result.get("status") == "ok":
                print("✓ Success")
                return 0
            print("⚠️  Refresh did not complete cleanly")
            hb.status = "failure"
            hb.error = f"refresh_from_nse status={result.get('status')!r}"
            return 1
    except Exception:
        logging.exception("Instruments refresh failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())
