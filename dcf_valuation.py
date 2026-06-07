import pandas as pd
import numpy as np

def build_dcf_model(ufcf_projections: pd.Series, wacc_inputs: dict, tv_inputs: dict, cap_struct: dict) -> dict:
    """
    Executes institutional discounting mathematics using the Mid-Year Convention
    to convert projected free cash flows and terminal value into an Implied Share Price.
    """
    # Extract the pre-calculated WACC from the live market data packet
    wacc = wacc_inputs['Calculated WACC']
    
    # Generate the timeline array matching the length of projections (e.g., [1, 2, 3, 4, 5])
    years = np.arange(1, len(ufcf_projections) + 1)
    
    # ---------------------------------------------------------
    # 1. Present Value of Discrete Cash Flows (Mid-Year Convention)
    # ---------------------------------------------------------
    # Compounding factor occurs at the mid-point of each period (0.5, 1.5, 2.5...)
    mid_year_discount_factors = (1 + wacc) ** (years - 0.5)
    pv_of_ufcf = ufcf_projections / mid_year_discount_factors
    sum_pv_ufcf = pv_of_ufcf.sum()
    
    # ---------------------------------------------------------
    # 2. Terminal Value Calculation & Discounting
    # ---------------------------------------------------------
    final_year_ufcf = ufcf_projections.iloc[-1]
    pg_rate = tv_inputs['Perpetuity Growth Rate']
    
    # Gordon Growth Formula for normalized perpetual cash generation
    terminal_value = (final_year_ufcf * (1 + pg_rate)) / (wacc - pg_rate)
    
    # Terminal Value represents the asset's worth at the end of Year 5, 
    # requiring discounting by the full final year exponent
    final_year_discount_factor = (1 + wacc) ** years[-1]
    pv_of_terminal_value = terminal_value / final_year_discount_factor
    
    # ---------------------------------------------------------
    # 3. Enterprise Value to Equity Value Bridge
    # ---------------------------------------------------------
    enterprise_value = sum_pv_ufcf + pv_of_terminal_value
    equity_value = enterprise_value + cap_struct['Cash'] - cap_struct['Total Debt']
    
    # ---------------------------------------------------------
    # 4. Per-Share Capital Metric Assembly
    # ---------------------------------------------------------
    implied_share_price = equity_value / cap_struct['Shares Outstanding']
    current_price = cap_struct['Current Price']
    
    # Handle possible division-by-zero or missing market price data gracefully
    if current_price > 0:
        upside_downside_pct = ((implied_share_price / current_price) - 1) * 100
    else:
        upside_downside_pct = 0.0

    # Return the unified structured output required by the app.py dashboard layer
    return {
        'WACC (%)': wacc * 100,
        'Sum of PV of UFCF': float(sum_pv_ufcf),
        'Terminal Value': float(terminal_value),
        'PV of Terminal Value': float(pv_of_terminal_value),
        'Enterprise Value': float(enterprise_value),
        'Equity Value': float(equity_value),
        'Implied Share Price': float(implied_share_price),
        'Current Share Price': float(current_price),
        'Upside / (Downside) %': float(upside_downside_pct)
    }