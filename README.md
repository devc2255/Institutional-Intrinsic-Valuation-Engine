# Institutional Intrinsic Valuation Engine

A Python-based valuation toolkit for estimating intrinsic stock value using a multi-stage discounted cash flow (DCF) workflow. The repository combines live market data, operating forecasts, WACC automation, sensitivity analysis, and a reverse-DCF growth check into one modular pipeline.

## What this project does

This repository is designed to:

- pull historical financial statements from Yahoo Finance,
- build a 5-year operating forecast,
- calculate a live or estimated WACC,
- value the company using DCF math,
- stress-test the valuation with sensitivity matrices,
- infer the growth rate required to justify the current market price (reverse DCF).

## Repository structure

- `app.py` — terminal-based valuation pipeline orchestration.
- `app1.py` — Streamlit dashboard for interactive analysis.
- `data_ingestion.py` — downloads and normalizes financial statement data.
- `operating_model.py` — generates projected operating and cash flow outputs.
- `wacc_automation.py` — fetches market inputs and computes WACC.
- `dcf_valuation.py` — calculates enterprise value, equity value, implied share price, and upside/downside.
- `reverse_dcf.py` — runs a binary-search reverse DCF to estimate the growth rate implied by the market price.
- `sensitivity_analysis.py` — builds WACC vs. growth and WACC vs. exit multiple matrices.
- `requirements.txt` — project dependencies.

## Core workflow

1. Ingest historical financial data.
2. Build the operating model and free cash flow projections.
3. Calculate WACC using market inputs and fallback assumptions.
4. Run the DCF valuation and sensitivity analysis.
5. Compare the result to the current market price through reverse DCF logic.

## Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the command-line pipeline

```bash
python app.py
```

This executes the full valuation flow with default inputs (currently centered on AAPL).

### 3. Run the interactive dashboard

```bash
streamlit run app1.py
```

The Streamlit app provides a more user-friendly workflow for entering a ticker, fetching baseline data, and running the valuation model interactively.

## Live Demo

A live hosted version of the Streamlit interface is available on Render.

- Status: Live on Render
- App: https://institutional-intrinsic-valuation-engine.onrender.com

## Notes

- The project relies on `yfinance`, so an internet connection is required for live market data.
- Some modules include institutional-style fallback assumptions when live data is incomplete or unavailable.
- This repository is best treated as a research / prototype valuation engine rather than a production-grade financial platform.

## License

This project is licensed under the MIT License. See `LICENSE` for details.