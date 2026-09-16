"""
risk_scoring.py

Turns a GARCH volatility forecast into two things a business person can
actually use:

1. A 0-100 risk SCORE (and Low/Medium/High category) that says how risky
   this currency pair is *relative to the other pairs we track*.
2. A dollar Value-at-Risk (VaR) estimate: "with 95% confidence, you will
   not lose more than $X on this deal, over this time horizon, purely
   from currency movement."

This module is meant to be imported by the dashboard (step 6) as well as
run directly to print a report for all tracked pairs.

Run locally, from the project root:
    python src/risk_scoring.py
    (on Windows: py src\\risk_scoring.py)

Requires results/volatility_forecast_summary.csv (from volatility_forecast.py).
"""

import os
import argparse
import numpy as np
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FORECAST_PATH = os.path.join(RESULTS_DIR, "volatility_forecast_summary.csv")

TRADING_DAYS_PER_YEAR = 252
# One-sided 95% confidence z-score. "95% VaR" is the standard convention
# in market risk reporting (e.g. it's what RiskMetrics/most bank desks use).
Z_SCORE_95 = 1.645

DEFAULT_EXPOSURE_USD = 100_000
DEFAULT_HORIZON_DAYS = 30


def load_forecast_table() -> pd.DataFrame:
    if not os.path.exists(FORECAST_PATH):
        raise FileNotFoundError(
            f"Could not find {FORECAST_PATH}. Run src/volatility_forecast.py first."
        )
    return pd.read_csv(FORECAST_PATH)


def compute_relative_scores(forecast_table: pd.DataFrame) -> pd.DataFrame:
    """0-100 score based on where each pair's forecast volatility falls
    relative to the other pairs we currently track.

    Important limitation (worth stating plainly in the README/demo): this
    score is relative to the small set of pairs in this project, not to
    the entire FX market. A pair scoring 100 here just means "riskiest of
    the 5 we track right now", not "riskiest currency pair in the world."
    """
    vol = forecast_table["forecast_5d_annualized_vol_pct"]
    vol_min, vol_max = vol.min(), vol.max()

    table = forecast_table.copy()
    if vol_max > vol_min:
        table["risk_score"] = ((vol - vol_min) / (vol_max - vol_min) * 100).round(1)
    else:
        table["risk_score"] = 50.0  # all pairs equally volatile (edge case)

    def categorize(score):
        if score < 33:
            return "Low"
        elif score < 67:
            return "Medium"
        return "High"

    table["risk_category"] = table["risk_score"].apply(categorize)
    return table


def compute_var(annualized_vol_pct: float, exposure_usd: float, horizon_days: int) -> float:
    """95% Value-at-Risk in USD for a given exposure and time horizon.

    Logic: annualized volatility is scaled down to the chosen horizon using
    the square-root-of-time rule (a standard, if simplified, assumption
    that daily returns are independent and identically distributed), then
    multiplied by the 95% z-score and the exposure amount.
    """
    horizon_vol_pct = annualized_vol_pct * np.sqrt(horizon_days / TRADING_DAYS_PER_YEAR)
    var_usd = exposure_usd * (horizon_vol_pct / 100) * Z_SCORE_95
    return round(float(var_usd), 2)


def build_risk_report(pair: str, exposure_usd: float, horizon_days: int) -> dict:
    forecast_table = load_forecast_table()
    scored = compute_relative_scores(forecast_table)

    row = scored[scored["pair"] == pair]
    if row.empty:
        available = ", ".join(scored["pair"])
        raise ValueError(f"Unknown pair '{pair}'. Available pairs: {available}")
    row = row.iloc[0]

    annualized_vol_pct = row["forecast_5d_annualized_vol_pct"]
    var_usd = compute_var(annualized_vol_pct, exposure_usd, horizon_days)

    return {
        "pair": pair,
        "exposure_usd": exposure_usd,
        "horizon_days": horizon_days,
        "forecast_annualized_vol_pct": round(float(annualized_vol_pct), 2),
        "risk_score": float(row["risk_score"]),
        "risk_category": row["risk_category"],
        "value_at_risk_usd_95pct": var_usd,
        "value_at_risk_pct_of_exposure": round(var_usd / exposure_usd * 100, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="FX risk scoring for a single deal.")
    parser.add_argument("--pair", default=None, help="e.g. EURUSD. Omit to report on all tracked pairs.")
    parser.add_argument("--exposure", type=float, default=DEFAULT_EXPOSURE_USD, help="Deal size in USD.")
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON_DAYS, help="Time horizon in days.")
    args = parser.parse_args()

    forecast_table = load_forecast_table()
    scored = compute_relative_scores(forecast_table)
    pairs = [args.pair] if args.pair else scored["pair"].tolist()

    reports = [build_risk_report(pair, args.exposure, args.horizon) for pair in pairs]
    report_df = pd.DataFrame(reports)

    out_path = os.path.join(RESULTS_DIR, "risk_scores.csv")
    report_df.to_csv(out_path, index=False)
    print(f"Exposure: ${args.exposure:,.0f} | Horizon: {args.horizon} days\n")
    print(report_df.to_string(index=False))
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()
