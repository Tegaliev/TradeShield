"""
dashboard.py

The user-facing part of the project: pick a currency pair, a deal size,
and a time horizon, and see the risk score, the dollar VaR, and an
LLM-generated business report, all in one screen.

Run locally, from the project root:
    streamlit run src/dashboard.py

Requires:
    - results/volatility_forecast_summary.csv (run volatility_forecast.py first)
    - a .env file with FEATHERLESS_API_KEY (only needed if you tick the
      "generate LLM report" box -- the risk score and VaR work without it)
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from risk_scoring import (
    build_risk_report,
    load_forecast_table,
    compute_relative_scores,
    DEFAULT_EXPOSURE_USD,
    DEFAULT_HORIZON_DAYS,
)

st.set_page_config(page_title="FX Risk Scorer", layout="centered")
st.title("FX Volatility & Export Risk Scorer")
st.caption(
    "Research prototype built for GIBC V2 (Track 02: Applied - Finance). "
    "Not a financial product, not investment advice."
)

try:
    forecast_table = load_forecast_table()
except FileNotFoundError:
    st.error(
        "No volatility forecast found yet. Run these two scripts first, in "
        "order, from a terminal:\n\n"
        "1. python src/data_collection.py\n"
        "2. python src/volatility_forecast.py"
    )
    st.stop()

pairs = forecast_table["pair"].tolist()

col1, col2, col3 = st.columns(3)
with col1:
    pair = st.selectbox("Currency pair", pairs)
with col2:
    exposure = st.number_input(
        "Deal size (USD)", min_value=1000.0, value=float(DEFAULT_EXPOSURE_USD), step=1000.0
    )
with col3:
    horizon = st.slider("Time horizon (days)", min_value=1, max_value=180, value=DEFAULT_HORIZON_DAYS)

generate_llm = st.checkbox(
    "Also generate an LLM business report (calls the Featherless API, needs .env set up)",
    value=True,
)

if st.button("Analyze risk", type="primary"):
    report = build_risk_report(pair, exposure, horizon)

    category_color = {"Low": "green", "Medium": "orange", "High": "red"}[report["risk_category"]]
    st.markdown(f"### Risk score: {report['risk_score']}/100 — :{category_color}[{report['risk_category']}]")

    m1, m2, m3 = st.columns(3)
    m1.metric("Forecasted annualized volatility", f"{report['forecast_annualized_vol_pct']}%")
    m2.metric("95% Value-at-Risk (VaR)", f"${report['value_at_risk_usd_95pct']:,.0f}")
    m3.metric("VaR as % of deal size", f"{report['value_at_risk_pct_of_exposure']}%")

    st.subheader("How this pair compares to the others we track")
    scored = compute_relative_scores(forecast_table)
    chart_data = scored.set_index("pair")[["risk_score"]]
    st.bar_chart(chart_data)
    st.caption(
        "This comparison is relative to the small set of pairs this project "
        "tracks, not the entire FX market."
    )

    if generate_llm:
        with st.spinner("Asking the LLM for a business report..."):
            try:
                from llm_report import generate_report  # imported here so a
                # missing/broken .env doesn't crash the risk-score-only path
                report_text = generate_report(report)
                st.subheader("Business report")
                st.markdown(report_text)
            except Exception as exc:
                st.error(f"Could not generate the LLM report: {exc}")

st.divider()
st.caption(
    "GIBC V2 hackathon research prototype. This tool does not account for "
    "your specific financial situation and should not be used for real "
    "trading, hedging, or investment decisions."
)
