/**
 * Tax Reports — Schedule C generation
 * Feature 19: Generate and export Schedule C from P&L data
 */
const TaxPage = {
    async render() {
        const year = new Date().getFullYear();
        return `
            <div class="page-header">
                <h2>Tax Reports — Schedule C</h2>
                <div style="font-size:10px; color:var(--text-muted);">
                    Profit or Loss from Business (Sole Proprietorship)
                </div>
            </div>
            <div class="toolbar">
                <label style="font-size:10px;font-weight:700;">From:</label>
                <input type="date" id="tax-start" value="${year}-01-01">
                <label style="font-size:10px;font-weight:700;">To:</label>
                <input type="date" id="tax-end" value="${year}-12-31">
                <button class="btn btn-primary" onclick="TaxPage.generate()">Generate</button>
                <button class="btn btn-secondary" onclick="TaxPage.exportCSV()">Export CSV</button>
            </div>
            <div style="background:#fef3c7;border:1px solid #fbbf24;padding:6px 10px;margin-bottom:12px;font-size:10px;color:#92400e;">
                <strong>Disclaimer:</strong> This report is for reference only. Please verify all figures with a qualified tax professional.
            </div>
            <div id="tax-results"></div>`;
    },

    async generate() {
        const start = $('#tax-start').value;
        const end = $('#tax-end').value;
        const data = await API.get(`/tax/schedule-c?start_date=${start}&end_date=${end}`);
        const container = $('#tax-results');

        let html = `<div class="table-container"><table>
            <thead><tr><th>Tax Line</th><th>Account</th><th class="amount">Amount</th></tr></thead><tbody>`;

        for (const line of data.lines) {
            html += `<tr style="background:var(--toolbar-bg);"><td colspan="2" style="font-weight:700;font-size:11px;">${escapeHtml(line.line)}</td><td class="amount" style="font-weight:700;">${formatCurrency(line.total)}</td></tr>`;
            for (const acct of line.accounts) {
                html += `<tr><td style="padding-left:24px;">${escapeHtml(acct.account_number || '')}</td><td>${escapeHtml(acct.account_name)}</td><td class="amount">${formatCurrency(acct.amount)}</td></tr>`;
            }
        }

        html += `</tbody></table></div>
            <div class="invoice-totals" style="margin-top:12px;">
                <div class="total-row"><span class="label">Gross Income</span><span class="value">${formatCurrency(data.gross_income)}</span></div>
                <div class="total-row"><span class="label">Total Expenses</span><span class="value">${formatCurrency(data.total_expenses)}</span></div>
                <div class="total-row grand-total"><span class="label">Net Profit (Loss)</span><span class="value">${formatCurrency(data.net_profit)}</span></div>
            </div>`;
        container.innerHTML = html;
    },

    exportCSV() {
        const start = $('#tax-start').value;
        const end = $('#tax-end').value;
        window.open(`/api/tax/schedule-c/csv?start_date=${start}&end_date=${end}`, '_blank');
    },
};
