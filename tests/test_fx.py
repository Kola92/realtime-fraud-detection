import pytest

from fraudsvc.core.fx import FX_TO_NGN, FX_VERSION, to_ngn_minor
from fraudsvc.core.models import Currency


def test_ngn_is_identity():
    assert to_ngn_minor(12345, Currency.NGN) == 12345


def test_usd_converts_to_naira_kobo():
    # USD 100.00 = 10,000 cents -> NGN 150,000.00 = 15,000,000 kobo
    assert to_ngn_minor(10_000, Currency.USD) == 15_000_000


def test_every_currency_has_a_rate():
    assert set(FX_TO_NGN) == set(Currency)


def test_rates_are_positive_integers():
    assert all(isinstance(r, int) and r > 0 for r in FX_TO_NGN.values())


def test_version_is_set():
    assert FX_VERSION


def test_table_is_read_only():
    with pytest.raises(TypeError):
        FX_TO_NGN[Currency.USD] = 1  # type: ignore[index]
