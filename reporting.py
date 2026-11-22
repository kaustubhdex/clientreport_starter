from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "date", "campaign", "channel", "spend", "impressions", "clicks", "conversions", "revenue"
]
NUMERIC_COLUMNS = ["spend", "impressions", "clicks", "conversions", "revenue"]


def load_uploaded_file(uploaded_file: Any) -> pd.DataFrame:
    """Read a CSV or XLSX upload into a DataFrame."""
    name = getattr(uploaded_file, "name", "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file, engine="openpyxl")
    raise ValueError("Unsupported file type. Please upload CSV or XLSX.")



COLUMN_ALIASES = {
    "date": ["date", "day", "report_date", "reporting_date", "time"],
    "campaign": ["campaign", "campaign_name", "campaigns", "ad_campaign", "campaign_title"],
    "channel": ["channel", "platform", "source", "network", "publisher", "media_source"],
    "spend": ["spend", "cost", "amount_spent", "ad_spend", "total_spend", "amount"],
    "impressions": ["impressions", "impression", "views", "reach_impressions"],
    "clicks": ["clicks", "link_clicks", "outbound_clicks", "total_clicks"],
    "conversions": ["conversions", "conversion", "purchases", "leads", "results"],
    "revenue": ["revenue", "sales", "conversion_value", "purchase_value", "total_revenue"],
}


def _normalise_header(value: Any) -> str:
    """Convert a source header into a comparable token."""
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def suggest_column_mapping(columns: list[Any]) -> dict[str, str]:
    """Suggest source-header to ClientReport-field mappings using conservative aliases."""
    normalised = {_normalise_header(col): str(col) for col in columns}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for target in REQUIRED_COLUMNS:
        candidates = [target, *COLUMN_ALIASES.get(target, [])]
        for candidate in candidates:
            source = normalised.get(_normalise_header(candidate))
            if source is not None and source not in used:
                mapping[target] = source
                used.add(source)
                break
    return mapping


def apply_column_mapping(raw: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Return a copy with mapped source headers renamed to canonical field names."""
    if raw is None:
        return pd.DataFrame()
    selected = {target: source for target, source in mapping.items()
                if target in REQUIRED_COLUMNS and source in raw.columns and source}
    if len(set(selected.values())) != len(selected):
        raise ValueError("Each source column can only be mapped to one reporting field.")
    result = raw.rename(columns={source: target for target, source in selected.items()}).copy()
    return result

def clean_and_validate(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Normalise headers, coerce types, remove unusable rows, and report data quality."""
    if raw is None or raw.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS), {
            "ok": False, "valid_rows": 0, "dropped_rows": 0,
            "messages": ["The file is empty."],
        }

    df = raw.copy()
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
    messages: list[str] = []

    # Common aliases help with ordinary export variations without claiming to support every vendor schema.
    aliases = {
        "campaign_name": "campaign", "campaigns": "campaign",
        "source": "channel", "network": "channel", "platform": "channel",
        "cost": "spend", "amount_spent": "spend", "ad_spend": "spend",
        "views": "impressions", "link_clicks": "clicks",
        "purchases": "conversions", "conversion": "conversions",
        "sales": "revenue", "conversion_value": "revenue",
        "report_date": "date", "day": "date",
    }
    df = df.rename(columns={col: aliases[col] for col in df.columns if col in aliases})

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return pd.DataFrame(columns=REQUIRED_COLUMNS), {
            "ok": False, "valid_rows": 0, "dropped_rows": len(raw),
            "messages": ["Missing required columns: " + ", ".join(missing),
                         "Use the sample CSV template or rename your columns to the required field names."],
        }

    df = df[REQUIRED_COLUMNS].copy()
    original_count = len(df)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["campaign"] = df["campaign"].astype("string").str.strip()
    df["channel"] = df["channel"].astype("string").str.strip()
    for col in NUMERIC_COLUMNS:
        # Accept currency symbols and comma thousands separators in ordinary spreadsheet exports.
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            cleaned_text = df[col].astype("string").str.replace(r"[$,]", "", regex=True).str.strip()
            df[col] = pd.to_numeric(cleaned_text, errors="coerce")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Treat blank campaign/channel labels as missing, not valid categories.
    for col in ["campaign", "channel"]:
        df[col] = df[col].replace(r"^\\s*$", pd.NA, regex=True)

    required_non_null = ["date", "campaign", "channel", *NUMERIC_COLUMNS]
    valid_mask = df[required_non_null].notna().all(axis=1)
    dropped_nulls = int((~valid_mask).sum())
    df = df.loc[valid_mask].copy()

    nonnegative_mask = (df[NUMERIC_COLUMNS] >= 0).all(axis=1)
    dropped_negative = int((~nonnegative_mask).sum())
    df = df.loc[nonnegative_mask].copy()

    fractional_counts = {}
    for col in ["impressions", "clicks", "conversions"]:
        fractional = (df[col] % 1 != 0)
        fractional_counts[col] = int(fractional.sum())
        if fractional.any():
            df = df.loc[~fractional].copy()
            messages.append(f"{fractional_counts[col]} row(s) with fractional {col} values were excluded; counts should be whole numbers.")

    df["impressions"] = df["impressions"].astype("int64")
    df["clicks"] = df["clicks"].astype("int64")
    df["conversions"] = df["conversions"].astype("int64")
    df["date"] = df["date"].dt.date

    # These are warnings, not automatic exclusions: attribution and platform definitions can differ.
    clicks_exceed_impressions = int((df["clicks"] > df["impressions"]).sum())
    conversions_exceed_clicks = int((df["conversions"] > df["clicks"]).sum())
    if clicks_exceed_impressions:
        messages.append(
            f"Review {clicks_exceed_impressions} row(s) where clicks exceed impressions. "
            "This may reflect different platform definitions or a source-data issue."
        )
    if conversions_exceed_clicks:
        messages.append(
            f"Review {conversions_exceed_clicks} row(s) where conversions exceed clicks. "
            "This may reflect attribution or counting differences."
        )

    duplicate_count = int(df.duplicated().sum())
    if duplicate_count:
        messages.append(f"Found {duplicate_count} exact duplicate row(s). They were retained; review before external reporting.")

    dropped = original_count - len(df)
    if dropped_nulls:
        messages.append(f"{dropped_nulls} row(s) with missing or invalid required values were excluded.")
    if dropped_negative:
        messages.append(f"{dropped_negative} row(s) with negative spend, traffic, conversion or revenue values were excluded.")
    if not messages:
        messages.append("No data-quality issues detected in the required fields.")

    return df.sort_values("date").reset_index(drop=True), {
        "ok": len(df) > 0, "valid_rows": len(df), "dropped_rows": dropped,
        "messages": messages,
    }


def generate_observations(df: pd.DataFrame) -> list[str]:
    """Generate deterministic observations; these are not causal explanations."""
    if df.empty:
        return ["No valid data is available for analysis."]
    obs: list[str] = []
    spend = float(df["spend"].sum())
    revenue = float(df["revenue"].sum())
    clicks = int(df["clicks"].sum())
    impressions = int(df["impressions"].sum())
    conversions = int(df["conversions"].sum())
    if spend > 0:
        obs.append(f"Overall return on ad spend is {revenue / spend:.2f}x based on the uploaded revenue and spend fields.")
    else:
        obs.append("Total spend is zero, so return on ad spend and cost metrics cannot be calculated.")
    if impressions > 0:
        obs.append(f"Overall click-through rate is {clicks / impressions * 100:.2f}%.")
    if clicks > 0:
        obs.append(f"Overall conversion rate is {conversions / clicks * 100:.2f}% of clicks.")
    if not obs:
        obs.append("There are not enough non-zero values to calculate the headline ratios.")

    by_campaign = df.groupby("campaign", as_index=False).agg(spend=("spend", "sum"), conversions=("conversions", "sum"))
    if len(by_campaign) > 1:
        by_campaign["CPA"] = by_campaign.apply(lambda r: r["spend"] / r["conversions"] if r["conversions"] else float("inf"), axis=1)
        eligible = by_campaign[by_campaign["CPA"] != float("inf")]
        if not eligible.empty:
            best = eligible.sort_values("CPA").iloc[0]
            obs.append(f"Among campaigns with at least one conversion, '{best['campaign']}' has the lowest cost per acquisition at ${best['CPA']:.2f}.")
    return obs


def build_xlsx_report(
    cleaned: pd.DataFrame,
    summary: pd.DataFrame,
    channel_summary: pd.DataFrame,
    campaign_summary: pd.DataFrame,
) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cleaned.to_excel(writer, sheet_name="Cleaned Data", index=False)
        summary.to_excel(writer, sheet_name="Overview", index=False)
        channel_summary.to_excel(writer, sheet_name="By Channel", index=False)
        campaign_summary.to_excel(writer, sheet_name="By Campaign", index=False)
        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for column_cells in worksheet.columns:
                max_length = max((len(str(cell.value)) if cell.value is not None else 0) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 32)
    return output.getvalue()


def build_pdf_report(summary: dict[str, Any], channel_summary: pd.DataFrame, observations: list[str], source_label: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch,
                            topMargin=0.55 * inch, bottomMargin=0.55 * inch)
    styles = getSampleStyleSheet()
    story = [Paragraph("ClientReport — Campaign Performance Summary", styles["Title"]),
             Paragraph(f"Source file: {source_label}", styles["Normal"]), Spacer(1, 12)]

    def fmt(key: str, value: Any) -> str:
        if value is None or pd.isna(value):
            return "N/A"
        if key in {"spend", "revenue", "CPC", "CPA"}:
            return f"${float(value):,.2f}"
        if key == "CTR_percent":
            return f"{float(value):.2f}%"
        if key == "ROAS":
            return f"{float(value):.2f}x"
        return f"{value:,}"

    display_keys = ["spend", "revenue", "impressions", "clicks", "conversions", "CTR_percent", "CPC", "CPA", "ROAS"]
    rows = [["Metric", "Result"]] + [[key.replace("_", " ").upper(), fmt(key, summary.get(key))] for key in display_keys]
    table = Table(rows, colWidths=[2.5 * inch, 2.0 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#23324A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9DEE7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F9")]),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([table, Spacer(1, 16), Paragraph("Automated observations", styles["Heading2"])])
    for item in observations:
        story.append(Paragraph("• " + item, styles["BodyText"]))
        story.append(Spacer(1, 5))
    if not channel_summary.empty:
        story.extend([Spacer(1, 10), Paragraph("Channel summary", styles["Heading2"])])
        channel_rows = [[str(c).title() for c in channel_summary.columns]]
        for _, row in channel_summary.iterrows():
            channel_rows.append([str(v)[:32] if isinstance(v, str) else (f"${v:,.2f}" if isinstance(v, float) else f"{v:,}") for v in row.tolist()])
        channel_table = Table(channel_rows, repeatRows=1)
        channel_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#23324A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9DEE7")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(channel_table)
    story.extend([Spacer(1, 16), Paragraph("Generated from uploaded data. Ratios depend on the accuracy and definitions of the source fields. This report does not establish causation.", styles["Italic"])])
    doc.build(story)
    return output.getvalue()
