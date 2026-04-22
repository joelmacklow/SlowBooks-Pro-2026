/**
 * Decompiled from QBW32.EXE!CReportEngine + CReportViewer  Offset: 0x00210000
 * The original report engine was actually impressive - it had its own query
 * language ("QBReportQuery") that got compiled to Btrieve API calls. The
 * P&L report alone generated 14 separate Btrieve operations. We just use SQL.
 * CReportViewer was an OLE container that hosted a Crystal Reports 8.5 OCX
 * for print preview. We do not miss Crystal Reports.
 */
const ReportsPage = {
    async render() {
        return `
            <div class="page-header"><h2>Reports</h2></div>
            <div class="card-grid">
                <div class="card" style="cursor:pointer" onclick="ReportsPage.profitLoss()">
                    <div class="card-header">Profit & Loss</div>
                    <p style="font-size:13px; color:var(--gray-500);">Income vs expenses for a period</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.balanceSheet()">
                    <div class="card-header">Balance Sheet</div>
                    <p style="font-size:13px; color:var(--gray-500);">Assets, liabilities, and equity</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.trialBalance()">
                    <div class="card-header">Trial Balance</div>
                    <p style="font-size:13px; color:var(--gray-500);">Ending debit and credit balances by account</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.cashFlow()">
                    <div class="card-header">Cash Flow</div>
                    <p style="font-size:13px; color:var(--gray-500);">Operating, investing, and financing cash movements</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.arAging()">
                    <div class="card-header">A/R Aging</div>
                    <p style="font-size:13px; color:var(--gray-500);">Outstanding receivables by age</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.apAging()">
                    <div class="card-header">A/P Aging</div>
                    <p style="font-size:13px; color:var(--gray-500);">Outstanding payables by age</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.gstReturn()">
                    <div class="card-header">GST Return</div>
                    <p style="font-size:13px; color:var(--gray-500);">GST101A boxes and PDF return</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.generalLedger()">
                    <div class="card-header">General Ledger</div>
                    <p style="font-size:13px; color:var(--gray-500);">All journal entries by account</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.incomeByCustomer()">
                    <div class="card-header">Income by Customer</div>
                    <p style="font-size:13px; color:var(--gray-500);">Sales totals per customer</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.customerStatement()">
                    <div class="card-header">Customer Statement</div>
                    <p style="font-size:13px; color:var(--gray-500);">Invoice/payment history PDF</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.monthlyStatements()">
                    <div class="card-header">Monthly Statements</div>
                    <p style="font-size:13px; color:var(--gray-500);">Batch send statements to flagged customers, including zero balances</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="ReportsPage.overdueStatements()">
                    <div class="card-header">Overdue Statements</div>
                    <p style="font-size:13px; color:var(--gray-500);">Batch send statements to overdue customers</p>
                </div>
            </div>`;
    },

    periodOptions(selected) {
        const options = [
            ["this_month", "This Month"],
            ["this_quarter", "This Quarter"],
            ["this_year", "This Year"],
            ["this_year_to_date", "This Year to Date"],
            ["this_fy", "This FY"],
            ["last_month", "Last Month"],
            ["last_quarter", "Last Quarter"],
            ["last_year", "Last Year"],
            ["last_year_to_date", "Last Year to Date"],
            ["last_fy", "Last FY"],
            ["custom", "Custom Date"],
        ];
        return options.map(([value, label]) =>
            `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`
        ).join("");
    },

    _pad(value) {
        return String(value).padStart(2, "0");
    },

    _isoDate(dateObj) {
        return `${dateObj.getFullYear()}-${ReportsPage._pad(dateObj.getMonth() + 1)}-${ReportsPage._pad(dateObj.getDate())}`;
    },

    _quarterStart(monthIndex) {
        return Math.floor(monthIndex / 3) * 3;
    },

    _financialYearBoundary() {
        const value = typeof App !== "undefined" && App.settings ? App.settings.financial_year_start : "";
        const match = /^(\d{2})-(\d{2})$/.exec(String(value || "").trim());
        if (!match) return { month: 1, day: 1 };
        const month = Number(match[1]);
        const day = Number(match[2]);
        if (!month || month < 1 || month > 12 || !day || day < 1 || day > 31) {
            return { month: 1, day: 1 };
        }
        return { month, day };
    },

    _financialYearStartForDate(dateObj) {
        const boundary = ReportsPage._financialYearBoundary();
        const candidate = new Date(dateObj.getFullYear(), boundary.month - 1, boundary.day);
        if (dateObj < candidate) {
            return new Date(dateObj.getFullYear() - 1, boundary.month - 1, boundary.day);
        }
        return candidate;
    },

    _financialYearRange(offset = 0) {
        const currentStart = ReportsPage._financialYearStartForDate(new Date());
        const start = new Date(currentStart.getFullYear() + offset, currentStart.getMonth(), currentStart.getDate());
        const end = new Date(start.getFullYear() + 1, start.getMonth(), start.getDate() - 1);
        return { start, end };
    },

    getDateRange(period, customStart = null, customEnd = null) {
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth();
        const day = today.getDate();
        let start;
        let end;

        switch (period) {
            case "this_month":
                start = new Date(year, month, 1);
                end = new Date(year, month + 1, 0);
                break;
            case "this_quarter": {
                const qStart = ReportsPage._quarterStart(month);
                start = new Date(year, qStart, 1);
                end = new Date(year, qStart + 3, 0);
                break;
            }
            case "this_year":
                start = new Date(year, 0, 1);
                end = new Date(year, 11, 31);
                break;
            case "this_year_to_date":
                start = new Date(year, 0, 1);
                end = today;
                break;
            case "this_fy": {
                const range = ReportsPage._financialYearRange(0);
                start = range.start;
                end = range.end;
                break;
            }
            case "last_month":
                start = new Date(year, month - 1, 1);
                end = new Date(year, month, 0);
                break;
            case "last_quarter": {
                const thisQuarterStart = ReportsPage._quarterStart(month);
                start = new Date(year, thisQuarterStart - 3, 1);
                end = new Date(year, thisQuarterStart, 0);
                break;
            }
            case "last_year":
                start = new Date(year - 1, 0, 1);
                end = new Date(year - 1, 11, 31);
                break;
            case "last_year_to_date":
                start = new Date(year - 1, 0, 1);
                end = new Date(year - 1, month, Math.min(day, new Date(year - 1, month + 1, 0).getDate()));
                break;
            case "last_fy": {
                const range = ReportsPage._financialYearRange(-1);
                start = range.start;
                end = range.end;
                break;
            }
            case "custom":
                return {
                    start: customStart || ReportsPage._isoDate(new Date(year, 0, 1)),
                    end: customEnd || ReportsPage._isoDate(today),
                };
            default:
                start = new Date(year, 0, 1);
                end = today;
                break;
        }

        return {
            start: ReportsPage._isoDate(start),
            end: ReportsPage._isoDate(end),
        };
    },

    getAsOfDate(period, customEnd = null) {
        if (period === "custom") return customEnd || todayISO();
        return ReportsPage.getDateRange(period).end;
    },

    customRangeHtml(initialStart, initialEnd) {
        return `
            <div id="report-custom-range" style="display:none; margin:4px 0 12px 0; font-size:11px; align-items:center; gap:8px;">
                <label for="report-custom-start">From:</label>
                <input id="report-custom-start" type="date" value="${initialStart}">
                <label for="report-custom-end">To:</label>
                <input id="report-custom-end" type="date" value="${initialEnd}">
            </div>`;
    },

    toggleCustomRange() {
        const select = $("#report-period-select");
        const row = $("#report-custom-range");
        if (!select || !row) return;
        row.style.display = select.value === "custom" ? "flex" : "none";
    },

    async openPeriodModal(title, initialPeriod, loadContent, label = "Dates", useAsOfOnly = false) {
        const currentYear = new Date().getFullYear();
        const defaultCustomStart = `${currentYear}-01-01`;
        const defaultCustomEnd = todayISO();

        openModal(title, `
            <div class="form-grid" style="margin-bottom:4px;">
                <div class="form-group">
                    <label>${label}</label>
                    <select id="report-period-select">${ReportsPage.periodOptions(initialPeriod)}</select>
                </div>
            </div>
            ${ReportsPage.customRangeHtml(defaultCustomStart, defaultCustomEnd)}
            <div id="report-content">
                <div style="font-size:11px; color:var(--gray-500);">Loading report...</div>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>`);

        const select = $("#report-period-select");
        const startInput = $("#report-custom-start");
        const endInput = $("#report-custom-end");
        const content = $("#report-content");

        const render = async () => {
            ReportsPage.toggleCustomRange();
            content.innerHTML = `<div style="font-size:11px; color:var(--gray-500);">Loading report...</div>`;
            try {
                if (useAsOfOnly) {
                    const asOfDate = ReportsPage.getAsOfDate(select.value, endInput.value || todayISO());
                    content.innerHTML = await loadContent(select.value, { as_of_date: asOfDate });
                } else {
                    const range = ReportsPage.getDateRange(select.value, startInput.value, endInput.value);
                    content.innerHTML = await loadContent(select.value, range);
                }
            } catch (err) {
                content.innerHTML = `<div class="empty-state"><p>${escapeHtml(err.message)}</p></div>`;
            }
        };

        select.addEventListener("change", render);
        startInput.addEventListener("change", () => { if (select.value === "custom" && !useAsOfOnly) render(); });
        endInput.addEventListener("change", () => { if (select.value === "custom") render(); });
        await render();
    },

    _reportRoute(key) {
        return `#/reports/${key}`;
    },

    _defaultRangeReportState() {
        return {
            period: "this_year_to_date",
            custom_start: `${new Date().getFullYear()}-01-01`,
            custom_end: todayISO(),
        };
    },

    _defaultAsOfReportState() {
        return {
            period: "this_year_to_date",
            custom_end: todayISO(),
        };
    },

    _reportDefinitions() {
        return {
            "profit-loss": {
                title: "Profit & Loss",
                filterMode: "range",
                loadData: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return API.get(`/reports/profit-loss?start_date=${range.start}&end_date=${range.end}`);
                },
                pdfPath: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return `/reports/profit-loss/pdf?start_date=${range.start}&end_date=${range.end}`;
                },
                pdfFilename: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return `ProfitLoss_${range.start}_${range.end}.pdf`;
                },
                renderContent: (data) => ReportsPage.renderProfitLossContent(data),
            },
            "balance-sheet": {
                title: "Balance Sheet",
                filterMode: "as_of",
                loadData: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return API.get(`/reports/balance-sheet?as_of_date=${asOfDate}`);
                },
                pdfPath: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return `/reports/balance-sheet/pdf?as_of_date=${asOfDate}`;
                },
                pdfFilename: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return `BalanceSheet_${asOfDate}.pdf`;
                },
                renderContent: (data) => ReportsPage.renderBalanceSheetContent(data),
            },
            "trial-balance": {
                title: "Trial Balance",
                filterMode: "as_of",
                loadData: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return API.get(`/reports/trial-balance?as_of_date=${asOfDate}`);
                },
                pdfPath: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return `/reports/trial-balance/pdf?as_of_date=${asOfDate}`;
                },
                pdfFilename: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return `TrialBalance_${asOfDate}.pdf`;
                },
                renderContent: (data) => ReportsPage.renderTrialBalanceContent(data),
            },
            "cash-flow": {
                title: "Cash Flow",
                filterMode: "range",
                loadData: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return API.get(`/reports/cash-flow?start_date=${range.start}&end_date=${range.end}`);
                },
                pdfPath: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return `/reports/cash-flow/pdf?start_date=${range.start}&end_date=${range.end}`;
                },
                pdfFilename: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return `CashFlow_${range.start}_${range.end}.pdf`;
                },
                renderContent: (data) => ReportsPage.renderCashFlowContent(data),
            },
            "ar-aging": {
                title: "Accounts Receivable Aging",
                filterMode: "as_of",
                loadData: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return API.get(`/reports/ar-aging?as_of_date=${asOfDate}`);
                },
                pdfPath: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return `/reports/ar-aging/pdf?as_of_date=${asOfDate}`;
                },
                pdfFilename: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return `ARAging_${asOfDate}.pdf`;
                },
                renderContent: (data) => ReportsPage.renderArAgingContent(data),
            },
            "ap-aging": {
                title: "Accounts Payable Aging",
                filterMode: "as_of",
                loadData: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return API.get(`/reports/ap-aging?as_of_date=${asOfDate}`);
                },
                pdfPath: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return `/reports/ap-aging/pdf?as_of_date=${asOfDate}`;
                },
                pdfFilename: (state) => {
                    const asOfDate = ReportsPage.getAsOfDate(state.period, state.custom_end);
                    return `APAging_${asOfDate}.pdf`;
                },
                renderContent: (data) => ReportsPage.renderApAgingContent(data),
            },
            "general-ledger": {
                title: "General Ledger",
                filterMode: "range",
                loadData: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return API.get(`/reports/general-ledger?start_date=${range.start}&end_date=${range.end}`);
                },
                pdfPath: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return `/reports/general-ledger/pdf?start_date=${range.start}&end_date=${range.end}`;
                },
                pdfFilename: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return `GeneralLedger_${range.start}_${range.end}.pdf`;
                },
                renderContent: (data) => ReportsPage.renderGeneralLedgerContent(data),
            },
            "income-by-customer": {
                title: "Income by Customer",
                filterMode: "range",
                loadData: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return API.get(`/reports/income-by-customer?start_date=${range.start}&end_date=${range.end}`);
                },
                pdfPath: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return `/reports/income-by-customer/pdf?start_date=${range.start}&end_date=${range.end}`;
                },
                pdfFilename: (state) => {
                    const range = ReportsPage.getDateRange(state.period, state.custom_start, state.custom_end);
                    return `IncomeByCustomer_${range.start}_${range.end}.pdf`;
                },
                renderContent: (data) => ReportsPage.renderIncomeByCustomerContent(data),
            },
        };
    },

    _reportDefinition(key) {
        return ReportsPage._reportDefinitions()[key];
    },

    _ensureReportState(key) {
        ReportsPage._reportStates = ReportsPage._reportStates || {};
        const definition = ReportsPage._reportDefinition(key);
        if (!ReportsPage._reportStates[key]) {
            ReportsPage._reportStates[key] = definition.filterMode === "range"
                ? ReportsPage._defaultRangeReportState()
                : ReportsPage._defaultAsOfReportState();
        }
        return ReportsPage._reportStates[key];
    },

    openReport(key) {
        ReportsPage._ensureReportState(key);
        return App.navigate(ReportsPage._reportRoute(key));
    },

    refreshReport(key) {
        return App.navigate(ReportsPage._reportRoute(key));
    },

    changeReportPeriod(key, value) {
        const state = ReportsPage._ensureReportState(key);
        state.period = value;
        App.navigate(ReportsPage._reportRoute(key));
    },

    changeReportDate(key, field, value) {
        const state = ReportsPage._ensureReportState(key);
        state[field] = value;
        App.navigate(ReportsPage._reportRoute(key));
    },

    openReportPdf(key) {
        const definition = ReportsPage._reportDefinition(key);
        const state = ReportsPage._ensureReportState(key);
        API.open(definition.pdfPath(state), definition.pdfFilename(state));
    },

    _renderReportFilterControls(key, definition, state) {
        const label = definition.filterMode === "range" ? "Dates" : "As Of";
        const customRow = definition.filterMode === "range"
            ? `
                <div style="display:${state.period === "custom" ? "flex" : "none"}; margin-top:12px; align-items:center; gap:8px; flex-wrap:wrap;">
                    <label for="${key}-custom-start">From:</label>
                    <input id="${key}-custom-start" type="date" value="${state.custom_start}" onchange="ReportsPage.changeReportDate('${key}', 'custom_start', this.value)">
                    <label for="${key}-custom-end">To:</label>
                    <input id="${key}-custom-end" type="date" value="${state.custom_end}" onchange="ReportsPage.changeReportDate('${key}', 'custom_end', this.value)">
                </div>`
            : `
                <div style="display:${state.period === "custom" ? "flex" : "none"}; margin-top:12px; align-items:center; gap:8px; flex-wrap:wrap;">
                    <label for="${key}-custom-end">As of date:</label>
                    <input id="${key}-custom-end" type="date" value="${state.custom_end}" onchange="ReportsPage.changeReportDate('${key}', 'custom_end', this.value)">
                </div>`;

        return `
            <div class="form-grid">
                <div class="form-group">
                    <label>${label}</label>
                    <select onchange="ReportsPage.changeReportPeriod('${key}', this.value)">
                        ${ReportsPage.periodOptions(state.period)}
                    </select>
                </div>
            </div>
            ${customRow}
            <div class="form-actions" style="justify-content:flex-start;">
                <button class="btn btn-secondary" onclick="ReportsPage.refreshReport('${key}')">Refresh</button>
                <button class="btn btn-primary" onclick="ReportsPage.openReportPdf('${key}')">View / Print PDF</button>
            </div>`;
    },

    async renderReportScreen(key) {
        const definition = ReportsPage._reportDefinition(key);
        const state = ReportsPage._ensureReportState(key);
        const data = await definition.loadData(state);
        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Reports</div>
                    <h2>${escapeHtml(definition.title)}</h2>
                </div>
                <button class="btn btn-secondary" onclick="App.navigate('#/reports')">Back to Reports</button>
            </div>
            <div class="settings-section">
                ${ReportsPage._renderReportFilterControls(key, definition, state)}
            </div>
            <div class="settings-section">
                ${definition.renderContent(data, state)}
            </div>`;
    },

    renderProfitLossContent(data) {
        const section = (items) => {
            if (!items.length) return `<tr><td colspan="2" style="color:var(--gray-400);">None</td></tr>`;
            return items.map(i =>
                `<tr><td style="padding-left:24px;">${escapeHtml(i.account_name)}</td><td class="amount">${formatCurrency(Math.abs(i.amount))}</td></tr>`
            ).join("");
        };
        return `
            <p style="margin-bottom:12px; color:var(--gray-500);">${formatDate(data.start_date)} &mdash; ${formatDate(data.end_date)}</p>
            <div class="table-container"><table>
                <thead><tr><th>Account</th><th class="amount">Amount</th></tr></thead>
                <tbody>
                    <tr><td><strong>Income</strong></td><td></td></tr>
                    ${section(data.income)}
                    <tr style="font-weight:600; background:var(--gray-50);"><td>Total Income</td><td class="amount">${formatCurrency(data.total_income)}</td></tr>
                    <tr><td><strong>Cost of Goods Sold</strong></td><td></td></tr>
                    ${section(data.cogs)}
                    <tr style="font-weight:600; background:var(--gray-50);"><td>Gross Profit</td><td class="amount">${formatCurrency(data.gross_profit)}</td></tr>
                    <tr><td><strong>Expenses</strong></td><td></td></tr>
                    ${section(data.expenses)}
                    <tr style="font-weight:600; background:var(--gray-50);"><td>Total Expenses</td><td class="amount">${formatCurrency(data.total_expenses)}</td></tr>
                    <tr style="font-weight:700; font-size:15px; background:var(--primary-light);"><td>Net Income</td><td class="amount">${formatCurrency(data.net_income)}</td></tr>
                </tbody>
            </table></div>`;
    },

    renderBalanceSheetContent(data) {
        const section = (items) => items.map(i =>
            `<tr><td style="padding-left:24px;">${escapeHtml(i.account_name)}</td><td class="amount">${formatCurrency(Math.abs(i.amount))}</td></tr>`
        ).join("") || `<tr><td colspan="2" style="color:var(--gray-400);">None</td></tr>`;
        const diffStyle = data.is_balanced ? 'color:var(--success);' : 'color:var(--danger);';
        return `
            <p style="margin-bottom:12px; color:var(--gray-500);">As of ${formatDate(data.as_of_date)}</p>
            <div class="table-container"><table>
                <thead><tr><th>Account</th><th class="amount">Amount</th></tr></thead>
                <tbody>
                    <tr><td><strong>Assets</strong></td><td></td></tr>
                    ${section(data.assets)}
                    <tr style="font-weight:600; background:var(--gray-50);"><td>Total Assets</td><td class="amount">${formatCurrency(data.total_assets)}</td></tr>
                    <tr><td><strong>Liabilities</strong></td><td></td></tr>
                    ${section(data.liabilities)}
                    <tr style="font-weight:600; background:var(--gray-50);"><td>Total Liabilities</td><td class="amount">${formatCurrency(data.total_liabilities)}</td></tr>
                    <tr><td><strong>Equity</strong></td><td></td></tr>
                    ${section(data.equity)}
                    <tr><td style="padding-left:24px;">Current Earnings</td><td class="amount">${formatCurrency(data.current_earnings)}</td></tr>
                    <tr style="font-weight:600; background:var(--gray-50);"><td>Total Equity</td><td class="amount">${formatCurrency(data.total_equity)}</td></tr>
                    <tr style="font-weight:600; background:var(--gray-50);"><td>Total Liabilities + Equity</td><td class="amount">${formatCurrency(data.total_liabilities_and_equity)}</td></tr>
                    <tr style="font-weight:700; ${diffStyle}"><td>Difference</td><td class="amount">${formatCurrency(data.balance_difference)}</td></tr>
                </tbody>
            </table></div>`;
    },

    renderTrialBalanceContent(data) {
        const rows = data.accounts.map((account) => `
            <tr>
                <td>${escapeHtml(account.account_number || '')}</td>
                <td>${escapeHtml(account.account_name)}</td>
                <td>${escapeHtml(account.account_type)}</td>
                <td class="amount">${account.debit_balance ? formatCurrency(account.debit_balance) : ''}</td>
                <td class="amount">${account.credit_balance ? formatCurrency(account.credit_balance) : ''}</td>
            </tr>
        `).join("") || `<tr><td colspan="5" style="color:var(--gray-400);">No balances for this date</td></tr>`;

        return `
            <p style="margin-bottom:12px; color:var(--gray-500);">As of ${formatDate(data.as_of_date)}</p>
            <div class="table-container"><table>
                <thead><tr><th>No.</th><th>Account</th><th>Type</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead>
                <tbody>
                    ${rows}
                    <tr style="font-weight:700; background:var(--primary-light);">
                        <td colspan="3">Totals</td>
                        <td class="amount">${formatCurrency(data.total_debit)}</td>
                        <td class="amount">${formatCurrency(data.total_credit)}</td>
                    </tr>
                </tbody>
            </table></div>`;
    },

    renderProfitLossScreen() {
        return ReportsPage.renderReportScreen("profit-loss");
    },

    renderBalanceSheetScreen() {
        return ReportsPage.renderReportScreen("balance-sheet");
    },

    renderTrialBalanceScreen() {
        return ReportsPage.renderReportScreen("trial-balance");
    },

    async cashFlow() {
        return ReportsPage.openReport("cash-flow");
    },

    renderCashFlowContent(data) {
        const section = (title, payload) => {
            const rows = (payload.items || []).map((item) => `
                <tr>
                    <td>${formatDate(item.date)}</td>
                    <td>${escapeHtml(item.description)}</td>
                    <td>${escapeHtml(item.reference)}</td>
                    <td class="amount">${formatCurrency(item.amount)}</td>
                </tr>
            `).join("") || `<tr><td colspan="4" style="color:var(--gray-400);">No ${title.toLowerCase()} cash flows</td></tr>`;

            return `
                <h3 style="margin:16px 0 8px 0;">${title}</h3>
                <div class="table-container"><table>
                    <thead><tr><th>Date</th><th>Description</th><th>Reference</th><th class="amount">Amount</th></tr></thead>
                    <tbody>
                        ${rows}
                        <tr style="font-weight:700; background:var(--gray-50);">
                            <td colspan="3">Net cash from ${title.toLowerCase()}</td>
                            <td class="amount">${formatCurrency(payload.total || 0)}</td>
                        </tr>
                    </tbody>
                </table></div>`;
        };

        return `
            <p style="margin-bottom:12px; color:var(--gray-500);">${formatDate(data.start_date)} &mdash; ${formatDate(data.end_date)}</p>
            <div style="margin-bottom:12px; padding:8px; background:var(--gray-50); border:1px solid var(--gray-200);">
                <div style="display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; font-size:12px;">
                    <span>Opening cash: <strong>${formatCurrency(data.opening_cash)}</strong></span>
                    <span>Net change: <strong>${formatCurrency(data.net_cash_change)}</strong></span>
                    <span>Closing cash: <strong>${formatCurrency(data.closing_cash)}</strong></span>
                </div>
            </div>
            ${section('Operating Activities', data.operating || { items: [], total: 0 })}
            ${section('Investing Activities', data.investing || { items: [], total: 0 })}
            ${section('Financing Activities', data.financing || { items: [], total: 0 })}`;
    },

    renderCashFlowScreen() {
        return ReportsPage.renderReportScreen("cash-flow");
    },

    async profitLoss() {
        return ReportsPage.openReport("profit-loss");
    },

    async balanceSheet() {
        return ReportsPage.openReport("balance-sheet");
    },

    async trialBalance() {
        return ReportsPage.openReport("trial-balance");
    },

    gstReturn() {
        ReportsPage._gstDetailState = null;
        return App.navigate('#/reports/gst-return');
    },

    _gstStatusBadge(status, label) {
        const style = status === 'confirmed'
            ? 'background:#dff5e6; color:#216e3a; border:1px solid #a8d5b8;'
            : status === 'due'
                ? 'background:#fde7c7; color:#8a5a00; border:1px solid #f3c98a;'
                : 'background:var(--gray-50); color:var(--text-muted); border:1px solid var(--gray-200);';
        return `<span style="display:inline-block; padding:2px 8px; border-radius:999px; font-size:10px; font-weight:600; ${style}">${escapeHtml(label)}</span>`;
    },

    _gstSourceTypeLabel(sourceType) {
        const map = {
            invoice: 'Invoice',
            payment: 'Payment',
            bill: 'Bill',
            bill_payment: 'Bill Payment',
            credit_memo: 'Credit Memo',
        };
        return map[sourceType] || sourceType;
    },

    _ensureGstHistoryState(groups) {
        if (!ReportsPage._gstExpandedYears || ReportsPage._gstExpandedYears.size === 0) {
            ReportsPage._gstExpandedYears = new Set((groups || []).slice(0, 1).map(group => group.label));
        }
    },

    toggleGstHistoryYear(label) {
        ReportsPage._gstExpandedYears = ReportsPage._gstExpandedYears || new Set();
        if (ReportsPage._gstExpandedYears.has(label)) {
            ReportsPage._gstExpandedYears.delete(label);
        } else {
            ReportsPage._gstExpandedYears.add(label);
        }
        App.navigate('#/reports/gst-return');
    },

    openGstReturnDetail(startDate, endDate, box9Adjustments = '0.00', box13Adjustments = '0.00', periodLabel = '', dueDate = '', status = '') {
        ReportsPage._gstDetailState = {
            start_date: startDate,
            end_date: endDate,
            box9_adjustments: box9Adjustments,
            box13_adjustments: box13Adjustments,
            period_label: periodLabel,
            due_date: dueDate,
            status,
            return_status: status === 'confirmed' ? 'confirmed' : 'draft',
            confirmed_at: null,
            tab: 'summary',
            page: 1,
            page_size: 50,
        };
        App.navigate('#/reports/gst-return/detail');
    },

    _gstDetailStateOrNull() {
        return ReportsPage._gstDetailState || null;
    },

    _gstDetailControls() {
        const state = ReportsPage._gstDetailStateOrNull();
        if (!state) return '';
        const isConfirmed = state.return_status === 'confirmed';
        const confirmationNote = isConfirmed
            ? `Return confirmed ${state.confirmed_at ? formatDate(state.confirmed_at) : ''}`
            : 'Confirm this GST return to save Box 9 and Box 13 permanently before viewing or printing GST101A.';
        return `
            <div class="settings-section">
                <div style="font-size:11px; color:var(--text-muted); margin-bottom:8px;">${confirmationNote}</div>
                <div class="form-grid" style="margin-bottom:4px;">
                    <div class="form-group">
                        <label>Box 9 adjustments</label>
                        <input id="gst-box9-adjustments" type="number" step="0.01" value="${escapeHtml(state.box9_adjustments || '0.00')}" ${isConfirmed ? 'disabled' : ''}>
                    </div>
                    <div class="form-group">
                        <label>Box 13 credit adjustments</label>
                        <input id="gst-box13-adjustments" type="number" step="0.01" value="${escapeHtml(state.box13_adjustments || '0.00')}" ${isConfirmed ? 'disabled' : ''}>
                    </div>
                </div>
                <div class="form-actions" style="justify-content:flex-start;">
                    <button class="btn btn-secondary" onclick="ReportsPage.refreshGstReturnDetail()" ${isConfirmed ? 'disabled' : ''}>Refresh</button>
                    ${isConfirmed ? '' : '<button class="btn btn-primary" onclick="ReportsPage.confirmGstReturn()">Confirm GST Return</button>'}
                    <button class="btn btn-primary" onclick="ReportsPage.downloadGstReturnPdf()" ${isConfirmed ? '' : 'disabled'}>View / Print GST101A PDF</button>
                </div>
            </div>`;
    },

    refreshGstReturnDetail() {
        const state = ReportsPage._gstDetailStateOrNull();
        if (!state) return App.navigate('#/reports/gst-return');
        state.box9_adjustments = $("#gst-box9-adjustments")?.value || '0.00';
        state.box13_adjustments = $("#gst-box13-adjustments")?.value || '0.00';
        state.page = 1;
        App.navigate('#/reports/gst-return/detail');
    },

    switchGstTab(tab) {
        const state = ReportsPage._gstDetailStateOrNull();
        if (!state) return App.navigate('#/reports/gst-return');
        state.tab = tab;
        if (tab !== 'transactions') state.page = 1;
        App.navigate('#/reports/gst-return/detail');
    },

    goGstTransactionsPage(page) {
        const state = ReportsPage._gstDetailStateOrNull();
        if (!state) return App.navigate('#/reports/gst-return');
        state.tab = 'transactions';
        state.page = page;
        App.navigate('#/reports/gst-return/detail');
    },

    backToGstReturns() {
        App.navigate('#/reports/gst-return');
    },

    async renderGstReturnsScreen() {
        const data = await API.get('/reports/gst-return/overview');
        ReportsPage._ensureGstHistoryState(data.historical_groups || []);
        const currentRows = (data.open_periods || []).map(period => `
            <tr>
                <td><strong>${escapeHtml(period.period_label)}</strong></td>
                <td>${formatDate(period.due_date)}</td>
                <td>${ReportsPage._gstStatusBadge(period.status, period.status_label)}</td>
                <td class="amount">${period.net_gst == null ? '&mdash;' : formatCurrency(period.net_gst)}</td>
                <td class="actions"><button class="btn btn-sm btn-secondary" onclick="ReportsPage.openGstReturnDetail('${period.start_date}', '${period.end_date}', '${period.box9_adjustments}', '${period.box13_adjustments}', '${escapeHtml(period.period_label)}', '${period.due_date}', '${period.status}')">View return</button></td>
            </tr>`).join('');

        const historicalGroups = (data.historical_groups || []).map(group => {
            const expanded = ReportsPage._gstExpandedYears.has(group.label);
            const rows = (group.returns || []).map(period => `
                <tr>
                    <td><strong>${escapeHtml(period.period_label)}</strong></td>
                    <td>${formatDate(period.due_date)}</td>
                    <td>${ReportsPage._gstStatusBadge(period.status, period.status_label)}</td>
                    <td class="amount">${formatCurrency(period.net_gst)}</td>
                    <td class="actions"><button class="btn btn-sm btn-secondary" onclick="ReportsPage.openGstReturnDetail('${period.start_date}', '${period.end_date}', '${period.box9_adjustments}', '${period.box13_adjustments}', '${escapeHtml(period.period_label)}', '${period.due_date}', '${period.status}')">View return</button></td>
                </tr>`).join('');
            return `
                <div class="settings-section" style="padding:0;">
                    <button type="button" class="btn btn-secondary" style="width:100%; text-align:left; border:none; border-radius:0; background:transparent; padding:14px 16px;" onclick="ReportsPage.toggleGstHistoryYear('${escapeHtml(group.label)}')">
                        <strong>${expanded ? '&#9662;' : '&#9656;'}</strong> ${escapeHtml(group.label)}
                    </button>
                    ${expanded ? `<div class="table-container" style="border-top:1px solid var(--gray-200);"><table>
                        <thead><tr><th>Period</th><th>File by date</th><th>Status</th><th class="amount">Net GST</th><th>Actions</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table></div>` : ''}
                </div>`;
        }).join('');

        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Reports</div>
                    <h2>GST Returns</h2>
                </div>
                <button class="btn btn-secondary" onclick="App.navigate('#/reports')">Back to Reports</button>
            </div>
            <div class="settings-section">
                <h3>Current &amp; In Progress</h3>
                <div class="table-container"><table>
                    <thead><tr><th>Period</th><th>File by date</th><th>Status</th><th class="amount">Net GST</th><th>Actions</th></tr></thead>
                    <tbody>${currentRows || '<tr><td colspan="5" style="text-align:center; color:var(--gray-400);">No open GST periods.</td></tr>'}</tbody>
                </table></div>
            </div>
            <div>
                <div class="page-header" style="margin-top:20px;">
                    <h3>Historical Returns</h3>
                </div>
                ${historicalGroups || '<div class="empty-state"><p>No confirmed GST returns yet.</p></div>'}
            </div>`;
    },

    renderGstReturnSummary(data) {
        const boxRows = [
            ["5", "Total sales and income including GST and zero-rated supplies"],
            ["6", "Zero-rated supplies included in Box 5"],
            ["7", "Box 5 minus Box 6"],
            ["8", "Box 7 multiplied by 3/23"],
            ["9", "Adjustments from calculation sheet"],
            ["10", "Total GST collected on sales and income"],
            ["11", "Total purchases and expenses including GST"],
            ["12", "Box 11 multiplied by 3/23"],
            ["13", "Credit adjustments from calculation sheet"],
            ["14", "Total GST credit for purchases and expenses"],
            ["15", "Difference between Box 10 and Box 14"],
        ].map(([box, label]) => `
            <tr>
                <td><strong>${box}</strong></td>
                <td>${escapeHtml(label)}</td>
                <td class="amount">${formatCurrency(data.boxes[box] || 0)}</td>
            </tr>`).join("");
        const position = data.net_position === "refundable" ? "GST refund" :
            data.net_position === "payable" ? "GST to pay" : "Nil GST";
        const settlement = data.settlement || { status: 'unsettled', candidates: [] };
        const settlementHtml = settlement.status === 'confirmed'
            ? `<div style="margin-top:12px; padding:8px; background:var(--primary-light); border:1px solid var(--primary);">
                    <strong>Settlement Status:</strong> Confirmed<br>
                    <span style="font-size:10px; color:var(--text-muted);">Settlement date: ${formatDate(settlement.settlement?.settlement_date || '')}</span>
               </div>`
            : settlement.status === 'no_settlement_required'
                ? `<div style="margin-top:12px; padding:8px; background:var(--gray-50); border:1px solid var(--gray-200);">
                        <strong>Settlement Status:</strong> No settlement required for this period.
                   </div>`
                : settlement.status === 'awaiting_return_confirmation'
                    ? `<div style="margin-top:12px; padding:8px; background:var(--gray-50); border:1px solid var(--gray-200);">
                            <strong>Settlement Status:</strong> Awaiting return confirmation<br>
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">Confirm the GST return before settlement options become available.</div>
                       </div>`
                : `<div style="margin-top:12px; padding:8px; background:var(--gray-50); border:1px solid var(--gray-200);">
                        <strong>Settlement Status:</strong> Unsettled<br>
                        <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">Expected bank amount: ${formatCurrency(settlement.expected_bank_amount || 0)}</div>
                        ${(settlement.candidates || []).length > 0 ? `
                            <div style="margin-top:8px;">
                                ${(settlement.candidates || []).map(candidate => `
                                    <div style="display:flex; justify-content:space-between; gap:8px; align-items:center; padding:4px 0; border-top:1px solid var(--gray-200);">
                                        <div style="font-size:10px;">
                                            <strong>${formatDate(candidate.date)}</strong> — ${escapeHtml(candidate.payee || candidate.description || 'Bank transaction')}
                                            <div style="color:var(--text-muted);">${formatCurrency(candidate.amount)}</div>
                                        </div>
                                        <button class="btn btn-sm btn-primary" onclick="ReportsPage.confirmGstSettlement(${candidate.id})">Confirm Settlement</button>
                                    </div>`).join('')}
                            </div>`
                            : '<div style="font-size:10px; color:var(--text-muted); margin-top:6px;">No reconciled bank transactions match this GST period yet.</div>'}
                   </div>`;
        return `
            <p style="margin-bottom:12px; color:var(--gray-500);">
                ${formatDate(data.start_date)} &mdash; ${formatDate(data.end_date)}
                · Basis: <strong>${escapeHtml(data.gst_basis)}</strong>
                · Period: <strong>${escapeHtml(data.gst_period)}</strong>
            </p>
            <div style="margin-bottom:12px; padding:8px; background:var(--gray-50); border:1px solid var(--gray-200);">
                <div style="display:flex; justify-content:space-between; font-size:12px;">
                    <span>Output GST: <strong>${formatCurrency(data.output_gst)}</strong></span>
                    <span>Input GST: <strong>${formatCurrency(data.input_gst)}</strong></span>
                    <span>${position}: <strong>${formatCurrency(data.net_gst)}</strong></span>
                </div>
            </div>
                <div class="table-container"><table>
                <thead><tr><th>Box</th><th>GST101A field</th><th class="amount">Amount</th></tr></thead>
                <tbody>${boxRows}</tbody>
            </table></div>
            ${settlementHtml}`;
    },

    renderGstTransactions(data) {
        const startIndex = data.total_count === 0 ? 0 : ((data.page - 1) * data.page_size) + 1;
        const endIndex = Math.min(data.page * data.page_size, data.total_count);
        const rows = (data.items || []).map(item => `
            <tr>
                <td>${formatDate(item.date)}</td>
                <td>${escapeHtml(ReportsPage._gstSourceTypeLabel(item.source_type))}</td>
                <td>${escapeHtml(item.number)}</td>
                <td>${escapeHtml(item.name)}</td>
                <td class="amount">${formatCurrency(item.standard_gross || 0)}</td>
                <td class="amount">${formatCurrency(item.zero_rated || 0)}</td>
                <td class="amount">${formatCurrency(item.excluded || 0)}</td>
            </tr>`).join('');
        return `
            <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px;">
                <div style="font-size:11px; color:var(--text-muted);">Showing ${startIndex}-${endIndex} of ${data.total_count}</div>
                <div class="actions">
                    <button class="btn btn-sm btn-secondary" ${data.page <= 1 ? 'disabled' : ''} onclick="ReportsPage.goGstTransactionsPage(${data.page - 1})">Previous</button>
                    <button class="btn btn-sm btn-secondary" ${data.page >= data.total_pages ? 'disabled' : ''} onclick="ReportsPage.goGstTransactionsPage(${data.page + 1})">Next</button>
                </div>
            </div>
            <div class="table-container" style="max-height:480px; overflow:auto;"><table>
                <thead><tr><th>Date</th><th>Source</th><th>Number</th><th>Name</th><th class="amount">Standard-rated</th><th class="amount">Zero-rated</th><th class="amount">Excluded</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="7" style="text-align:center; color:var(--gray-400);">No GST activity</td></tr>'}</tbody>
            </table></div>`;
    },

    async renderGstReturnDetailScreen() {
        const state = ReportsPage._gstDetailStateOrNull();
        if (!state) {
            return `<div class="empty-state"><p>Select a GST return from the GST Returns screen first.</p><p style="margin-top:8px;"><button class="btn btn-primary" onclick="ReportsPage.backToGstReturns()">Back to GST Returns</button></p></div>`;
        }

        let detailContent = `<div class="empty-state"><p>Loading GST return...</p></div>`;
        if (state.tab === 'transactions') {
            const data = await API.get(`/reports/gst-return/transactions?start_date=${state.start_date}&end_date=${state.end_date}&box9_adjustments=${encodeURIComponent(state.box9_adjustments || '0.00')}&box13_adjustments=${encodeURIComponent(state.box13_adjustments || '0.00')}&page=${state.page || 1}&page_size=${state.page_size || 50}`);
            detailContent = ReportsPage.renderGstTransactions(data);
        } else {
            const data = await API.get(`/reports/gst-return?start_date=${state.start_date}&end_date=${state.end_date}&box9_adjustments=${encodeURIComponent(state.box9_adjustments || '0.00')}&box13_adjustments=${encodeURIComponent(state.box13_adjustments || '0.00')}`);
            state.return_status = data.return_confirmation?.status || 'draft';
            state.confirmed_at = data.return_confirmation?.confirmed_at || null;
            if (data.return_confirmation?.due_date) state.due_date = data.return_confirmation.due_date;
            if (data.return_confirmation?.box9_adjustments) state.box9_adjustments = data.return_confirmation.box9_adjustments;
            if (data.return_confirmation?.box13_adjustments) state.box13_adjustments = data.return_confirmation.box13_adjustments;
            detailContent = ReportsPage.renderGstReturnSummary(data);
        }

        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Reports / GST Returns</div>
                    <h2>${escapeHtml(state.period_label || `${state.start_date} - ${state.end_date}`)}</h2>
                    <div style="font-size:11px; color:var(--text-muted);">
                        ${state.due_date ? `File by ${formatDate(state.due_date)}` : ''}${state.status ? ` · ${escapeHtml(state.status.replaceAll('_', ' '))}` : ''}
                    </div>
                </div>
                <button class="btn btn-secondary" onclick="ReportsPage.backToGstReturns()">Back to GST Returns</button>
            </div>
            ${ReportsPage._gstDetailControls()}
            <div class="settings-section">
                <div style="display:flex; gap:8px; margin-bottom:12px;">
                    <button class="btn ${state.tab === 'summary' ? 'btn-primary' : 'btn-secondary'}" onclick="ReportsPage.switchGstTab('summary')">GST Return</button>
                    <button class="btn ${state.tab === 'transactions' ? 'btn-primary' : 'btn-secondary'}" onclick="ReportsPage.switchGstTab('transactions')">Transactions</button>
                </div>
                ${detailContent}
            </div>`;
    },

    downloadGstReturnPdf() {
        const state = ReportsPage._gstDetailStateOrNull();
        if (!state) return;
        if (state.return_status !== 'confirmed') {
            toast('Confirm the GST return before viewing GST101A', 'error');
            return;
        }
        const box9 = ($("#gst-box9-adjustments")?.value || state.box9_adjustments || "0.00");
        const box13 = ($("#gst-box13-adjustments")?.value || state.box13_adjustments || "0.00");
        state.box9_adjustments = box9;
        state.box13_adjustments = box13;
        API.open(`/reports/gst-return/pdf?start_date=${state.start_date}&end_date=${state.end_date}&box9_adjustments=${encodeURIComponent(box9)}&box13_adjustments=${encodeURIComponent(box13)}`, `GST101A_${state.start_date}_${state.end_date}.pdf`);
    },

    async confirmGstReturn() {
        const state = ReportsPage._gstDetailStateOrNull();
        if (!state) return;
        const box9 = ($("#gst-box9-adjustments")?.value || state.box9_adjustments || "0.00");
        const box13 = ($("#gst-box13-adjustments")?.value || state.box13_adjustments || "0.00");
        try {
            const result = await API.post('/reports/gst-return/confirm', {
                start_date: state.start_date,
                end_date: state.end_date,
                box9_adjustments: box9,
                box13_adjustments: box13,
            });
            toast('GST return confirmed');
            state.return_status = 'confirmed';
            state.confirmed_at = result.confirmed_at || null;
            state.box9_adjustments = result.box9_adjustments || box9;
            state.box13_adjustments = result.box13_adjustments || box13;
            if (result.due_date) state.due_date = result.due_date;
            App.navigate('#/reports/gst-return/detail');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async confirmGstSettlement(bankTransactionId) {
        const state = ReportsPage._gstDetailStateOrNull();
        if (!state) return;
        const box9 = ($("#gst-box9-adjustments")?.value || state.box9_adjustments || "0.00");
        const box13 = ($("#gst-box13-adjustments")?.value || state.box13_adjustments || "0.00");
        try {
            await API.post('/reports/gst-return/settlement', {
                start_date: state.start_date,
                end_date: state.end_date,
                bank_transaction_id: bankTransactionId,
                box9_adjustments: box9,
                box13_adjustments: box13,
            });
            toast('GST settlement confirmed');
            state.box9_adjustments = box9;
            state.box13_adjustments = box13;
            App.navigate('#/reports/gst-return/detail');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async salesTax() {
        return ReportsPage.gstReturn();
    },

    async generalLedger() {
        return ReportsPage.openReport("general-ledger");
    },

    renderGeneralLedgerContent(data) {
        let html = `<p style="margin-bottom:12px; color:var(--gray-500);">${formatDate(data.start_date)} &mdash; ${formatDate(data.end_date)}</p>`;
        if (data.accounts.length === 0) {
            html += `<div class="empty-state"><p>No journal entries found</p></div>`;
            return html;
        }
        for (const acct of data.accounts) {
            html += `<h3 style="margin:12px 0 4px; font-size:12px; color:var(--qb-navy);">${escapeHtml(acct.account_number || '')} ${acct.account_number ? '&mdash;' : ''} ${escapeHtml(acct.account_name)}</h3>`;
            html += `<div class="table-container"><table>
                <thead><tr><th>Date</th><th>Description</th><th>Reference</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead><tbody>`;
            for (const e of acct.entries) {
                html += `<tr>
                    <td>${formatDate(e.date)}</td>
                    <td>${escapeHtml(e.description)}</td>
                    <td>${escapeHtml(e.reference)}</td>
                    <td class="amount">${e.debit > 0 ? formatCurrency(e.debit) : ""}</td>
                    <td class="amount">${e.credit > 0 ? formatCurrency(e.credit) : ""}</td>
                </tr>`;
            }
            html += `<tr style="font-weight:600; background:var(--gray-50);">
                <td colspan="3">Total</td>
                <td class="amount">${formatCurrency(acct.total_debit)}</td>
                <td class="amount">${formatCurrency(acct.total_credit)}</td>
            </tr></tbody></table></div>`;
        }
        return html;
    },

    renderGeneralLedgerScreen() {
        return ReportsPage.renderReportScreen("general-ledger");
    },

    async incomeByCustomer() {
        return ReportsPage.openReport("income-by-customer");
    },

    renderIncomeByCustomerContent(data) {
        let rows = data.items.map(i =>
            `<tr>
                <td>${escapeHtml(i.customer_name)}</td>
                <td class="amount">${i.invoice_count}</td>
                <td class="amount">${formatCurrency(i.total_sales)}</td>
                <td class="amount">${formatCurrency(i.total_paid)}</td>
                <td class="amount">${formatCurrency(i.total_balance)}</td>
            </tr>`
        ).join("");
        rows += `<tr style="font-weight:700; background:var(--gray-50);">
            <td>TOTAL</td>
            <td class="amount">${data.items.reduce((sum, item) => sum + item.invoice_count, 0)}</td>
            <td class="amount">${formatCurrency(data.total_sales)}</td>
            <td class="amount">${formatCurrency(data.total_paid)}</td>
            <td class="amount">${formatCurrency(data.total_balance)}</td>
        </tr>`;
        return `
            <p style="margin-bottom:12px; color:var(--gray-500);">${formatDate(data.start_date)} &mdash; ${formatDate(data.end_date)}</p>
            <div class="table-container"><table>
                <thead><tr><th>Customer</th><th class="amount">Invoices</th><th class="amount">Sales</th><th class="amount">Paid</th><th class="amount">Balance</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="5" style="text-align:center; color:var(--gray-400);">No sales data</td></tr>'}</tbody>
            </table></div>`;
    },

    renderIncomeByCustomerScreen() {
        return ReportsPage.renderReportScreen("income-by-customer");
    },

    _ensureStatementState(customers = []) {
        ReportsPage._reportStates = ReportsPage._reportStates || {};
        if (!ReportsPage._reportStates["customer-statement"]) {
            ReportsPage._reportStates["customer-statement"] = {
                customer_id: customers[0] ? String(customers[0].id) : "",
                as_of_date: todayISO(),
                recipient: customers[0]?.email || "",
            };
        }
        return ReportsPage._reportStates["customer-statement"];
    },

    _ensureOverdueStatementsState() {
        ReportsPage._reportStates = ReportsPage._reportStates || {};
        if (!ReportsPage._reportStates["overdue-statements"]) {
            ReportsPage._reportStates["overdue-statements"] = {
                as_of_date: todayISO(),
                selected_customer_ids: [],
                items: [],
            };
        }
        return ReportsPage._reportStates["overdue-statements"];
    },

    _ensureMonthlyStatementsState() {
        ReportsPage._reportStates = ReportsPage._reportStates || {};
        if (!ReportsPage._reportStates["monthly-statements"]) {
            ReportsPage._reportStates["monthly-statements"] = {
                as_of_date: todayISO(),
                selected_customer_ids: [],
                items: [],
                last_results: [],
            };
        }
        return ReportsPage._reportStates["monthly-statements"];
    },

    async customerStatement() {
        ReportsPage._ensureStatementState();
        return App.navigate('#/reports/customer-statement');
    },

    async overdueStatements() {
        ReportsPage._ensureOverdueStatementsState();
        return App.navigate('#/reports/overdue-statements');
    },

    async monthlyStatements() {
        ReportsPage._ensureMonthlyStatementsState();
        return App.navigate('#/reports/monthly-statements');
    },

    changeStatementCustomer(value) {
        const state = ReportsPage._ensureStatementState(ReportsPage._statementCustomers || []);
        const customer = (ReportsPage._statementCustomers || []).find((entry) => String(entry.id) === String(value));
        state.customer_id = value;
        state.recipient = customer?.email || '';
        App.navigate('#/reports/customer-statement');
    },

    changeStatementDate(value) {
        const state = ReportsPage._ensureStatementState();
        state.as_of_date = value;
        App.navigate('#/reports/customer-statement');
    },

    changeOverdueStatementsDate(value) {
        const state = ReportsPage._ensureOverdueStatementsState();
        state.as_of_date = value;
        state.selected_customer_ids = [];
        App.navigate('#/reports/overdue-statements');
    },

    changeMonthlyStatementsDate(value) {
        const state = ReportsPage._ensureMonthlyStatementsState();
        state.as_of_date = value;
        state.selected_customer_ids = [];
        App.navigate('#/reports/monthly-statements');
    },

    toggleOverdueStatementSelection(customerId) {
        const state = ReportsPage._ensureOverdueStatementsState();
        const id = String(customerId);
        if (state.selected_customer_ids.includes(id)) {
            state.selected_customer_ids = state.selected_customer_ids.filter(item => item !== id);
        } else {
            state.selected_customer_ids.push(id);
        }
        App.navigate('#/reports/overdue-statements');
    },

    toggleAllOverdueStatements() {
        const state = ReportsPage._ensureOverdueStatementsState();
        const ids = (state.items || []).map(item => String(item.customer_id));
        state.selected_customer_ids = state.selected_customer_ids.length === ids.length ? [] : ids;
        App.navigate('#/reports/overdue-statements');
    },

    toggleMonthlyStatementSelection(customerId) {
        const state = ReportsPage._ensureMonthlyStatementsState();
        const id = String(customerId);
        if (state.selected_customer_ids.includes(id)) {
            state.selected_customer_ids = state.selected_customer_ids.filter(item => item !== id);
        } else {
            state.selected_customer_ids.push(id);
        }
        App.navigate('#/reports/monthly-statements');
    },

    toggleAllMonthlyStatements() {
        const state = ReportsPage._ensureMonthlyStatementsState();
        const ids = (state.items || []).map(item => String(item.customer_id));
        state.selected_customer_ids = state.selected_customer_ids.length === ids.length ? [] : ids;
        App.navigate('#/reports/monthly-statements');
    },

    updateStatementRecipient(value) {
        const state = ReportsPage._ensureStatementState();
        state.recipient = value;
    },

    openStatementPdf() {
        const state = ReportsPage._ensureStatementState();
        if (!state.customer_id) {
            toast('Select a customer first', 'error');
            return;
        }
        API.open(`/reports/customer-statement/${state.customer_id}/pdf?as_of_date=${state.as_of_date}`, `Statement_${state.customer_id}_${state.as_of_date}.pdf`);
    },

    async emailStatementPdf() {
        const state = ReportsPage._ensureStatementState();
        if (!state.customer_id) {
            toast('Select a customer first', 'error');
            return;
        }
        const recipient = $("#statement-recipient")?.value || state.recipient || "";
        if (!recipient) {
            toast('Enter a recipient email address', 'error');
            return;
        }
        state.recipient = recipient;
        try {
            await API.post(`/reports/customer-statement/${state.customer_id}/email`, {
                recipient,
                as_of_date: state.as_of_date,
            });
            toast('Statement emailed');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async renderCustomerStatementScreen() {
        const customers = await API.get("/customers?active_only=true");
        ReportsPage._statementCustomers = customers;
        const state = ReportsPage._ensureStatementState(customers);
        if (!state.customer_id && customers[0]) {
            state.customer_id = String(customers[0].id);
            state.recipient = customers[0].email || "";
        }
        const custOpts = customers.map(c => `<option value="${c.id}" ${String(c.id) === String(state.customer_id) ? 'selected' : ''}>${escapeHtml(c.name)}</option>`).join("");
        const selected = customers.find((entry) => String(entry.id) === String(state.customer_id));
        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Reports</div>
                    <h2>Customer Statement</h2>
                </div>
                <button class="btn btn-secondary" onclick="App.navigate('#/reports')">Back to Reports</button>
            </div>
            <div class="settings-section">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Customer</label>
                        <select onchange="ReportsPage.changeStatementCustomer(this.value)">
                            <option value="">Select...</option>
                            ${custOpts}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>As of Date</label>
                        <input type="date" value="${state.as_of_date}" onchange="ReportsPage.changeStatementDate(this.value)">
                    </div>
                    <div class="form-group">
                        <label>Email recipient</label>
                        <input id="statement-recipient" type="email" value="${escapeHtml(state.recipient || '')}" onchange="ReportsPage.updateStatementRecipient(this.value)" placeholder="customer@example.com">
                    </div>
                </div>
                <div class="form-actions" style="justify-content:flex-start;">
                    <button class="btn btn-primary" onclick="ReportsPage.openStatementPdf()" ${state.customer_id ? '' : 'disabled'}>View / Print PDF</button>
                    <button class="btn btn-secondary" onclick="ReportsPage.emailStatementPdf()" ${state.customer_id ? '' : 'disabled'}>Email PDF</button>
                </div>
            </div>
            <div class="settings-section">
                ${selected
                    ? `<p style="margin:0 0 8px 0; color:var(--gray-500);">Generate a statement for <strong>${escapeHtml(selected.name)}</strong> as at ${formatDate(state.as_of_date)}.</p>
                       <p style="margin:0; color:var(--text-muted); font-size:11px;">Use View / Print PDF to open the statement in the browser PDF viewer, or email the same PDF directly from this screen.</p>`
                    : '<div class="empty-state"><p>Select a customer to generate a statement PDF.</p></div>'}
            </div>`;
    },

    async sendSelectedOverdueStatements() {
        const state = ReportsPage._ensureOverdueStatementsState();
        const selectedItems = (state.items || []).filter(item => state.selected_customer_ids.includes(String(item.customer_id)));
        if (!selectedItems.length) {
            toast('Select at least one overdue customer first', 'error');
            return;
        }
        try {
            const result = await API.post('/reports/overdue-statements/send', {
                as_of_date: state.as_of_date,
                recipients: selectedItems.map(item => ({
                    customer_id: item.customer_id,
                    recipient: item.recipient,
                })),
            });
            state.last_results = result.results || [];
            toast(`Sent ${result.sent_count} overdue statements`);
            App.navigate('#/reports/overdue-statements');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async sendSelectedMonthlyStatements() {
        const state = ReportsPage._ensureMonthlyStatementsState();
        const selectedItems = (state.items || []).filter(item => state.selected_customer_ids.includes(String(item.customer_id)));
        if (!selectedItems.length) {
            toast('Select at least one monthly statement customer first', 'error');
            return;
        }
        try {
            const result = await API.post('/reports/monthly-statements/send', {
                as_of_date: state.as_of_date,
                recipients: selectedItems.map(item => ({
                    customer_id: item.customer_id,
                    recipient: item.recipient,
                })),
            });
            state.last_results = result.results || [];
            toast(`Sent ${result.sent_count} monthly statements`);
            App.navigate('#/reports/monthly-statements');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async renderOverdueStatementsScreen() {
        const state = ReportsPage._ensureOverdueStatementsState();
        const data = await API.get(`/reports/overdue-statements/candidates?as_of_date=${state.as_of_date}`);
        state.items = data.items || [];
        const selected = new Set(state.selected_customer_ids);
        const allSelected = state.items.length > 0 && state.items.every(item => selected.has(String(item.customer_id)));
        const rows = state.items.map(item => `
            <tr>
                <td><input type="checkbox" ${selected.has(String(item.customer_id)) ? 'checked' : ''} onchange="ReportsPage.toggleOverdueStatementSelection(${item.customer_id})"></td>
                <td>${escapeHtml(item.customer_name)}</td>
                <td>${escapeHtml(item.recipient)}</td>
                <td class="amount">${item.overdue_invoice_count}</td>
                <td>${formatDate(item.oldest_due_date)}</td>
                <td class="amount">${formatCurrency(item.overdue_balance)}</td>
            </tr>
        `).join("") || '<tr><td colspan="6" style="text-align:center; color:var(--gray-400);">No overdue statement candidates</td></tr>';
        const resultsHtml = (state.last_results || []).length ? `
            <div class="settings-section">
                <h3>Last batch results</h3>
                <div class="table-container"><table>
                    <thead><tr><th>Customer</th><th>Recipient</th><th>Status</th><th>Detail</th></tr></thead>
                    <tbody>
                        ${(state.last_results || []).map(row => `
                            <tr>
                                <td>${escapeHtml(row.customer_name || String(row.customer_id))}</td>
                                <td>${escapeHtml(row.recipient || '')}</td>
                                <td>${escapeHtml(row.status)}</td>
                                <td>${escapeHtml(row.detail || '')}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table></div>
            </div>` : '';
        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Reports</div>
                    <h2>Overdue Statements</h2>
                </div>
                <button class="btn btn-secondary" onclick="App.navigate('#/reports')">Back to Reports</button>
            </div>
            <div class="settings-section">
                <div class="form-grid">
                    <div class="form-group">
                        <label>As of Date</label>
                        <input type="date" value="${state.as_of_date}" onchange="ReportsPage.changeOverdueStatementsDate(this.value)">
                    </div>
                </div>
                <div class="form-actions" style="justify-content:flex-start;">
                    <button class="btn btn-secondary" onclick="ReportsPage.toggleAllOverdueStatements()">${allSelected ? 'Clear Selection' : 'Select All'}</button>
                    <button class="btn btn-primary" onclick="ReportsPage.sendSelectedOverdueStatements()" ${(state.selected_customer_ids || []).length ? '' : 'disabled'}>Send Selected Statements</button>
                </div>
            </div>
            <div class="settings-section">
                <div class="table-container"><table>
                    <thead><tr><th></th><th>Customer</th><th>Email</th><th class="amount">Invoices</th><th>Oldest Due</th><th class="amount">Overdue Balance</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table></div>
            </div>
            ${resultsHtml}`;
    },

    async renderMonthlyStatementsScreen() {
        const state = ReportsPage._ensureMonthlyStatementsState();
        const data = await API.get(`/reports/monthly-statements/candidates?as_of_date=${state.as_of_date}`);
        state.items = data.items || [];
        const selected = new Set(state.selected_customer_ids);
        const allSelected = state.items.length > 0 && state.items.every(item => selected.has(String(item.customer_id)));
        const rows = state.items.map(item => `
            <tr>
                <td><input type="checkbox" ${selected.has(String(item.customer_id)) ? 'checked' : ''} onchange="ReportsPage.toggleMonthlyStatementSelection(${item.customer_id})"></td>
                <td>${escapeHtml(item.customer_name)}</td>
                <td>${item.recipient ? escapeHtml(item.recipient) : '<span style="color:var(--gray-400);">No email</span>'}</td>
                <td class="amount">${formatCurrency(item.statement_balance || 0)}</td>
            </tr>
        `).join("") || '<tr><td colspan="4" style="text-align:center; color:var(--gray-400);">No monthly statement customers configured</td></tr>';
        const resultsHtml = (state.last_results || []).length ? `
            <div class="settings-section">
                <h3>Last batch results</h3>
                <div class="table-container"><table>
                    <thead><tr><th>Customer</th><th>Recipient</th><th>Status</th><th>Detail</th></tr></thead>
                    <tbody>
                        ${(state.last_results || []).map(row => `
                            <tr>
                                <td>${escapeHtml(row.customer_name || String(row.customer_id))}</td>
                                <td>${escapeHtml(row.recipient || '')}</td>
                                <td>${escapeHtml(row.status)}</td>
                                <td>${escapeHtml(row.detail || '')}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table></div>
            </div>` : '';
        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Reports</div>
                    <h2>Monthly Statements</h2>
                </div>
                <button class="btn btn-secondary" onclick="App.navigate('#/reports')">Back to Reports</button>
            </div>
            <div class="settings-section">
                <div class="form-grid">
                    <div class="form-group">
                        <label>As of Date</label>
                        <input type="date" value="${state.as_of_date}" onchange="ReportsPage.changeMonthlyStatementsDate(this.value)">
                    </div>
                </div>
                <div class="form-actions" style="justify-content:flex-start;">
                    <button class="btn btn-secondary" onclick="ReportsPage.toggleAllMonthlyStatements()">${allSelected ? 'Clear Selection' : 'Select All'}</button>
                    <button class="btn btn-primary" onclick="ReportsPage.sendSelectedMonthlyStatements()" ${(state.selected_customer_ids || []).length ? '' : 'disabled'}>Send Selected Statements</button>
                </div>
            </div>
            <div class="settings-section">
                <div class="table-container"><table>
                    <thead><tr><th></th><th>Customer</th><th>Email</th><th class="amount">Statement Balance</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table></div>
            </div>
            ${resultsHtml}`;
    },

    async arAging() {
        return ReportsPage.openReport("ar-aging");
    },

    renderArAgingContent(data) {
        let rows = data.items.map(i =>
            `<tr>
                <td>${escapeHtml(i.customer_name)}</td>
                <td class="amount">${formatCurrency(i.current)}</td>
                <td class="amount">${formatCurrency(i.over_30)}</td>
                <td class="amount">${formatCurrency(i.over_60)}</td>
                <td class="amount">${formatCurrency(i.over_90)}</td>
                <td class="amount" style="font-weight:600;">${formatCurrency(i.total)}</td>
            </tr>`
        ).join("");
        const t = data.totals;
        rows += `<tr style="font-weight:700; background:var(--gray-50);">
            <td>TOTAL</td>
            <td class="amount">${formatCurrency(t.current)}</td>
            <td class="amount">${formatCurrency(t.over_30)}</td>
            <td class="amount">${formatCurrency(t.over_60)}</td>
            <td class="amount">${formatCurrency(t.over_90)}</td>
            <td class="amount">${formatCurrency(t.total)}</td>
        </tr>`;
        return `
            <p style="margin-bottom:12px; color:var(--gray-500);">As of ${formatDate(data.as_of_date)}</p>
            <div class="table-container"><table>
                <thead><tr>
                    <th>Customer</th><th class="amount">Current</th><th class="amount">1-30</th>
                    <th class="amount">31-60</th><th class="amount">61-90+</th><th class="amount">Total</th>
                </tr></thead>
                <tbody>${rows || '<tr><td colspan="6" style="text-align:center; color:var(--gray-400);">No outstanding receivables</td></tr>'}</tbody>
            </table></div>`;
    },

    renderArAgingScreen() {
        return ReportsPage.renderReportScreen("ar-aging");
    },

    async apAging() {
        return ReportsPage.openReport("ap-aging");
    },

    renderApAgingContent(data) {
        let rows = data.items.map(i =>
            `<tr>
                <td>${escapeHtml(i.vendor_name)}</td>
                <td class="amount">${formatCurrency(i.current)}</td>
                <td class="amount">${formatCurrency(i.over_30)}</td>
                <td class="amount">${formatCurrency(i.over_60)}</td>
                <td class="amount">${formatCurrency(i.over_90)}</td>
                <td class="amount" style="font-weight:600;">${formatCurrency(i.total)}</td>
            </tr>`
        ).join("");
        const t = data.totals;
        rows += `<tr style="font-weight:700; background:var(--gray-50);">
            <td>TOTAL</td>
            <td class="amount">${formatCurrency(t.current)}</td>
            <td class="amount">${formatCurrency(t.over_30)}</td>
            <td class="amount">${formatCurrency(t.over_60)}</td>
            <td class="amount">${formatCurrency(t.over_90)}</td>
            <td class="amount">${formatCurrency(t.total)}</td>
        </tr>`;
        return `
            <p style="margin-bottom:12px; color:var(--gray-500);">As of ${formatDate(data.as_of_date)}</p>
            <div class="table-container"><table>
                <thead><tr>
                    <th>Vendor</th><th class="amount">Current</th><th class="amount">1-30</th>
                    <th class="amount">31-60</th><th class="amount">61-90+</th><th class="amount">Total</th>
                </tr></thead>
                <tbody>${rows || '<tr><td colspan="6" style="text-align:center; color:var(--gray-400);">No outstanding payables</td></tr>'}</tbody>
            </table></div>`;
    },

    renderApAgingScreen() {
        return ReportsPage.renderReportScreen("ap-aging");
    },
};
