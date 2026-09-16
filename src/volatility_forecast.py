"""
volatility_forecast.py

Fits a GARCH(1,1) model per currency pair to forecast near-term volatility,
evaluates it on a held-out test period, and saves the "current" forecast
that step 4 (risk scoring) will use.

What is GARCH, in plain terms:
    GARCH ("Generalized AutoRegressive Conditional Heteroskedasticity") is
    the standard model in finance for one simple idea: volatility clusters.
    Calm periods tend to stay calm, and turbulent periods tend to stay
    turbulent, at least for a while. GARCH(1,1) predicts tomorrow's
    volatility from (a) how volatile things were yesterday, and (b) how
    volatile things have been "on average" recently. It does not predict
    the direction of the exchange rate — only how much it's likely to move.

Run locally, from the project root:
    python src/volatility_forecast.py
    (on Windows: py src\\volatility_forecast.py)

Requires data/fx_rates_combined.csv (from data_collection.py).
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from arch import arch_model

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_PATH = os.path.join(BASE_DIR, "data", "fx_rates_combined.csv")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

TRADING_DAYS_PER_YEAR = 252
TRAIN_FRACTION = 0.8       # first 80% of history used to fit the model
FORECAST_HORIZONS = [1, 5]  # days ahead we report a forward-looking forecast for


def load_returns() -> dict:
    """Return {pair: pd.Series of log_return in percent, indexed by date}."""
    df = pd.read_csv(DATA_PATH, parse_dates=["date"]).sort_values(["pair", "date"])
    out = {}
    for pair, g in df.groupby("pair"):
        log_ret = np.log(g["close"] / g["close"].shift(1)).dropna()
        # GARCH fits more reliably on returns scaled to roughly 1-unit size;
        # percent log returns (e.g. 0.5 instead of 0.005) is the standard convention.
        log_ret_pct = (log_ret * 100).values
        dates = g["date"].iloc[1:].values  # aligns with the shift(1) above
        out[pair] = pd.Series(log_ret_pct, index=dates)
    return out


def fit_and_evaluate(pair: str, returns_pct: pd.Series) -> dict:
    """Fit GARCH(1,1) on the training slice, evaluate one-step-ahead
    forecasts on the held-out test slice, and produce a forward forecast
    from the full history for use in risk scoring."""
    n = len(returns_pct)
    split = int(n * TRAIN_FRACTION)
    test = returns_pct.iloc[split:]

    if len(test) < 30:
        raise ValueError(f"{pair}: not enough data for a meaningful test split.")

    # --- Fit on the training period only, then score on the unseen test period ---
    # Important: we build the model on the FULL series, but tell .fit() to only
    # use data up to `split` (last_obs) when estimating the GARCH parameters.
    # This is the arch library's documented pattern for a fair out-of-sample
    # test: the model "knows about" the full timeline for forecasting purposes,
    # but the parameters themselves are learned only from the training period,
    # then held fixed while we score them against the unseen test period.
    model = arch_model(returns_pct, mean="Zero", vol="Garch", p=1, q=1, dist="normal")
    train_res = model.fit(last_obs=split, disp="off")

    forecasts = train_res.forecast(horizon=1, start=split, reindex=False)
    predicted_variance_pct2 = forecasts.variance.values.flatten()

    # Realized variance proxy: squared return on the day being forecast.
    # This is noisy (it's a proxy, not the "true" variance) but is the
    # standard, simplest way to evaluate a volatility forecast.
    realized_variance_pct2 = test.values ** 2

    rmse_variance = float(np.sqrt(np.mean((predicted_variance_pct2 - realized_variance_pct2) ** 2)))
    mae_variance = float(np.mean(np.abs(predicted_variance_pct2 - realized_variance_pct2)))

    predicted_vol_pct = np.sqrt(predicted_variance_pct2)
    realized_vol_pct = np.sqrt(realized_variance_pct2)
    rmse_vol = float(np.sqrt(np.mean((predicted_vol_pct - realized_vol_pct) ** 2)))

    # --- Refit on ALL available data to get the most current forward forecast ---
    # (same model definition, just without the last_obs cutoff this time)
    full_res = model.fit(disp="off")
    forward = full_res.forecast(horizon=max(FORECAST_HORIZONS), reindex=False)
    forward_variance_pct2 = forward.variance.values.flatten()  # one value per horizon day

    forward_forecasts = {}
    for h in FORECAST_HORIZONS:
        # Average the daily variance forecast up to horizon h, then annualize.
        avg_daily_variance_pct2 = forward_variance_pct2[:h].mean()
        annualized_vol_pct = np.sqrt(avg_daily_variance_pct2 * TRADING_DAYS_PER_YEAR)
        forward_forecasts[f"forecast_{h}d_annualized_vol_pct"] = round(float(annualized_vol_pct), 3)

    return {
        "pair": pair,
        "n_train": split,
        "n_test": len(test),
        "rmse_variance_pct2": round(rmse_variance, 4),
        "mae_variance_pct2": round(mae_variance, 4),
        "rmse_volatility_pct": round(rmse_vol, 4),
        **forward_forecasts,
        "_train_res": train_res,        # kept only for plotting below
        "_test_index": test.index,
        "_predicted_vol_pct": predicted_vol_pct,
        "_realized_vol_pct": realized_vol_pct,
    }


def plot_forecast_vs_realized(pair: str, result: dict, out_path: str):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(result["_test_index"], result["_realized_vol_pct"], label="realized (proxy)", alpha=0.6)
    ax.plot(result["_test_index"], result["_predicted_vol_pct"], label="GARCH forecast", linewidth=1.3)
    ax.set_title(f"{pair}: one-step-ahead volatility forecast vs realized (test period)")
    ax.set_ylabel("daily volatility (%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    returns_by_pair = load_returns()

    summary_rows = []
    for pair, returns_pct in returns_by_pair.items():
        print(f"Fitting GARCH(1,1) for {pair}...")
        result = fit_and_evaluate(pair, returns_pct)

        plot_path = os.path.join(RESULTS_DIR, f"garch_forecast_{pair}.png")
        plot_forecast_vs_realized(pair, result, plot_path)

        # drop the plotting-only fields before saving the summary table
        row = {k: v for k, v in result.items() if not k.startswith("_")}
        summary_rows.append(row)
        print(f"  test RMSE (volatility, %): {row['rmse_volatility_pct']}")

    summary = pd.DataFrame(summary_rows)
    out_path = os.path.join(RESULTS_DIR, "volatility_forecast_summary.csv")
    summary.to_csv(out_path, index=False)
    print(f"\nSaved forecast summary + latest forward forecasts -> {out_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
