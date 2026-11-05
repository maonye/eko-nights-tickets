from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.paystack import FakePaystack
from app.seed import seed_memory
from app.service import TicketService
from app.store import MemoryStore


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, minutes):
        self.now += timedelta(minutes=minutes)


def make_settings(**over):
    base = dict(store_backend="memory", google_sheet_id="", google_service_account_json="",
                paystack_secret_key="sk_test_fake", paystack_mode="fake", allow_live_keys=False,
                mcp_bearer_token="secret-token", staff_pin="0604", public_base_url="https://tix.example",
                hold_minutes=15, placeholder_email_domain="example.com")
    base.update(over)
    return Settings(**base)


@pytest.fixture
def env():
    store = MemoryStore()
    seed_memory(store)
    clock = Clock()
    ps = FakePaystack()
    svc = TicketService(store, ps, make_settings(), clock=clock)
    return svc, ps, clock, store


BUYER = "0803 123 4567"
FRIEND = "+234 812 000 1111"
SIS = "07011112222"
