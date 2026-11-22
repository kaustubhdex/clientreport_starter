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


def test_suggest_column_mapping_recognises_common_headers():
    from reporting import suggest_column_mapping

    columns = ["Date", "Campaign Name", "Platform", "Amount Spent",
               "Impressions", "Link Clicks", "Purchases", "Sales"]
    mapping = suggest_column_mapping(columns)
    assert mapping == {
        "date": "Date",
        "campaign": "Campaign Name",
        "channel": "Platform",
        "spend": "Amount Spent",
        "impressions": "Impressions",
        "clicks": "Link Clicks",
        "conversions": "Purchases",
        "revenue": "Sales",
    }


def test_apply_column_mapping_renames_without_mutating_source():
    from reporting import apply_column_mapping

    source = pd.DataFrame({"Campaign Name": ["Spring"], "Amount Spent": [25]})
    mapped = apply_column_mapping(source, {
        "campaign": "Campaign Name",
        "spend": "Amount Spent",
    })
    assert "campaign" in mapped.columns
    assert "spend" in mapped.columns
    assert "Campaign Name" in source.columns


def test_apply_column_mapping_rejects_duplicate_source_mapping():
    import pytest
    from reporting import apply_column_mapping

    source = pd.DataFrame({"Value": [1]})
    with pytest.raises(ValueError):
        apply_column_mapping(source, {"spend": "Value", "revenue": "Value"})
