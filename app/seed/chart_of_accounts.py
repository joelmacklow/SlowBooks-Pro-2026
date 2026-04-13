# ============================================================================
# NZ default chart of accounts
#
# Source basis:
# - Xero-style NZ chart reference supplied out-of-repo via ChartOfAccounts.csv
# - Augmented with a small number of explicit system accounts needed by the
#   current SlowBooks NZ posting flows
#
# Notes:
# - Account types are mapped into the app's reduced enum model
# - This is the canonical default chart for new seeded databases on
#   `nz-localization`
# ============================================================================

CHART_OF_ACCOUNTS = [
    # Assets
    {"account_number": "090", "name": "Business Bank Account", "account_type": "asset"},
    {"account_number": "091", "name": "Business Savings Account", "account_type": "asset"},
    {"account_number": "610", "name": "Accounts Receivable", "account_type": "asset"},
    {"account_number": "611", "name": "less Provision for Doubtful Debts", "account_type": "asset"},
    {"account_number": "615", "name": "Undeposited Funds", "account_type": "asset"},
    {"account_number": "620", "name": "Prepayments", "account_type": "asset"},
    {"account_number": "625", "name": "Withholding tax paid", "account_type": "asset"},
    {"account_number": "630", "name": "Inventory", "account_type": "asset"},
    {"account_number": "710", "name": "Office Equipment", "account_type": "asset"},
    {"account_number": "711", "name": "Less Accumulated Depreciation on Office Equipment", "account_type": "asset"},
    {"account_number": "720", "name": "Computer Equipment", "account_type": "asset"},
    {"account_number": "721", "name": "Less Accumulated Depreciation on Computer Equipment", "account_type": "asset"},
    {"account_number": "497", "name": "Bank Revaluations", "account_type": "asset"},

    # Liabilities
    {"account_number": "800", "name": "Accounts Payable", "account_type": "liability"},
    {"account_number": "801", "name": "Unpaid Expense Claims", "account_type": "liability"},
    {"account_number": "805", "name": "Accrued Liabilities", "account_type": "liability"},
    {"account_number": "814", "name": "Wages Payable - Payroll", "account_type": "liability"},
    {"account_number": "816", "name": "Wages Deductions Payable", "account_type": "liability"},
    {"account_number": "820", "name": "GST", "account_type": "liability"},
    {"account_number": "825", "name": "PAYE Payable", "account_type": "liability"},
    {"account_number": "826", "name": "KiwiSaver Payable", "account_type": "liability"},
    {"account_number": "827", "name": "ESCT Payable", "account_type": "liability"},
    {"account_number": "828", "name": "Child Support Payable", "account_type": "liability"},
    {"account_number": "830", "name": "Income Tax", "account_type": "liability"},
    {"account_number": "835", "name": "Revenue Received in Advance", "account_type": "liability"},
    {"account_number": "850", "name": "Suspense", "account_type": "liability"},
    {"account_number": "855", "name": "Clearing Account", "account_type": "liability"},
    {"account_number": "900", "name": "Loan", "account_type": "liability"},

    # Equity
    {"account_number": "840", "name": "Historical Adjustment", "account_type": "equity"},
    {"account_number": "877", "name": "Tracking Transfers", "account_type": "equity"},
    {"account_number": "960", "name": "Retained Earnings", "account_type": "equity"},
    {"account_number": "970", "name": "Owner A Funds Introduced", "account_type": "equity"},
    {"account_number": "980", "name": "Owner A Drawings", "account_type": "equity"},

    # Income
    {"account_number": "200", "name": "Sales", "account_type": "income"},
    {"account_number": "260", "name": "Other Revenue", "account_type": "income"},
    {"account_number": "270", "name": "Interest Income", "account_type": "income"},
    {"account_number": "498", "name": "Unrealised Currency Gains", "account_type": "income"},
    {"account_number": "499", "name": "Realised Currency Gains", "account_type": "income"},

    # Cost of goods sold / direct costs
    {"account_number": "300", "name": "Purchases", "account_type": "cogs"},
    {"account_number": "310", "name": "Cost of Goods Sold", "account_type": "cogs"},

    # Expenses
    {"account_number": "400", "name": "Advertising", "account_type": "expense"},
    {"account_number": "404", "name": "Bank Fees", "account_type": "expense"},
    {"account_number": "408", "name": "Cleaning", "account_type": "expense"},
    {"account_number": "412", "name": "Consulting & Accounting", "account_type": "expense"},
    {"account_number": "416", "name": "Depreciation", "account_type": "expense"},
    {"account_number": "420", "name": "Entertainment", "account_type": "expense"},
    {"account_number": "424", "name": "Entertainment - Non deductible", "account_type": "expense"},
    {"account_number": "425", "name": "Freight & Courier", "account_type": "expense"},
    {"account_number": "429", "name": "General Expenses", "account_type": "expense"},
    {"account_number": "433", "name": "Insurance", "account_type": "expense"},
    {"account_number": "437", "name": "Interest Expense", "account_type": "expense"},
    {"account_number": "441", "name": "Legal expenses", "account_type": "expense"},
    {"account_number": "445", "name": "Light, Power, Heating", "account_type": "expense"},
    {"account_number": "449", "name": "Motor Vehicle Expenses", "account_type": "expense"},
    {"account_number": "453", "name": "Office Expenses", "account_type": "expense"},
    {"account_number": "461", "name": "Printing & Stationery", "account_type": "expense"},
    {"account_number": "469", "name": "Rent", "account_type": "expense"},
    {"account_number": "473", "name": "Repairs and Maintenance", "account_type": "expense"},
    {"account_number": "477", "name": "Salaries", "account_type": "expense"},
    {"account_number": "478", "name": "KiwiSaver Employer Contributions", "account_type": "expense"},
    {"account_number": "485", "name": "Subscriptions", "account_type": "expense"},
    {"account_number": "489", "name": "Telephone & Internet", "account_type": "expense"},
    {"account_number": "493", "name": "Travel - National", "account_type": "expense"},
    {"account_number": "494", "name": "Travel - International", "account_type": "expense"},
    {"account_number": "505", "name": "Income Tax Expense", "account_type": "expense"},
    {"account_number": "860", "name": "Rounding", "account_type": "expense"},
]
