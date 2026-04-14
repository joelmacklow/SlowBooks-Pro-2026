const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/auth.js', 'utf8')}\nthis.AuthPage = AuthPage;`;
let lastNavigated = null;
const localStore = {};
const context = {
    API: {
        post: async (path, data) => {
            if (path === '/auth/login') {
                return { token: 'tok-login', user: { full_name: 'Admin User', membership: { effective_permissions: ['users.manage'] } } };
            }
            if (path === '/auth/bootstrap-admin') {
                return { token: 'tok-bootstrap', user: { full_name: 'Owner User', membership: { effective_permissions: ['users.manage'] } } };
            }
            if (path === '/auth/logout') return { status: 'logged_out' };
            throw new Error(`unexpected post ${path}`);
        },
        get: async (path) => {
            if (path === '/auth/users') return [{ email: 'ops@example.com', full_name: 'Ops User', membership: { role_key: 'staff', effective_permissions: ['audit.view'], allow_permissions: ['audit.view'], deny_permissions: [] }, is_active: true }];
            if (path === '/auth/meta') return { roles: [{ key: 'staff', label: 'Staff' }], permissions: [{ key: 'audit.view', description: 'View audit log' }] };
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
    openModal() {},
    closeModal() {},
    toast() {},
    FormData,
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

    context.App.authState = { authenticated: false, bootstrap_required: false, user: null };
    const loginHtml = await context.AuthPage.render();
    assert.ok(loginHtml.includes('Sign In'));
    assert.ok(loginHtml.includes('Email'));

    const userHtml = await context.AuthPage.renderUserManagement();
    assert.ok(userHtml.includes('Users & Access'));
    assert.ok(userHtml.includes('audit.view'));
    assert.ok(userHtml.includes('Ops User'));

    await context.AuthPage.logout();
    assert.strictEqual(localStore['slowbooks-auth-token'], undefined);
    assert.strictEqual(lastNavigated, '#/login');
})();
