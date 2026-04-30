const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/app.js', 'utf8')}\nthis.App = App;`;
const context = {
    API: { get: async () => ({}) },
    $: () => ({ innerHTML: '', textContent: '', classList: { add() {}, remove() {}, toggle() {} } }),
    $$: () => [],
    console,
    document: {
        documentElement: { getAttribute: () => 'light', setAttribute() {} },
        addEventListener() {},
        querySelector: () => null,
        querySelectorAll: () => [],
    },
    escapeHtml: value => String(value || ''),
    location: { hash: '#/login?bootstrap_token=setup-url-token' },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    setInterval: () => 1,
    window: { addEventListener() {} },
};

vm.createContext(context);
vm.runInContext(code, context);

assert.strictEqual(context.App.routePathFromHash('#/login?bootstrap_token=setup-url-token'), '/login');
assert.strictEqual(context.App.routePathFromHash('#/reports/gst-return/detail?period=2026-04'), '/reports/gst-return/detail');
assert.strictEqual(context.App.routePathFromHash('#/reports/trial-balance?period=this_year_to_date'), '/reports/trial-balance');
assert.strictEqual(context.App.routePathFromHash('#/'), '/');
assert.strictEqual(context.App.routes['/reports/statement-of-changes-in-equity'].label, 'Statement of Changes in Equity');
assert.strictEqual(typeof context.App.routes['/reports/statement-of-changes-in-equity'].render, 'function');
assert.ok(context.App.routes['/payroll/detail']);
assert.strictEqual(typeof context.App.openDetail, 'function');

context.App.setDetailOrigin('#/invoices/detail', '#/customers/detail');
assert.strictEqual(context.App.detailBackLabel('#/invoices/detail', '#/invoices'), 'Back to Customer');

context.App.routes = {
    '/fixed-assets/detail': { page: 'fixed-assets', label: 'Fixed Asset', render: async () => '<div>detail</div>' },
};
context.App.authState = { authenticated: true, bootstrap_required: false, user: { membership: { effective_permissions: [] } } };
context.App.hasPermission = () => true;
context.App.syncNavAccordion = () => {};
context.App.setStatus = () => {};
context.App.syncAuthUI = () => {};
context.App.syncNavVisibility = () => {};

(async () => {
    context.App._detailOrigins = {};
    context.App.openDetail('#/fixed-assets/detail?id=7', '#/fixed-assets');
    assert.strictEqual(context.location.hash, '#/fixed-assets/detail?id=7');
    await context.App.navigate('#/fixed-assets/detail?id=7');
    assert.strictEqual(context.location.hash, '#/fixed-assets/detail?id=7');
})();
