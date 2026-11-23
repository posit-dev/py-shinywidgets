# Lending Club loans (OpenIntro extract)

10,000 Lending Club personal loans issued in Q1 2018, as collected by OpenIntro
(`loans_full_schema.csv`, CC BY-SA). Each row is one loan.

- **loan_id**: a synthetic row identifier (not a real Lending Club ID).
- **state**: the borrower's two-letter US state code (50 states + DC).
- **homeownership**: `MORTGAGE`, `RENT`, or `OWN`.
- **annual_income**: the borrower's self-reported annual income, in dollars. A
  few loans report $0 (likely a joint/co-borrower application).
- **verified_income**: `Verified`, `Source Verified`, or `Not Verified`.
- **debt_to_income**: monthly debt payments divided by monthly income, as a
  percentage. Missing for a small number of loans.
- **emp_length**: years of employment, 0-10 (10 means "10 or more"). Missing
  for about 8% of loans.
- **loan_purpose**: the borrower's stated reason, e.g. "Debt Consolidation",
  "Credit Card", "Home Improvement", "Small Business", "Renewable Energy".
- **loan_amount**: the amount borrowed, in dollars.
- **term**: loan length in months, either 36 or 60.
- **interest_rate**: the loan's interest rate, as a percentage (e.g. 14.07
  means 14.07%, not a fraction).
- **grade**: Lending Club's letter grade, A (safest, lowest rate) through G
  (riskiest, highest rate).
- **sub_grade**: a finer grade, e.g. "C3".
- **installment**: the monthly payment, in dollars.
- **loan_status**: `Current`, `Fully Paid`, `Late (16-30 days)`,
  `Late (31-120 days)`, `In Grace Period`, or `Charged Off`. Nearly all loans
  are `Current` since this is a snapshot soon after origination -- treat this
  column with caution for anything implying "default rate".
- **issue_month**: the month the loan was issued (Jan-2018, Feb-2018, or
  Mar-2018 -- a narrow three-month window, not a time series worth trending).
