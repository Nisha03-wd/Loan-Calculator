# streamlit_app.py
import math
from datetime import date
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ------------------------ Page config ------------------------
st.set_page_config(
    page_title="Interactive Loan Calculator",
    layout="wide",
    page_icon="💸",
)

# ------------------------ Helpers ------------------------
CURRENCY_MAP = {
    "INR (₹)": "₹",
    "USD ($)": "$",
    "EUR (€)": "€",
    "GBP (£)": "£",
}

def fmt_money(x, symbol="₹"):
    try:
        return f"{symbol}{x:,.2f}"
    except Exception:
        return f"{symbol}{x}"

def compute_emi(principal: float, annual_rate_pct: float, months: int) -> float:
    """Standard amortized EMI. If rate==0, spread principal evenly."""
    if months <= 0:
        return 0.0
    r = annual_rate_pct / 12 / 100
    if r == 0:
        return principal / months
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)

def amortization_schedule(
    principal: float,
    annual_rate_pct: float,
    months: int,
    start: date,
    extra_payment: float = 0.0,
):
    """Return schedule dataframe (month-by-month). Stops early if loan is fully repaid."""
    r = annual_rate_pct / 12 / 100
    emi = compute_emi(principal, annual_rate_pct, months)
    balance = principal
    rows = []
    m = 0

    while balance > 0 and m < months + 600:  # hard cap to avoid infinite loop
        m += 1
        curr_date = start + relativedelta(months=+ (m - 1))

        if r == 0:
            interest = 0.0
            principal_component = min(emi + extra_payment, balance)
        else:
            interest = balance * r
            principal_component = min(emi + extra_payment - interest, balance)

        if principal_component < 0:
            # If extra_payment is too small (e.g., negative), guard
            principal_component = 0.0

        new_balance = balance - principal_component
        total_payment = principal_component + interest

        rows.append({
            "Installment #": m,
            "Date": curr_date,
            "Opening Balance": balance,
            "EMI (excl. extra)": emi,
            "Extra Payment": extra_payment,
            "Interest": interest,
            "Principal": principal_component,
            "Total Payment": total_payment,
            "Closing Balance": new_balance,
        })

        balance = new_balance
        if balance <= 0.01:
            break

    df = pd.DataFrame(rows)
    # Ensure last row snaps to 0 precisely for neatness
    if not df.empty:
        df.loc[df.index[-1], "Closing Balance"] = 0.0
    return df

@st.cache_data(show_spinner=False)
def sensitivity_table(principal: float, base_rate: float, years_list, rate_list):
    """Grid of EMI values for different rates and tenures."""
    out = []
    for r in rate_list:
        row = {"Rate %": r}
        for y in years_list:
            months = int(y * 12)
            row[f"{y}y"] = compute_emi(principal, r, months)
        out.append(row)
    df = pd.DataFrame(out)
    return df

# ------------------------ Sidebar Inputs ------------------------
st.sidebar.title("⚙️ Controls")

with st.sidebar:
    st.markdown("### Borrower")
    name = st.text_input("Full Name", value="Nisha Kumari Singh")
    age = st.number_input("Age", min_value=18, max_value=75, value=25, step=1)
    currency_label = st.selectbox("Currency", list(CURRENCY_MAP.keys()), index=0)
    cur = CURRENCY_MAP[currency_label]

    income = st.number_input(f"Monthly Take-Home Income ({currency_label})",
                             min_value=0.0, value=80000.0, step=1000.0, format="%.2f")
    has_existing_emi = st.checkbox("I have existing EMIs")
    existing_emi = 0.0
    if has_existing_emi:
        existing_emi = st.number_input(f"Total Existing Monthly EMIs ({currency_label})",
                                       min_value=0.0, value=0.0, step=1000.0, format="%.2f")

    coapp_toggle = st.toggle("Add Co-applicant?")
    co_income = 0.0
    if coapp_toggle:
        co_income = st.number_input(f"Co-applicant Monthly Income ({currency_label})",
                                    min_value=0.0, value=0.0, step=1000.0, format="%.2f")

    st.markdown("---")
    st.markdown("### Loan Details")
    loan_purpose = st.selectbox("Loan Purpose", ["Home", "Car", "Education", "Personal", "Other"], index=0)
    property_value = st.number_input(f"{'Property/Asset' if loan_purpose=='Home' else 'Asset'} Value ({currency_label})",
                                     min_value=0.0, value=5000000.0, step=50000.0, format="%.2f")
    deposit_perc = st.slider("Deposit / Down Payment (%)", min_value=0, max_value=90, value=20, step=1)
    deposit = property_value * deposit_perc / 100.0

    rate = st.slider("Annual Interest Rate (%)", min_value=0.0, max_value=25.0, value=9.0, step=0.1)
    tenure_years = st.slider("Tenure (years)", min_value=1, max_value=40, value=20, step=1)
    start_date = st.date_input("Loan Start Date", value=date.today())

    advanced = st.toggle("Show Advanced Options")
    extra_monthly = 0.0
    processing_fee_rate = 0.0
    insurance_rate = 0.0
    finance_fees = False

    if advanced:
        extra_monthly = st.number_input(f"Extra Monthly Principal Payment ({currency_label})",
                                        min_value=0.0, value=0.0, step=1000.0, format="%.2f")
        processing_fee_rate = st.number_input("Processing Fee (% of Loan Amount)",
                                              min_value=0.0, value=0.5, step=0.1, format="%.2f")
        insurance_rate = st.number_input("One-time Insurance (% of Loan Amount)",
                                         min_value=0.0, value=0.0, step=0.1, format="%.2f")
        finance_fees = st.checkbox("Add fees to loan amount (finance them)")

    st.markdown("---")
    calc = st.button("💡 Calculate")

# ------------------------ Compute ------------------------
loan_amount = max(property_value - deposit, 0.0)
months = tenure_years * 12

if calc:
    if loan_amount <= 0:
        st.error("Down payment is equal to or higher than the asset value. Please lower the deposit or raise the asset value.")
        st.stop()

    # upfront fees
    processing_fee = loan_amount * processing_fee_rate / 100.0
    insurance_fee = loan_amount * insurance_rate / 100.0
    financed_principal = loan_amount + (processing_fee + insurance_fee if finance_fees else 0.0)

    # schedule + EMI
    emi = compute_emi(financed_principal, rate, months)
    sched = amortization_schedule(
        principal=financed_principal,
        annual_rate_pct=rate,
        months=months,
        start=start_date,
        extra_payment=extra_monthly,
    )

    total_interest = float(sched["Interest"].sum()) if not sched.empty else 0.0
    total_paid = float(sched["Total Payment"].sum()) if not sched.empty else 0.0
    payoff_date = sched["Date"].iloc[-1] if not sched.empty else start_date

    # Add non-financed fees as upfront cash
    upfront_cash = deposit + (0 if finance_fees else (processing_fee + insurance_fee))
    total_project_cost = upfront_cash + total_paid

    # Affordability (simple heuristic)
    household_income = income + co_income
    affordability_ratio = 0.0 if household_income == 0 else (emi + existing_emi) / household_income
    max_safe_ratio = 0.4  # 40% is a common rule-of-thumb

    # ------------------------ Header & Greeting ------------------------
    st.success(f"Hi {name}, here are your loan results 👇")

    # ------------------------ Summary Metrics ------------------------
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Loan Amount", fmt_money(loan_amount, cur))
    col2.metric("EMI (base)", fmt_money(emi, cur))
    col3.metric("Total Interest", fmt_money(total_interest, cur))
    col4.metric("Total Paid (EMIs)", fmt_money(total_paid, cur))
    col5.metric("Expected Payoff", payoff_date.strftime("%b %Y"))

    st.markdown(
        f"**Upfront Cash** (Deposit + non-financed fees): {fmt_money(upfront_cash, cur)}  •  "
        f"**Total Project Cost**: {fmt_money(total_project_cost, cur)}"
    )

    # ------------------------ Affordability ------------------------
    st.subheader("Affordability")
    st.write(f"Household Income: {fmt_money(household_income, cur)} • Existing EMIs: {fmt_money(existing_emi, cur)}")
    aff_col1, aff_col2 = st.columns([3, 1])
    with aff_col1:
        st.progress(min(1.0, affordability_ratio), text=f"EMI burden: {affordability_ratio:.1%} of income (target ≤ {max_safe_ratio:.0%})")
    with aff_col2:
        if affordability_ratio <= max_safe_ratio:
            st.success("Looks manageable ✅")
        else:
            st.warning("High EMI burden ⚠️ Consider larger down payment, lower rate, or longer tenure.")

    # ------------------------ Tabs ------------------------
    t1, t2, t3, t4 = st.tabs(["📈 Charts", "📋 Amortization Table", "🧪 Sensitivity", "ℹ️ About"])

    # Charts
    with t1:
        if sched.empty:
            st.info("No schedule to display.")
        else:
            # Balance over time
            bal_fig = px.line(
                sched,
                x="Date",
                y="Closing Balance",
                title="Remaining Balance Over Time",
                labels={"Closing Balance": f"Balance ({cur})"},
            )
            st.plotly_chart(bal_fig, use_container_width=True)

            # Principal vs Interest area (monthly)
            area_df = sched.melt(
                id_vars=["Date"],
                value_vars=["Principal", "Interest"],
                var_name="Component",
                value_name="Amount",
            )
            area_fig = px.area(
                area_df,
                x="Date",
                y="Amount",
                color="Component",
                title="Monthly Payment Breakdown (Principal vs Interest)",
                labels={"Amount": f"Amount ({cur})"},
            )
            st.plotly_chart(area_fig, use_container_width=True)

            # Principal vs Interest pie (totals)
            pie_df = pd.DataFrame({
                "Component": ["Principal", "Interest"],
                "Amount": [financed_principal, total_interest],
            })
            pie_fig = px.pie(pie_df, names="Component", values="Amount", title="Total Paid: Principal vs Interest")
            st.plotly_chart(pie_fig, use_container_width=True)

    # Amortization table
    with t2:
        if not sched.empty:
            show_all = st.checkbox("Show full schedule (may be long)")
            if not show_all:
                st.write("Showing first 120 rows. Tick the box above to view all.")
                st.dataframe(sched.head(120), use_container_width=True, hide_index=True)
            else:
                st.dataframe(sched, use_container_width=True, hide_index=True)

            # CSV download
            csv = sched.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download amortization CSV",
                data=csv,
                file_name="amortization_schedule.csv",
                mime="text/csv",
            )
        else:
            st.info("No table to show.")

    # Sensitivity analysis
    with t3:
        st.markdown("**How would EMI change if the interest rate or tenure changes?**")
        years_list = list(range(max(1, tenure_years - 10), tenure_years + 11, 2))  # +/-10 years, step=2
        rate_list = [round(x, 1) for x in np.arange(max(0.0, rate - 5), rate + 5.1, 0.5)]
        sens = sensitivity_table(loan_amount, rate, years_list, rate_list)

        st.write("EMI Table (change in EMI for various rates & tenures):")
        st.dataframe(sens, use_container_width=True, hide_index=True)

        # Heatmap
        heat = sens.set_index("Rate %")
        heat_fig = px.imshow(
            heat.values,
            x=list(heat.columns),
            y=list(heat.index),
            aspect="auto",
            title="EMI Heatmap",
            labels={"x": "Tenure", "y": "Rate %", "color": f"EMI ({cur})"},
        )
        st.plotly_chart(heat_fig, use_container_width=True)

        # Quick lines
        st.markdown("**Quick Lines**")
        line1 = pd.DataFrame({
            "Rate %": rate_list,
            "EMI": [compute_emi(loan_amount, r, months) for r in rate_list]
        })
        rate_line = px.line(line1, x="Rate %", y="EMI", title=f"EMI vs Interest Rate ({tenure_years}y)", labels={"EMI": f"EMI ({cur})"})
        st.plotly_chart(rate_line, use_container_width=True)

        line2 = pd.DataFrame({
            "Years": years_list,
            "EMI": [compute_emi(loan_amount, rate, y * 12) for y in years_list]
        })
        years_line = px.line(line2, x="Years", y="EMI", title=f"EMI vs Tenure (Rate {rate}%)", labels={"EMI": f"EMI ({cur})"})
        st.plotly_chart(years_line, use_container_width=True)

    # About
    with t4:
        st.markdown(
            """
            **How this works**
            - EMI uses the standard amortized loan formula.
            - *Advanced Options* let you add fees and optional extra monthly prepayments.
            - *Affordability* is a rough guideline comparing monthly EMIs to household income (target ≤ 40%).
            
            **Tip:** Try adjusting the *Deposit %, Rate,* and *Tenure* to see how the EMI and total interest change.
            """
        )
else:
    st.info("Set your inputs on the left and press **Calculate**.")
