"""Core event and profile models. Contract defined in docs/DATA_MODEL.md."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    field_validator,
    model_validator,
)

# Hard upper bound in minor units of the original currency (ADR-006).
MAX_AMOUNT_MINOR = 10_000_000_000

AmountMinor = Annotated[int, Field(strict=True, gt=0, le=MAX_AMOUNT_MINOR)]
AccountId = Annotated[str, Field(pattern=r"^acc_\d{6}$")]
CountryCode = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]


class Currency(StrEnum):
    NGN = "NGN"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"


class Channel(StrEnum):
    CARD_PRESENT = "card_present"
    CARD_ONLINE = "card_online"
    TRANSFER = "transfer"
    USSD = "ussd"


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


class _Frozen(BaseModel):
    """Base: unknown fields are errors, instances are immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Geo(_Frozen):
    country: CountryCode
    city: str = Field(min_length=1, max_length=64)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class TransactionEvent(_Frozen):
    txn_id: UUID
    occurred_at: AwareDatetime
    account_id: AccountId
    amount_minor: AmountMinor
    currency: Currency
    merchant_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    merchant_category: str = Field(pattern=r"^\d{4}$")
    channel: Channel
    ip: IPvAnyAddress | None = None
    geo: Geo
    device_id: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("occurred_at")
    @classmethod
    def _occurred_at_utc(cls, value: datetime) -> datetime:
        return _to_utc(value)

    @model_validator(mode="after")
    def _physical_channels_have_no_ip_or_device(self) -> "TransactionEvent":
        physical = self.channel in (Channel.CARD_PRESENT, Channel.USSD)
        if physical and (self.ip is not None or self.device_id is not None):
            raise ValueError(f"{self.channel.value} events must not carry ip or device_id")
        return self


class AccountProfile(_Frozen):
    """Bank-visible fields only. Generator internals never live here."""

    account_id: AccountId
    created_at: AwareDatetime
    home_country: CountryCode
    home_city: str = Field(min_length=1, max_length=64)
    home_lat: float = Field(ge=-90, le=90)
    home_lon: float = Field(ge=-180, le=180)
    home_tz: str = Field(min_length=1, max_length=64)

    @field_validator("created_at")
    @classmethod
    def _created_at_utc(cls, value: datetime) -> datetime:
        return _to_utc(value)

    @field_validator("home_tz")
    @classmethod
    def _home_tz_is_real(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (KeyError, ValueError, OSError) as exc:
            raise ValueError("unknown IANA timezone") from exc
        return value
