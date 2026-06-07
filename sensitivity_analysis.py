import pandas as pd
import numpy as np

def calculate_implied_prices(ufcf: pd.Series, final_ebitda: float, wacc: float, pgr: float, exit_mult: float, cap_struct: dict) -> tuple:
    """
    Calculates two implied share prices using the Mid-Year Convention:
    1. Perpetuity Growth Method (Gordon Growth)
    2. Exit Multiple Method (EV/EBITDA)
    """
    years = np.arange(1, len(ufcf) + 1)
    
    # INSTITUTIONAL UPGRADE: Mid-Year Convention Discounting
    mid_year_discount_factors = (1 + wacc) ** (years - 0.5)
    sum_pv_ufcf = (ufcf / mid_year_discount_factors).sum()
    
    # Terminal Value discounting always happens at the END of the final year
    final_year_discount_factor = (1 + wacc) ** years[-1]
    
    # --- Method 1: Perpetuity Growth ---
    tv_pgr = (ufcf.iloc[-1] * (1 + pgr)) / (wacc - pgr)
    pv_tv_pgr = tv_pgr / final_year_discount_factor
    ev_pgr = sum_pv_ufcf + pv_tv_pgr
    equity_val_pgr = ev_pgr + cap_struct['Cash'] - cap_struct['Total Debt']
    price_pgr = equity_val_pgr / cap_struct['Shares Outstanding']
    
    # --- Method 2: Exit Multiple ---
    tv_mult = final_ebitda * exit_mult
    pv_tv_mult = tv_mult / final_year_discount_factor
    ev_mult = sum_pv_ufcf + pv_tv_mult
    equity_val_mult = ev_mult + cap_struct['Cash'] - cap_struct['Total Debt']
    price_mult = equity_val_mult / cap_struct['Shares Outstanding']
    
    return price_pgr, price_mult

def build_dual_sensitivity_matrices(ufcf: pd.Series, final_ebitda: float, base_wacc: float, base_pgr: float, base_mult: float, cap_struct: dict):
    """
    Generates two 2D Data Tables: WACC vs PGR, and WACC vs Exit Multiple.
    """
    print("\n[System] Generating Institutional Sensitivity Matrices (Mid-Year Convention Applied)...")
    
    wacc_range = base_wacc + np.array([-0.010, -0.005, 0.0, 0.005, 0.010])
    pgr_range = base_pgr + np.array([-0.0050, -0.0025, 0.0, 0.0025, 0.0050])
    mult_range = base_mult + np.array([-1.0, -0.5, 0.0, 0.5, 1.0])
    
    # Initialize empty matrices
    matrix_pgr = pd.DataFrame(index=wacc_range, columns=pgr_range)
    matrix_mult = pd.DataFrame(index=wacc_range, columns=mult_range)
    
    for w in wacc_range:
        for p in pgr_range:
            if w <= p:
                matrix_pgr.loc[w, p] = np.nan
            else:
                price_pgr, _ = calculate_implied_prices(ufcf, final_ebitda, w, p, base_mult, cap_struct)
                matrix_pgr.loc[w, p] = price_pgr
                
        for m in mult_range:
             _, price_mult = calculate_implied_prices(ufcf, final_ebitda, w, base_pgr, m, cap_struct)
             matrix_mult.loc[w, m] = price_mult
                
    # Format axes
    matrix_pgr.index = matrix_mult.index = [f"{w*100:.2f}%" for w in wacc_range]
    matrix_pgr.columns = [f"{p*100:.2f}%" for p in pgr_range]
    matrix_mult.columns = [f"{m:.1f}x" for m in mult_range]
    
    matrix_pgr.index.name = "WACC ↓ / PGR →"
    matrix_mult.index.name = "WACC ↓ / Exit Mult →"
    
    return matrix_pgr.astype(float).round(2), matrix_mult.astype(float).round(2)

# =========================================================
# Execution Simulation 
# =========================================================

if __name__ == "__main__":
    # Baseline Data
    projected_ufcf = pd.Series([120.50, 145.20, 168.90, 190.10, 215.00])
    projected_final_ebitda = 350.00  # Required for Exit Multiple method
    
    capital_structure = {
        'Cash': 300.0,
        'Total Debt': 800.0,
        'Shares Outstanding': 150.0
    }
    
    # Base Case assumptions 
    base_case_wacc = 0.0950  
    base_case_pgr = 0.0250   
    base_case_exit_multiple = 10.0  # 10x EV/EBITDA
    
    mat_pgr, mat_mult = build_dual_sensitivity_matrices(
        projected_ufcf, projected_final_ebitda, base_case_wacc, base_case_pgr, base_case_exit_multiple, capital_structure
    )
    
    print("\n--- MATRIX 1: PERPETUITY GROWTH METHOD ---")
    print(mat_pgr.to_string())
    
    print("\n--- MATRIX 2: EXIT MULTIPLE METHOD ---")
    print(mat_mult.to_string())
    print("\n* Base Cases are located dead-center.\n")