const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const reportsCode = fs.readFileSync('app/static/js/reports.js', 'utf8');

const context = {
    console,
    App: { settings: {} },
    todayISO: () => '2026-04-23',
    openModal() {},
    closeModal() {},
    API: {},
    $: () => null,
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
};

vm.createContext(context);
vm.runInContext(`${reportsCode}\nthis.ReportsPage = ReportsPage;`, context);

const html = context.ReportsPage.renderBalanceSheetContent({
    as_of_date: '2026-04-30',
    assets: [{ account_name: 'Business Bank', amount: 115 }],
    liabilities: [{ account_name: 'GST', amount: 15 }],
    equity: [],
    current_earnings: 100,
    total_assets: 115,
    total_liabilities: 15,
    total_equity: 100,
    total_liabilities_and_equity: 115,
    balance_difference: 0,
    is_balanced: true,
});

assert.ok(html.includes('Current Earnings'));
assert.ok(html.includes('Total Liabilities + Equity'));
assert.ok(html.includes('Difference'));
assert.ok(html.includes('$0.00'));
