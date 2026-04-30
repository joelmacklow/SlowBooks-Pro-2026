const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const reportsCode = fs.readFileSync('app/static/js/reports.js', 'utf8');

class MockDate extends Date {
    constructor(...args) {
        if (args.length === 0) {
            super('2026-04-23T12:00:00Z');
            return;
        }
        super(...args);
    }

    static now() {
        return new Date('2026-04-23T12:00:00Z').valueOf();
    }
}

const context = {
    console,
    Date: MockDate,
    App: { settings: { financial_year_start: '04-01' } },
    todayISO: () => '2026-04-23',
    openModal() {},
    closeModal() {},
    API: {},
    $: () => null,
    escapeHtml: value => String(value || ''),
};

vm.createContext(context);
vm.runInContext(`${reportsCode}\nthis.ReportsPage = ReportsPage;`, context);

const optionHtml = context.ReportsPage.periodOptions('this_fy');
assert.ok(optionHtml.includes('value="this_fy" selected'));
assert.ok(optionHtml.includes('value="last_fy"'));

let range = context.ReportsPage.getDateRange('this_fy');
assert.strictEqual(range.start, '2026-04-01');
assert.strictEqual(range.end, '2027-03-31');

range = context.ReportsPage.getDateRange('last_fy');
assert.strictEqual(range.start, '2025-04-01');
assert.strictEqual(range.end, '2026-03-31');

context.App.settings = {};
range = context.ReportsPage.getDateRange('this_fy');
assert.strictEqual(range.start, '2026-01-01');
assert.strictEqual(range.end, '2026-12-31');
