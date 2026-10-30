"""Runtime configuration, read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    store_backend: str                  # "sheets" or "memory"
    google_sheet_id: str
    google_service_account_json: str    # JSON contents, or a path to the JSON file
    paystack_secret_key: str
    paystack_mode: str                  # "paystack" (test-mode API) or "fake" (offline tests)
    allow_live_keys: bool
    mcp_bearer_token: str
    staff_pin: str
    public_base_url: str
    hold_minutes: int
    placeholder_email_domain: str
    currency: str = "NGN"

    @classmethod
    def from_env(cls) -> "Settings":
        s = cls(
            store_backend=os.getenv("STORE_BACKEND", "sheets").lower(),
            google_sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
            google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""),
            paystack_secret_key=os.getenv("PAYSTACK_SECRET_KEY", ""),
            paystack_mode=os.getenv("PAYSTACK_MODE", "paystack").lower(),
            allow_live_keys=_bool(os.getenv("ALLOW_LIVE_KEYS"), False),
            mcp_bearer_token=os.getenv("MCP_BEARER_TOKEN", ""),
            staff_pin=os.getenv("STAFF_PIN", ""),
            public_base_url=os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
            hold_minutes=int(os.getenv("HOLD_MINUTES", "15")),
            placeholder_email_domain=os.getenv("PLACEHOLDER_EMAIL_DOMAIN", "example.com"),
        )
        s.validate()
        return s

    def validate(self) -> None:
        if self.paystack_mode == "paystack":
            if not self.paystack_secret_key:
                raise RuntimeError("PAYSTACK_SECRET_KEY is required when PAYSTACK_MODE=paystack")
            # Ground rule for the exercise: test keys only.
            if self.paystack_secret_key.startswith("sk_live_") and not self.allow_live_keys:
                raise RuntimeError("Refusing to start with a live Paystack key. Use an sk_test_ key.")
        if self.store_backend == "sheets" and not self.google_sheet_id:
            raise RuntimeError("GOOGLE_SHEET_ID is required when STORE_BACKEND=sheets")
        if not self.staff_pin:
            raise RuntimeError("STAFF_PIN is required so gate check-in cannot be used by customers")
