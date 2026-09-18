from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal


class PaymentProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PaymentResult:
    status: str
    provider_reference: str


class DeterministicPaymentProvider:
    """In-process provider used to make payment outcomes repeatable in the benchmark."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str]] = []
        self._results: dict[tuple[str, str], PaymentResult | PaymentProviderUnavailable] = {}

    def authorize(self, amount: Decimal, currency: str, idempotency_key: str) -> PaymentResult:
        return self._operation("authorize", amount, currency, idempotency_key)

    def void(self, amount: Decimal, currency: str, idempotency_key: str) -> PaymentResult:
        return self._operation("void", amount, currency, idempotency_key)

    def _operation(
        self, operation: str, amount: Decimal, currency: str, idempotency_key: str
    ) -> PaymentResult:
        cache_key = (operation, idempotency_key)
        if cache_key in self._results:
            cached = self._results[cache_key]
            if isinstance(cached, PaymentProviderUnavailable):
                raise cached
            return cached

        normalized_amount = format(amount, ".2f")
        self.calls.append((operation, normalized_amount, currency, idempotency_key))
        if idempotency_key.startswith("unavailable-"):
            unavailable = PaymentProviderUnavailable("deterministic provider unavailability")
            self._results[cache_key] = unavailable
            raise unavailable

        status = "failed" if idempotency_key.startswith("fail-") else "authorized"
        digest = hashlib.sha256(f"{operation}:{idempotency_key}".encode()).hexdigest()[:24]
        result = PaymentResult(status=status, provider_reference=f"mock-{digest}")
        self._results[cache_key] = result
        return result
