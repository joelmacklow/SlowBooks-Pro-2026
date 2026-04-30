const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/companies.js', 'utf8')}\nthis.CompaniesPage = CompaniesPage;`;

let modalHtml = '';
const posts = [];

const context = {
    console,
    Promise,
    FormData: class {
        constructor(target) { this.target = target; }
        entries() {
            return [
                ['name', this.target.name.value],
                ['description', this.target.description.value],
                ['org_lock_date', this.target.org_lock_date.value],
            ][Symbol.iterator]();
        }
    },
    API: {
        get: async (path) => {
            if (path === '/companies') return [{
                id: 2,
                name: 'Demo Company',
                database_name: 'demo_company',
                description: 'Sandbox',
                last_accessed: null,
                org_lock_date: '2026-03-31',
            }];
            throw new Error(`unexpected get ${path}`);
        },
        post: async () => ({ success: true }),
        put: async (path, data) => {
            posts.push({ path, data });
            return { id: 2, ...data };
        },
    },
    App: { hasPermission: () => true, navigate() {} },
    openModal(_title, html) { modalHtml = html; },
    closeModal() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => value || '',
    toast() {},
    localStorage: { setItem() {} },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const html = await context.CompaniesPage.render();
    assert.ok(html.includes('Org Lock: 2026-03-31'));
    assert.ok(html.includes('Edit'));
    context.CompaniesPage.showEdit(2);
    assert.ok(modalHtml.includes('Organization Lock Date'));
    await context.CompaniesPage.update({
        preventDefault() {},
        target: {
            name: { value: 'Demo Company' },
            description: { value: 'Sandbox' },
            org_lock_date: { value: '2026-04-30' },
        },
    }, 2);
    assert.strictEqual(posts[0].path, '/companies/2');
    assert.strictEqual(posts[0].data.org_lock_date, '2026-04-30');
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
