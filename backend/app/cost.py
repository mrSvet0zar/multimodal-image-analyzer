"""Token usage and cost estimation for Claude Vision calls."""

from typing import Any

from app.config import settings


def compute_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimated USD cost from token counts and configured per-MTok prices."""
    cost = (
        input_tokens / 1_000_000 * settings.price_per_mtok_input
        + output_tokens / 1_000_000 * settings.price_per_mtok_output
    )
    return round(cost, 6)


def usage_to_dict(usage: Any) -> dict:
    """Normalize an Anthropic `usage` object into a serializable dict + cost."""
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": compute_cost(input_tokens, output_tokens),
    }
