from unittest.mock import Mock, patch

import pytest
from main import fetch_market_data

import pandas as pd

from main import analyse_market


def make_sample_data(number_of_days=70):
    """Create predictable daily market data for testing."""
    dates = pd.date_range("2026-01-01", periods=number_of_days, freq="D")

    return pd.DataFrame({
        "timestamp": range(number_of_days),
        "date": dates.date,
        "open": [100.0] * number_of_days,
        "high": [105.0] * number_of_days,
        "low": [95.0] * number_of_days,
        "close": [100.0 + i for i in range(number_of_days)],
        "vwap": [100.0] * number_of_days,
        "volume": [1000.0] * number_of_days,
        "trades": [100] * number_of_days,
    })


def test_analysis_returns_exactly_30_days():
    data = make_sample_data()
    result = analyse_market(data)

    assert len(result) == 30


def test_daily_return_is_calculated():
    data = make_sample_data()
    result = analyse_market(data)

    # Last close is 169; previous close is 168.
    expected = (169 / 168 - 1) * 100

    assert abs(result.iloc[-1]["daily_return_pct"] - expected) < 1e-9


def test_moving_averages_are_calculated():
    data = make_sample_data()
    result = analyse_market(data)
    latest = result.iloc[-1]

    # Last seven closes: 163 through 169.
    assert abs(latest["sma_7"] - 166.0) < 1e-9

    # Last thirty closes: 140 through 169.
    assert abs(latest["sma_30"] - 154.5) < 1e-9


def test_high_volume_rule_detects_above_average_volume():
    data = make_sample_data()
    data.loc[69, "volume"] = 5000.0

    result = analyse_market(data)

    assert bool(result.iloc[-1]["high_volume"]) is True


def test_invalid_kraken_pair_raises_clear_error():
    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "error": ["EQuery:Unknown asset pair"]
    }

    with patch("main.requests.get", return_value=fake_response):
        with pytest.raises(RuntimeError, match="Unknown asset pair"):
            fetch_market_data()


def test_unusual_movement_rule_detects_large_return():
    data = make_sample_data()
    data.loc[69, "close"] = 300.0

    result = analyse_market(data)

    assert bool(result.iloc[-1]["unusual_movement"]) is True
