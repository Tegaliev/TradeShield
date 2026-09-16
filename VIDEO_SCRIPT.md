# Demo video script (~3 minutes, English)

## [0:00-0:15] The problem
"Small and medium exporters and importers lose real money to currency
swings, but most of them have no way to quantify that risk before it
happens. They either ignore it, or pay a bank for generic advice. I built
a tool that gives them a data-driven answer in seconds."

## [0:15-0:35] What it does (show the GitHub repo briefly)
"This is the FX Volatility and Export Risk Scorer, built for GIBC V2,
Track 2, Applied Finance. It pulls 5 years of real exchange rate data,
forecasts near-term volatility with a GARCH model, and turns that into
three things a business owner can actually use: a risk score, a
portfolio-level risk view, and a historical hedge backtest."

## [0:35-1:15] Tab 1: Single Deal (screen-record the dashboard)
"Let's say I'm paying a supplier in Japan in 30 days. I select USD/JPY,
enter my deal size, and hit Analyze. [point at gauge] The model forecasts
11.26% annualized volatility right now — actually higher than its 5-year
average, meaning the market is currently more nervous than usual about
this pair. That translates to a risk score of 100 out of 100 relative to
the other currencies I track, and a 95% Value-at-Risk of about $6,400 on
a $250,000 deal. [point at LLM report] And here's the part that matters
for a non-technical business owner: an LLM turns those numbers into a
plain-English report explaining what's happening and what their options
are — forward contracts, options, or accepting the risk."

## [1:15-1:50] Tab 2: Portfolio (screen-record)
"But real companies rarely have just one exposure. Here I've entered
three: euros, yen, and yuan. Because these currencies don't move in
lockstep — in fact EUR/USD and USD/JPY are negatively correlated in this
data — the actual portfolio risk, calculated with a 20,000-scenario Monte
Carlo simulation, is about 50% lower than if you naively added up each
currency's risk separately. That's a concrete, dollar-denominated
diversification benefit, not just a theory."

## [1:50-2:20] Tab 3: Hedge Backtest (screen-record)
"Finally: does hedging actually help? I backtested every 30-day USD/JPY
window over the last 5 years. Unhedged, this deal size would have lost
money in almost two-thirds of those windows, with a worst-case loss
around $6,300. Hedging would have locked in zero currency P&L every
time — the tradeoff is giving up the upside windows too. This is the
real, honest tradeoff of hedging: it removes risk, it doesn't create
profit."

## [2:20-2:45] Under the hood (can be voice-over static code screenshot)
"Under the hood: Python, a GARCH(1,1) model from the arch library for
volatility forecasting, Monte Carlo simulation with Cholesky
decomposition for the correlated portfolio risk, and the DeepSeek model
via the Featherless API for the business-language reports. Full
methodology and every simplifying assumption is documented in the
README — for example, this prototype doesn't yet model which side of
the trade you're on, which would be a natural next step."

## [2:45-3:00] Close
"I used Claude and GitHub Copilot throughout development — that's fully
disclosed in the README, along with every AI tool this project uses.
This is a research prototype, not financial advice. Thanks for
watching."

---

## Recording tips
- Record the dashboard screens FIRST (screen recording, no audio needed
  yet), narrate over them afterward — much easier than talking live while
  clicking.
- Use OBS Studio (free) or Windows' built-in Xbox Game Bar (Win+G) for
  screen recording if you don't have anything else installed.
- You don't need to memorize this word-for-word — reading naturally,
  even a bit imperfectly, is fine and often sounds more genuine than a
  scripted read.
- Upload as Unlisted on YouTube (not Private) so judges can access it.
