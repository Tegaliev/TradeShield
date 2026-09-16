"""
portfolio_risk.py

Extends the single-pair risk score into a multi-currency PORTFOLIO risk
tool. Real exporters/importers rarely have exposure to just one currency
pair -- they buy from suppliers in one country and sell to customers in
another. This module answers: "if I hold several FX exposures at once,
what's my combined risk, accounting for the fact that these currencies
don't move independently of each other?"

Method, in plain terms:
    1. Look at how the currency pairs have actually moved together
       historically (their correlation).
    2. Use each pair's current GARCH volatility forecast (from
       volatility_forecast.py) as "how much it's expected to move."
    3. Run 20,000 simulated scenarios of correlated currency moves
       (Monte Carlo simulation), using a technique called Cholesky
       decomposition to make sure the simulated moves respect the real
       historical correlation between pairs, not just their individual
       volatility.
    4. For each simulated scenario, compute the portfolio's total dollar
       gain/loss. The 95% VaR is then just: "the loss you'd see in the
       worst 5% of these 20,000 simulated scenarios."
    5. Compare that to the "naive" VaR (what you'd get by just adding up
       each exposure's individual VaR, ignoring correlation) to show the
       diversification benefit in dollar terms.

Simplifying assumption (stated plainly, not hidden): each exposure is
treated as "you lose money if this pair's rate rises." For a real
company this depends on which side of the trade you're on (importer vs
exporter); this prototype does not model that directionality, which
would be a natural next step.

Run locally, from the project root:
    python src/portfolio_risk.py
    (on Windows: py src\\portfolio_risk.py)

Requires:
    - data/fx_rates_combined.csv (from data_collection.py)
    - results/volatility_forecast_summary.csv (from volatility_forecast.py)
"""

import os
import argparse
import json

import numpy as np
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(BASE_DIR, "data", "fx_rates_combined.csv")
FORECAST_PATH = os.path.join(BASE_DIR, "results", "volatility_forecast_summary.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

TRADING_DAYS_PER_YEAR = 252
Z_SCORE_95 = 1.645
N_SIMULATIONS = 20_000
RANDOM_SEED = 42  # fixed so results are reproducible for the demo/judges

# Example portfolio used when this script is run directly without
# --exposures. Mirrors a small trading company with exposure to three
# different trade partners at once.
DEFAULT_EXPOSURES = {
    "EURUSD": 100_000,
    "USDJPY": 80_000,
    "USDCNY": 150_000,
}


def load_return_matrix() -> pd.DataFrame:
    """Wide dataframe: one column per pair, one row per date, values = log returns.
    Only dates where ALL pairs have data are kept, so the correlation matrix
    is computed on a fair, aligned sample."""
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    wide_prices = df.pivot(index="date", columns="pair", values="close").sort_index()
    wide_returns = np.log(wide_prices / wide_prices.shift(1)).dropna()
    return wide_returns


def load_forecast_vols() -> pd.Series:
    """Latest GARCH 5-day-ahead annualized volatility forecast per pair,
    converted to a DAILY std-dev (the unit the simulation works in)."""
    forecast = pd.read_csv(FORECAST_PATH).set_index("pair")["forecast_5d_annualized_vol_pct"]
    daily_vol_pct = forecast / np.sqrt(TRADING_DAYS_PER_YEAR)
    return daily_vol_pct / 100  # convert from percent to a plain decimal


def simulate_portfolio(exposures: dict, horizon_days: int, n_sims: int = N_SIMULATIONS) -> dict:
    pairs = list(exposures.keys())

    returns = load_return_matrix()
    missing = [p for p in pairs if p not in returns.columns]
    if missing:
        raise ValueError(f"No historical data for: {missing}. Check pair names/spelling.")

    corr_matrix = returns[pairs].corr().values
    daily_vols = load_forecast_vols()[pairs].values
    horizon_vols = daily_vols * np.sqrt(horizon_days)  # scale to the chosen horizon

    # Cholesky decomposition turns independent random shocks into
    # correlated ones that match our historical correlation matrix.
    rng = np.random.default_rng(RANDOM_SEED)
    chol = np.linalg.cholesky(corr_matrix)
    independent_shocks = rng.standard_normal((n_sims, len(pairs)))
    correlated_shocks = independent_shocks @ chol.T

    simulated_returns = correlated_shocks * horizon_vols  # shape: (n_sims, n_pairs)

    exposure_vector = np.array([exposures[p] for p in pairs])
    # Dollar P&L per simulation: positive return in a pair * that pair's
    # exposure = a loss under our stated "adverse move = rate rises" assumption.
    simulated_pnl = -(simulated_returns * exposure_vector).sum(axis=1)

    diversified_var = float(np.percentile(simulated_pnl, 95))

    # Naive VaR: what you'd get by just adding up each pair's OWN parametric
    # VaR, as if the pairs moved completely independently of each other.
    naive_var = float(sum(
        exposures[p] * horizon_vols[i] * Z_SCORE_95 for i, p in enumerate(pairs)
    ))

    diversification_benefit = naive_var - diversified_var

    return {
        "pairs": pairs,
        "exposures_usd": exposures,
        "horizon_days": horizon_days,
        "total_exposure_usd": float(exposure_vector.sum()),
        "correlation_matrix": pd.DataFrame(corr_matrix, index=pairs, columns=pairs).round(3).to_dict(),
        "diversified_var_95_usd": round(diversified_var, 2),
        "naive_var_95_usd": round(naive_var, 2),
        "diversification_benefit_usd": round(diversification_benefit, 2),
        "diversification_benefit_pct": round(diversification_benefit / naive_var * 100, 1) if naive_var else 0.0,
        "_simulated_pnl": simulated_pnl,  # kept for optional plotting/inspection
    }


def main():
    parser = argparse.ArgumentParser(description="Portfolio-level FX risk via Monte Carlo simulation.")
    parser.add_argument(
        "--exposures", type=str, default=None,
        help='JSON string, e.g. \'{"EURUSD": 100000, "USDJPY": 80000}\'. '
             'Omit to use the built-in example portfolio.'
    )
    parser.add_argument("--horizon", type=int, default=30)
    args = parser.parse_args()

    exposures = json.loads(args.exposures) if args.exposures else DEFAULT_EXPOSURES

    result = simulate_portfolio(exposures, args.horizon)

    print(f"Portfolio: {result['exposures_usd']}")
    print(f"Total exposure: ${result['total_exposure_usd']:,.0f} | Horizon: {result['horizon_days']} days\n")
    print("Correlation between pairs (from 5y history):")
    print(pd.DataFrame(result["correlation_matrix"]).to_string())
    print(f"\nDiversified portfolio VaR (95%, Monte Carlo): ${result['diversified_var_95_usd']:,.2f}")
    print(f"Naive VaR (if pairs were independent):         ${result['naive_var_95_usd']:,.2f}")
    print(f"Diversification benefit:                       ${result['diversification_benefit_usd']:,.2f} "
          f"({result['diversification_benefit_pct']}% lower than the naive estimate)")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = {k: v for k, v in result.items() if not k.startswith("_")}
    out_path = os.path.join(RESULTS_DIR, "portfolio_risk_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()
