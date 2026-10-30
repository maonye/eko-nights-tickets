"""Phone number normalisation.

Nigerian numbers arrive in many shapes (0803..., 803..., 234803..., +234 803 ...).
Everything is stored in E.164 form, for example +2348031234567.
"""
from __future__ import annotations

import re

_NG_MOBILE_PREFIXES = ("70", "71", "80", "81", "90", "91")


class InvalidPhone(ValueError):
    pass


def normalise_phone(raw: str) -> str:
    if raw is None or not str(raw).strip():
        raise InvalidPhone("No phone number given")
    text = str(raw).strip()
    has_plus = text.startswith("+")
    digits = re.sub(r"\D", "", text)
    if text.startswith("00"):
        digits, has_plus = digits[2:], True

    # Nigerian formats
    national = None
    if digits.startswith("234") and len(digits) == 13:
        national = digits[3:]
    elif digits.startswith("0") and len(digits) == 11:
        national = digits[1:]
    elif len(digits) == 10 and not has_plus:
        national = digits

    if national is not None:
        if not national.startswith(_NG_MOBILE_PREFIXES):
            raise InvalidPhone(f"{raw} does not look like a Nigerian mobile number")
        return "+234" + national

    # Other countries: accept a plausible E.164 number given with + or 00.
    if has_plus and 8 <= len(digits) <= 15:
        return "+" + digits
    raise InvalidPhone(f"{raw} is not a valid phone number")


def mask_phone(e164: str) -> str:
    """+2348031234567 becomes +234 803 *** 4567."""
    if len(e164) < 8:
        return e164
    return f"{e164[:4]} {e164[4:7]} *** {e164[-4:]}"
