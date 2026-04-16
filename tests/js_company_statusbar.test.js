const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = fs.readFileSync('app/static/js/app.js', 'utf8');
const statusCompany = { textContent: 'Company: bookkeeper.sbk' };
const store = { slowbooks_company: 'never_opened' };

const context = {
    API: { get: async () => ({}) },
    $: selector => (
        selector === '#status-company' ? statusCompany :
        selector === '#topbar-clock' || selector === '#status-date' ? { textContent: '' } :
        null
    ),
    $$: () => [],
    console,
    document: {
        documentElement: { getAttribute: () => 'light', setAttribute() {} },
        addEventListener() {},
        querySelector: () => null,
        querySelectorAll: () => [],
        createElement: () => ({ click() {}, remove() {}, style: {} }),
    },
    escapeHtml: value => String(value || ''),
    location: { hash: '#/' },
    localStorage: {
        getItem(key) { return store[key] || null; },
        setItem(key, value) { store[key] = value; },
        removeItem(key) { delete store[key]; },
    },
    setInterval: () => 1,
    setTimeout,
    window: { addEventListener() {} },
    closeModal() {},
    openModal() {},
    toast() {},
    Date,
    Intl,
    Number,
};

vm.createContext(context);
vm.runInContext(`${code}\nthis.App = App;`, context);

(() => {
    context.App.settings = { company_name: 'My Company' };
    context.App.loadCompanyName();
    assert.strictEqual(statusCompany.textContent, 'Company: never_opened');

    context.App.settings = { company_name: 'Auckland Books' };
    context.App.loadCompanyName();
    assert.strictEqual(statusCompany.textContent, 'Company: Auckland Books (never_opened)');
})();
