from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from reporting import (
    REQUIRED_COLUMNS,
    apply_column_mapping,
    suggest_column_mapping,
    build_pdf_report,
    build_xlsx_report,
    clean_and_validate,
    generate_observations,
    load_uploaded_file,
)

st.set_page_config(
    page_title="ClientReport | Campaign Reporting",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px;}
      .hero {padding: 1.25rem 1.4rem; border: 1px solid rgba(128,128,128,.25); border-top: 1px solid rgba(128,128,128,.4); border-radius: 14px; margin-top: 1px; margin-bottom: 1rem; box-shadow: inset 0 1px 0 rgba(255,255,255,.035);}
      .muted {opacity: .72;}
      div[data-testid="stExpander"] {
        border: 1px solid rgba(128,128,128,.28);
        border-radius: 10px;
        overflow: hidden;
      }
      div[data-testid="stExpander"] details {
        border: 0;
      }
      div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.18); padding: 12px 14px; border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1 style="margin:0">ClientReport</h1>
      <p class="muted" style="margin:.4rem 0 0 0">Turn campaign spreadsheets into clear, client-ready performance reports.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Get started")
    st.write("Use the synthetic demo dataset or upload your own file.")
    demo_path = Path(__file__).parent / "sample_data.csv"
    data_source = st.radio("Data source", ["Demo dataset", "Upload a file"], horizontal=False)
    uploaded = None
    if data_source == "Upload a file":
        uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"], help="Expected fields: date, campaign, channel, spend, impressions, clicks, conversions, revenue.")
    st.divider()
    st.caption("Demo only: do not upload confidential client data. This prototype does not provide authentication, persistent storage or production-grade tenant isolation.")

raw_df: pd.DataFrame | None = None
source_label = ""

if data_source == "Demo dataset":
    try:
        raw_df = pd.read_csv(demo_path)
        source_label = "Synthetic demonstration dataset"
    except Exception as exc:  # pragma: no cover - defensive UI handling
        st.error(f"Could not load the demo dataset: {exc}")
elif uploaded is not None:
    try:
        raw_df = load_uploaded_file(uploaded)
        source_label = uploaded.name
    except Exception as exc:
        st.error(f"We couldn't read that file. Please check that it is a valid CSV or XLSX file. Details: {exc}")

if raw_df is None:
    st.info("Choose **Demo dataset** or upload a CSV/XLSX file in the left panel.")
    st.subheader("Required data format")
    st.write("Your file should contain these columns. Column names are case-insensitive; extra columns are ignored.")
    st.code(",".join(REQUIRED_COLUMNS), language="text")
    st.download_button(
        "Download sample CSV",
        data=demo_path.read_bytes(),
        file_name="clientreport_sample_data.csv",
        mime="text/csv",
    )
    st.stop()

if data_source == "Upload a file" and raw_df is not None:
    st.subheader("Match your spreadsheet columns")
    st.write("We suggest mappings from your headers. Review them before continuing.")
    suggestions = suggest_column_mapping(list(raw_df.columns))
    mapping = {}
    options = ["— Not mapped —", *[str(c) for c in raw_df.columns]]
    cols = st.columns(2)
    for index, target in enumerate(REQUIRED_COLUMNS):
        suggested = suggestions.get(target)
        default_index = options.index(suggested) if suggested in options else 0
        with cols[index % 2]:
            choice = st.selectbox(
                target.replace("_", " ").title(),
                options,
                index=default_index,
                key=f"column_map_{target}",
            )
        if choice != "— Not mapped —":
            mapping[target] = choice

    duplicate_sources = len(mapping.values()) != len(set(mapping.values()))
    missing_targets = [target for target in REQUIRED_COLUMNS if target not in mapping]
    if duplicate_sources:
        st.error("A source column is mapped more than once. Choose a different column for each field.")
        st.stop()
    if missing_targets:
        st.warning("Please map all required fields: " + ", ".join(missing_targets))
        st.stop()
    raw_df = apply_column_mapping(raw_df, mapping)

cleaned, validation = clean_and_validate(raw_df)

with st.expander("Data validation", expanded=not validation["ok"]):
    if validation["ok"]:
        st.success(f"Validated {validation['valid_rows']} usable rows.")
    else:
        st.error("The uploaded file needs attention before a report can be generated.")
    for message in validation["messages"]:
        st.write(f"• {message}")
    if validation["dropped_rows"]:
        st.warning(f"{validation['dropped_rows']} row(s) were excluded because required values were missing or invalid.")

if cleaned.empty:
    st.warning("No usable rows remain. Correct the file format and upload it again.")
    st.stop()

st.caption(f"Source: {source_label} · {len(cleaned):,} valid rows")

# Filters operate on the cleaned dataset and are not written back to the uploaded file.
with st.sidebar:
    st.divider()
    st.subheader("Report filters")
    channels = sorted(cleaned["channel"].dropna().unique().tolist())
    selected_channels = st.multiselect("Channels", channels, default=channels)
    campaigns = sorted(cleaned.loc[cleaned["channel"].isin(selected_channels), "campaign"].dropna().unique().tolist())
    selected_campaigns = st.multiselect("Campaigns", campaigns, default=campaigns)

filtered = cleaned[
    cleaned["channel"].isin(selected_channels)
    & cleaned["campaign"].isin(selected_campaigns)
].copy()

if filtered.empty:
    st.warning("No data matches the selected filters. Adjust the filters in the sidebar.")
    st.stop()

spend = float(filtered["spend"].sum())
impressions = int(filtered["impressions"].sum())
clicks = int(filtered["clicks"].sum())
conversions = int(filtered["conversions"].sum())
revenue = float(filtered["revenue"].sum())
ctr = (clicks / impressions * 100) if impressions else None
cpc = (spend / clicks) if clicks else None
cpa = (spend / conversions) if conversions else None
roas = (revenue / spend) if spend else None

st.subheader("Performance overview")
metric_cols = st.columns(4)
metric_cols[0].metric("Ad spend", f"${spend:,.2f}")
metric_cols[1].metric("Revenue", f"${revenue:,.2f}")
metric_cols[2].metric("Conversions", f"{conversions:,}")
metric_cols[3].metric("ROAS", f"{roas:,.2f}x" if roas is not None else "N/A")
metric_cols = st.columns(4)
metric_cols[0].metric("Impressions", f"{impressions:,}")
metric_cols[1].metric("Clicks", f"{clicks:,}")
metric_cols[2].metric("CTR", f"{ctr:.2f}%" if ctr is not None else "N/A")
metric_cols[3].metric("CPC / CPA", f"${cpc:.2f} / ${cpa:.2f}" if cpc is not None and cpa is not None else "N/A")

st.subheader("Performance trends")
daily = filtered.groupby("date", as_index=False).agg(
    spend=("spend", "sum"), revenue=("revenue", "sum"), conversions=("conversions", "sum")
).sort_values("date")
trend_tab, channel_tab, campaign_tab = st.tabs(["Over time", "By channel", "By campaign"])
with trend_tab:
    trend_metric = st.selectbox("Trend metric", ["spend", "revenue", "conversions"], format_func=lambda x: x.title())
    fig = px.line(daily, x="date", y=trend_metric, markers=True, title=f"{trend_metric.title()} over time")
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), yaxis_title=trend_metric.title(), xaxis_title="Date")
    st.plotly_chart(fig, use_container_width=True)
with channel_tab:
    channel_summary = filtered.groupby("channel", as_index=False).agg(
        spend=("spend", "sum"), revenue=("revenue", "sum"), clicks=("clicks", "sum"),
        conversions=("conversions", "sum"), impressions=("impressions", "sum")
    )
    channel_summary["ROAS"] = channel_summary.apply(lambda r: r["revenue"] / r["spend"] if r["spend"] else None, axis=1)
    fig = px.bar(channel_summary, x="channel", y="spend", title="Spend by channel", text_auto=".2s")
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), xaxis_title="Channel", yaxis_title="Spend ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(channel_summary, use_container_width=True, hide_index=True)
with campaign_tab:
    campaign_summary = filtered.groupby("campaign", as_index=False).agg(
        spend=("spend", "sum"), revenue=("revenue", "sum"), clicks=("clicks", "sum"),
        conversions=("conversions", "sum"), impressions=("impressions", "sum")
    )
    campaign_summary["ROAS"] = campaign_summary.apply(lambda r: r["revenue"] / r["spend"] if r["spend"] else None, axis=1)
    fig = px.bar(campaign_summary.sort_values("spend", ascending=False), x="campaign", y="spend", title="Spend by campaign", text_auto=".2s")
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), xaxis_title="Campaign", yaxis_title="Spend ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(campaign_summary, use_container_width=True, hide_index=True)

st.subheader("Automated observations")
for observation in generate_observations(filtered):
    st.write(f"• {observation}")
st.caption("Observations are generated from simple rules and calculated values. They do not establish why performance changed.")

st.subheader("Download your report")
summary = pd.DataFrame([{
    "spend": spend, "revenue": revenue, "impressions": impressions, "clicks": clicks,
    "conversions": conversions, "CTR_percent": ctr, "CPC": cpc, "CPA": cpa, "ROAS": roas,
}])
channel_summary = filtered.groupby("channel", as_index=False).agg(
    spend=("spend", "sum"), revenue=("revenue", "sum"), impressions=("impressions", "sum"),
    clicks=("clicks", "sum"), conversions=("conversions", "sum")
)
campaign_summary = filtered.groupby("campaign", as_index=False).agg(
    spend=("spend", "sum"), revenue=("revenue", "sum"), impressions=("impressions", "sum"),
    clicks=("clicks", "sum"), conversions=("conversions", "sum")
)
observations = generate_observations(filtered)
xlsx_bytes = build_xlsx_report(filtered, summary, channel_summary, campaign_summary)
pdf_bytes = build_pdf_report(summary.iloc[0].to_dict(), channel_summary, observations, source_label)
col1, col2 = st.columns(2)
with col1:
    st.download_button("Download Excel report", data=xlsx_bytes, file_name="clientreport_output.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
with col2:
    st.download_button("Download PDF summary", data=pdf_bytes, file_name="clientreport_summary.pdf", mime="application/pdf", use_container_width=True)

with st.expander("Preview cleaned data"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)

st.divider()
st.caption("ClientReport portfolio prototype · Demonstration data is synthetic · Not for confidential or production client data")
