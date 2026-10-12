from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from fraudsvc.core.models import AccountProfile, TransactionEvent


def event_data(**overrides):
    data = {
        "txn_id": "3f2b8c1e-5a4d-4b7e-9c1a-2d6e8f0a1b3c",
        "occurred_at": datetime(2026, 10, 9, 10, 0, tzinfo=UTC),
        "account_id": "acc_000123",
        "amount_minor": 1_500_000,
        "currency": "NGN",
        "merchant_id": "mch_shoprite_ikeja",
        "merchant_category": "5411",
        "channel": "card_online",
        "ip": "102.89.12.34",
        "geo": {"country": "NG", "city": "Lagos", "lat": 6.5244, "lon": 3.3792},
        "device_id": "dev_a1b2c3",
    }
    data.update(overrides)
    return data


def profile_data(**overrides):
    data = {
        "account_id": "acc_000123",
        "created_at": datetime(2025, 3, 1, tzinfo=UTC),
        "home_country": "NG",
        "home_city": "Lagos",
        "home_lat": 6.5244,
        "home_lon": 3.3792,
        "home_tz": "Africa/Lagos",
    }
    data.update(overrides)
    return data


def test_valid_event_parses():
    event = TransactionEvent(**event_data())
    assert event.amount_minor == 1_500_000


def test_unknown_field_is_rejected_so_labels_cannot_leak():
    with pytest.raises(ValidationError):
        TransactionEvent(**event_data(fraud_label="takeover"))


@pytest.mark.parametrize("bad", [100.5, 1_500_000.0, "1500000"])
def test_money_must_be_a_strict_integer(bad):
    with pytest.raises(ValidationError):
        TransactionEvent(**event_data(amount_minor=bad))


@pytest.mark.parametrize("bad", [0, -1, 10_000_000_001])
def test_amount_bounds(bad):
    with pytest.raises(ValidationError):
        TransactionEvent(**event_data(amount_minor=bad))


def test_naive_datetime_is_rejected():
    with pytest.raises(ValidationError):
        TransactionEvent(**event_data(occurred_at=datetime(2026, 10, 9, 10, 0)))  # noqa: DTZ001 - naive on purpose


def test_offset_datetime_is_normalized_to_utc():
    local = datetime(2026, 10, 9, 11, 0, tzinfo=timezone(timedelta(hours=1)))
    event = TransactionEvent(**event_data(occurred_at=local))
    assert event.occurred_at.utcoffset() == timedelta(0)
    assert event.occurred_at.hour == 10


@pytest.mark.parametrize("channel", ["card_present", "ussd"])
def test_physical_channels_reject_ip_and_device(channel):
    with pytest.raises(ValidationError):
        TransactionEvent(**event_data(channel=channel))


def test_physical_channel_without_ip_or_device_is_valid():
    event = TransactionEvent(**event_data(channel="ussd", ip=None, device_id=None))
    assert event.ip is None


@pytest.mark.parametrize("bad", ["acc_12", "ACC_000123", "acc_00012a", "x"])
def test_bad_account_id_is_rejected(bad):
    with pytest.raises(ValidationError):
        TransactionEvent(**event_data(account_id=bad))


def test_latitude_out_of_range_is_rejected():
    geo = {"country": "NG", "city": "Lagos", "lat": 95.0, "lon": 3.3}
    with pytest.raises(ValidationError):
        TransactionEvent(**event_data(geo=geo))


def test_json_round_trip():
    event = TransactionEvent(**event_data())
    assert TransactionEvent.model_validate_json(event.model_dump_json()) == event


def test_events_are_immutable():
    event = TransactionEvent(**event_data())
    with pytest.raises(ValidationError):
        event.amount_minor = 1


def test_valid_profile_parses():
    assert AccountProfile(**profile_data()).home_tz == "Africa/Lagos"


@pytest.mark.parametrize("bad", ["Mars/Phobos", "../etc/passwd", "Africa"])
def test_profile_rejects_unknown_timezones(bad):
    with pytest.raises(ValidationError):
        AccountProfile(**profile_data(home_tz=bad))
