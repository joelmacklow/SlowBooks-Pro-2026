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
            monthly_revenue: [{ month: 'Apr', amount: 100 }],
        },
    });
    const staffHtml = await staffContext.App.renderDashboard();
    assert.ok(staffHtml.includes('Active Customers'));
    assert.ok(staffHtml.includes('Financial overview hidden'));
    assert.ok(!staffHtml.includes('Total Receivables'));
    assert.ok(!staffHtml.includes('Total Payables'));
    assert.ok(!staffHtml.includes('Bank Balances'));
    assert.ok(!staffHtml.includes('Recent Invoices'));
    assert.ok(!staffHtml.includes('Recent Payments'));
    assert.ok(!staffHtml.includes('Monthly Revenue'));
    assert.deepStrictEqual(staffContext.__apiCalls, ['/dashboard']);

    const ownerContext = makeContext({
        permissions: ['dashboard.financials.view'],
        dashboardData: {
            customer_count: 8,
            financial_overview_available: true,
            total_receivables: 1200,
            overdue_count: 2,
            total_payables: 800,
            recent_invoices: [{ invoice_number: 'INV-1', date: '2026-04-20', status: 'sent', total: 1200 }],
            recent_payments: [{ date: '2026-04-20', method: 'Bank Transfer', amount: 400 }],
            bank_balances: [{ id: 1, name: 'Main Bank', balance: 5000 }],
        },
        chartsData: {
            aging_current: 100,
            aging_30: 50,
            aging_60: 0,
            aging_90: 0,
            monthly_revenue: [{ month: 'Apr', amount: 1000 }],
        },
    });
    const ownerHtml = await ownerContext.App.renderDashboard();
    assert.ok(ownerHtml.includes('Total Receivables'));
    assert.ok(ownerHtml.includes('Total Payables'));
    assert.ok(ownerHtml.includes('Bank Balances'));
    assert.ok(ownerHtml.includes('Recent Invoices'));
    assert.ok(ownerHtml.includes('Recent Payments'));
    assert.ok(ownerHtml.includes('Monthly Revenue'));
    assert.deepStrictEqual(ownerContext.__apiCalls, ['/dashboard', '/dashboard/charts']);
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
