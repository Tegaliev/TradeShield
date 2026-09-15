# FX Volatility & Export Risk Scorer

**GIBC V2 — Track 02 (Applied: Finance)**

> ⚠️ This is a research prototype built for a hackathon. It is not a
> financial product, not investment advice, and must not be used for real
> trading or hedging decisions.

## What this is (short version, expand at submission time)

A tool for exporters/importers to gauge how much currency risk they're
exposed to on a given trade. It forecasts near-term FX volatility for a
currency pair, converts that into a plain risk score, and uses an LLM to
turn the score into a short, readable business explanation.

Pipeline: **historical FX data → volatility model → risk score → LLM-generated
business report → dashboard**

## Status

- [x] Step 1: data collection script
- [ ] Step 2: exploratory analysis / volatility metrics
- [ ] Step 3: volatility forecasting model
- [ ] Step 4: risk scoring logic
- [ ] Step 5: LLM business report
- [ ] Step 6: Streamlit dashboard
- [ ] Step 7: full documentation + AI-tool disclosure
- [ ] Step 8: demo video + Devpost submission

## Setup

```bash
pip install -r requirements.txt
python src/data_collection.py
```

This downloads 5 years of daily rates for EUR/USD, USD/JPY, GBP/USD,
USD/CNY, and USD/INR from Yahoo Finance into `data/`.

## Data sources

- FX rates: [Yahoo Finance](https://finance.yahoo.com) via the `yfinance`
  Python library. Public market data, no license restrictions for research use.

## AI tools used

(To be filled in fully in the final README — track every AI tool used,
per GIBC V2 disclosure requirements.)
