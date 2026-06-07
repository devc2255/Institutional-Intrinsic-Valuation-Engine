import pandas as pd
import sys

# Import the functional engines built across all phases
try:
    from data_ingestion import build_historical_model
    from operating_model import build_operating_model
    from wacc_automation import fetch_live_wacc_inputs
    from dcf_valuation import build_dcf_model
    from sensitivity_analysis import build_dual_sensitivity_matrices
    from reverse_dcf import execute_goal_seek  # <--- NEW PHASE 5 IMPORT
except ImportError as e:
    print(f"[Error] Pipeline failure during module import: {e}")
    sys.exit(1)

def run_valuation_pipeline(ticker: str, current_market_price: float):
    """
    Orchestrates the entire 5-Phase Valuation and Financial Modeling Pipeline.
    """
    print("=" * 60)
    print(f"      EXECUTION PIPELINE: INTRINSIC VALUATION ENGINE")
    print(f"      TARGET TICKER: {ticker.upper()}")
    print("=" * 60)

    # ---------------------------------------------------------
    # PHASE 1: Historical Data Ingestion & Clean Up
    # ---------------------------------------------------------
    print("\n>>> [PHASE 1] Executing Historical Financial Ingestion...")
    try:
        historical_df = build_historical_model(ticker)
        print(f"[Success] Extracted {len(historical_df.columns)} years of clean historical data.")
    except Exception as e:
        print(f"[Failure] Phase 1 Ingestion crashed: {e}")
        return

    # ---------------------------------------------------------
    # PHASE 3A: Live Cost of Capital (WACC) Calculation
    # ---------------------------------------------------------
    print("\n>>> [PHASE 3A] Deploying Live Market Scout for WACC...")
    try:
        live_wacc_profile = fetch_live_wacc_inputs(ticker, erp_assumption=0.055)
        print(f"[Success] Calculated Blended Live WACC: {live_wacc_profile['Calculated WACC']*100:.2f}%")
    except Exception as e:
        print(f"[Failure] Phase 3A WACC Engine crashed: {e}")
        return

    # ---------------------------------------------------------
    # PHASE 2: Institutional Operating Projections
    # ---------------------------------------------------------
    print("\n>>> [PHASE 2] Building 5-Year Operating Forecast...")
    # Apple (AAPL) Specific Operating DNA
    operating_assumptions = {
        'Revenue Growth': 0.05,     # Baseline target
        'COGS Margin': 0.55,        
        'SG&A Margin': 0.14,        
        'Tax Rate': live_wacc_profile['Tax Rate'], 
        'DSO': 25,                  
        'DIO': 9,                   
        'DPO': 100,                 
        'CapEx (% of Rev)': 0.03,   
        'D&A (% of PP&E)': 0.20     
    }
    
    try:
        operating_model_df = build_operating_model(historical_df, operating_assumptions, forecast_years=5)
        projected_ufcf = operating_model_df.loc['Unlevered FCF']
        print("[Success] 5-Year Unlevered Free Cash Flow line generated successfully.")
    except Exception as e:
        print(f"[Failure] Phase 2 Operating Engine crashed: {e}")
        return

    # ---------------------------------------------------------
    # PHASE 3B: Intrinsic DCF Valuation Math
    # ---------------------------------------------------------
    print("\n>>> [PHASE 3B] Running Valuation & Enterprise Bridge...")
    tv_assumptions = {'Perpetuity Growth Rate': 0.025} 
    
    capital_structure = {
        'Cash': historical_df.loc['Total Current Assets'].iloc[-1] * 0.4, 
        'Total Debt': live_wacc_profile['Total Debt'],
        'Shares Outstanding': live_wacc_profile['Market Cap (Equity Value)'] / current_market_price,
        'Current Price': current_market_price
    }
    
    try:
        valuation_results = build_dcf_model(projected_ufcf, live_wacc_profile, tv_assumptions, capital_structure)
        print(f"[Success] Base Implied Share Price calculated: ${valuation_results['Implied Share Price']:.2f}")
    except Exception as e:
        print(f"[Failure] Phase 3B Core Discounting Engine crashed: {e}")
        return

    # ---------------------------------------------------------
    # PHASE 4: Stress-Testing & Sensitivity Matrices
    # ---------------------------------------------------------
    print("\n>>> [PHASE 4] Running High-Stakes Sensitivity Simulations...")
    try:
        final_ebitda = operating_model_df.loc['EBIT', 'Year 5'] + operating_model_df.loc['D&A', 'Year 5']
        mat_pgr, mat_mult = build_dual_sensitivity_matrices(
            ufcf=projected_ufcf, final_ebitda=final_ebitda, base_wacc=live_wacc_profile['Calculated WACC'],
            base_pgr=tv_assumptions['Perpetuity Growth Rate'], base_mult=12.0, cap_struct=capital_structure
        )
        print("[Success] Dual multidimensional risk matrices compiled.")
    except Exception as e:
        print(f"[Failure] Phase 4 Sensitivity Engine crashed: {e}")
        return

    # ---------------------------------------------------------
    # PHASE 5: The Reverse DCF (Market Expectations)
    # ---------------------------------------------------------
    print("\n>>> [PHASE 5] Executing Reverse DCF Algorithm...")
    try:
        implied_growth, matched_price = execute_goal_seek(
            target_price=current_market_price, historical_df=historical_df, 
            base_op_assumptions=operating_assumptions, wacc_inputs=live_wacc_profile, 
            tv_inputs=tv_assumptions, cap_struct=capital_structure
        )
        print(f"[Success] Found Market-Implied Growth Rate: {implied_growth*100:.2f}%")
    except Exception as e:
        print(f"[Failure] Phase 5 Reverse DCF Engine crashed: {e}")
        implied_growth = 0.0

    # ---------------------------------------------------------
    # FINAL PRESENTATION LAYER
    # ---------------------------------------------------------
    print("\n" + "="*60)
    print(f"            FINAL VALUATION DASHBOARD: {ticker.upper()}")
    print("="*60)
    print(f"Current Market Trading Price:     ${current_market_price:.2f}")
    print(f"DCF Base Implied Intrinsic Value: ${valuation_results['Implied Share Price']:.2f}")
    print(f"Indicated Premium / (Discount):   {valuation_results['Upside / (Downside) %']:.2f}%\n")
    
    print("--- REVERSE DCF ANALYSIS ---")
    print(f"Base Case Revenue Growth Target:  {operating_assumptions['Revenue Growth']*100:.2f}%")
    print(f"Market-Implied Required Growth:   {implied_growth*100:.2f}%")
    
    print("-" * 60)
    print("Recommendation Horizon Analysis:")
    if operating_assumptions['Revenue Growth'] >= implied_growth:
        print(">> STATUS: MISPRICED | Action: Market is underestimating growth. Strong Buy.")
    else:
        print(">> STATUS: PRICED TO PERFECTION | Action: Market expectations are high. Pass/Hold.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    run_valuation_pipeline(ticker="AAPL", current_market_price=175.00)