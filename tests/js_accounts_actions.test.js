const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/app.js', 'utf8')}
this.App = App;`;

const context = {
    console,
    setTimeout,
    clearTimeout,
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    document: {
        documentElement: { getAttribute() { return 'light'; }, setAttribute() {} },
        querySelector: () => null,
        querySelectorAll: () => [],
        addEventListener() {},
        createElement: () => ({ click() {} }),
    },
    window: { open() { return true; } },
    fetch: async () => ({ ok: true, json: async () => ({}) }),
    API: { get: async () => ({}), put: async () => ({}) },
    URL: { createObjectURL() { return 'blob:url'; }, revokeObjectURL() {} },
    openModal(title, html) { context.__lastModal = { title, html }; },
    closeModal() {},
    toast() {},
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    formatDate: value => String(value || ''),
    statusBadge: value => String(value || ''),
    AuthPage: { logout() {} },
    FormData: class {
        constructor(target) {
            this._entries = target.__formDataEntries || [];
        }
        entries() {
            return this._entries[Symbol.iterator]();
        }
    },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    context.App.hasPermission = (key) => key === 'accounts.manage' || key === 'accounts.system_roles.manage';
    context.App.navigate = () => {};
    let updatePayload = null;
    context.API.get = async (path) => {
        if (path === '/accounts') {
            return [
                { id: 1, account_number: '090', name: 'Business Bank Account', account_type: 'asset', balance: 1000, is_system: true, is_dashboard_favorite: true },
                { id: 2, account_number: '429', name: 'General Expenses', account_type: 'expense', balance: 0, is_system: false, is_dashboard_favorite: false },
            ];
        }
        if (path === '/accounts/system-roles') {
            return [];
        }
        if (path === '/accounts/1') {
            return { id: 1, account_number: '090', name: 'Business Bank Account', account_type: 'asset', description: '', is_dashboard_favorite: true };
        }
        throw new Error(`unexpected path ${path}`);
    };
    context.API.put = async (_path, data) => {
        updatePayload = data;
        return {};
    };

    const html = await context.App.renderAccounts();
    assert.ok(html.includes('New Account'));
    assert.ok(html.includes("App.showAccountForm(1)"));
    assert.ok(html.includes("App.showAccountForm(2)"));
    assert.ok(html.includes('Favorite'));
    assert.ok(html.includes('&#9733;'));

    await context.App.showAccountForm(1);
    assert.ok(context.__lastModal.html.includes('Show this account in the dashboard watchlist'));
    assert.ok(context.__lastModal.html.includes('name="is_dashboard_favorite" checked'));

    await context.App.saveAccount({
        preventDefault() {},
        target: {
            __formDataEntries: [
                ['account_number', '090'],
                ['name', 'Business Bank Account'],
                ['account_type', 'asset'],
                ['description', ''],
            ],
            elements: {
                is_dashboard_favorite: { checked: true },
            },
        },
    }, 1);
    assert.strictEqual(updatePayload.is_dashboard_favorite, true);
})();
