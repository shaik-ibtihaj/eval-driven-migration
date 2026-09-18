from decimal import Decimal

import pytest

from legacy_app.payment_provider import (
    DeterministicPaymentProvider,
    PaymentProviderUnavailable,
)


def test_provider_replays_without_a_second_call() -> None:
    provider = DeterministicPaymentProvider()

    first = provider.authorize(Decimal("19.90"), "USD", "order-1")
    second = provider.authorize(Decimal("19.90"), "USD", "order-1")

    assert first == second
    assert first.status == "authorized"
    assert provider.calls == [("authorize", "19.90", "USD", "order-1")]


def test_provider_has_deterministic_failure_modes() -> None:
    provider = DeterministicPaymentProvider()

    assert provider.authorize(Decimal("1.00"), "USD", "fail-order").status == "failed"
    with pytest.raises(PaymentProviderUnavailable):
        provider.authorize(Decimal("1.00"), "USD", "unavailable-order")
    with pytest.raises(PaymentProviderUnavailable):
        provider.authorize(Decimal("1.00"), "USD", "unavailable-order")

    assert provider.calls.count(("authorize", "1.00", "USD", "unavailable-order")) == 1
