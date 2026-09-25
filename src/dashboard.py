---

### 2. Содержимое файла `src/dashboard.py`

Скопируйте этот код и сохраните его в файл **`src/dashboard.py`**[cite: 3]:

```python
import os
import sys
import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from risk_scoring import (
    build_risk_report,
    load_forecast_table,
    compute_relative_scores,
    DEFAULT_EXPOSURE_USD,
    DEFAULT_HORIZON_DAYS,
)
from portfolio_risk import simulate_portfolio
from backtest_hedging import load_prices, rolling_window_pnl, summarize, build_distribution_figure

st.set_page_config(page_title="TradeShield", layout="centered")
st.title("TradeShield")
st.caption(
    "A currency risk radar for exporters and importers. "
    "Research prototype built for GIBC V2 (Track 02: Applied Finance). "
    "Not a financial product, not investment advice."
)

try:
    forecast_table = load_forecast_table()
    TRACKED_PAIRS = forecast_table["pair"].tolist()
except FileNotFoundError:
    st.error(
        "No volatility forecast found yet. Run these two scripts first, in order, from a terminal:\n\n"
        "1. python src/data_collection.py\n"
        "2. python src/volatility_forecast.py"
    )
    st.stop()

def risk_gauge_figure(score: float, category: str):
    """A simple semicircular gauge: green/orange/red zones with a needle pointing at the current risk score (0-100)."""
    fig, ax = plt.subplots(figsize=(5, 3), subplot_kw={"projection": "polar"})
    zone_bounds = [(0, 33, "#2ecc71"), (33, 67, "#f39c12"), (67, 100, "#e74c3c")]
    
    for lo, hi, color in zone_bounds:
        theta1 = np.deg2rad(180 - lo * 1.8)
        theta2 = np.deg2rad(180 - hi * 1.8)
        ax.bar(
            x=(theta1 + theta2) / 2,
            height=0.4,
            width=abs(theta1 - theta2),
            bottom=0.6,
            color=color,
            alpha=0.85,
        )
        
    needle_angle = np.deg2rad(180 - score * 1.8)
    ax.plot([needle_angle, needle_angle], [0, 0.95], color="black", linewidth=3)
    ax.plot(0, 0, "o", color="black", markersize=10)
    
    ax.set_theta_zero_location("W")
    ax.set_theta_direction(-1)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.set_ylim(0, 1)
    ax.spines["polar"].set_visible(False)
    ax.grid(False)
    ax.set_title(f"Risk score: {score:.0f}/100 ({category})", pad=20)
    fig.tight_layout()
    return fig

def build_pdf_report(risk_report: dict, gauge_fig, llm_text: str | None) -> bytes:
    """Combine the gauge chart and key figures (plus the LLM text, if generated) into a single-page PDF."""
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(8.27, 11.69)) # A4 portrait
        ax.axis("off")
        
        gauge_fig.savefig("_tmp_gauge.png", dpi=150, bbox_inches="tight")
        gauge_img = plt.imread("_tmp_gauge.png")
        os.remove("_tmp_gauge.png")
        
        ax.imshow(gauge_img, extent=(0.15, 0.85, 0.70, 0.98), transform=ax.transAxes)
        
        lines = [
            "TradeShield FX Risk Report",
            "Research prototype (GIBC V2, Track 02). Not financial advice.",
            "",
            f"Currency pair: {risk_report['pair']}",
            f"Deal size: ${risk_report['exposure_usd']:,.0f}",
            f"Time horizon: {risk_report['horizon_days']} days",
            f"Forecasted annualized volatility: {risk_report['forecast_annualized_volatility']:.2%}",
            f"Risk score: {risk_report['risk_score']}/100 ({risk_report['risk_category']})",
            f"95% Value-at-Risk: ${risk_report['value_at_risk_usd_95pct']:,.2f} ({risk_report['value_at_risk_pct_of_exposure']:.2f}% of deal size)",
            "",
        ]
        
        if llm_text:
            lines.append("Business report:")
            lines.append("")
            import textwrap
            for paragraph in llm_text.split("\n"):
                lines.extend(textwrap.wrap(paragraph, width=90) or [""])
                
        ax.text(0.05, 0.65, "\n".join(lines), transform=ax.transAxes, va="top", ha="left", fontsize=9, family="monospace")
        pdf.savefig(fig)
        plt.close(fig)
        
    return buf.getvalue()

tab_single, tab_portfolio, tab_backtest = st.tabs(["Single Deal", "Portfolio", "Hedge Backtest"])

# Tab 1
with tab_single:
    col1, col2, col3 = st.columns(3)
    with col1:
        pair = st.selectbox("Currency pair", TRACKED_PAIRS, key="single_pair")
    with col2:
        exposure = st.number_input(
            "Deal size (USD)", min_value=1000.0, value=float(DEFAULT_EXPOSURE_USD), step=1000.0, key="single_exposure"
        )
    with col3:
        horizon = st.slider("Time horizon (days)", 1, 180, DEFAULT_HORIZON_DAYS, key="single_horizon")
        
    generate_llm = st.checkbox("Also generate an LLM business report (needs .env with FEATHERLESS_API_KEY)")
    
    if st.button("Analyze risk", type="primary", key="single_analyze"):
        report = build_risk_report(pair, exposure, horizon)
        gauge_fig = risk_gauge_figure(report["risk_score"], report["risk_category"])
        st.pyplot(gauge_fig)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Forecasted annualized volatility", f"{report['forecast_annualized_volatility']:.2%}")
        m2.metric("95% Value-at-Risk (VaR)", f"${report['value_at_risk_usd_95pct']:,.2f}")
        m3.metric("VaR as % of deal size", f"{report['value_at_risk_pct_of_exposure']:.2f}%")
        
        st.subheader("How this pair compares to the others we track")
        scored = compute_relative_scores(forecast_table)
        st.bar_chart(scored.set_index("pair")[["risk_score"]])
        
        llm_text = None
        if generate_llm:
            with st.spinner("Asking the LLM for a business report..."):
                try:
                    from llm_report import generate_report
                    llm_text = generate_report(report)
                    st.subheader("Business report")
                    st.markdown(llm_text)
                except Exception as exc:
                    st.error(f"Could not generate the LLM report: {exc}")
                    
        pdf_bytes = build_pdf_report(report, gauge_fig, llm_text)
        st.download_button(
            "Download this report as PDF",
            data=pdf_bytes,
            file_name=f"fx_risk_report_{pair}.pdf",
            mime="application/pdf",
        )

# Tab 2
with tab_portfolio:
    st.write("Enter exposure amounts for the pairs you're exposed to at the same time. Leave a pair at 0 to exclude it.")
    portfolio_horizon = st.slider("Time horizon (days)", 1, 180, DEFAULT_HORIZON_DAYS, key="port_horizon")
    
    exposures_input = {}
    cols = st.columns(len(TRACKED_PAIRS))
    for col, pair_name in zip(cols, TRACKED_PAIRS):
        with col:
            exposures_input[pair_name] = st.number_input(
                pair_name, min_value=0.0, value=0.0, step=10000.0, key=f"port_{pair_name}"
            )
            
    active_exposures = {p: v for p, v in exposures_input.items() if v > 0}
    
    if st.button("Analyze portfolio risk", type="primary", key="portfolio_analyze"):
        if len(active_exposures) == 0:
            st.warning("Enter a nonzero exposure for at least one currency pair.")
        else:
            result = simulate_portfolio(active_exposures, portfolio_horizon)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Diversified VaR (Monte Carlo)", f"${result['diversified_var_95_usd']:,.2f}")
            m2.metric("Naive VaR (no correlation)", f"${result['naive_var_95_usd']:,.2f}")
            m3.metric("Diversification benefit", f"{result['diversification_benefit_pct']:.1f}%")
            
            if len(active_exposures) > 1:
                st.subheader("Correlation between your exposures (5y history)")
                corr_df = pd.DataFrame(result["correlation_matrix"])
                fig, ax = plt.subplots(figsize=(4 + len(corr_df), 3 + len(corr_df)))
                im = ax.imshow(corr_df.values, cmap="RdYlGn_r", vmin=-1, vmax=1)
                
                ax.set_xticks(range(len(corr_df.columns)))
                ax.set_xticklabels(corr_df.columns)
                ax.set_yticks(range(len(corr_df.index)))
                ax.set_yticklabels(corr_df.index)
                
                for i in range(len(corr_df.index)):
                    for j in range(len(corr_df.columns)):
                        ax.text(j, i, f"{corr_df.values[i, j]:.2f}", ha="center", va="center", color="black")
                        
                fig.colorbar(im, ax=ax, label="correlation")
                fig.tight_layout()
                st.pyplot(fig)
            else:
                st.caption("Add a second currency pair to see the correlation matrix.")

# Tab 3
with tab_backtest:
    col1, col2, col3 = st.columns(3)
    with col1:
        bt_pair = st.selectbox("Currency pair", TRACKED_PAIRS, key="bt_pair")
    with col2:
        bt_exposure = st.number_input(
            "Deal size (USD)", min_value=1000.0, value=float(DEFAULT_EXPOSURE_USD), step=1000.0, key="bt_exposure"
        )
    with col3:
        bt_horizon = st.slider("Time horizon (days)", 5, 180, DEFAULT_HORIZON_DAYS, key="bt_horizon")
        
    if st.button("Run historical backtest", type="primary", key="bt_analyze"):
        prices = load_prices(bt_pair)
        pnl = rolling_window_pnl(prices, bt_exposure, bt_horizon)
        stats = summarize(pnl, bt_exposure)
        
        st.write(
            f"Over **{stats['n_windows']}** overlapping {bt_horizon}-day windows in available history, "
            f"an unhedged position of this size **lost money in {stats['pct_windows_with_a_loss']:.1f}% of windows**."
        )
        
        m1, m2 = st.columns(2)
        m1.metric("Worst-case loss (95th pctile)", f"${stats['worst_case_loss_usd']:,.2f}")
        m2.metric("Best-case gain (5th pctile)", f"${stats['best_case_gain_usd']:,.2f}")
        
        fig = build_distribution_figure(pnl, bt_pair, bt_horizon)
        st.pyplot(fig)
        
        st.caption(
            "A hedged position would have had $0 currency P&L in every one of those windows. "
            "Hedging trades away the best-case upside in exchange for removing the worst-case downside — "
            "it is not a way to make money on average."
        )

st.divider()
st.caption(
    "GIBC V2 hackathon research prototype. This tool does not account for your specific financial situation "
    "and should not be used for real trading, hedging, or investment decisions."
)
