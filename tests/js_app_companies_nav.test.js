const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = fs.readFileSync('app/static/js/app.js', 'utf8');

const events = {};
const navLink = {
    getAttribute(name) { return name === 'href' ? '#/companies' : null; },
    dataset: { page: 'companies' },
    addEventListener(event, handler) { events[event] = handler; },
    classList: { toggle() {} },
    parentElement: { style: {} },
};

const context = {
    API: {
        get: async path => {
            if (path === '/auth/me') return { authenticated: true, bootstrap_required: false, user: { full_name: 'Ops', membership: { role_key: 'owner', effective_permissions: ['companies.view'] } } };
            if (path === '/settings/public') return { locale: 'en-NZ', currency: 'NZD', company_name: 'SlowBooks NZ' };
            if (path === '/companies') return [];
            if (path === '/dashboard') return { total_receivables: 0, overdue_count: 0, customer_count: 0, total_payables: 0, recent_invoices: [], recent_payments: [], bank_balances: [] };
            if (path === '/dashboard/charts') return {};
            throw new Error(`unexpected path ${path}`);
        },
    },
    CompaniesPage: { render: async () => '<div>Companies</div>' },
    AuthPage: { render: () => '', logout() {}, renderUserManagement: () => '' },
    CustomersPage: { showForm() {}, render: async () => '' },
    InvoicesPage: { showForm() {}, render: async () => '' },
    PaymentsPage: { showForm() {}, render: async () => '' },
    EstimatesPage: { render: async () => '' },
    BankingPage: { render: async () => '' },
    DepositsPage: { render: async () => '' },
    CheckRegisterPage: { render: async () => '' },
    CCChargesPage: { render: async () => '' },
    JournalPage: { render: async () => '' },
    ReportsPage: { render: async () => '', renderGstReturnsScreen: async () => '', renderGstReturnDetailScreen: async () => '' },
    SettingsPage: { render: async () => '' },
    IIFPage: { render: async () => '' },
    XeroImportPage: { render: async () => '' },
    AuditPage: { render: async () => '' },
    PurchaseOrdersPage: { render: async () => '', renderDetailScreen: async () => '' },
    BillsPage: { render: async () => '' },
    CreditMemosPage: { render: async () => '' },
    RecurringPage: { render: async () => '' },
    BatchPaymentsPage: { render: async () => '' },
    EmployeesPage: { render: async () => '' },
    PayrollPage: { render: async () => '' },
    document: {
        documentElement: { getAttribute: () => 'light', setAttribute() {} },
        addEventListener() {},
        querySelector(selector) {
            if (selector === '#page-content') return { innerHTML: '' };
            if (selector === '#status-text' || selector === '#topbar-clock' || selector === '#status-date' || selector === '#status-company' || selector === '#auth-user') return { textContent: '', style: {} };
            if (selector === '#auth-logout' || selector === '#auth-login') return { style: {} };
            return null;
        },
        querySelectorAll(selector) {
            if (selector === '.nav-link') return [navLink];
            return [];
        },
        createElement: () => ({ click() {}, remove() {}, style: {} }),
    },
    window: { addEventListener() {} },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { hash: '#/', reload() {} },
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${value}`,
    formatDate: value => value || '',
    todayISO: () => '2026-04-17',
    openModal() {},
    closeModal() {},
    toast() {},
    setInterval: () => 1,
    setTimeout,
    console,
    fetch: async () => ({ ok: true, headers: { get: () => null }, blob: async () => ({}) }),
    URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
    $: selector => context.document.querySelector(selector),
    $$: selector => context.document.querySelectorAll(selector),
    Date,
    Intl,
    Number,
};

vm.createContext(context);
vm.runInContext(`${code}\nthis.App = App;`, context);

(async () => {
    const navigations = [];
    context.App.navigate = hash => navigations.push(hash);
    await context.App.init();
    assert.ok(events.click);
    events.click({ preventDefault() {} });
    assert.deepStrictEqual(navigations.includes('#/companies'), true);
})().catch(err => {
    console.error(err);
    process.exit(1);
});
