"""Create the four tabs in your Google Sheet and load the made-up Eko Nights data.

Usage:
  export GOOGLE_SHEET_ID=...            # from the sheet URL
  export GOOGLE_SERVICE_ACCOUNT_JSON=path/to/key.json
  python scripts/seed_sheet.py           # add --reset to wipe and reseed

Share the sheet with the service account's client_email (Editor) first.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread  # noqa: E402

from app.seed import EVENTS, TIERS  # noqa: E402
from app.store import TABLES  # noqa: E402


def main(reset: bool) -> None:
    key = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    client = gspread.service_account(filename=key) if os.path.exists(key) else \
        gspread.service_account_from_dict(__import__("json").loads(key))
    book = client.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    existing = {ws.title: ws for ws in book.worksheets()}
    seed = {"events": EVENTS, "tiers": TIERS}

    for table, cols in TABLES.items():
        ws = existing.get(table)
        if ws and reset:
            ws.clear()
        if not ws:
            ws = book.add_worksheet(title=table, rows=1000, cols=len(cols))
        if not ws.row_values(1):
            ws.update([cols], "A1", value_input_option="RAW")
            ws.freeze(rows=1)
            rows = [[r.get(c, "") for c in cols] for r in seed.get(table, [])]
            if rows:
                ws.append_rows(rows, value_input_option="RAW")
        print(f"{table}: ready")

    if "Sheet1" in existing and len(existing) == 1:
        book.del_worksheet(existing["Sheet1"])
    print("Done. Open the sheet to watch orders and tickets arrive.")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
