"""Static FX table (ADR-008). Rates are illustrative constants, fixed for reproducibility."""

from types import MappingProxyType

from fraudsvc.core.models import Currency

FX_VERSION = "fx-2026-10-static"

# NGN per 1 unit of each currency. Every supported currency has 2 decimal places, so the
# minor-unit ratio equals the major-unit ratio. A 0-decimal currency would need scaling.
FX_TO_NGN = MappingProxyType(
    {
        Currency.NGN: 1,
        Currency.USD: 1500,
        Currency.GBP: 1900,
        Currency.EUR: 1650,
    }
)


def to_ngn_minor(amount_minor: int, currency: Currency) -> int:
    """Convert an amount in the currency's minor units to NGN kobo."""
    return amount_minor * FX_TO_NGN[currency]
