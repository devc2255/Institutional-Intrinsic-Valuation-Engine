import pandas as pd
import numpy as np

# Import your existing proprietary engines
from operating_model import build_operating_model
from dcf_valuation import build_dcf_model

def execute_goal_seek(target_price: float, historical_df: pd.DataFrame, base_op_assumptions: dict, wacc_inputs: dict, tv_inputs: dict, cap_struct: dict) -> tuple:
    """
    Deploys a Binary Search algorithm to dynamically solve for the exact 
    Revenue Growth Rate required to justify the current market share price.
    """
    print("\n[System] Initiating Algorithmic Goal Seek (Binary Search)...")
    
    # Define our algorithmic search boundaries (-20% to +100% growth)
    low_rate = -0.20
    high_rate = 1.00
    tolerance = 0.05 # We want to get within $0.05 of the target stock price
    
    implied_rate = np.nan
    final_simulated_price = np.nan
    
    # Cap the loop at 50 iterations to prevent infinite runtimes
    for iteration in range(50):
        # 1. Guess the midpoint of our current bounds
        test_rate = (low_rate + high_rate) / 2.0
        
        # 2. Inject the test rate into a fresh copy of assumptions
        test_assumptions = base_op_assumptions.copy()
        test_assumptions['Revenue Growth'] = test_rate
        
        # 3. Run the complete pipeline with the test rate
        test_op_model = build_operating_model(historical_df, test_assumptions, forecast_years=5)
        test_ufcf = test_op_model.loc['Unlevered FCF']
        
        test_val_results = build_dcf_model(test_ufcf, wacc_inputs, tv_inputs, cap_struct)
        test_price = test_val_results['Implied Share Price']
        
        # 4. Evaluate the result against our target price
        if abs(test_price - target_price) <= tolerance:
            implied_rate = test_rate
            final_simulated_price = test_price
            break
        elif test_price < target_price:
            # Price is too low; we need MORE revenue growth. Shift lower bound up.
            low_rate = test_rate
        else:
            # Price is too high; we need LESS revenue growth. Shift upper bound down.
            high_rate = test_rate
            
    # Fallback if the market price is so detached from reality that it breaks the bounds
    if np.isnan(implied_rate):
        implied_rate = test_rate
        final_simulated_price = test_price
        
    return float(implied_rate), float(final_simulated_price)