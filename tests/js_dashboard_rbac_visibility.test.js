const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const appCode = fs.readFileSync('app/static/js/app.js', 'utf8');

const makeContext = ({ permissions, dashboardData, chartsData }) => {
    const apiCalls = [];
    const context = {
        API: {
            get: async (path) => {
                apiCalls.push(path);
                if (path === '/dashboard') return dashboardData;
                if (path === '/dashboard/charts') return chartsData;
                throw new Error(`unexpected path ${path}`);
            },
        },
        document: {
            documentElement: { getAttribute: () => 'light', setAttribute() {} },
            querySelector() { return null; },
            querySelectorAll() { return []; },
            addEventListener() {},
            createElement: () => ({ click() {}, remove() {}, style: {} }),
        },
        window: { addEventListener() {} },
        localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
        location: { hash: '#/', reload() {} },
        escapeHtml: (value) => String(value || ''),
        formatCurrency: (value) => `$${value}`,
        formatDate: (value) => value || '',
        statusBadge: (value) => value || '',
        openModal() {},
        closeModal() {},
        toast() {},
        setInterval: () => 1,
        setTimeout,
        clearTimeout,
        console,
        fetch: async () => ({ ok: true, headers: { get: () => null }, blob: async () => ({}) }),
        URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
        $: () => null,
        $$: () => [],
        Date,
        Intl,
        Number,
    };
    vm.createContext(context);
    vm.runInContext(`${appCode}\nthis.App = App;`, context);
    context.App.authState = {
        authenticated: true,
        bootstrap_required: false,
        user: { full_name: 'Viewer', membership: { role_key: 'staff', effective_permissions: permissions } },
    };
    context.__apiCalls = apiCalls;
    return context;
};

(async () => {
    const staffContext = makeContext({
        permissions: ['contacts.view'],
        dashboardData: {
            customer_count: 5,
            financial_overview_available: false,
        },
        chartsData: {
            profit_summary: { net_profit: 100 },
        },
    });
    const staffHtml = await staffContext.App.renderDashboard();
    assert.ok(staffHtml.includes('Active Customers'));
    assert.ok(staffHtml.includes('Financial overview hidden'));
    assert.ok(!staffHtml.includes('Invoices owed to you'));
    assert.ok(!staffHtml.includes('Net profit or loss'));
    assert.ok(!staffHtml.includes('Cash in and out'));
    assert.ok(!staffHtml.includes('Chart of accounts watchlist'));
    assert.deepStrictEqual(staffContext.__apiCalls, ['/dashboard']);

    const ownerContext = makeContext({
        permissions: ['dashboard.financials.view'],
        dashboardData: {
            customer_count: 8,
            financial_overview_available: true,
            total_receivables: 1200,
            overdue_count: 2,
            total_payables: 800,
            invoice_summary: {
                total_receivables: 1200,
                awaiting_payment_count: 4,
                overdue_count: 2,
                overdue_value: 325,
            },
            bank_accounts: [{ id: 1, name: 'Main Bank', bank_name: 'ANZ', last_four: '1208', balance: 5000, unreconciled_count: 3, status_label: '3 items to reconcile' }],
            watchlist: [
                { account_id: 10, account_number: '200', account_name: 'Sales', this_month: 540.98, ytd: 5440.98 },
                { account_id: 11, account_number: '610', account_name: 'Office Expenses', this_month: 92.64, ytd: 190.64 },
            ],
        },
        chartsData: {
            profit_summary: {
                income: 22122,
                expenses: 4129,
                net_profit: 17993,
                period_label: '1 Apr - 21 Apr 2026',
            },
            cash_flow: {
                months: [{ month: 'Apr', cash_in: 1000, cash_out: 600 }],
                cash_in_total: 1000,
                cash_out_total: 600,
                net_total: 400,
            },
        },
    });
    const ownerHtml = await ownerContext.App.renderDashboard();
    assert.ok(ownerHtml.includes('Invoices owed to you'));
    assert.ok(ownerHtml.includes('Net profit or loss'));
    assert.ok(ownerHtml.includes('Cash in and out'));
    assert.ok(ownerHtml.includes('Chart of accounts watchlist'));
    assert.ok(ownerHtml.includes('Main Bank'));
    assert.ok(ownerHtml.includes('Sales'));
    assert.deepStrictEqual(ownerContext.__apiCalls, ['/dashboard', '/dashboard/charts']);

    const emptyOwnerContext = makeContext({
        permissions: ['dashboard.financials.view'],
        dashboardData: {
            customer_count: 0,
            financial_overview_available: true,
            total_receivables: 0,
            overdue_count: 0,
            total_payables: 0,
            invoice_summary: {
                total_receivables: 0,
                awaiting_payment_count: 0,
                overdue_count: 0,
                overdue_value: 0,
            },
            bank_accounts: [],
            watchlist: [],
        },
        chartsData: {
            profit_summary: {
                income: 0,
                expenses: 0,
                net_profit: 0,
                period_label: '1 Apr - 21 Apr 2026',
            },
            cash_flow: {
                months: [],
                cash_in_total: 0,
                cash_out_total: 0,
                net_total: 0,
            },
        },
    });
    const emptyOwnerHtml = await emptyOwnerContext.App.renderDashboard();
    assert.ok(emptyOwnerHtml.includes('No bank accounts connected yet'));
    assert.ok(emptyOwnerHtml.includes('No watchlist accounts yet'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
