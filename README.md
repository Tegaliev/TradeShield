TradeShield
A currency risk radar for exporters and importers — GIBC V2, Track 02 (Applied:
Medical Technology & Finance)
This is a research prototype built for a hackathon. It is not a financial
product, not a diagnostic tool, and not financial advice. It must not be
used for real trading, hedging, or investment decisions.
The problem
Mei runs a small electronics trading company in Shenzhen. Every month she
pays a supplier in Japan in yen, and gets paid by a customer in Europe in
euros. Between the invoice date and the payment date, the exchange rate
moves — sometimes in her favor, sometimes against her. She has no easy
way to answer three questions that actually matter to her business:
1. How risky is this one payment, right now?
2. I'm exposed to yen AND euros at the same time — what's my real,
combined risk, given that these currencies don't move independently?
3. Would it actually have been worth paying a bank to hedge this, based
on what's happened historically?
This project answers all three, using real market data instead of gut feel.
How FX risk actually works
Currency pairs don't drift randomly at a constant speed — they go through
calm periods and turbulent periods, and turbulent periods tend to cluster
together (a currency that moved a lot yesterday is more likely to move a
lot again today than a currency that's been quiet for weeks). This
"volatility clustering" is exactly what a GARCH model is built to
capture: instead of a single "average risk" number, it gives a
forward-looking estimate of how choppy a currency is right now.
Some currencies, like the Chinese yuan, are managed floats — a central
bank actively keeps them inside a narrow band. That shows up in the data
as low day-to-day volatility, but occasional sharp one-off jumps when the
band itself moves. A currency like the Japanese yen, which floats freely,
behaves very differently: more day-to-day noise, but fewer sudden jumps.
Both patterns show up clearly in this project's results below.
Building it — step by step
1. Pulling 5 years of real FX data
Five currency pairs (EUR/USD, GBP/USD, USD/CNY, USD/INR, USD/JPY),
downloaded from Yahoo Finance via yfinance . No API key needed, no cost —
just a clean 5-year daily history to work with.
<!-- paste a screenshot of the terminal output from data_collection.py here -->
2. Looking at the data before modeling anything
Rolling volatility, return distributions, and a year-by-year heatmap.
This is where the managed-float pattern first showed up: USD/CNY has
the lowest average volatility of the five pairs (5.43% annualized) but
one of the highest kurtosis values (9.3) — a strong early signal that its
risk profile is fundamentally different from a freely floating pair.
<!-- paste a screenshot of results/volatility_heatmap.png here -->
3. Forecasting volatility with GARCH(1,1)
Fit per currency pair, evaluated on a held-out test period so the
reported accuracy isn't just curve-fitting. One thing worth flagging:
GARCH's current forecast can disagree meaningfully with the long-run
historical average — USD/CNY's forecast came out at 1.89% vs. its 5.43%
historical average, meaning the model correctly picked up that the yuan
is unusually calm right now, not just "calm on average."
<!-- paste a screenshot of one of the results/garch_forecast_*.png plots here -->
4. Turning a forecast into a risk score business owners can use
A 0-100 risk score plus a 95% Value-at-Risk dollar figure. Be careful
with the sign convention here — it's easy to flip "a rate increase" and
"a rate decrease" by accident when you're translating a statistical
return into a dollar gain or loss. I actually did get this backwards on
my first pass (see the AI disclosure section below for how it got caught
and fixed) — worth double-checking against a known real-world trend
before trusting the output.
5. Going from one deal to a whole portfolio
Real companies rarely have just one currency exposure. This step adds a
Monte Carlo simulation — 20,000 simulated scenarios, generated so they
respect the actual historical correlation between currency pairs (via
Cholesky decomposition), not just their individual volatility. The
payoff: a portfolio of EUR/USD, USD/JPY, and USD/CNY comes out with
roughly 50% lower risk than you'd estimate by naively adding up each
pair's risk on its own, because EUR/USD and USD/JPY move in partly
opposite directions.
<!-- paste a screenshot of the Portfolio tab's correlation heatmap here -->
6. Testing the "would hedging have helped?" question on real history
A backtest over every 30-day window in the last 5 years. For USD/JPY,
staying unhedged lost money in 65.7% of those windows — consistent with
the yen's well-known multi-year weakening trend — with a worst-case loss
around $6,300 on a $100,000 deal. Hedging would have avoided that loss
completely, at the cost of also giving up the best-case windows.
<!-- paste a screenshot of results/hedge_backtest_USDJPY.png here -->
7. Making it readable for someone who isn't a data scientist
All of the above produces numbers. An LLM (DeepSeek-V3.2, via the
Featherless sponsor API) turns those numbers into a short business memo:
what's happening, why the risk score is what it is, and 2-3 concrete
next steps — forward contracts, options, or doing nothing if the risk is
genuinely small.
Finalizing: the dashboard
Everything above is wired into one Streamlit app with three tabs — Single
Deal, Portfolio, and Hedge Backtest — plus a risk gauge and a one-click
PDF export of the full report.
<!-- paste a screenshot of the Single Deal tab (with the gauge) here -->
<!-- paste a screenshot of the Portfolio tab here -->
To get a screenshot into this README with a real GitHub-hosted link
(like the images above are meant to have): open README.md for editing
directly on github.com, then drag-and-drop or paste your screenshot into
the text box. GitHub uploads it automatically and inserts the image
markdown for you — no separate image hosting needed.
Key results
USD/CNY long-run volatility: 5.43% annualized (lowest of the 5 pairs) — managed float
USD/JPY long-run volatility: 9.87% annualized (highest) — current GARCH forecast
even higher, at 11.26%
Portfolio diversification benefit (3-currency example): ~50% lower VaR than the naive
sum
USD/JPY, 30-day unhedged exposure, 5-year backtest: 65.7% of windows lost money;
worst-case (95th pctile) loss $6,319 on $100,000
Project structure
fx-risk-scorer/
├── src/
│   
├── data_collection.py       # downloads 5y of daily FX data (yfinance)
│   
│   
│   
│   
│   
│   
│   
├── eda_and_volatility.py    # rolling volatility, plots, summary stats
├── volatility_forecast.py   # GARCH(1,1) forecasting + evaluation
├── risk_scoring.py          # single-deal 0-100 risk score + 95% VaR
├── portfolio_risk.py        # multi-currency Monte Carlo VaR + correlation
├── backtest_hedging.py      # historical hedged vs. unhedged backtest
├── llm_report.py            # LLM business report (Featherless API)
└── dashboard.py             # 3-tab Streamlit UI
├── data/                        # downloaded FX data (not committed; see .gitignore)
├── results/                     # generated plots, metrics, and reports
├── requirements.txt
└── README.md
Setup
pip install -r requirements.txt
Create a .env file in the project root (only needed for the LLM report step):
FEATHERLESS_API_KEY=fw-your-key-here
Running the pipeline
python src/data_collection.py
python src/eda_and_volatility.py
python src/volatility_forecast.py
python src/risk_scoring.py
python src/portfolio_risk.py
python src/backtest_hedging.py --pair USDJPY --exposure 100000 --horizon 30
python src/llm_report.py --pair USDJPY --exposure 250000 --horizon 30
streamlit run src/dashboard.py
(On Windows, use py instead of python if python isn't recognized.)
Methodology and limitations
Sign convention: every P&L calculation assumes "a rate increase is
adverse" for the exposure being measured. A real company's actual
exposure direction depends on which side of the trade they're on —
this prototype doesn't model that distinction yet.
Relative risk score: the 0-100 score is relative only to the 5
currency pairs this project tracks, not the entire FX market.
VaR scaling: uses the standard square-root-of-time rule to scale
annualized volatility to a chosen horizon — a common approximation,
not a full risk-management-grade model.
Monte Carlo simulation: assumes the historical correlation matrix
stays stable, which is a simplification — real correlations shift,
especially during crises.
Hedging backtest: treats hedging as a free "zero-cost forward,"
ignoring the interest-rate differential real forward contracts price
in, and uses overlapping (non-independent) historical windows.
Data ethics and scope (per Track 02 rules)
All data is publicly available market data; no personal or identifiable
data is used. This project does not operate on real trades or real
money — all scoring, simulation, and backtesting is for research and
demonstration purposes only.
AI tools used (disclosure)
Claude (Anthropic): used throughout for planning the architecture,
writing and debugging every script in this repo, and drafting this
README. Claude also caught a P&L sign-convention bug during
development — an early version of the risk scoring and portfolio
simulation had the direction of "rate up = loss" flipped, found by
cross-checking a backtest result against USD/JPY's known real-world
trend and fixed before the final submission (see git history).
GitHub Copilot: used for initial local environment setup
(Python/Git installation) at the start of the project.
DeepSeek-V3.2 (via the Featherless API): used at runtime, inside
the app itself, to generate the plain-language business report — a
core product feature, not just a development aid.
I can explain how every part of this project works, including the
statistics and financial reasoning behind the volatility model, the
Monte Carlo simulation, and the risk scoring logic.
Built With
Python, pandas, numpy, yfinance, matplotlib, arch (GARCH models),
scikit-learn, Monte Carlo simulation, Cholesky decomposition, Streamlit,
OpenAI Python SDK (used against the Featherless API), python-dotenv,
DeepSeek-V3.2 (via Featherless), Claude (Anthropic), GitHub Copilot,
Git, GitHub
TradeShield — built solo for Global Innovation Build Challenge V2, Track 02.
