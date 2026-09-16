"""
eda_and_volatility.py

Loads the FX data downloaded by data_collection.py, computes daily returns
and rolling volatility, and produces the plots + summary metrics you need
for both your own analysis and your hackathon screenshots.

Run locally, from the project root (same folder as requirements.txt):
    python src/eda_and_volatility.py
    (on Windows, if "python" is not recognized, use "py" instead)

Requires data/fx_rates_combined.csv to already exist — run
src/data_collection.py first if it doesn't.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # write PNGs directly, no need for a display window
import matplotlib.pyplot as plt

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(BASE_DIR, "data", "fx_rates_combined.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

# Trading days per year, used to annualize daily volatility figures.
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.02  # 2% annual, used only for the Sharpe ratio estimate

ROLLING_WINDOWS = [30, 90, 252]


def load_data() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Could not find {DATA_PATH}. Run src/data_collection.py first "
            f"to download the FX data."
        )
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df = df.sort_values(["pair", "date"]).reset_index(drop=True)
    return df


def add_returns_and_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """Add log return and rolling volatility columns, computed per pair
    so one pair's history never leaks into another pair's rolling window."""
    out = []
    for pair, g in df.groupby("pair"):
        g = g.copy()
        g["log_return"] = np.log(g["close"] / g["close"].shift(1))
        for window in ROLLING_WINDOWS:
            # Annualized rolling volatility: daily std * sqrt(trading days/year)
            g[f"volatility_{window}d"] = (
                g["log_return"].rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
            )
        out.append(g)
    return pd.concat(out).reset_index(drop=True)


def compute_summary_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """One row of summary stats per currency pair."""
    rows = []
    for pair, g in df.groupby("pair"):
        returns = g["log_return"].dropna()
        if returns.empty:
            continue

        annualized_return = returns.mean() * TRADING_DAYS_PER_YEAR
        annualized_vol = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        sharpe = (
            (annualized_return - RISK_FREE_RATE) / annualized_vol
            if annualized_vol > 0
            else np.nan
        )

        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        rows.append({
            "pair": pair,
            "annualized_return_pct": round(annualized_return * 100, 2),
            "annualized_volatility_pct": round(annualized_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3) if pd.notna(sharpe) else None,
            "max_drawdown_pct": round(max_drawdown * 100, 2),
            "skewness": round(returns.skew(), 3),
            "kurtosis": round(returns.kurtosis(), 3),
            "n_observations": len(returns),
        })
    return pd.DataFrame(rows)


def plot_prices(df: pd.DataFrame, out_path: str):
    pairs = df["pair"].unique()
    fig, axes = plt.subplots(len(pairs), 1, figsize=(10, 2.5 * len(pairs)), sharex=False)
    if len(pairs) == 1:
        axes = [axes]
    for ax, pair in zip(axes, pairs):
        g = df[df["pair"] == pair]
        ax.plot(g["date"], g["close"], linewidth=0.9)
        ax.set_title(pair)
        ax.set_ylabel("close")
    fig.suptitle("FX closing prices, last 5 years")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_rolling_volatility(df: pd.DataFrame, out_path: str, window: int = 30):
    col = f"volatility_{window}d"
    fig, ax = plt.subplots(figsize=(10, 5))
    for pair, g in df.groupby("pair"):
        ax.plot(g["date"], g[col], label=pair, linewidth=1.0)
    ax.set_title(f"{window}-day rolling annualized volatility")
    ax.set_ylabel("annualized volatility")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_return_distributions(df: pd.DataFrame, out_path: str):
    pairs = df["pair"].unique()
    fig, axes = plt.subplots(1, len(pairs), figsize=(3.2 * len(pairs), 3.5), sharey=True)
    if len(pairs) == 1:
        axes = [axes]
    for ax, pair in zip(axes, pairs):
        returns = df[df["pair"] == pair]["log_return"].dropna()
        ax.hist(returns, bins=60, density=True)
        ax.set_title(pair)
    fig.suptitle("Distribution of daily log returns")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_volatility_heatmap(df: pd.DataFrame, out_path: str, window: int = 30):
    """Pair x year average volatility, as a simple heatmap."""
    col = f"volatility_{window}d"
    tmp = df.copy()
    tmp["year"] = tmp["date"].dt.year
    pivot = tmp.pivot_table(index="pair", columns="year", values=col, aggfunc="mean")

    fig, ax = plt.subplots(figsize=(1.1 * len(pivot.columns) + 2, 1 + 0.6 * len(pivot.index)))
    im = ax.imshow(pivot.values, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title(f"Average {window}-day volatility by year")
    fig.colorbar(im, ax=ax, label="annualized volatility")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_cumulative_returns(df: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(10, 5))
    for pair, g in df.groupby("pair"):
        returns = g["log_return"].fillna(0)
        cumulative = (1 + returns).cumprod() * 100  # start at 100
        ax.plot(g["date"], cumulative, label=pair, linewidth=1.0)
    ax.set_title("Cumulative return (starting value = 100)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Loading data...")
    df = load_data()

    print("Computing returns and rolling volatility...")
    df = add_returns_and_volatility(df)

    print("Computing summary metrics...")
    metrics = compute_summary_metrics(df)
    metrics_path = os.path.join(RESULTS_DIR, "volatility_metrics.csv")
    metrics.to_csv(metrics_path, index=False)
    print(f"  saved -> {metrics_path}")
    print(metrics.to_string(index=False))

    print("\nGenerating plots...")
    plot_prices(df, os.path.join(RESULTS_DIR, "prices.png"))
    plot_rolling_volatility(df, os.path.join(RESULTS_DIR, "rolling_volatility_30d.png"), window=30)
    plot_return_distributions(df, os.path.join(RESULTS_DIR, "returns_distribution.png"))
    plot_volatility_heatmap(df, os.path.join(RESULTS_DIR, "volatility_heatmap.png"), window=30)
    plot_cumulative_returns(df, os.path.join(RESULTS_DIR, "cumulative_returns.png"))

    print(f"\nAll done. Check the '{RESULTS_DIR}' folder for PNGs and the metrics CSV.")


if __name__ == "__main__":
    main()
