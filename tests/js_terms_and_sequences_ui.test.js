const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = [
    fs.readFileSync('app/static/js/app.js', 'utf8'),
    fs.readFileSync('app/static/js/customers.js', 'utf8'),
    fs.readFileSync('app/static/js/vendors.js', 'utf8'),
    fs.readFileSync('app/static/js/bills.js', 'utf8'),
    fs.readFileSync('app/static/js/invoices.js', 'utf8'),
    fs.readFileSync('app/static/js/estimates.js', 'utf8'),
    fs.readFileSync('app/static/js/recurring.js', 'utf8'),
    'this.App = App; this.CustomersPage = CustomersPage; this.VendorsPage = VendorsPage; this.BillsPage = BillsPage; this.InvoicesPage = InvoicesPage; this.EstimatesPage = EstimatesPage; this.RecurringPage = RecurringPage;',
].join('\n');

let modalHtml = '';
const customTermsConfig = 'Net 30|net:30\nDue 1st of next month|next_month_day:1';

const context = {
    API: {
        get: async (path) => {
            if (path === '/settings/public') return { default_terms: 'Due 1st of next month', payment_terms_config: customTermsConfig, locale: 'en-NZ', currency: 'NZD' };
            if (path === '/settings') return { default_terms: 'Due 1st of next month', payment_terms_config: customTermsConfig, default_tax_rate: '15', invoice_notes: 'Default invoice notes' };
            if (path === '/customers?active_only=true') return [{ id: 5, name: 'Aroha Ltd', terms: 'Due 1st of next month' }];
            if (path === '/items?active_only=true') return [{ id: 2, name: 'Pens', description: 'Pens', rate: 50, cost: 15 }];
            if (path === '/vendors?active_only=true') return [{ id: 7, name: 'Harbour Supplies' }];
            if (path === '/accounts?account_type=expense' || path === '/accounts?active_only=true&account_type=expense') {
                return [{ id: 11, account_number: '600', name: 'General Expenses' }];
            }
            if (path === '/gst-codes') return [{ code: 'GST15', rate: 0.15, name: 'GST 15%' }];
            return [];
        },
    },
    App: {
        settings: { default_terms: 'Due 1st of next month', payment_terms_config: customTermsConfig, locale: 'en-NZ', currency: 'NZD' },
        hasPermission: () => true,
        navigate() {},
        setStatus() {},
        authState: { authenticated: true, bootstrap_required: false, user: { membership: { effective_permissions: ['sales.manage', 'contacts.manage', 'purchasing.manage'] } } },
    },
    openModal(_title, html) { modalHtml = html; },
    closeModal() {},
    toast() {},
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    formatDate: value => String(value || ''),
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-21',
    gstOptionsHtml: selected => `<option value="${selected || 'GST15'}">GST 15%</option>`,
    readGstLinePayload: () => ({ quantity: 1, rate: 0, gst_code: 'GST15', gst_rate: 0.15 }),
    calculateGstTotals: () => ({ subtotal: 0, tax_amount: 0, total: 0 }),
    $: () => null,
    $$: () => [],
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { hash: '#/' },
    document: { documentElement: { getAttribute: () => 'light', setAttribute() {} }, addEventListener() {}, querySelector: () => null, querySelectorAll: () => [], createElement: () => ({ click() {}, remove() {}, style: {} }) },
    window: { addEventListener() {} },
    setTimeout,
    setInterval: () => 1,
    console,
    fetch: async () => ({ ok: true, headers: { get: () => null }, blob: async () => ({}) }),
    URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
    Date,
    Intl,
    Number,
};

vm.createContext(context);
vm.runInContext(code, context);
context.App.settings = { default_terms: 'Due 1st of next month', payment_terms_config: customTermsConfig, locale: 'en-NZ', currency: 'NZD' };

(async () => {
    const quickEntryHtml = await context.App.renderQuickEntry();
    assert.ok(quickEntryHtml.includes('Due 1st of next month'));

    await context.CustomersPage.showForm();
    assert.ok(modalHtml.includes('Due 1st of next month'));

    await context.VendorsPage.showForm();
    assert.ok(modalHtml.includes('Due 1st of next month'));

    await context.BillsPage.showForm();
    assert.ok(modalHtml.includes('Due 1st of next month'));

    await context.InvoicesPage._loadEditorContext(null);
    let html = context.InvoicesPage.renderDetailScreen();
    assert.ok(html.includes('Due 1st of next month'));

    await context.EstimatesPage._loadEditorContext(null);
    assert.ok(context.EstimatesPage.paymentTermLabels().includes('Due 1st of next month'));

    await context.RecurringPage._loadEditorContext(null);
    html = context.RecurringPage.renderDetailScreen();
    assert.ok(html.includes('Due 1st of next month'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
