"""Unit tests: the risk slider levels come from config/risk_levels.yaml."""

import pytest

from app.errors import ConfigurationError
from app.finance import risk_profile


def test_five_levels_from_prudent_to_dynamic():
    lv = risk_profile.levels()
    assert [x.level for x in lv] == [1, 2, 3, 4, 5]
    # Monotonic: more risk = more expected return and more volatility allowed
    assert [x.target_annual_return for x in lv] == sorted(x.target_annual_return for x in lv)
    assert [x.max_annual_volatility for x in lv] == sorted(x.max_annual_volatility for x in lv)


def test_level_3_is_the_balanced_profile():
    lv = risk_profile.resolve(3)
    assert lv.target_annual_return == pytest.approx(0.06)
    assert lv.max_annual_volatility == pytest.approx(0.12)


def test_levels_share_one_capital_market_line():
    """Implied Sharpe (r_f 2.5 %) is roughly constant: no level is a free lunch or a trap."""
    sharpes = [
        (x.target_annual_return - 0.025) / x.max_annual_volatility for x in risk_profile.levels()
    ]
    assert max(sharpes) - min(sharpes) < 0.1


def test_unknown_level_is_a_configuration_error():
    with pytest.raises(ConfigurationError):
        risk_profile.resolve(9)
