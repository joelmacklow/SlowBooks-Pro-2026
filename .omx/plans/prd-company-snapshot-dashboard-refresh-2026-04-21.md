# PRD — Company Snapshot dashboard refresh (Xero-inspired)

## Date
2026-04-21

## Objective
Refresh the dashboard content area so the Company Snapshot feels closer to the Xero Business Overview reference (`../tmp/XeroDash.png`) while staying inside SlowBooks Pro's existing SPA shell, RBAC model, and no-framework frontend architecture.

## Current-state evidence
- The current dashboard is rendered as one large template in `app/static/js/app.js:344-491` with a simple metric row, bank balances, two charts, and two recent-activity tables.
- Dashboard styling is still the legacy QuickBooks-style section treatment in `app/static/css/style.css:713-726`, with only a small dark-mode override in `app/static/css/dark.css:146-149`.
- The backend contract is intentionally small: `GET /api/dashboard` returns counts, receivables/payables, recent invoices/payments, and bank balances in `app/routes/dashboard.py:24-66`.
- `GET /api/dashboard/charts` only exposes AR aging and monthly revenue in `app/routes/dashboard.py:69-109`.
- Richer financial calculations already exist, but live behind report-route permissions (`accounts.manage`) in `app/routes/reports.py:616-921`, so the dashboard cannot safely call report endpoints directly for all `dashboard.financials.view` users.

## Problem
The current Company Snapshot is functional but visually dated and structurally flat compared with the Xero-style business overview the user referenced. It does not surface higher-value "what needs attention now" widgets such as reconciliation prompts, invoice collection status, account watchlists, or quick financial deltas in a modular way.

## Constraints
- Keep the existing application chrome and navigation; refresh the dashboard content region, not the entire QB-style shell.
- Preserve current RBAC behavior: non-financial users should continue to see a safe operational snapshot, while financial widgets remain gated by `dashboard.financials.view`.
- Do not make the dashboard depend on `accounts.manage`-only report routes.
- Stay inside the current vanilla HTML/CSS/JS stack.
- Keep light and dark themes supported.
- Avoid introducing payroll/employee widgets until repo auth/privacy hardening catches up with payroll-sensitive data.

## Recommended approach
Adopt a **hybrid Xero-inspired dashboard**:
1. Keep the existing page header and shell framing.
2. Replace the current single-flow dashboard body with a modular widget grid.
3. Expand the dashboard backend contract so the page can render richer cards without making extra permission-problematic report calls.
4. Reuse report-calculation logic on the server by extracting shared helpers instead of duplicating math in route handlers.

## Proposed dashboard scope

### Primary widgets
- **Bank/reconciliation cards**: one card per active bank account with current balance, statement/reconciliation delta summary when available, and CTA into `#/banking`.
- **Invoices owed to you**: outstanding receivables total, awaiting-payment count, overdue count/value, and link into invoices/collections workflows.
- **Net profit or loss (YTD)**: compact income-vs-expenses summary and mini comparison visual.
- **Cash in and out (last 6 months)**: grouped inflow/outflow bars with a net difference summary.
- **Chart of accounts watchlist**: small table of important accounts/balances with CTA into `#/accounts`.

### Secondary behavior
- Keep a reduced operational-only layout for users without financial permission.
- Preserve empty states for new companies with no invoices, no bank accounts, or no transaction history.
- Keep deep-link actions on cards/buttons so the dashboard remains actionable, not just informational.

## Data/API plan
- **`/api/dashboard`** should become the single summary payload for:
  - user-visible snapshot cards
  - bank account/reconciliation summary rows
  - invoice-collection summary
  - account watchlist rows
  - permission-safe empty-state flags
- **`/api/dashboard/charts`** should be extended to return:
  - YTD income/expense/net-profit snapshot
  - 6-month cash in/out series
  - existing AR aging data if still used
- Shared financial aggregation should move into a service/helper module so dashboard routes can reuse profit/cash-flow math without importing report routes as dependencies.

## Implementation sketch
1. Extract or add backend aggregation helpers for:
   - YTD income/expenses/net income
   - 6-month cash in/out totals
   - invoice collection summary
   - watchlist account balances
   - reconciliation status summary per active bank account
2. Reshape `App.renderDashboard()` into smaller widget-render helpers rather than one monolithic template string.
3. Add dedicated dashboard layout classes (widget grid, KPI card, chart card, action pill, watchlist table, empty-state tile) in `style.css` and matching dark-theme overrides in `dark.css`.
4. Wire widget CTAs to existing routes (`#/banking`, `#/accounts`, `#/reports/profit-loss`, `#/reports/cash-flow`, `#/invoices`).
5. Update README screenshots/feature bullets after the UI is implemented.

## Impacted files
- `app/routes/dashboard.py`
- `app/routes/reports.py` or a new shared reporting/dashboard service module
- `app/static/js/app.js`
- `app/static/css/style.css`
- `app/static/css/dark.css`
- `tests/js_dashboard_rbac_visibility.test.js`
- backend dashboard/report aggregation tests (likely a new targeted dashboard route test module)
- `README.md` and dashboard screenshots after implementation

## Acceptance criteria
1. Financially authorized users see a modular Company Snapshot with at least bank/reconciliation, invoices owed, YTD profit/loss, cash in/out, and watchlist widgets.
2. Users without `dashboard.financials.view` still receive a safe dashboard that hides financial widgets and does not request financial chart data.
3. Dashboard widgets degrade gracefully for empty companies with clear empty states and no broken layout.
4. Dashboard actions deep-link into existing banking, accounts, invoice, and report flows.
5. Light and dark themes both render the refreshed dashboard legibly.
6. The refreshed backend contract remains permission-safe and does not require dashboard users to hold `accounts.manage`.

## Risks and mitigations
- **Permission drift**: dashboard viewers are broader than report viewers.  
  **Mitigation**: compute dashboard metrics inside dashboard-owned helpers/services instead of calling report endpoints from the client.
- **Query cost on page load**: adding multiple widgets can make the dashboard expensive.  
  **Mitigation**: keep date windows bounded (YTD, last 6 months), consolidate aggregates, and avoid N+1 account lookups.
- **Design conflict with QB-era shell**: a full Xero clone would fight the app's established chrome.  
  **Mitigation**: modernize only the content region and preserve the app shell/sidebar/topbar.
- **Empty-state fragility**: many demo/new companies will not have data for every widget.  
  **Mitigation**: define explicit zero-data states for each widget before implementation.
