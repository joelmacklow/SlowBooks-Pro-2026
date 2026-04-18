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
