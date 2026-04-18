const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/reports.js', 'utf8')}\nthis.ReportsPage = ReportsPage;`;
const calls = [];
const opens = [];
const posts = [];
const navigations = [];
const elements = {
    '#statement-recipient': { value: 'customer@example.com' },
};

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
            if (path === '/customers?active_only=true') {
                return [{ id: 5, name: 'Aroha Ltd', email: 'customer@example.com' }];
            }
            throw new Error(`unexpected get ${path}`);
        },
        open: async (path, filename) => {
            opens.push({ path, filename });
        },
        post: async (path, body) => {
            posts.push({ path, body });
            return { status: 'sent' };
        },
    },
    App: {
        navigate: (hash) => navigations.push(hash),
    },
    toast() {},
    $: (selector) => elements[selector],
    escapeHtml: (value) => String(value ?? ''),
    formatCurrency: (value) => `$${Number(value).toFixed(2)}`,
    formatDate: (value) => value,
    todayISO: () => '2026-04-30',
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.ReportsPage.customerStatement();
    assert.deepStrictEqual(navigations, ['#/reports/customer-statement']);

    const html = await context.ReportsPage.renderCustomerStatementScreen();
    assert.deepStrictEqual(calls, ['/customers?active_only=true']);
    assert.ok(html.includes('View / Print PDF'));
    assert.ok(html.includes('Email PDF'));
    assert.ok(html.includes('Aroha Ltd'));

    context.ReportsPage.openStatementPdf();
    await context.ReportsPage.emailStatementPdf();

    assert.deepStrictEqual(opens, [
        {
            path: '/reports/customer-statement/5/pdf?as_of_date=2026-04-30',
            filename: 'Statement_5_2026-04-30.pdf',
        },
    ]);
    assert.strictEqual(JSON.stringify(posts), JSON.stringify([
        {
            path: '/reports/customer-statement/5/email',
            body: {
                recipient: 'customer@example.com',
                as_of_date: '2026-04-30',
            },
        },
    ]));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
