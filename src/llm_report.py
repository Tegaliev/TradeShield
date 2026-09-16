"""
llm_report.py

Takes the numeric risk assessment from risk_scoring.py and asks an LLM
(via the Featherless sponsor API) to turn it into a short, plain-language
business report -- the kind of thing you'd actually hand to a small
exporter/importer, not a data scientist.

Setup (one-time):
    1. Create a file named ".env" in the project root (same folder as
       requirements.txt) containing one line:
           FEATHERLESS_API_KEY=fw-your-key-here
       (.env is already in .gitignore, so this key never gets committed.)
    2. pip install -r requirements.txt  (already includes openai + python-dotenv)

Run locally, from the project root:
    python src/llm_report.py --pair USDJPY --exposure 250000 --horizon 30
    (on Windows: py src\\llm_report.py --pair USDJPY --exposure 250000 --horizon 30)

Requires results/volatility_forecast_summary.csv to already exist
(run volatility_forecast.py first).
"""

import os
import sys
import argparse

from dotenv import load_dotenv
from openai import OpenAI

# risk_scoring.py lives in the same folder as this file
sys.path.insert(0, os.path.dirname(__file__))
from risk_scoring import build_risk_report, DEFAULT_EXPOSURE_USD, DEFAULT_HORIZON_DAYS

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

# Any Featherless-hosted model works here; DeepSeek-V3.2 gives noticeably
# more coherent business writing than the smaller models. Swap in
# "mistralai/Mistral-Nemo-Instruct-2407" if you want faster/cheaper calls
# while testing (it only costs 1 concurrency unit instead of 4).
MODEL_NAME = "deepseek-ai/DeepSeek-V3.2"

SYSTEM_PROMPT = """You are a currency risk analyst writing a short internal \
memo for a small/medium exporter or importer who is not a finance expert. \
You are given a quantitative FX risk assessment (volatility forecast, a \
0-100 risk score, and a 95% Value-at-Risk figure). Write a report with \
exactly these four short sections, using plain business English and no \
jargon beyond what you explain inline:

1. What's happening (1-2 sentences: current volatility regime for this pair)
2. Why this risk level (1-2 sentences: connect the risk score/category to \
the VaR figure in dollar terms)
3. Practical options (2-3 bullet points: e.g. forward contracts, currency \
options, natural hedging, or doing nothing if risk is genuinely low -- be \
specific to the numbers given, not generic finance advice)
4. Disclaimer (one sentence, verbatim): "This is an automated research \
prototype, not financial advice, and does not account for your specific \
financial situation."

Keep the whole report under 200 words. Do not invent numbers that were not \
given to you."""


def get_client() -> OpenAI:
    load_dotenv()
    api_key = os.environ.get("FEATHERLESS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FEATHERLESS_API_KEY not found. Create a .env file in the project "
            "root with a line like:\n  FEATHERLESS_API_KEY=fw-your-key-here"
        )
    return OpenAI(api_key=api_key, base_url="https://api.featherless.ai/v1")


def build_user_prompt(risk_report: dict) -> str:
    return (
        f"Currency pair: {risk_report['pair']}\n"
        f"Deal size: ${risk_report['exposure_usd']:,.0f}\n"
        f"Time horizon: {risk_report['horizon_days']} days\n"
        f"Forecasted annualized volatility: {risk_report['forecast_annualized_vol_pct']}%\n"
        f"Risk score (0-100, relative to the currency pairs this tool tracks): "
        f"{risk_report['risk_score']}\n"
        f"Risk category: {risk_report['risk_category']}\n"
        f"95% Value-at-Risk: ${risk_report['value_at_risk_usd_95pct']:,.2f} "
        f"({risk_report['value_at_risk_pct_of_exposure']}% of the deal size)"
    )


def generate_report(risk_report: dict, model: str = MODEL_NAME) -> str:
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(risk_report)},
            ],
            max_tokens=400,
            temperature=0.4,
        )
    except Exception as exc:
        # Surface the sponsor doc's known error codes in plain language
        # instead of a raw stack trace.
        msg = str(exc)
        if "401" in msg:
            raise RuntimeError("Featherless says the API key is invalid. Re-copy it or make a new one.") from exc
        if "403" in msg:
            raise RuntimeError(f"Model '{model}' is locked on your account. Open its page on featherless.ai and click 'Unlock Model'.") from exc
        if "429" in msg:
            raise RuntimeError("Out of concurrency units right now. Wait a bit and retry.") from exc
        if "503" in msg:
            raise RuntimeError("Model is waking up or at capacity. Retry in a few seconds.") from exc
        raise

    return response.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(description="Generate an LLM business report for one FX deal.")
    parser.add_argument("--pair", required=True, help="e.g. USDJPY")
    parser.add_argument("--exposure", type=float, default=DEFAULT_EXPOSURE_USD)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON_DAYS)
    parser.add_argument("--model", default=MODEL_NAME)
    args = parser.parse_args()

    risk_report = build_risk_report(args.pair, args.exposure, args.horizon)
    print("--- Quantitative inputs ---")
    for k, v in risk_report.items():
        print(f"{k}: {v}")

    print("\nGenerating LLM report (this calls the Featherless API)...")
    report_text = generate_report(risk_report, model=args.model)

    print("\n--- Business report ---")
    print(report_text)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"llm_report_{args.pair}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()
