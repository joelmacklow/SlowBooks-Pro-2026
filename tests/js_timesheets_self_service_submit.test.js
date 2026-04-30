const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/timesheets_self_service.js', 'utf8')}\nthis.TimesheetSelfServicePage = TimesheetSelfServicePage;`;

function buildContext(confirmResult) {
    const posts = [];
    const toasts = [];
    const navigations = [];
    const confirmCalls = [];
    const context = {
        console,
        Promise,
        location: { hash: '#/my-timesheets?id=55' },
        URLSearchParams,
        API: {
            post: async (path, payload) => {
                posts.push([path, payload]);
                return { ok: true };
            },
            download: async () => { throw new Error('unexpected download'); },
            get: async () => { throw new Error('unexpected get'); },
            put: async () => { throw new Error('unexpected put'); },
        },
        App: {
            confirmAction: async (payload) => {
                confirmCalls.push(payload);
                return confirmResult;
            },
            navigate: (hash) => navigations.push(hash),
        },
        toast: (message, tone = 'ok') => toasts.push([message, tone]),
        escapeHtml: value => String(value || ''),
        formatDate: value => String(value || ''),
        formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
        document: { getElementById: () => null },
    };
    vm.createContext(context);
    vm.runInContext(code, context);
    return { context, posts, toasts, navigations, confirmCalls };
}

(async () => {
    {
        const { context, posts, toasts, navigations, confirmCalls } = buildContext(true);
        await context.TimesheetSelfServicePage.submitTimesheet(55);

        assert.strictEqual(confirmCalls.length, 1);
        assert.strictEqual(confirmCalls[0].title, 'Submit Timesheet');
        assert.ok(String(confirmCalls[0].message || '').includes('payroll review'));
        assert.strictEqual(posts.length, 1);
        assert.strictEqual(posts[0][0], '/timesheets/self/55/submit');
        assert.strictEqual(Object.keys(posts[0][1] || {}).length, 0);
        assert.deepStrictEqual(navigations, ['#/my-timesheets?id=55']);
        assert.ok(toasts.some(([msg]) => msg === 'Timesheet submitted'));
    }

    {
        const { context, posts, toasts, navigations } = buildContext(false);
        await context.TimesheetSelfServicePage.submitTimesheet(77);

        assert.deepStrictEqual(posts, []);
        assert.deepStrictEqual(navigations, []);
        assert.ok(!toasts.some(([msg]) => msg === 'Timesheet submitted'));
    }
})().catch(err => {
    console.error(err);
    process.exit(1);
});
