import pandas as pd

from reporting import clean_and_validate, generate_observations


def test_clean_and_validate_accepts_standard_data():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "campaign": ["A", "B"],
        "channel": ["Search", "Social"],
        "spend": [10, "$20.50"],
        "impressions": [1000, 2000],
        "clicks": [50, 80],
        "conversions": [5, 8],
        "revenue": [100, 180],
    })
    cleaned, report = clean_and_validate(df)
    assert report["ok"] is True
    assert len(cleaned) == 2
    assert cleaned["spend"].sum() == 30.5


def test_missing_columns_are_reported():
    cleaned, report = clean_and_validate(pd.DataFrame({"date": ["2026-01-01"]}))
    assert cleaned.empty
    assert report["ok"] is False
    assert "Missing required columns" in report["messages"][0]


def test_observations_are_deterministic():
    df = pd.DataFrame({
        "date": [pd.Timestamp("2026-01-01").date()],
        "campaign": ["A"], "channel": ["Search"], "spend": [10.0],
        "impressions": [1000], "clicks": [50], "conversions": [5], "revenue": [100.0],
    })
    observations = generate_observations(df)
    assert any("10.00x" in text for text in observations)
