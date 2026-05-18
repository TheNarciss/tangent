"""Application-level exception hierarchy.

Each exception carries an HTTP status code and a human-readable detail. The
global handler in `main.py` translates instances to JSON responses; nothing
else in the app should issue raw `HTTPException`.

`analytics.py` stays pure and raises plain `ValueError`; orchestrators (e.g.
`dashboard.py`) catch those and re-raise as `InsufficientHistoryError`.
"""


class AppError(Exception):
    """Base for all expected, recoverable errors. Carries an HTTP status."""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PortfolioEmptyError(AppError):
    """Stored portfolio has no positions."""
    status_code = 404


class PortfolioCorruptedError(AppError):
    """portfolio.json failed to parse or violates the schema."""
    status_code = 500


class TickerNotFoundError(AppError):
    """One or more tickers returned no usable data from the provider."""
    status_code = 422


class MarketDataError(AppError):
    """Upstream market data provider failure (network, timeout, etc.)."""
    status_code = 502


class InsufficientHistoryError(AppError):
    """Asset universe lacks enough overlapping history for the requested computation."""
    status_code = 422


class ConfigurationError(AppError):
    """A static config file (YAML, env) is missing or malformed."""
    status_code = 500


class UnknownBrokerError(AppError):
    """Client requested a broker_id that isn't in the loaded config."""
    status_code = 422