import pytest

from parse_int import parse_uint16


def test_valid():
    assert parse_uint16("0") == 0
    assert parse_uint16("65535") == 65535
    assert parse_uint16("1234") == 1234


def test_negative_raises():
    with pytest.raises(ValueError):
        parse_uint16("-1")


def test_too_large_raises():
    with pytest.raises(ValueError):
        parse_uint16("65536")
    with pytest.raises(ValueError):
        parse_uint16("100000")


def test_non_numeric_raises():
    with pytest.raises(ValueError):
        parse_uint16("nope")
