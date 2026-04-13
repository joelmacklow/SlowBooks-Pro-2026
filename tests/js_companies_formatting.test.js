const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const utilsCode = fs.readFileSync('app/static/js/utils.js', 'utf8');
const companiesCode = fs.readFileSync('app/static/js/companies.js', 'utf8');

const context = {
    API: {
        get: async path => {
            assert.strictEqual(path, '/companies');
            return [
                {
                    name: 'Auckland Books',
                    database_name: 'auckland_books',
                    description: '',
                    last_accessed: '2026-04-13',
                },
                {
                    name: 'Never Opened',
                    database_name: 'never_opened',
                    description: '',
                    last_accessed: null,
                },
            ];
        },
    },
    App: {
        settings: { locale: 'en-NZ', currency: 'NZD' },
    },
    Date,
    Intl,
    Number,
    document: {
        querySelector: () => null,
        querySelectorAll: () => [],
        createElement: () => ({ className: '', textContent: '', remove() {} }),
    },
    escapeHtml: value => String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;'),
    localStorage: { setItem() {} },
    location: { reload() {} },
    openModal() {},
    setTimeout,
    toast() {},
};

vm.createContext(context);
vm.runInContext(`${utilsCode}\n${companiesCode}\nthis.CompaniesPage = CompaniesPage;`, context);

(async () => {
    const html = await context.CompaniesPage.render();
    assert.ok(html.includes('Last accessed: 13 Apr 2026'));
    assert.ok(html.includes('Last accessed: Never'));
})().catch(err => {
    console.error(err);
    process.exit(1);
});
