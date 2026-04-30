const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/reports.js', 'utf8')}\nthis.ReportsPage = ReportsPage;`;
const calls = [];
const posts = [];
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
            if (path === '/reports/monthly-statements/candidates?as_of_date=2026-04-30') {
                return {
                    as_of_date: '2026-04-30',
                    items: [
                        {
                            customer_id: 5,
                            customer_name: 'Aroha Ltd',
                            recipient: 'aroha@example.com',
                            statement_balance: 0,
                        },
                    ],
                };
            }
            throw new Error(`unexpected get ${path}`);
        },
        post: async (path, body) => {
            posts.push({ path, body });
            return { sent_count: 1, failed_count: 0, skipped_count: 0, results: [{ customer_id: 5, customer_name: 'Aroha Ltd', recipient: 'aroha@example.com', status: 'sent', detail: null }] };
        },
    },
    toast() {},
    escapeHtml: (value) => String(value ?? ''),
    formatCurrency: (value) => `$${Number(value).toFixed(2)}`,
    formatDate: (value) => value,
    todayISO: () => '2026-04-30',
    App: { navigate: (hash) => navigations.push(hash) },
    $() { return null; },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const landing = await context.ReportsPage.render();
    assert.ok(landing.includes('Monthly Statements'));

    await context.ReportsPage.monthlyStatements();
    assert.deepStrictEqual(navigations, ['#/reports/monthly-statements']);

    const state = context.ReportsPage._ensureMonthlyStatementsState();
    state.as_of_date = '2026-04-30';
    let html = await context.ReportsPage.renderMonthlyStatementsScreen();
    assert.ok(html.includes('Aroha Ltd'));
    assert.ok(html.includes('$0.00'));
    assert.ok(calls.includes('/reports/monthly-statements/candidates?as_of_date=2026-04-30'));

    context.ReportsPage.toggleMonthlyStatementSelection(5);
    assert.ok(context.ReportsPage._ensureMonthlyStatementsState().selected_customer_ids.includes('5'));

    await context.ReportsPage.sendSelectedMonthlyStatements();
    assert.strictEqual(posts.length, 1);
    assert.strictEqual(posts[0].path, '/reports/monthly-statements/send');
    assert.strictEqual(posts[0].body.recipients[0].customer_id, 5);

    html = await context.ReportsPage.renderMonthlyStatementsScreen();
    assert.ok(html.includes('Last batch results'));
    assert.ok(html.includes('sent'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
