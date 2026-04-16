const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/auth.js', 'utf8')}\nthis.AuthPage = AuthPage;`;
let lastModal = null;
let lastPosted = null;

const context = {
    API: {
        post: async (path, data) => {
            lastPosted = [path, data];
            return { id: 1 };
        },
        get: async (path) => {
            if (path === '/auth/users') return [];
            if (path === '/auth/meta') return {
                roles: [{ key: 'staff', label: 'Staff', permissions: ['companies.view'] }],
                permissions: [{ key: 'companies.view', description: 'View company database entries.' }],
                company_scopes: [
                    { key: '__current__', label: 'SlowBooks NZ', database_name: 'bookkeeper', is_default: true },
                    { key: 'auckland_books', label: 'Auckland Books', database_name: 'auckland_books', is_default: false },
                ],
            };
            throw new Error(`unexpected get ${path}`);
        },
    },
    App: {
        navigate() {},
        authState: { authenticated: true, bootstrap_required: false, user: { membership: { effective_permissions: ['users.manage'] } } },
        setAuthState() {},
        loadSettings: async () => {},
        syncAuthUI() {},
        syncNavVisibility() {},
    },
    escapeHtml: value => String(value || ''),
    openModal(title, html) { lastModal = { title, html }; },
    closeModal() {},
    toast() {},
    FormData,
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    console,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.AuthPage.renderUserManagement();
    context.AuthPage.showUserForm();
    assert.ok(lastModal);
    assert.ok(lastModal.html.includes('Company Access'));
    assert.ok(lastModal.html.includes('value="__current__"'));
    assert.ok(lastModal.html.includes('value="auckland_books"'));

    await context.AuthPage.saveUser({
        preventDefault() {},
        target: {
            full_name: { value: 'Ops User' },
            email: { value: 'ops@example.com' },
            password: { value: 'opssecret1' },
            role_key: { value: 'staff' },
            is_active: { checked: true },
            membership_active: { checked: true },
            querySelectorAll(selector) {
                if (selector === 'input[name="allow_permissions"]:checked') return [{ value: 'companies.view' }];
                if (selector === 'input[name="deny_permissions"]:checked') return [];
                if (selector === 'input[name="company_scopes"]:checked') return [{ value: '__current__' }, { value: 'auckland_books' }];
                return [];
            },
        },
    }, null);

    assert.strictEqual(lastPosted[0], '/auth/users');
    assert.strictEqual(JSON.stringify(lastPosted[1].company_scopes), JSON.stringify(['__current__', 'auckland_books']));
})();
