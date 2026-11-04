"""Thin Paystack client (test mode) plus a fake for offline tests.

Endpoints used:
  POST https://api.paystack.co/transaction/initialize
  GET  https://api.paystack.co/transaction/verify/:reference
Webhook signatures are HMAC SHA512 of the raw body, keyed with the secret key.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field

import httpx

PAYSTACK_BASE = "https://api.paystack.co"


class PaystackError(Exception):
    """The provider could not be reached or returned something unusable."""


@dataclass
class VerifyResult:
    status: str            # success, failed, abandoned, ongoing, pending, processing, queued, reversed
    amount_kobo: int
    currency: str
    gateway_response: str = ""
    paid_at: str = ""


class PaystackClient:
    def __init__(self, secret_key: str, timeout: float = 15.0) -> None:
        self._secret = secret_key
        self._client = httpx.Client(
            base_url=PAYSTACK_BASE,
            timeout=timeout,
            headers={"Authorization": f"Bearer {secret_key}", "Content-Type": "application/json"},
        )

    def _call(self, method: str, path: str, **kwargs) -> dict:
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise PaystackError(f"Could not reach Paystack: {exc.__class__.__name__}") from exc
        try:
            body = resp.json()
        except ValueError:
            raise PaystackError(f"Paystack returned non-JSON (HTTP {resp.status_code})") from None
        if resp.status_code >= 400 or not body.get("status"):
            raise PaystackError(f"Paystack error (HTTP {resp.status_code}): {body.get('message', 'no message')}")
        if not body.get("data"):
            raise PaystackError("Paystack returned an empty data object")
        return body["data"]

    def initialize(self, *, email: str, amount_kobo: int, reference: str, callback_url: str,
                   metadata: dict, currency: str = "NGN") -> str:
        data = self._call("POST", "/transaction/initialize", json={
            "email": email, "amount": amount_kobo, "reference": reference,
            "currency": currency, "callback_url": callback_url, "metadata": metadata,
        })
        url = data.get("authorization_url")
        if not url:
            raise PaystackError("Paystack did not return an authorization_url")
        return url

    def verify(self, reference: str) -> VerifyResult:
        data = self._call("GET", f"/transaction/verify/{reference}")
        return VerifyResult(
            status=str(data.get("status", "")).lower(),
            amount_kobo=int(data.get("amount") or 0),
            currency=str(data.get("currency", "")),
            gateway_response=str(data.get("gateway_response", "")),
            paid_at=str(data.get("paid_at") or ""),
        )

    def valid_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature:
            return False
        expected = hmac.new(self._secret.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature)


@dataclass
class FakePaystack:
    """Deterministic stand-in used by tests and the offline dev mode."""
    outcomes: dict = field(default_factory=dict)    # reference -> VerifyResult
    initialized: dict = field(default_factory=dict) # reference -> amount_kobo
    fail_initialize: bool = False
    fail_verify: bool = False
    secret: str = "sk_test_fake"

    def initialize(self, *, email, amount_kobo, reference, callback_url, metadata, currency="NGN") -> str:
        if self.fail_initialize:
            raise PaystackError("Simulated Paystack outage")
        self.initialized[reference] = amount_kobo
        # Real Paystack URLs end with an access code, not the merchant reference. Mirror that
        # here so the agent/model cannot learn to extract the reference from the URL path.
        access_code = "PAY_" + secrets.token_hex(8).upper()
        _ = metadata
        return (
            f"https://checkout.paystack.test/{access_code}"
            f"?email={email}&amount_kobo={amount_kobo}&currency={currency}"
            f"&callback={callback_url}&reference={reference}"
        )

    def verify(self, reference: str) -> VerifyResult:
        if self.fail_verify:
            raise PaystackError("Simulated Paystack outage")
        if reference not in self.initialized:
            raise PaystackError("Transaction reference not found")
        return self.outcomes.get(reference) or VerifyResult("abandoned", self.initialized[reference], "NGN")

    def pay(self, reference: str, status: str = "success", amount_kobo: int | None = None) -> None:
        amount = self.initialized[reference] if amount_kobo is None else amount_kobo
        self.outcomes[reference] = VerifyResult(status, amount, "NGN", paid_at="2026-11-01T12:00:00Z")

    def valid_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature:
            return False
        expected = hmac.new(self.secret.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature)
