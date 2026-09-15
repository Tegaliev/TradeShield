"""
data_collection.py

Downloads historical daily FX rates for a set of currency pairs relevant to
international trade and saves them as clean CSVs in data/.

Run locally (requires internet access):
    python src/data_collection.py

Yahoo Finance tickers for FX pairs look like "EURUSD=X". Yahoo quotes are
always expressed as FOREIGN currency per 1 USD or as BASE/QUOTE depending on
convention; we normalize everything to "units of QUOTE per 1 unit of BASE"
in a comment next to each pair so there's no ambiguity later in the pipeline.
"""

import os
import sys
import pandas as pd
import yfinance as yf

# pair_name -> (yahoo_ticker, human description)
CURRENCY_PAIRS = {
    "EURUSD": ("EURUSD=X", "Euro area / United States"),
    "USDJPY": ("USDJPY=X", "United States / Japan"),
    "GBPUSD": ("GBPUSD=X", "United Kingdom / United States"),
    "USDCNY": ("USDCNY=X", "United States / China"),
    "USDINR": ("USDINR=X", "United States / India"),
}

YEARS_OF_HISTORY = 5
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def fetch_pair(pair_name: str, ticker: str) -> pd.DataFrame:
    """Download daily OHLC data for a single FX ticker from Yahoo Finance."""
    print(f"Downloading {pair_name} ({ticker}) ...")
    df = yf.download(
        ticker,
        period=f"{YEARS_OF_HISTORY}y",
        interval="1d",
        auto_adjust=False,
        progress=False,
    )

    if df.empty:
        raise ValueError(
            f"No data returned for {ticker}. Check your internet connection "
            f"or whether Yahoo Finance changed this ticker symbol."
        )

    # yfinance sometimes returns a MultiIndex column header when downloading
    # a single ticker depending on version; flatten it defensively.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns=str.lower)
    df.index.name = "date"
    df["pair"] = pair_name
    return df[["open", "high", "low", "close", "pair"]]


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    all_frames = []
    failed = []

    for pair_name, (ticker, _desc) in CURRENCY_PAIRS.items():
        try:
            df = fetch_pair(pair_name, ticker)
            out_path = os.path.join(DATA_DIR, f"{pair_name}.csv")
            df.to_csv(out_path)
            print(f"  saved {len(df)} rows -> {out_path}")
            all_frames.append(df)
        except Exception as exc:
            print(f"  FAILED for {pair_name}: {exc}", file=sys.stderr)
            failed.append(pair_name)

    if all_frames:
        combined = pd.concat(all_frames)
        combined_path = os.path.join(DATA_DIR, "fx_rates_combined.csv")
        combined.to_csv(combined_path)
        print(f"\nCombined dataset saved -> {combined_path} ({len(combined)} rows)")

    if failed:
        print(f"\nWarning: failed to download {failed}. Re-run the script "
              f"later or check ticker symbols on finance.yahoo.com.")
        sys.exit(1)


if __name__ == "__main__":
    main()
