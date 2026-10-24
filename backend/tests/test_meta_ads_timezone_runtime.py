"""Provider time zones must resolve in the deployed slim Python image."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


@pytest.mark.parametrize("name", ["Europe/Kiev", "Europe/Kyiv", "America/Chicago"])
def test_meta_ad_account_timezone_is_available(name):
    assert datetime(2026, 10, 23, tzinfo=ZoneInfo(name)).utcoffset() is not None


def test_meta_legacy_kyiv_timezone_preserves_dst_offsets():
    for month in (1, 7, 10):
        day = datetime(2026, month, 23)
        assert day.replace(tzinfo=ZoneInfo("Europe/Kiev")).utcoffset() == day.replace(tzinfo=ZoneInfo("Europe/Kyiv")).utcoffset()
