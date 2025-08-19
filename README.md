# 💸 Interactive Loan Calculator (Streamlit)

An interactive loan calculator built with Streamlit. Enter borrower and loan details, then view EMI, total interest, payoff date, amortization table, and multiple charts. Includes sensitivity analysis and CSV download.

## Features
- Inputs: text, numbers, sliders, toggles, checkboxes, selectboxes, date
- Charts: Remaining balance line, monthly principal vs interest (area), principal vs interest pie
- Dataframes: Full amortization schedule (downloadable), rate/tenure sensitivity table
- Advanced options: processing fee, insurance, optional fee financing, extra monthly prepayment
- Affordability indicator vs income


## 🚀 Live Demo  
👉 [Click here to use the Loan Calculator](https://loan-calculator-5enyjqligkkq6dkdvwdgep.streamlit.app/)


## Quickstart (Local)
```bash
# (optional) create & activate virtual env
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
streamlit run streamlit_app.py
