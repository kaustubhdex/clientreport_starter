# ClientReport — Campaign Reporting Prototype

A beginner-friendly portfolio project that turns a standardised campaign CSV/XLSX export into a dashboard and downloadable Excel/PDF summary.

## What it demonstrates

- Python data handling with Pandas
- Basic data validation and cleaning
- KPI calculations (CTR, CPC, CPA, ROAS)
- Interactive charts with Plotly
- Excel export with OpenPyXL
- PDF generation with ReportLab
- A simple web UI with Streamlit

## Important scope and safety notes

- The included dataset is synthetic and created only for demonstration.
- This prototype does not provide user accounts, persistent storage, tenant separation, audit logging, or production-grade security.
- Do not upload confidential customer, advertising, financial, or personal data to the public demo.
- Marketing platform exports have different schemas and metric definitions. This MVP accepts the standard column template below; vendor-specific mapping should be added only after validating actual customer files.
- The automated observations are deterministic descriptions of calculated values. They do not explain causation or make optimisation recommendations.

## Required input columns

`date,campaign,channel,spend,impressions,clicks,conversions,revenue`

Column names are case-insensitive. A small set of common aliases is supported. Use `sample_data.csv` as the template.

## Run locally on Windows

1. Install Python 3.11 or newer from https://www.python.org/downloads/ and enable **Add Python to PATH** during installation.
2. Extract this project folder.
3. Open PowerShell in the extracted folder.
4. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```

6. Start the app:

   ```powershell
   streamlit run app.py
   ```

7. Open the local URL printed in the terminal (usually http://localhost:8501).
8. Run the basic tests with `python -m pytest -q tests`.

## Deploy a public portfolio demo

1. Create a GitHub repository named `clientreport`.
2. Add `app.py`, `reporting.py`, `requirements.txt`, `sample_data.csv`, and this README.
3. Push the repository to GitHub.
4. Sign in to https://share.streamlit.io/ with GitHub.
5. Choose **Create app**, select the repository and branch, and set the app file to `app.py`.
6. Deploy. Streamlit Community Cloud provides a `streamlit.app` URL.

Keep the repository public for a straightforward portfolio demo. Do not include credentials, client files, private datasets, or secrets.

## Portfolio case study

Use `PORTFOLIO_CASE_STUDY_TEMPLATE.md` as the project write-up. Add the real deployed URL and a walkthrough video only after you have created them. Keep the synthetic-data disclosure and current limitations visible.

## Suggested next improvements (after the MVP works)

1. Add a column-mapping screen for real vendor exports.
2. Add date-range filtering and a previous-period comparison.
3. Add a client branding field (agency name, logo, report title).
4. Add more tests for malformed files, zeros, duplicate rows, and edge cases.
5. Only after a real client requests it, add a private deployment, authentication and secure storage model.

## Portfolio disclosure

Present this as an independently developed demonstration using synthetic data. Do not claim it has been deployed for or used by real clients unless that becomes true.
