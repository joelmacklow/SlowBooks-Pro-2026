const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const utilsCode = fs.readFileSync('app/static/js/utils.js', 'utf8');
const companiesCode = fs.readFileSync('app/static/js/companies.js', 'utf8');
let modalHtml = '';
const modalTitle = { textContent: '' };
const modalBody = { innerHTML: '' };
const modalOverlay = { classList: { remove() {}, add() {} } };

const context = {
    API: {
        get: async path => {
            assert.strictEqual(path, '/companies');
            return [
                {
                    name: 'SlowBooks NZ',
                    database_name: 'bookkeeper',
                    description: 'Default company',
                    last_accessed: null,
                    is_default: true,
                },
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
        querySelector: selector => {
            if (selector === '#modal-title') return modalTitle;
            if (selector === '#modal-body') return modalBody;
            if (selector === '#modal-overlay') return modalOverlay;
            return null;
        },
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
    setTimeout,
    toast() {},
};

vm.createContext(context);
vm.runInContext(`${utilsCode}\n${companiesCode}\nthis.CompaniesPage = CompaniesPage;`, context);

(async () => {
    const html = await context.CompaniesPage.render();
    assert.ok(html.includes('SlowBooks NZ'));
    assert.ok(html.includes('Default'));
    assert.ok(html.includes('Last accessed: 13 Apr 2026'));
    assert.ok(html.includes('Last accessed: Never'));

    context.CompaniesPage.showCreate();
    modalHtml = modalBody.innerHTML;
    assert.ok(modalHtml.includes('CompaniesPage.handleCompanyNameInput(this)'));
    assert.ok(modalHtml.includes('CompaniesPage.handleDatabaseNameInput(this)'));

    const databaseInput = { value: '' };
    const nameInput = { value: 'Acme Books Ltd', form: { database_name: databaseInput } };
    context.CompaniesPage.handleCompanyNameInput(nameInput);
    assert.strictEqual(databaseInput.value, 'acme_books_ltd');

    databaseInput.value = 'custom_db';
    context.CompaniesPage.handleDatabaseNameInput(databaseInput);
    nameInput.value = 'Acme Books Limited';
    context.CompaniesPage.handleCompanyNameInput(nameInput);
    assert.strictEqual(databaseInput.value, 'custom_db');
})().catch(err => {
    console.error(err);
    process.exit(1);
});
