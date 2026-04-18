const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/reports.js', 'utf8')}\nthis.ReportsPage = ReportsPage;`;
const calls = [];
const opens = [];
const navigations = [];

const context = {
    console,
    Date,
    Math,
    Promise,
    setTimeout,
    URLSearchParams,
    API: {
        get: async (path) => {
            calls.push(path);
            if (path === '/reports/cash-flow?start_date=2026-04-01&end_date=2026-04-30') {
                return {
                    start_date: '2026-04-01',
                    end_date: '2026-04-30',
                    opening_cash: 250,
                    net_cash_change: 615,
                    closing_cash: 865,
                    operating: {
                        total: 115,
                        items: [{ date: '2026-04-01', description: 'Customer receipt', reference: 'INV-1001', amount: 115 }],
                    },
                    investing: {
                        total: -500,
                        items: [{ date: '2026-04-10', description: 'Equipment purchase', reference: 'EQ-1', amount: -500 }],
                    },
                    financing: {
                        total: 1000,
                        items: [{ date: '2026-04-20', description: 'Loan proceeds', reference: 'LOAN-1', amount: 1000 }],
                    },
                };
            }
            throw new Error(`unexpected get ${path}`);
        },
        open: async (path, filename) => {
            opens.push({ path, filename });
        },
    },
    escapeHtml: (value) => String(value ?? ''),
    formatCurrency: (value) => `$${Number(value).toFixed(2)}`,
    formatDate: (value) => value,
    todayISO: () => '2026-04-30',
    App: { navigate: (hash) => navigations.push(hash) },
    openModal() {},
    $() { return null; },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const landing = await context.ReportsPage.render();
    assert.ok(landing.includes('Cash Flow'));
    assert.ok(landing.includes('ReportsPage.cashFlow()'));

    await context.ReportsPage.cashFlow();
    assert.deepStrictEqual(navigations, ['#/reports/cash-flow']);

    context.ReportsPage._reportStates['cash-flow'].period = 'custom';
    context.ReportsPage._reportStates['cash-flow'].custom_start = '2026-04-01';
    context.ReportsPage._reportStates['cash-flow'].custom_end = '2026-04-30';
    const html = await context.ReportsPage.renderCashFlowScreen();
    assert.deepStrictEqual(calls, ['/reports/cash-flow?start_date=2026-04-01&end_date=2026-04-30']);
    assert.ok(html.includes('Operating Activities'));
    assert.ok(html.includes('Investing Activities'));
    assert.ok(html.includes('Financing Activities'));
    assert.ok(html.includes('Opening cash'));
    assert.ok(html.includes('$615.00'));

    context.ReportsPage.openReportPdf('cash-flow');
    assert.deepStrictEqual(opens, [
        {
            path: '/reports/cash-flow/pdf?start_date=2026-04-01&end_date=2026-04-30',
            filename: 'CashFlow_2026-04-01_2026-04-30.pdf',
        },
    ]);
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
