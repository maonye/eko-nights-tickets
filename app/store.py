"""Storage for events, tiers, orders and tickets.

Two backends share one small interface:

* SheetsStore: a Google Sheet the organiser can open and watch in real time.
* MemoryStore: the same tables in memory, for local development and tests.

Every value is stored as a string so both backends behave the same way;
the service layer does the parsing.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Iterable, Protocol

TABLES: dict[str, list[str]] = {
    "events": ["event_id", "name", "venue", "starts_at", "doors_open", "organiser",
               "verified", "on_sale", "age_limit", "description"],
    "tiers": ["tier_id", "event_id", "name", "price_ngn", "capacity", "max_per_order", "perks"],
    "orders": ["order_id", "reference", "event_id", "tier_id", "quantity", "buyer_phone",
               "buyer_email", "recipients_json", "amount_kobo", "status", "paystack_status",
               "payment_url", "created_at", "expires_at", "paid_at", "note"],
    "tickets": ["ticket_id", "code", "order_id", "event_id", "tier_id", "holder_phone",
                "holder_name", "status", "issued_at", "checked_in_at"],
}

# Reference data changes rarely, so cache it briefly to stay inside Sheets API quotas.
CACHED_TABLES = {"events", "tiers"}
CACHE_SECONDS = 30


class Store(Protocol):
    def all(self, table: str) -> list[dict]: ...
    def append(self, table: str, row: dict) -> None: ...
    def append_many(self, table: str, rows: Iterable[dict]) -> None: ...
    def update(self, table: str, key_field: str, key: str, changes: dict) -> None: ...


def _clean(table: str, row: dict) -> dict:
    cols = TABLES[table]
    unknown = set(row) - set(cols)
    if unknown:
        raise KeyError(f"Unknown columns for {table}: {sorted(unknown)}")
    return {c: "" if row.get(c) is None else str(row.get(c)) for c in cols}


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, list[dict]] = {t: [] for t in TABLES}
        self._lock = threading.Lock()

    def all(self, table: str) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._data[table]]

    def append(self, table: str, row: dict) -> None:
        self.append_many(table, [row])

    def append_many(self, table: str, rows: Iterable[dict]) -> None:
        with self._lock:
            self._data[table].extend(_clean(table, r) for r in rows)

    def update(self, table: str, key_field: str, key: str, changes: dict) -> None:
        with self._lock:
            for r in self._data[table]:
                if r[key_field] == key:
                    for k, v in changes.items():
                        if k not in TABLES[table]:
                            raise KeyError(k)
                        r[k] = "" if v is None else str(v)
                    return
        raise KeyError(f"{table}: no row with {key_field}={key}")


class SheetsStore:
    """Google Sheets backend. One worksheet (tab) per table, header in row 1."""

    def __init__(self, sheet_id: str, service_account_json: str) -> None:
        import gspread  # imported here so tests do not need Google credentials

        if service_account_json.strip().startswith("{"):
            info = json.loads(service_account_json)
            client = gspread.service_account_from_dict(info)
        elif service_account_json and os.path.exists(service_account_json):
            client = gspread.service_account(filename=service_account_json)
        else:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON must be the key JSON or a path to it")
        self._book = client.open_by_key(sheet_id)
        self._ws = {}
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._lock = threading.Lock()

    def worksheet(self, table: str):
        if table not in self._ws:
            self._ws[table] = self._book.worksheet(table)
        return self._ws[table]

    def all(self, table: str) -> list[dict]:
        if table in CACHED_TABLES:
            hit = self._cache.get(table)
            if hit and time.time() - hit[0] < CACHE_SECONDS:
                return [dict(r) for r in hit[1]]
        rows = self.worksheet(table).get_all_records(
            numericise_ignore=["all"], expected_headers=TABLES[table]
        )
        rows = [{c: str(r.get(c, "")) for c in TABLES[table]} for r in rows]
        if table in CACHED_TABLES:
            self._cache[table] = (time.time(), rows)
        return [dict(r) for r in rows]

    def append(self, table: str, row: dict) -> None:
        self.append_many(table, [row])

    def append_many(self, table: str, rows: Iterable[dict]) -> None:
        cleaned = [_clean(table, r) for r in rows]
        if not cleaned:
            return
        values = [[r[c] for c in TABLES[table]] for r in cleaned]
        with self._lock:
            # RAW keeps "+234..." and codes as plain text instead of formulas.
            self.worksheet(table).append_rows(values, value_input_option="RAW")
            self._cache.pop(table, None)

    def update(self, table: str, key_field: str, key: str, changes: dict) -> None:
        ws = self.worksheet(table)
        cols = TABLES[table]
        with self._lock:
            key_col = cols.index(key_field) + 1
            column_values = ws.col_values(key_col)
            try:
                row_number = column_values.index(key) + 1
            except ValueError:
                raise KeyError(f"{table}: no row with {key_field}={key}") from None
            cells = []
            import gspread
            for k, v in changes.items():
                cells.append(gspread.Cell(row_number, cols.index(k) + 1, "" if v is None else str(v)))
            ws.update_cells(cells, value_input_option="RAW")
            self._cache.pop(table, None)


def build_store(settings) -> Store:
    if settings.store_backend == "memory":
        from .seed import seed_memory
        store = MemoryStore()
        seed_memory(store)
        return store
    if settings.store_backend == "sheets":
        return SheetsStore(settings.google_sheet_id, settings.google_service_account_json)
    raise RuntimeError(f"Unknown STORE_BACKEND {settings.store_backend}")
