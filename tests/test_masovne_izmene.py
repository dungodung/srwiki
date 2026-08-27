import datetime

import pytest

from app.tools.masovne_izmene import parse_start


def test_parse_start_valid():
    assert parse_start("2026-08-20T14:30") == datetime.datetime(2026, 8, 20, 14, 30)


def test_parse_start_invalid_raises():
    with pytest.raises(ValueError):
        parse_start("not-a-date")
