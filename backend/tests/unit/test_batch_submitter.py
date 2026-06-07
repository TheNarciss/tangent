"""Unit tests for batch_submitter helpers (pure functions)."""

from app.llm import batch_submitter


def test_estimate_cost_per_review_positive() -> None:
    """Per-review estimate must be a positive float."""
    cost = batch_submitter.estimate_cost_per_review()
    assert cost > 0


def test_estimate_cost_per_review_reasonable_range() -> None:
    """Estimate should fall in a sane $0.03-$0.15 range for typical params.

    Guards against accidentally bumping the constants to unrealistic values
    (e.g. tokens *= 10 typo). Adjust if pricing or token estimates change.
    """
    cost = batch_submitter.estimate_cost_per_review()
    assert 0.03 < cost < 0.15, f"Expected $0.03-$0.15, got ${cost:.4f}"


def test_estimate_scales_with_batch_discount() -> None:
    """Estimate must be ~50% of the non-discounted equivalent."""
    from app.llm import cost_tracker

    # Replicate the submitter's constants
    n_in = batch_submitter._ESTIMATED_INPUT_TOKENS_PER_REVIEW
    n_out = batch_submitter._ESTIMATED_OUTPUT_TOKENS_PER_REVIEW
    n_ws = batch_submitter._ESTIMATED_WEB_SEARCHES_PER_REVIEW

    full = cost_tracker.compute_cost_usd(n_in, n_out, n_ws)
    estimated = batch_submitter.estimate_cost_per_review()
    assert estimated == full * 0.5
