import pandas as pd
import numpy as np

def build_operating_model(historicals: pd.DataFrame, assumptions: dict, forecast_years: int = 5) -> pd.DataFrame:
    """
    Constructs an institutional-grade 3-statement projection model.
    Drives working capital from days schedules and links D&A to fixed asset schedules,
    culminating in Unlevered Free Cash Flow (UFCF).
    """
   # print(f"\n[System] Generating {forecast_years}-Year Operating Model...")
    
    # Setup projection DataFrame columns
    proj_cols = [f"Year {i}" for i in range(1, forecast_years + 1)]
    
    # Define the exact line items required for the model in chronological order
    line_items = [
        'Total Revenue', 'COGS', 'Gross Profit', 'SG&A', 'EBIT', 'Taxes', 'NOPAT',
        'Accounts Receivable', 'Inventory', 'Accounts Payable', 'Net Working Capital', 'Change in NWC',
        'Beginning PP&E', 'CapEx', 'D&A', 'Ending PP&E',
        'Unlevered FCF'
    ]
    proj = pd.DataFrame(index=line_items, columns=proj_cols)
    
    # ---------------------------------------------------------
    # 1. Initialize Base Year (Year 0) Variables
    # ---------------------------------------------------------
    base_year = historicals.columns[-1]
    
    prev_revenue = historicals.loc['Total Revenue', base_year]
    prev_ppe = historicals.loc['Net PP&E', base_year]
    
    # Calculate Base NWC
    base_ar = historicals.loc['Accounts Receivable', base_year]
    base_inv = historicals.loc['Inventory', base_year]
    base_ap = historicals.loc['Accounts Payable', base_year]
    prev_nwc = (base_ar + base_inv) - base_ap

    # ---------------------------------------------------------
    # 2. Projection Engine
    # ---------------------------------------------------------
    for year in proj_cols:
        
        # --- Income Statement Projections ---
        revenue = prev_revenue * (1 + assumptions['Revenue Growth'])
        cogs = revenue * assumptions['COGS Margin']
        gross_profit = revenue - cogs
        sga = revenue * assumptions['SG&A Margin']
        ebit = gross_profit - sga
        
        taxes = ebit * assumptions['Tax Rate']
        nopat = ebit - taxes
        
        # Write to DataFrame
        proj.loc['Total Revenue', year] = revenue
        proj.loc['COGS', year] = cogs
        proj.loc['Gross Profit', year] = gross_profit
        proj.loc['SG&A', year] = sga
        proj.loc['EBIT', year] = ebit
        proj.loc['Taxes', year] = taxes
        proj.loc['NOPAT', year] = nopat
        
        # --- Balance Sheet: Working Capital Schedule ---
        # AR is driven by Revenue; Inventory and AP are driven by COGS
        ar = (assumptions['DSO'] / 365) * revenue
        inv = (assumptions['DIO'] / 365) * cogs
        ap = (assumptions['DPO'] / 365) * cogs
        
        current_nwc = (ar + inv) - ap
        change_in_nwc = current_nwc - prev_nwc  # Positive change = Cash Outflow
        
        # Write to DataFrame
        proj.loc['Accounts Receivable', year] = ar
        proj.loc['Inventory', year] = inv
        proj.loc['Accounts Payable', year] = ap
        proj.loc['Net Working Capital', year] = current_nwc
        proj.loc['Change in NWC', year] = change_in_nwc
        
        # --- Fixed Asset Roll-Forward ---
        proj.loc['Beginning PP&E', year] = prev_ppe
        capex = revenue * assumptions['CapEx (% of Rev)']
        da = prev_ppe * assumptions['D&A (% of PP&E)']
        ending_ppe = prev_ppe + capex - da
        
        # Write to DataFrame
        proj.loc['CapEx', year] = capex
        proj.loc['D&A', year] = da
        proj.loc['Ending PP&E', year] = ending_ppe
        
        # --- The Holy Grail: Unlevered Free Cash Flow ---
        ufcf = nopat + da - capex - change_in_nwc
        proj.loc['Unlevered FCF', year] = ufcf
        
        # --- Reset Variables for Next Iteration ---
        prev_revenue = revenue
        prev_nwc = current_nwc
        prev_ppe = ending_ppe

    # Convert all values to float to prevent formatting errors, then round
    return proj.astype(float).round(2)

# =========================================================
# Execution Simulation (Bridging Phase 1 to Phase 2)
# =========================================================

# 1. Mock Phase 1 Output (The Baseline Reality)
# Note: In production, this DataFrame is returned by your 01_data_ingestion.py script.
phase_1_output = pd.DataFrame({
    '2025': {  # Base Year
        'Total Revenue': 1000.0, 
        'COGS': 400.0,
        'SG&A': 350.0,
        'EBIT': 250.0,
        'Net PP&E': 500.0, 
        'Accounts Receivable': 120.0, 
        'Inventory': 65.0, 
        'Accounts Payable': 45.0
    }
})

# 2. Institutional Assumptions Matrix (The "Base Case")
scenario_base = {
    'Revenue Growth': 0.08,     # 8% top-line growth
    'COGS Margin': 0.40,        # COGS as 40% of revenue
    'SG&A Margin': 0.35,        # SG&A as 35% of revenue
    'Tax Rate': 0.21,           # Statutory corporate tax rate
    
    # Working Capital Drivers (Days)
    'DSO': 45,                  # Accounts Receivable Collection Period
    'DIO': 60,                  # Days Inventory Held
    'DPO': 40,                  # Days to Pay Suppliers
    
    # Reinvestment Drivers
    'CapEx (% of Rev)': 0.05,   # Capital Expenditures mapping to revenue growth
    'D&A (% of PP&E)': 0.10     # Depreciation schedule (10% of existing asset base)
}

# 3. Execute Engine
operating_model_df = build_operating_model(phase_1_output, scenario_base)

# 4. Professional Formatting for Terminal Output
print("\n--- INSTITUTIONAL OPERATING MODEL: 5-YEAR PROJECTION ---")
print("\n[ Income Statement & Cash Generation ]")
print(operating_model_df.loc[['Total Revenue', 'EBIT', 'NOPAT', 'Unlevered FCF']].to_string())

print("\n[ Net Working Capital Schedule ]")
print(operating_model_df.loc[['Accounts Receivable', 'Inventory', 'Accounts Payable', 'Change in NWC']].to_string())

print("\n[ PP&E Roll-Forward ]")
print(operating_model_df.loc[['Beginning PP&E', 'CapEx', 'D&A', 'Ending PP&E']].to_string())
print("\n")