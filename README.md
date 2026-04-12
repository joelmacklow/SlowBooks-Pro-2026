# Slowbooks Pro 2026

**A personal bookkeeping application "decompiled" from the ashes of QuickBooks 2003 Pro.**

Free and open source. Runs on Linux and Windows. No Intuit activation servers required.

![Slowbooks Pro 2026 — Splash Screen](screenshots/splash.png)

![Slowbooks Pro 2026 — Dashboard](screenshots/dashboard.png)

![Slowbooks Pro 2026 — Invoices with IRS Pub 583 Mock Data](screenshots/invoices.png)

![Slowbooks Pro 2026 — QuickBooks 2003 IIF Interop](screenshots/iif-interop.png)

---

## The Story

I ran QuickBooks 2003 Pro for 14 years for side business invoicing and bookkeeping. Then the hard drive died. Intuit's activation servers have been dead since ~2017, so the software can't be reinstalled. The license I paid for is worthless.

So I built my own replacement. Every invoice I ever printed is getting re-entered from paper copies.

The codebase is annotated with "decompilation" comments referencing `QBW32.EXE` offsets, Btrieve table layouts, and MFC class names — a tribute to the software that served me well for 14 years before its maker decided it should stop working.

**This is a clean-room reimplementation.** No Intuit source code was available or used.

---

## Features

### Invoicing & Payments
- **Invoices** — Create, edit, duplicate, void, mark as sent. Auto-numbering, auto due-date from terms, dynamic line items with running totals. Print/PDF generation via WeasyPrint
- **Estimates** — Full estimate workflow with convert-to-invoice (deep-copies all fields and line items)
- **Payments** — Record payments with allocation across multiple invoices. Auto-updates invoice balances and status (draft/sent/partial/paid)
- **Quick Entry Mode** — Batch invoice entry for paper invoice backlog. Save & Next (Ctrl+Enter) with running log of created invoices

### Double-Entry Accounting
- **Journal Entries** — Every invoice and payment automatically creates balanced journal entries (DR A/R, CR Income per line, CR Sales Tax). Void creates reversing entries
- **Chart of Accounts** — 39 seeded accounts (Contractor template), 6 account types (asset, liability, equity, income, COGS, expense)
- **Account Balances** — Updated in real-time as transactions post

### Banking
- **Bank Accounts** — Register view with deposits and withdrawals
- **Bank Reconciliation** — Full workflow: enter statement balance, toggle cleared items, validate difference = $0, complete

### Contacts & Items
- **Customer & Vendor Management** — Full contact info, billing/shipping addresses, terms, credit limits
- **Items & Services** — Product, service, material, and labor types with default rates and linked income/expense accounts

### Reports
- **Profit & Loss** — Income vs expenses for any date range
- **Balance Sheet** — Assets, liabilities, and equity
- **A/R Aging** — Outstanding receivables grouped by customer with 30/60/90 day buckets
- **Sales Tax** — Tax collected by invoice with taxable/non-taxable breakdowns
- **General Ledger** — All journal entries grouped by account with debit/credit totals
- **Income by Customer** — Sales totals per customer with invoice counts
- **Customer Statements** — PDF statement with invoice/payment history and running balance

### Company Settings
- Company name, address, phone, email, tax ID
- Default terms, tax rate, invoice/estimate numbering
- Default invoice notes and footer text

### UI
- Authentic QB2003 "Default Blue" skin with navy/gold color palette
- Splash screen with build info and decompilation provenance
- Windows XP-era toolbar, sidebar navigator with icons, status bar
- Global search bar (searches customers and invoices live)
- Keyboard shortcuts: `Alt+N` (new invoice), `Alt+P` (payment), `Alt+Q` (quick entry), `Alt+H` (home), `Ctrl+K` (search), `Escape` (close modal)
- No frameworks — vanilla HTML/CSS/JS single-page app
- Dashboard with receivables, overdue count, recent invoices/payments, bank balances

### QuickBooks 2003 Pro Interoperability
- **IIF Export** — Export all Slowbooks data (accounts, customers, vendors, items, invoices, payments, estimates) as .iif files importable into QB2003 via File > Utilities > Import > IIF Files
- **IIF Import** — Parse and import .iif files exported from QB2003 with duplicate detection and per-row error handling
- **Validation** — Pre-flight validation of .iif files before import (checks structure, account types, balanced transactions)
- **Date Range Filtering** — Export invoices and payments for specific date ranges
- **Round-Trip Safe** — Export from Slowbooks, re-import into Slowbooks — deduplication prevents double-entry

### Utilities
- **Backup Script** — `scripts/backup.sh` — pg_dump with gzip compression, keeps last 30 backups
- **IRS Mock Data** — `scripts/seed_irs_mock_data.py` — Seeds realistic test data from IRS Publication 583 (Henry Brown's Auto Body Shop: 8 customers, 13 vendors, 10 invoices, 5 payments, 3 estimates)

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 |
| Migrations | Alembic |
| Frontend | Vanilla HTML/CSS/JS (no framework) |
| PDF | WeasyPrint 60.2 + Jinja2 |
| Port | 3001 |

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 12+ (running)

### Install

```bash
git clone https://github.com/VonHoltenCodes/SlowBooks-Pro-2026.git
cd SlowBooks-Pro-2026

# Install dependencies
pip install -r requirements.txt

# Create database
sudo -u postgres psql -c "CREATE USER bookkeeper WITH PASSWORD 'bookkeeper'"
sudo -u postgres psql -c "CREATE DATABASE bookkeeper OWNER bookkeeper"

# Copy and edit config
cp .env.example .env
# Edit .env if your PostgreSQL setup differs

# Run migrations and seed Chart of Accounts
alembic upgrade head
python3 scripts/seed_database.py

# Start the app
python3 run.py
```

Open **http://localhost:3001** in your browser.

### Backup

```bash
./scripts/backup.sh
# Backs up to ~/bookkeeper-backups/ with gzip compression
# Keeps the 30 most recent backups
```

---

## Project Structure

```
SlowBooks-Pro-2026/
├── .env.example              # Environment config template
├── requirements.txt          # Python dependencies
├── run.py                    # Uvicorn entry point (port 3001)
├── alembic.ini               # Alembic config
├── alembic/                  # Database migrations
├── app/
│   ├── main.py               # FastAPI app + router mounting
│   ├── config.py             # Environment-based settings
│   ├── database.py           # SQLAlchemy engine + session
│   ├── models/               # 14 SQLAlchemy models
│   │   ├── accounts.py       # Chart of Accounts (self-referencing)
│   │   ├── contacts.py       # Customers + Vendors
│   │   ├── items.py          # Products, services, materials, labor
│   │   ├── invoices.py       # Invoices + line items
│   │   ├── estimates.py      # Estimates + line items
│   │   ├── payments.py       # Payments + allocations
│   │   ├── transactions.py   # Journal entries (double-entry core)
│   │   ├── banking.py        # Bank accounts, transactions, reconciliations
│   │   └── settings.py       # Key-value company settings
│   ├── schemas/              # Pydantic request/response models
│   ├── routes/               # FastAPI routers (one per resource)
│   ├── services/
│   │   ├── accounting.py     # Double-entry journal entry engine
│   │   ├── iif_export.py     # IIF export (8 export functions)
│   │   ├── iif_import.py     # IIF parser + import + validation
│   │   └── pdf_service.py    # WeasyPrint PDF generation
│   ├── templates/
│   │   ├── invoice_pdf.html  # Invoice PDF layout
│   │   ├── estimate_pdf.html # Estimate PDF layout
│   │   └── statement_pdf.html # Customer statement PDF layout
│   ├── seed/                 # Chart of Accounts seed data
│   └── static/
│       ├── css/style.css     # QB2003 "Default Blue" skin
│       └── js/               # SPA router, API wrapper, 12 page modules
├── scripts/
│   ├── seed_database.py      # Seed the Chart of Accounts
│   ├── seed_irs_mock_data.py # IRS Pub 583 mock data (Henry Brown's Auto Body Shop)
│   └── backup.sh             # PostgreSQL backup with rotation
├── screenshots/              # README images
└── index.html                # SPA shell
```

---

## Database Schema

16 tables with a double-entry accounting foundation:

| Table | Purpose |
|-------|---------|
| `accounts` | Chart of Accounts — asset, liability, equity, income, expense, COGS |
| `customers` | Customer contacts with billing/shipping addresses |
| `vendors` | Vendor contacts |
| `items` | Product/service/material/labor items with rates |
| `invoices` | Invoice headers with status tracking |
| `invoice_lines` | Invoice line items |
| `estimates` | Estimate headers |
| `estimate_lines` | Estimate line items |
| `payments` | Payment records |
| `payment_allocations` | Maps payments to invoices (many-to-many) |
| `transactions` | Journal entry headers |
| `transaction_lines` | Journal entry splits (debit OR credit, enforced by CHECK) |
| `bank_accounts` | Bank accounts linked to COA |
| `bank_transactions` | Bank register entries |
| `reconciliations` | Bank reconciliation sessions |
| `settings` | Company settings key-value store |

---

## API

All endpoints under `/api/`. Swagger docs at `/docs`.

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/dashboard` | GET | Company snapshot stats |
| `/api/settings` | GET, PUT | Company settings |
| `/api/accounts` | GET, POST, PUT, DELETE | Chart of Accounts CRUD |
| `/api/customers` | GET, POST, PUT, DELETE | Customer management |
| `/api/vendors` | GET, POST, PUT, DELETE | Vendor management |
| `/api/items` | GET, POST, PUT, DELETE | Items & services |
| `/api/invoices` | GET, POST, PUT | Invoice CRUD with line items |
| `/api/invoices/{id}/pdf` | GET | Generate invoice PDF |
| `/api/invoices/{id}/void` | POST | Void with reversing journal entry |
| `/api/invoices/{id}/send` | POST | Mark invoice as sent |
| `/api/invoices/{id}/duplicate` | POST | Duplicate invoice as new draft |
| `/api/estimates` | GET, POST, PUT | Estimate CRUD with line items |
| `/api/estimates/{id}/pdf` | GET | Generate estimate PDF |
| `/api/estimates/{id}/convert` | POST | Convert estimate to invoice |
| `/api/payments` | GET, POST | Record payments with invoice allocation |
| `/api/banking/accounts` | GET, POST, PUT | Bank account management |
| `/api/banking/transactions` | GET, POST | Bank register entries |
| `/api/banking/reconciliations` | GET, POST | Reconciliation sessions |
| `/api/banking/reconciliations/{id}/transactions` | GET | Transactions for reconciliation |
| `/api/banking/reconciliations/{id}/toggle/{txn}` | POST | Toggle cleared status |
| `/api/banking/reconciliations/{id}/complete` | POST | Complete reconciliation |
| `/api/reports/profit-loss` | GET | P&L report |
| `/api/reports/balance-sheet` | GET | Balance sheet |
| `/api/reports/ar-aging` | GET | Accounts receivable aging |
| `/api/reports/sales-tax` | GET | Sales tax collected |
| `/api/reports/general-ledger` | GET | All journal entries by account |
| `/api/reports/income-by-customer` | GET | Sales totals per customer |
| `/api/reports/customer-statement/{id}/pdf` | GET | Customer statement PDF |
| `/api/iif/export/all` | GET | Export everything as single .iif file |
| `/api/iif/export/{section}` | GET | Export accounts, customers, vendors, items, invoices, payments, or estimates |
| `/api/iif/import` | POST | Upload and import .iif file |
| `/api/iif/validate` | POST | Validate .iif file without importing |

---

## License

**Source Available — Free for personal and enterprise use. No commercial resale.**

You can use, modify, and run Slowbooks Pro for any personal, educational, or internal business purpose. You cannot sell it or offer it as a paid service. See [LICENSE](LICENSE) for full terms.

---

## Acknowledgments

- 14 years of QuickBooks 2003 Pro (1 license, $199.95, 2003 dollars)
- IDA Pro and the reverse engineering community
- The Pervasive PSQL documentation that nobody else has read since 2005
- Every small business owner who lost software they paid for when activation servers died

---

*Built by [VonHoltenCodes](https://github.com/VonHoltenCodes) with Claude Code.*
