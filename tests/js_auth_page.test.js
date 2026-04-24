const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/auth.js', 'utf8')}
this.AuthPage = AuthPage;`;
let lastNavigated = null;
let lastModal = null;
let lastRawRequest = null;
const localStore = {};
class FakeFormData {
    constructor(form) {
        this.form = form || { _formData: {} };
    }
    get(name) {
        return this.form._formData?.[name] ?? null;
    }
}
const context = {
    API: {
        post: async (path, data) => {
            if (path === '/auth/login') {
                return { token: 'tok-login', user: { full_name: 'Admin User', membership: { effective_permissions: ['users.manage'] } } };
            }
            if (path === '/auth/logout') return { status: 'logged_out' };
            throw new Error(`unexpected post ${path}`);
        },
        raw: async (method, path, options = {}) => {
            lastRawRequest = { method, path, options };
            if (method === 'POST' && path === '/auth/bootstrap-admin') {
                return {
                    json: async () => ({ token: 'tok-bootstrap', user: { full_name: 'Owner User', membership: { effective_permissions: ['users.manage'] } } }),
                };
            }
            throw new Error(`unexpected raw ${method} ${path}`);
        },
        get: async (path) => {
            if (path === '/auth/users') return [{ email: 'ops@example.com', full_name: 'Ops User', membership: { role_key: 'staff', effective_permissions: ['accounts.view'], allow_permissions: ['accounts.view'], deny_permissions: ['employees.manage'] }, is_active: true }];
            if (path === '/auth/meta') return {
                roles: [{ key: 'staff', label: 'Staff', permissions: ['accounts.view', 'employees.manage'] }],
                permissions: [
                    { key: 'accounts.view', description: 'View the chart of accounts.' },
                    { key: 'employees.manage', description: 'Create and update employee records.' },
                ],
            };
            throw new Error(`unexpected get ${path}`);
        },
    },
    App: {
        authState: { authenticated: false, bootstrap_required: true, user: null },
        setAuthState(state) { this.authState = state; },
        hasPermission(permission) { return (this.authState.user?.membership?.effective_permissions || []).includes(permission); },
        navigate(hash) { lastNavigated = hash; },
        loadSettings: async () => {},
        syncAuthUI() {},
    },
    escapeHtml: value => String(value || ''),
    location: { hash: '#/login?bootstrap_token=setup-url-token', search: '' },
    openModal(title, html) { lastModal = { title, html }; },
    closeModal() {},
    toast() {},
    FormData: FakeFormData,
    localStorage: {
        getItem(key) { return localStore[key] || null; },
        setItem(key, value) { localStore[key] = value; },
        removeItem(key) { delete localStore[key]; },
    },
};
vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const bootstrapHtml = await context.AuthPage.render();
    assert.ok(bootstrapHtml.includes('Create First Admin'));
    assert.ok(bootstrapHtml.includes('Password'));
    assert.ok(bootstrapHtml.includes('Bootstrap Token'));
    assert.ok(bootstrapHtml.includes('prefilled below'));
    assert.ok(bootstrapHtml.includes('value="setup-url-token"'));

    await context.AuthPage.bootstrapAdmin({
        preventDefault() {},
        target: {
            _formData: {
                full_name: 'Owner User',
                email: 'owner@example.com',
                password: 'supersecret',
            },
        },
    });
    assert.ok(lastRawRequest);
    assert.strictEqual(lastRawRequest.method, 'POST');
    assert.strictEqual(lastRawRequest.path, '/auth/bootstrap-admin');
    assert.strictEqual(lastRawRequest.options.headers['X-Bootstrap-Token'], 'setup-url-token');
    assert.strictEqual(lastRawRequest.options.body.email, 'owner@example.com');
    assert.strictEqual(localStore['slowbooks-auth-token'], undefined);

    context.App.authState = { authenticated: false, bootstrap_required: false, user: null };
    const loginHtml = await context.AuthPage.render();
    assert.ok(loginHtml.includes('Sign In'));
    assert.ok(loginHtml.includes('Email'));

    const userHtml = await context.AuthPage.renderUserManagement();
    assert.ok(userHtml.includes('Users & Access'));
    assert.ok(userHtml.includes('View Accounts'));
    assert.ok(userHtml.includes('Manage Employees'));
    assert.ok(!userHtml.includes('accounts.view'));
    assert.ok(!userHtml.includes('employees.manage'));
    assert.ok(userHtml.includes('Ops User'));

    context.AuthPage.showUserForm();
    assert.ok(lastModal);
    assert.ok(lastModal.html.includes('View Accounts'));
    assert.ok(lastModal.html.includes('Manage Employees'));
    assert.ok(!lastModal.html.includes('accounts.view</strong>'));
    assert.ok(!lastModal.html.includes('employees.manage</strong>'));
    assert.ok(lastModal.html.includes('value="accounts.view"'));
    assert.ok(lastModal.html.includes('value="employees.manage"'));

    await context.AuthPage.logout();
    assert.strictEqual(localStore['slowbooks-auth-token'], undefined);
    assert.strictEqual(lastNavigated, '#/login');
})();
