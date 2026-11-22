# ClientReport — Campaign Reporting Prototype

> Portfolio demonstration built independently with synthetic data. It has not been deployed for a paying customer unless this statement is updated to reflect a verified engagement.

## Problem
Small marketing teams often receive campaign data in spreadsheets and spend time cleaning files, calculating metrics, and preparing recurring summaries.

## Proposed solution
ClientReport is a prototype that accepts a standardised campaign CSV/XLSX file, validates required fields, calculates common performance metrics, visualises results, and exports an Excel workbook and PDF summary.

## My role
Designed and implemented the data-processing logic, validation rules, Streamlit interface, visualisations, and report exports.

## Technology
- Python
- Pandas
- Streamlit
- Plotly
- OpenPyXL
- ReportLab

## Input and output
**Input:** `date, campaign, channel, spend, impressions, clicks, conversions, revenue`

**Output:** KPI summary, performance trends, channel/campaign breakdowns, cleaned Excel workbook, PDF summary.

## Validation and limitations
- Tested against the included 30-row synthetic demonstration dataset.
- Automated checks cover standard data, missing required columns, and deterministic observations.
- Vendor-specific Google Ads, Meta Ads, and analytics exports are not all supported yet; their schemas and definitions need mapping and validation.
- The prototype has no authentication, persistent storage, tenant separation, or production security controls.
- Automated observations describe calculated values and do not prove causation.

## Demonstration
- Live app: [Add the deployed Streamlit URL after deployment]
- Walkthrough video: [Add the recording URL]
- Source code: [Add the GitHub repository URL]

## What I would improve next
1. Add an interactive column-mapping interface for different vendor exports.
2. Add date-range and previous-period comparisons.
3. Add configurable agency branding.
4. Add further tests for edge cases and malformed workbooks.
5. Design a secure private deployment only after validating a real client requirement.
