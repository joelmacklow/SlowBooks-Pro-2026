const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/app.js', 'utf8')}\nthis.App = App;`;

const searchResultsEl = {
    innerHTML: '',
    classList: {
        add() {},
        remove() {},
    },
};
const globalSearchInput = { value: 'Aroha' };

const context = {
    console,
    escapeHtml: value => String(value || ''),
    document: {
        documentElement: { getAttribute: () => 'light', setAttribute() {} },
        addEventListener() {},
        querySelector: (selector) => (selector === '#search-results' ? searchResultsEl : null),
        querySelectorAll: () => [],
        createElement: () => ({ click() {} }),
    },
    window: { addEventListener() {} },
    location: { hash: '#/' },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    setInterval: () => 1,
    setTimeout: (fn) => { fn(); return 1; },
    clearTimeout() {},
    closeSearchDropdown() {},
    CustomersPage: { view() {} },
    EstimatesPage: { view() {} },
    CreditMemosPage: { open() {} },
    InvoicesPage: { view() {} },
    App: null,
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
            return {
                customers: [{ id: 7, name: 'Aroha Ltd', display: 'Aroha Ltd · Aroha Holdings' }],
                estimates: [{ id: 2, estimate_number: 'E-101', display: 'E-101 · Aroha Ltd' }],
                credit_memos: [{ id: 3, memo_number: 'CM-0001', display: 'CM-0001 · Aroha Ltd' }],
            };
        },
    },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.App.globalSearch('Aroha');
    const searchHtml = searchResultsEl.innerHTML;
    assert.ok(searchHtml.includes('Aroha Ltd · Aroha Holdings'));
    assert.ok(searchHtml.includes('E-101 · Aroha Ltd'));
    assert.ok(searchHtml.includes('CM-0001 · Aroha Ltd'));
    assert.ok(searchHtml.includes('CustomersPage.view(7)'));
    assert.ok(searchHtml.includes('EstimatesPage.view(2)'));
    assert.ok(searchHtml.includes('CreditMemosPage.open(3)'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
