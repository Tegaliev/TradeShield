# FX Volatility & Export Risk Scorer

**Global Innovation Build Challenge V2 — Track 02 (Applied: Medical Technology & Finance)**

> This is a research prototype built for a hackathon. It is not a financial
> product, not a diagnostic tool, and not financial advice. It must not be
> used for real trading, hedging, or investment decisions.

## What this is

A risk-management tool for exporters and importers who are exposed to
currency movements on their trade deals. It answers three questions a
real trade business would actually ask:

1. **"How risky is this one deal?"** — a GARCH(1,1) volatility forecast
   turned into a 0-100 risk score, a dollar Value-at-Risk figure, and a
   plain-language LLM-generated business report.
2. **"What if I have several deals in different currencies at once?"** —
   a Monte Carlo simulation of the whole portfolio that accounts for how
   currencies actually move together (correlation), showing the real
   diversification benefit in dollar terms.
3. **"Would hedging actually have helped, historically?"** — a backtest
   over 5 years of real data comparing hedged vs. unhedged outcomes for
   deals of this size and horizon.

**Pipeline:** historical FX data → volatility analysis → GARCH volatility
forecast → (single-deal risk score + VaR) / (portfolio Monte Carlo VaR) /
(historical hedge backtest) → LLM-generated business report → interactive
3-tab dashboard with a risk gauge and PDF export

## Key findings

Using 5 years of daily data (2021-2026) for EUR/USD, GBP/USD, USD/CNY,
USD/INR, and USD/JPY:

- **USD/CNY has by far the lowest long-run volatility (5.43% annualized)**
  of the pairs tracked — consistent with the yuan being a managed float
  that the People's Bank of China actively keeps in a narrow band.
- **USD/JPY has the highest long-run volatility (9.87% annualized)**, and
  its current GARCH forecast (11.26%) is even higher than its historical
  average — the model picks up an actively elevated-risk period.
- **USD/CNY and USD/INR both show high kurtosis** (9.3 and 10.4) despite
  low day-to-day volatility — "calm most of the time, occasional sharp
  jump" behavior typical of managed currencies.
- **Diversification is worth real money**: a 3-currency example portfolio
  (EUR/USD + USD/JPY + USD/CNY) has a Monte Carlo 95% VaR roughly
  **50% lower** than the naive sum of each pair's individual VaR, because
  EUR/USD and USD/JPY are negatively correlated (-0.49) over this period.
- **Hedging removes tail risk, not average risk**: backtesting a 30-day
  USD/JPY exposure over the last 5 years, an unhedged position lost money
  in **65.7% of historical windows** (consistent with the yen's sustained
  weakening trend), with a worst-case (95th percentile) loss of $6,319 on
  a $100,000 deal — but also gave up gains of $5,931 or more in the best
  windows. Hedging trades away the upside to remove that downside; it is
  not a way to profit on average.

## Project structure

```
fx-risk-scorer/
├── src/
│   ├── data_collection.py       # downloads 5y of daily FX data (yfinance)
│   ├── eda_and_volatility.py    # rolling volatility, plots, summary stats
│   ├── volatility_forecast.py   # GARCH(1,1) forecasting + evaluation
│   ├── risk_scoring.py          # single-deal 0-100 risk score + 95% VaR
│   ├── portfolio_risk.py        # multi-currency Monte Carlo VaR + correlation
│   ├── backtest_hedging.py      # historical hedged vs. unhedged backtest
│   ├── llm_report.py            # LLM business report (Featherless API)
│   └── dashboard.py             # 3-tab Streamlit UI (Single Deal / Portfolio / Backtest)
├── data/                        # downloaded FX data (not committed; see below)
├── results/                     # generated plots, metrics, and reports
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
```

Create a file named `.env` in the project root with your Featherless API
key (only needed for the LLM report; everything else works without it):

```
FEATHERLESS_API_KEY=fw-your-key-here
```

## Running the pipeline

Run these in order from the project root:

```bash
python src/data_collection.py        # downloads FX data into data/
python src/eda_and_volatility.py     # volatility analysis + plots
python src/volatility_forecast.py    # GARCH forecasting model
python src/risk_scoring.py           # single-deal risk score + VaR
python src/portfolio_risk.py         # multi-currency Monte Carlo VaR
python src/backtest_hedging.py --pair USDJPY --exposure 100000 --horizon 30
python src/llm_report.py --pair USDJPY --exposure 250000 --horizon 30
streamlit run src/dashboard.py       # interactive 3-tab dashboard
```

(On Windows, replace `python` with `py` if `python` is not recognized.)

## Methodology and limitations

Stated plainly, as any research prototype should:

- **Sign convention**: every P&L calculation in this project assumes "a
  rate increase is adverse" for the exposure being measured. A real
  company's actual exposure direction depends on whether they're paying
  or receiving the foreign currency — this prototype does not model that
  distinction, which would be a natural next step.
- **Relative risk score**: the 0-100 score is calculated only against the
  small set of currency pairs this project tracks (currently 5), not
  against the entire FX market.
- **VaR scaling**: Value-at-Risk uses the standard square-root-of-time
  rule to scale annualized volatility to a chosen horizon — a common
  first-order approximation, not a full risk-management-grade model.
- **Monte Carlo simulation**: the portfolio simulation uses each pair's
  current GARCH volatility forecast combined with the historical
  correlation matrix (via Cholesky decomposition) to generate 20,000
  correlated scenarios. It assumes correlations are stable, which is a
  simplification — real correlations shift, especially in crises.
- **Hedging backtest**: treats hedging as a free "zero-cost forward,"
  ignoring the interest-rate differential (covered interest rate parity)
  that real forward contracts price in. It also uses overlapping
  historical windows, which are not fully independent observations —
  the resulting distribution is illustrative, not a rigorous statistical
  sample.

## Data ethics and scope (per Track 02 rules)

- All data used is publicly available market data; no personal, private,
  or identifiable data of any kind is used.
- This project does not operate on real trades or real money. All
  scoring, simulation, and backtesting is for research/demonstration
  purposes only.

## AI tools used (disclosure)

In the interest of full transparency, as required by the hackathon rules:

- **Claude (Anthropic)**: used throughout for planning the project
  architecture, writing and debugging all Python scripts (data
  collection, volatility analysis, GARCH forecasting, risk scoring,
  Monte Carlo portfolio simulation, the hedging backtest, LLM
  integration, and the Streamlit dashboard), and drafting this README.
  Claude also caught and fixed a P&L sign-convention bug during
  development (see git history).
- **GitHub Copilot**: used for initial local environment setup and
  troubleshooting (Python/Git installation) at the start of the project.
- **DeepSeek-V3.2** (via the Featherless API): used at runtime, inside
  the application itself, to generate the plain-language business risk
  report from the quantitative risk assessment — a core feature of the
  product, not just a development aid.

I can explain how every part of this project works, including the
statistical/financial reasoning behind the volatility model, the Monte
Carlo simulation, and the risk scoring logic.

## Built With

Python, pandas, numpy, yfinance, matplotlib, arch (GARCH models),
scikit-learn, Monte Carlo simulation, Cholesky decomposition, Streamlit,
OpenAI Python SDK (used against the Featherless API), python-dotenv,
DeepSeek-V3.2 (via Featherless), Claude (Anthropic), GitHub Copilot,
Git, GitHub
