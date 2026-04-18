const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/reports.js', 'utf8')}\nthis.ReportsPage = ReportsPage;`;
const calls = [];
const modalCalls = [];

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
            if (path === '/reports/trial-balance?as_of_date=2026-04-30') {
                return {
                    as_of_date: '2026-04-30',
                    accounts: [
                        {
                            account_number: '090',
                            account_name: 'Business Bank',
                            account_type: 'asset',
                            debit_balance: 92,
                            credit_balance: 0,
                        },
                        {
                            account_number: '200',
                            account_name: 'Sales',
                            account_type: 'income',
                            debit_balance: 0,
                            credit_balance: 77,
                        },
                        {
                            account_number: '2200',
                            account_name: 'GST',
                            account_type: 'liability',
                            debit_balance: 0,
                            credit_balance: 15,
                        },
                    ],
                    total_debit: 92,
                    total_credit: 92,
                };
            }
            throw new Error(`unexpected get ${path}`);
        },
    },
    escapeHtml: (value) => String(value ?? ''),
    formatCurrency: (value) => `$${Number(value).toFixed(2)}`,
    formatDate: (value) => value,
    todayISO: () => '2026-04-30',
    App: { navigate() {} },
    openModal() {},
    $() { return null; },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const landing = await context.ReportsPage.render();
    assert.ok(landing.includes('Trial Balance'));
    assert.ok(landing.includes('ReportsPage.trialBalance()'));

    context.ReportsPage.openPeriodModal = async (title, initialPeriod, loadContent, label, useAsOfOnly) => {
        modalCalls.push({ title, initialPeriod, label, useAsOfOnly });
        return loadContent(initialPeriod, { as_of_date: '2026-04-30' });
    };

    const html = await context.ReportsPage.trialBalance();
    assert.deepStrictEqual(modalCalls, [
        {
            title: 'Trial Balance',
            initialPeriod: 'this_year_to_date',
            label: 'As Of',
            useAsOfOnly: true,
        },
    ]);
    assert.deepStrictEqual(calls, ['/reports/trial-balance?as_of_date=2026-04-30']);
    assert.ok(html.includes('Business Bank'));
    assert.ok(html.includes('Sales'));
    assert.ok(html.includes('GST'));
    assert.ok(html.includes('Totals'));
    assert.ok(html.includes('$92.00'));
    assert.ok(html.includes('$77.00'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
