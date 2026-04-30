const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/reports.js', 'utf8')}
this.ReportsPage = ReportsPage;`;
const downloads = [];

class FakeDate extends Date {
    constructor(...args) {
        if (args.length === 0) {
            super('2026-04-30T12:00:00Z');
            return;
        }
        super(...args);
    }

    static now() {
        return new Date('2026-04-30T12:00:00Z').valueOf();
    }
}

const context = {
    console,
    Date: FakeDate,
    Math,
    Promise,
    setTimeout,
    URLSearchParams,
    API: {
        download: async (path, filename) => {
            downloads.push({ path, filename });
        },
    },
    escapeHtml: (value) => String(value ?? ''),
    formatCurrency: (value) => `$${Number(value).toFixed(2)}`,
    formatDate: (value) => value,
    todayISO: () => '2026-04-30',
    App: { navigate: () => {} },
    openModal() {},
    $() { return null; },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const landing = await context.ReportsPage.render();
    assert.ok(landing.includes('Financial Statements Pack'));
    assert.ok(landing.includes('ReportsPage.financialStatementsPack()'));

    await context.ReportsPage.financialStatementsPack();
    assert.deepStrictEqual(downloads, [
        {
            path: '/reports/financial-statements-pack?start_date=2026-01-01&end_date=2026-04-30',
            filename: 'FinancialStatementsPack_2026-01-01_2026-04-30.zip',
        },
    ]);
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
