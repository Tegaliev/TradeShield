"""
backtest_hedging.py

Answers a concrete question: "if this company had hedged every deal of
this size and horizon over the past 5 years, how would that have compared
to never hedging at all?"

Method:
    Take every possible historical window of `horizon` trading days (e.g.
    every 30-day window in the last 5 years, overlapping). For each
    window, compute what an UNHEDGED position would have gained or lost
    from the actual currency move. A HEDGED position, by definition,
    locks in today's rate and has zero currency P&L (see the simplifying
    assumption below). Comparing the distribution of unhedged outcomes to
    the guaranteed zero of hedging shows the real trade-off: hedging
    doesn't make you money on average, it removes the tail risk.

Simplifying assumption (stated plainly): this treats hedging as free
(a "zero-cost forward"), i.e. it ignores the interest-rate differential
between the two currencies that real forward contracts price in (covered
interest rate parity). Modeling that properly would require interest
rate data for each currency, which is out of scope for this prototype.
This means the backtest isolates the value of REMOVING currency risk,
not the full real-world cost/benefit of a specific bank's forward quote.

Overlapping windows are not fully independent observations of risk (a
5-year history of 30-day windows has a lot of shared days between
neighboring windows), so treat the resulting distribution as illustrative,
not a rigorous i.i.d. sample -- this is noted in the README too.

Run locally, from the project root:
    python src/backtest_hedging.py --pair USDJPY --exposure 100000 --horizon 30
    (on Windows: py src\\backtest_hedging.py --pair USDJPY --exposure 100000 --horizon 30)

Requires data/fx_rates_combined.csv (from data_collection.py).
"""

import os
import argparse

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(BASE_DIR, "data", "fx_rates_combined.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "results")


def load_prices(pair: str) -> pd.Series:
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df = df[df["pair"] == pair].sort_values("date")
    if df.empty:
        available = sorted(pd.read_csv(DATA_PATH)["pair"].unique())
        raise ValueError(f"No data for pair '{pair}'. Available pairs: {available}")
    return df.set_index("date")["close"]


def rolling_window_pnl(prices: pd.Series, exposure_usd: float, horizon_days: int) -> np.ndarray:
    """Unhedged dollar P&L for every overlapping historical window of
    length `horizon_days`. Same sign convention as the rest of the
    project: a RISE in the rate is treated as adverse (a loss)."""
    start_prices = prices.values[:-horizon_days]
    end_prices = prices.values[horizon_days:]
    simple_return = (end_prices - start_prices) / start_prices
    pnl = exposure_usd * simple_return  # rate up => positive pnl => a loss, per the stated sign convention
    return pnl


def plot_distribution(pnl: np.ndarray, pair: str, horizon_days: int, out_path: str):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(pnl, bins=60, alpha=0.75, label="Unhedged outcome (historical windows)")
    ax.axvline(0, color="black", linewidth=2, label="Hedged outcome (locked at $0 by definition)")
    ax.axvline(np.percentile(pnl, 95), color="red", linestyle="--", label="95th percentile (worst-case loss tail)")
    ax.set_title(f"{pair}: unhedged vs. hedged outcome distribution, {horizon_days}-day windows")
    ax.set_xlabel("dollar P&L")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def summarize(pnl: np.ndarray, exposure_usd: float) -> dict:
    return {
        "n_windows": len(pnl),
        "mean_unhedged_pnl_usd": round(float(np.mean(pnl)), 2),
        "median_unhedged_pnl_usd": round(float(np.median(pnl)), 2),
        # Sign convention: pnl > 0 means a LOSS (the rate rose against you).
        # So the worst-case tail is the HIGH end of the distribution (95th
        # percentile), and the best-case tail is the LOW end (5th percentile,
        # where a negative pnl value represents a gain).
        "worst_case_loss_usd_95th_pctile": round(float(np.percentile(pnl, 95)), 2),
        "best_case_gain_usd_5th_pctile": round(float(-np.percentile(pnl, 5)), 2),
        "pct_windows_with_a_loss": round(float((pnl > 0).mean() * 100), 1),
        "largest_single_loss_usd": round(float(pnl.max()), 2),
        "largest_single_gain_usd": round(float(-pnl.min()), 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Backtest hedged vs. unhedged outcomes for one currency pair.")
    parser.add_argument("--pair", required=True, help="e.g. USDJPY")
    parser.add_argument("--exposure", type=float, default=100_000)
    parser.add_argument("--horizon", type=int, default=30)
    args = parser.parse_args()

    prices = load_prices(args.pair)
    pnl = rolling_window_pnl(prices, args.exposure, args.horizon)
    stats = summarize(pnl, args.exposure)

    print(f"{args.pair}: {stats['n_windows']} overlapping {args.horizon}-day windows over the "
          f"available history, exposure ${args.exposure:,.0f}\n")
    for k, v in stats.items():
        print(f"{k}: {v}")

    print(
        f"\nIn plain terms: over this history, an UNHEDGED position of this size and horizon "
        f"lost money in {stats['pct_windows_with_a_loss']}% of the time windows we looked at. "
        f"In the worst 5% of cases, the loss was ${stats['worst_case_loss_usd_95th_pctile']:,.2f} or more. "
        f"A HEDGED position would have had $0 currency P&L in every single one of those windows -- "
        f"the cost of that certainty is giving up the best-case windows too, where staying unhedged "
        f"would have gained roughly ${stats['best_case_gain_usd_5th_pctile']:,.2f} or more."
    )

    os.makedirs(RESULTS_DIR, exist_ok=True)
    plot_path = os.path.join(RESULTS_DIR, f"hedge_backtest_{args.pair}.png")
    plot_distribution(pnl, args.pair, args.horizon, plot_path)

    summary_path = os.path.join(RESULTS_DIR, f"hedge_backtest_{args.pair}.csv")
    pd.DataFrame([stats]).to_csv(summary_path, index=False)
    print(f"\nSaved plot -> {plot_path}")
    print(f"Saved summary -> {summary_path}")


if __name__ == "__main__":
    main()
