"""Unit tests for token cost estimation."""

from app.config import settings
from app.cost import compute_cost, usage_to_dict


def test_compute_cost_uses_configured_prices():
    # 1M input + 1M output tokens = input price + output price.
    cost = compute_cost(1_000_000, 1_000_000)
    expected = settings.price_per_mtok_input + settings.price_per_mtok_output
    assert round(cost, 6) == round(expected, 6)


def test_compute_cost_zero():
    assert compute_cost(0, 0) == 0.0


def test_usage_to_dict_from_object():
    class FakeUsage:
        input_tokens = 1000
        output_tokens = 500

    result = usage_to_dict(FakeUsage())
    assert result["input_tokens"] == 1000
    assert result["output_tokens"] == 500
    assert result["cost_usd"] == compute_cost(1000, 500)


def test_usage_to_dict_handles_missing_fields():
    result = usage_to_dict(object())
    assert result == {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
