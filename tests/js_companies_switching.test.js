const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const apiCode = fs.readFileSync('app/static/js/api.js', 'utf8');
const companiesCode = fs.readFileSync('app/static/js/companies.js', 'utf8');

const store = {};
const navigations = [];
const loaded = [];
const companyNames = [];

const context = {
    localStorage: {
        getItem(key) { return store[key] || null; },
        setItem(key, value) { store[key] = value; },
        removeItem(key) { delete store[key]; },
    },
    App: {
        async loadSettings() { loaded.push('settings'); },
        loadCompanyName() { companyNames.push('loaded'); },
        navigate(hash) { navigations.push(hash); },
    },
    toast() {},
    console,
    setTimeout,
};

vm.createContext(context);
vm.runInContext(`${apiCode}\n${companiesCode}\nthis.API = API; this.CompaniesPage = CompaniesPage;`, context);

(async () => {
    let headers = context.API.authHeaders('/dashboard');
    assert.strictEqual(Object.keys(headers).length, 0);

    store['slowbooks_company'] = 'auckland_books';
    headers = context.API.authHeaders('/dashboard');
    assert.strictEqual(headers['X-Company-Database'], 'auckland_books');
    assert.strictEqual(context.API.authHeaders('/auth/me')['X-Company-Database'], undefined);
    assert.strictEqual(context.API.authHeaders('/companies')['X-Company-Database'], undefined);

    await context.CompaniesPage.switchTo('never_opened');
    assert.strictEqual(store['slowbooks_company'], 'never_opened');
    assert.deepStrictEqual(loaded, ['settings']);
    assert.deepStrictEqual(companyNames, ['loaded']);
    assert.deepStrictEqual(navigations, ['#/']);
})().catch(err => {
    console.error(err);
    process.exit(1);
});
