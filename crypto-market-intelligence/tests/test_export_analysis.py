
import json

import pandas as pd
import pytest

import export_analysis as exporter


def make_analysed_data(count=30, frequency="D"):
    timestamps = pd.date_range(
        "2026-10-01",
        periods=count,
        freq=frequency,
        tz="UTC",
    )

    return pd.DataFrame({
        "datetime_utc": timestamps,
        "close": [100.0 + i for i in range(count)],
        "daily_return_pct": [None] + [1.0] * (count - 1),
        "volume": [1000.0] * count,
        "sma_7": [None] * 6
        + [103.0 + i for i in range(max(0, count - 6))],
        "sma_30": [None] * (count - 1) + [114.5],
        "unusual_movement": [False] * (count - 1) + [True],
        "high_volume": [False] * (count - 1) + [True],
        "trend_comparison": ["Insufficient data"] * (count - 1)
        + ["7-day SMA below 30-day SMA"],
    })


def test_build_export_returns_30_daily_observations(monkeypatch):
    monkeypatch.setattr(
        exporter,
        "fetch_market_data",
        lambda interval: pd.DataFrame({"dummy": [1]}),
    )
    monkeypatch.setattr(
        exporter,
        "analyse_market",
        lambda data, interval: make_analysed_data(),
    )

    result = exporter.build_export(exporter.DAILY_INTERVAL_MINUTES)

    assert result["source"] == "Kraken"
    assert result["pair"] == "XBT/USD"
    assert result["timeframe"] == "daily"
    assert result["observation_count"] == 30
    assert result["interval_minutes"] == 1440
    assert result["return_definition"] == "daily candle return"
    assert len(result["observations"]) == 30
    assert result["latest"]["close_usd"] == 129.0


def test_build_export_rejects_unsupported_interval():
    with pytest.raises(ValueError, match="Interval must be"):
        exporter.build_export(60)


def test_build_export_rejects_empty_analysis(monkeypatch):
    monkeypatch.setattr(
        exporter,
        "fetch_market_data",
        lambda interval: pd.DataFrame({"dummy": [1]}),
    )
    monkeypatch.setattr(
        exporter,
        "analyse_market",
        lambda data, interval: pd.DataFrame(),
    )

    with pytest.raises(
        RuntimeError,
        match="Cannot export an empty market analysis",
    ):
        exporter.build_export(exporter.DAILY_INTERVAL_MINUTES)


def test_save_export_writes_valid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(exporter, "EXPORT_DIR", tmp_path)

    sample = {
        "schema_version": 1,
        "pair": "XBT/USD",
        "observations": [{"close_usd": 100.0}],
    }

    path = exporter.save_export(sample)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved == sample
    assert path.suffix == ".json"


def test_save_export_rejects_non_finite_numbers(tmp_path, monkeypatch):
    monkeypatch.setattr(exporter, "EXPORT_DIR", tmp_path)

    with pytest.raises(ValueError):
        exporter.save_export({"price": float("nan")})


def test_build_export_identifies_four_hour_returns(monkeypatch):
    monkeypatch.setattr(
        exporter,
        "fetch_market_data",
        lambda interval: pd.DataFrame({"dummy": [1]}),
    )
    monkeypatch.setattr(
        exporter,
        "analyse_market",
        lambda data, interval: make_analysed_data(
            count=180,
            frequency="4h",
        ),
    )

    result = exporter.build_export(exporter.FOUR_HOUR_INTERVAL_MINUTES)

    assert result["timeframe"] == "4-hour"
    assert result["interval_minutes"] == 240
    assert result["return_definition"] == "4-hour candle return"
    assert result["observation_count"] == 180
    assert len(result["observations"]) == 180
