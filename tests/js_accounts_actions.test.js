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
    API: { get: async () => ({}) },
    URL: { createObjectURL() { return 'blob:url'; }, revokeObjectURL() {} },
    openModal() {},
    closeModal() {},
    toast() {},
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    formatDate: value => String(value || ''),
    statusBadge: value => String(value || ''),
    AuthPage: { logout() {} },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    context.App.hasPermission = (key) => key === 'accounts.manage' || key === 'accounts.system_roles.manage';
    context.API.get = async (path) => {
        if (path === '/accounts') {
            return [
                { id: 1, account_number: '090', name: 'Business Bank Account', account_type: 'asset', balance: 1000, is_system: true },
                { id: 2, account_number: '429', name: 'General Expenses', account_type: 'expense', balance: 0, is_system: false },
            ];
        }
        if (path === '/accounts/system-roles') {
            return [];
        }
        throw new Error(`unexpected path ${path}`);
    };

    const html = await context.App.renderAccounts();
    assert.ok(html.includes('New Account'));
    assert.ok(html.includes("App.showAccountForm(1)"));
    assert.ok(html.includes("App.showAccountForm(2)"));
})();
