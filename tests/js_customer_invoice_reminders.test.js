const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/customers.js', 'utf8')}\nthis.CustomersPage = CustomersPage;`;
const posts = [];
const puts = [];
const toasts = [];

const context = {
    API: {
        get: async (path) => {
            if (path === '/customers/5') {
                return {
                    id: 5,
                    name: 'Aroha Ltd',
                    invoice_reminders_enabled: false,
                    monthly_statements_enabled: true,
                };
            }
            return [];
        },
        post: async (path, body) => {
            posts.push({ path, body });
            return body;
        },
        put: async (path, body) => {
            puts.push({ path, body });
            return body;
        },
    },
    FormData: class {
        constructor(target) {
            this.target = target;
        }
        entries() {
            return Object.entries(this.target.data);
        }
    },
    App: { navigate() {}, hasPermission: () => true },
    closeModal() {},
    openModal() {},
    toast: (message) => { toasts.push(message); },
    escapeHtml: (value) => String(value ?? ''),
    formatCurrency: (value) => `$${Number(value || 0).toFixed(2)}`,
    $$: () => [],
    location: { hash: '#/customers' },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.CustomersPage.save({
        preventDefault() {},
        target: {
            data: { name: 'Reminder Co', email: 'x@example.com' },
            invoice_reminders_enabled: { checked: false },
            monthly_statements_enabled: { checked: true },
        },
    }, null);

    await context.CustomersPage.save({
        preventDefault() {},
        target: {
            data: { name: 'Aroha Ltd', email: 'a@example.com' },
            invoice_reminders_enabled: { checked: true },
            monthly_statements_enabled: { checked: false },
        },
    }, 5);

    assert.strictEqual(posts[0].path, '/customers');
    assert.strictEqual(posts[0].body.invoice_reminders_enabled, false);
    assert.strictEqual(posts[0].body.monthly_statements_enabled, true);
    assert.strictEqual(puts[0].path, '/customers/5');
    assert.strictEqual(puts[0].body.invoice_reminders_enabled, true);
    assert.strictEqual(puts[0].body.monthly_statements_enabled, false);
    assert.ok(toasts.includes('Customer created'));
    assert.ok(toasts.includes('Customer updated'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
