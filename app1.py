import streamlit as st
import pandas as pd
import yfinance as yf
import requests # Added for the ticker search API

# Import backend proprietary engines
from data_ingestion import build_historical_model, extract_historical_baselines
from wacc_automation import fetch_live_wacc_inputs
from operating_model import build_operating_model
from dcf_valuation import build_dcf_model
from sensitivity_analysis import build_dual_sensitivity_matrices
from reverse_dcf import execute_goal_seek

# --- HELPER FUNCTION: TICKER SEARCH ---
def get_ticker_from_name(company_name: str) -> str:
    """Hits the Yahoo Finance Search API to convert a company name to a ticker symbol."""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={company_name}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            # Look specifically for the first publicly traded equity (avoids mutual funds/crypto)
            for quote in data['quotes']:
                if quote.get('quoteType') in ['EQUITY', 'ETF']:
                    return quote['symbol']
            return data['quotes'][0]['symbol'] # Fallback
        return None
    except Exception:
        return None

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Intrinsic Valuation Engine", layout="wide")
st.title("🏦 Institutional Intrinsic Valuation Engine")
st.markdown("Automated M&A Deal Flow, DCF Pricing, & Market Expectations Model")

# --- INITIALIZE SESSION STATE ---
if "ticker" not in st.session_state:
    st.session_state.ticker = "AAPL"
if "current_price" not in st.session_state:
    st.session_state.current_price = 175.00  
if "rev_growth" not in st.session_state:
    st.session_state.rev_growth = 0.05
if "cogs_margin" not in st.session_state:
    st.session_state.cogs_margin = 0.55
if "sga_margin" not in st.session_state:
    st.session_state.sga_margin = 0.14
if "historical_df" not in st.session_state:
    st.session_state.historical_df = None
if "live_wacc_profile" not in st.session_state:
    st.session_state.live_wacc_profile = None

# --- SIDEBAR: ASSET SELECTOR & LOADER ---
st.sidebar.header("1. Asset Ingestion")

# 1A. The New Non-Finance Search Feature
with st.sidebar.expander("🔍 Don't know the ticker? Search by name"):
    search_name = st.text_input("Company Name (e.g., Tesla, Microsoft)")
    if st.button("Search & Apply", type="primary"):
        if search_name:
            with st.spinner("Searching market database..."):
                found_ticker = get_ticker_from_name(search_name)
                if found_ticker:
                    st.session_state.ticker = found_ticker
                    st.success(f"Matched '{search_name}' to **{found_ticker}**")
                    st.rerun() # Refresh the UI to update the ticker input box automatically
                else:
                    st.error("No matching public company found.")

st.sidebar.markdown("---")

# 1B. The Main Ticker Input
target_ticker = st.sidebar.text_input("Ticker Symbol", value=st.session_state.ticker).upper()

# Fetch Historical Baseline Button
if st.sidebar.button("Fetch Historical Baseline", type="secondary"):
    with st.spinner(f"Scraping yfinance records for {target_ticker}..."):
        try:
            live_ticker_data = yf.Ticker(target_ticker)
            live_close_price = live_ticker_data.history(period="1d")['Close'].iloc[-1]
            
            hist_df = build_historical_model(target_ticker)
            wacc_prof = fetch_live_wacc_inputs(target_ticker)
            baselines = extract_historical_baselines(hist_df)
            
            st.session_state.ticker = target_ticker
            st.session_state.current_price = float(live_close_price)
            st.session_state.historical_df = hist_df
            st.session_state.live_wacc_profile = wacc_prof
            st.session_state.rev_growth = baselines['Revenue Growth']
            st.session_state.cogs_margin = baselines['COGS Margin']
            st.session_state.sga_margin = baselines['SG&A Margin']
            
            st.toast(f"Successfully loaded {target_ticker} at ${live_close_price:.2f}!", icon="✅")
            st.rerun() 
        except Exception as e:
            st.sidebar.error(f"Inference failed: {e}")

st.sidebar.divider()

# --- SIDEBAR: DYNAMIC OPERATIONAL DRIVERS ---
st.sidebar.header("2. Fine-Tune Operating Forecast")
rev_growth = st.sidebar.slider("Target Revenue Growth", min_value=-0.10, max_value=0.50, value=st.session_state.rev_growth, step=0.01, format="%.2f")
cogs_margin = st.sidebar.slider("COGS Margin", min_value=0.10, max_value=0.90, value=st.session_state.cogs_margin, step=0.01, format="%.2f")
sga_margin = st.sidebar.slider("SG&A Margin", min_value=0.05, max_value=0.50, value=st.session_state.sga_margin, step=0.01, format="%.2f")

st.sidebar.header("Terminal Assumptions")
pgr = st.sidebar.slider("Perpetuity Growth Rate", min_value=0.01, max_value=0.05, value=0.025, step=0.005, format="%.3f")
exit_mult = st.sidebar.slider("Exit Multiple (EV/EBITDA)", min_value=5.0, max_value=30.0, value=12.0, step=0.5)

# --- EXECUTION TRIGGER ---
if st.sidebar.button("Execute Valuation Pipeline", type="primary", use_container_width=True):
    if st.session_state.historical_df is None or target_ticker != st.session_state.ticker:
        st.warning("⚠️ The input ticker changed. Please click 'Fetch Historical Baseline' first to load the correct financial structures.")
    else:
        with st.spinner("Executing mathematical discounting layers..."):
            historical_df = st.session_state.historical_df
            live_wacc_profile = st.session_state.live_wacc_profile
            current_price = st.session_state.current_price
            
            # Construct Operating Profile
            operating_assumptions = {
                'Revenue Growth': rev_growth, 'COGS Margin': cogs_margin, 'SG&A Margin': sga_margin,
                'Tax Rate': live_wacc_profile['Tax Rate'],
                'DSO': 25, 'DIO': 9, 'DPO': 100, 'CapEx (% of Rev)': 0.03, 'D&A (% of PP&E)': 0.20
            }
            
            operating_model_df = build_operating_model(historical_df, operating_assumptions, forecast_years=5)
            projected_ufcf = operating_model_df.loc['Unlevered FCF']
            final_ebitda = operating_model_df.loc['EBIT', 'Year 5'] + operating_model_df.loc['D&A', 'Year 5']
            
            tv_assumptions = {'Perpetuity Growth Rate': pgr}
            cap_struct = {
                'Cash': historical_df.loc['Total Current Assets'].iloc[-1] * 0.4,
                'Total Debt': live_wacc_profile['Total Debt'],
                'Shares Outstanding': live_wacc_profile['Market Cap (Equity Value)'] / current_price,
                'Current Price': current_price
            }
            
            val_results = build_dcf_model(projected_ufcf, live_wacc_profile, tv_assumptions, cap_struct)
            mat_pgr, mat_mult = build_dual_sensitivity_matrices(
                projected_ufcf, final_ebitda, live_wacc_profile['Calculated WACC'], pgr, exit_mult, cap_struct
            )
            implied_growth, _ = execute_goal_seek(
                current_price, historical_df, operating_assumptions, live_wacc_profile, tv_assumptions, cap_struct
            )

            # --- RENDERING DASHBOARD ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Live Market Price", f"${current_price:,.2f}")
            col2.metric("Implied Intrinsic Value", f"${val_results['Implied Share Price']:,.2f}", f"{val_results['Upside / (Downside) %']:.2f}%")
            col3.metric("Live WACC", f"{live_wacc_profile['Calculated WACC']*100:.2f}%")
            col4.metric("Market-Implied Growth", f"{implied_growth*100:.2f}%")

            st.divider()

            tab1, tab2, tab3 = st.tabs(["Executive Summary", "Financial Projections", "Sensitivity Matrices"])

            with tab1:
                st.subheader("Recommendation Horizon")
                upside = val_results['Upside / (Downside) %']
                if upside > 15:
                    st.success(">> STATUS: UNDERVALUED | Strong Long-Term Buy Target")
                elif upside < -15:
                    st.error(">> STATUS: OVERVALUED | Pass / Avoid Target Valuation")
                else:
                    st.warning(">> STATUS: FAIR VALUE | Hold / Re-evaluate Operational Synergies")
                
                st.markdown("---")
                st.subheader("Reverse DCF Analysis: Expectations vs. Reality")
                st.write(f"To justify a price of **${current_price:.2f}**, the market requires annual revenue growth of **{implied_growth*100:.2f}%**.")
                if rev_growth >= implied_growth:
                    st.info("💡 **Takeaway:** Projected growth outpaces market expectations. Margin of safety confirmed.")
                else:
                    st.warning("🚨 **Takeaway:** Stock requires aggressive operational outperformance to hit current price bounds.")

            with tab2:
                st.subheader("5-Year Projected Operating Model")
                st.dataframe(operating_model_df.style.format("{:,.2f}"), use_container_width=True)

            with tab3:
                col_mat1, col_mat2 = st.columns(2)
                with col_mat1:
                    st.subheader("WACC vs. Perpetuity Growth")
                    st.dataframe(mat_pgr.style.format("${:,.2f}").background_gradient(cmap="RdYlGn", axis=None), use_container_width=True)
                with col_mat2:
                    st.subheader("WACC vs. Exit Multiple")
                    st.dataframe(mat_mult.style.format("${:,.2f}").background_gradient(cmap="RdYlGn", axis=None), use_container_width=True)
else:
    st.info("💡 **Workflow Input Required:** Enter a company name or ticker, click **Fetch Historical Baseline**, then hit **Execute Valuation Pipeline**.")