const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/app.js', 'utf8')}\nthis.App = App;`;

const searchResultsEl = {
    innerHTML: '',
    hidden: true,
    classList: {
        add(cls) { if (cls === 'hidden') searchResultsEl.hidden = true; },
        remove(cls) { if (cls === 'hidden') searchResultsEl.hidden = false; },
        toggle() {},
    },
};
const globalSearchInput = { value: '' };
let pendingResolve = null;

const context = {
    console,
    document: {
        documentElement: { getAttribute: () => 'light', setAttribute() {} },
        addEventListener() {},
        querySelector: (selector) => {
            if (selector === '#search-results') return searchResultsEl;
            if (selector === '#global-search') return globalSearchInput;
            return { innerHTML: '', textContent: '', classList: { add() {}, remove() {}, toggle() {} } };
        },
        querySelectorAll: () => [],
        createElement: () => ({ click() {} }),
    },
    window: { addEventListener() {} },
    location: { hash: '#/' },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    setInterval: () => 1,
    setTimeout: (fn) => { fn(); return 1; },
    clearTimeout() {},
    escapeHtml: value => String(value || ''),
    $: (selector) => {
        if (selector === '#search-results') return searchResultsEl;
        if (selector === '#global-search') return globalSearchInput;
        if (selector === '#status-text') return { textContent: '' };
        return { innerHTML: '', textContent: '', classList: { add() {}, remove() {}, toggle() {} } };
    },
    $$: () => [],
    API: {
        get: async (path) => {
            if (!path.startsWith('/search?q=')) throw new Error(`unexpected path ${path}`);
            return new Promise((resolve) => {
                pendingResolve = () => resolve({
                    invoices: [{ id: 1, invoice_number: '1001', display: '1001 · Aroha Ltd' }],
                });
            });
        },
    },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    globalSearchInput.value = '1001';
    await context.App.globalSearch('1001');
    context.App.dismissSearchResults();
    assert.strictEqual(searchResultsEl.hidden, true);
    assert.strictEqual(globalSearchInput.value, '');
    pendingResolve();
    await Promise.resolve();
    await Promise.resolve();
    assert.strictEqual(searchResultsEl.hidden, true);
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
