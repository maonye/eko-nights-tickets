import pytest

from app.phone import InvalidPhone, mask_phone, normalise_phone


@pytest.mark.parametrize("raw", ["08031234567", "0803 123 4567", "+2348031234567", "2348031234567",
                                 "8031234567", "00234 803 123 4567", "+234 (803) 123-4567"])
def test_nigerian_formats(raw):
    assert normalise_phone(raw) == "+2348031234567"


def test_uk_number_with_plus():
    assert normalise_phone("+44 7700 900123") == "+447700900123"


@pytest.mark.parametrize("raw", ["", "12345", "01234567890", "hello", "+1"])
def test_invalid(raw):
    with pytest.raises(InvalidPhone):
        normalise_phone(raw)


def test_mask():
    assert mask_phone("+2348031234567") == "+234 803 *** 4567"
