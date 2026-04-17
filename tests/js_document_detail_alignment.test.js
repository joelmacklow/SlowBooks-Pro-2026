const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = [
    fs.readFileSync('app/static/js/app.js', 'utf8'),
    fs.readFileSync('app/static/js/invoices.js', 'utf8'),
    fs.readFileSync('app/static/js/estimates.js', 'utf8'),
    fs.readFileSync('app/static/js/credit_memos.js', 'utf8'),
    'this.App = App; this.InvoicesPage = InvoicesPage; this.EstimatesPage = EstimatesPage; this.CreditMemosPage = CreditMemosPage;',
].join('\n');

const navigations = [];
const opened = [];

const context = {
    API: {
        get: async (path) => {
            if (path === '/invoices') return [{ id: 1, invoice_number: 'INV-1001', customer_name: 'Aroha Ltd', date: '2026-04-16', due_date: '2026-04-30', status: 'draft', total: 115, balance_due: 115 }];
            if (path === '/invoices/1') return { id: 1, invoice_number: 'INV-1001', customer_id: 5, customer_name: 'Aroha Ltd', date: '2026-04-16', due_date: '2026-04-30', terms: 'Net 30', po_number: 'PO-55', status: 'draft', subtotal: 100, tax_rate: 0.15, tax_amount: 15, total: 115, amount_paid: 0, balance_due: 115, notes: 'Invoice notes', lines: [{ item_id: 2, description: 'Pens', quantity: 2, rate: 50, amount: 100, gst_code: 'GST15', gst_rate: 0.15 }] };
            if (path === '/credit-memos?customer_id=5&status=issued') return [{ id: 3, memo_number: 'CM-1001', customer_id: 5, status: 'issued', balance_remaining: 57.5, total: 57.5 }];
            if (path === '/estimates') return [{ id: 2, estimate_number: 'EST-1001', customer_name: 'Aroha Ltd', date: '2026-04-16', expiration_date: '2026-04-30', status: 'draft', total: 115 }];
            if (path === '/estimates/2') return { id: 2, estimate_number: 'EST-1001', customer_id: 5, customer_name: 'Aroha Ltd', date: '2026-04-16', expiration_date: '2026-04-30', status: 'draft', subtotal: 100, tax_rate: 0.15, tax_amount: 15, total: 115, notes: 'Estimate notes', lines: [{ item_id: 2, description: 'Pens', quantity: 2, rate: 50, amount: 100, gst_code: 'GST15', gst_rate: 0.15 }] };
            if (path === '/credit-memos') return [{ id: 3, memo_number: 'CM-1001', customer_name: 'Aroha Ltd', date: '2026-04-16', status: 'issued', total: 57.5, balance_remaining: 57.5 }];
            if (path === '/credit-memos/3') return { id: 3, memo_number: 'CM-1001', customer_id: 5, customer_name: 'Aroha Ltd', date: '2026-04-16', status: 'issued', subtotal: 50, tax_rate: 0.15, tax_amount: 7.5, total: 57.5, amount_applied: 0, balance_remaining: 57.5, notes: 'Credit notes', lines: [{ item_id: 2, description: 'Pens', quantity: 1, rate: 50, amount: 50, gst_code: 'GST15', gst_rate: 0.15 }] };
            if (path === '/customers?active_only=true') return [{ id: 5, name: 'Aroha Ltd', terms: 'Net 30' }];
            if (path === '/items?active_only=true') return [{ id: 2, name: 'Pens', description: 'Pens', rate: 50, cost: 15 }];
            if (path === '/settings') return { default_terms: 'Net 30', default_tax_rate: '15', invoice_notes: 'Default invoice notes' };
            if (path === '/gst-codes') return [{ code: 'GST15', rate: 0.15, name: 'GST 15%' }];
            if (path === '/customers/5') return { id: 5, name: 'Aroha Ltd', email: 'customer@example.com' };
            throw new Error(`unexpected path ${path}`);
        },
        post: async () => ({}),
        put: async () => ({}),
        open: (path, filename) => opened.push([path, filename]),
    },
    App: {
        authState: { authenticated: true, bootstrap_required: false, user: { membership: { effective_permissions: ['sales.view', 'sales.manage', 'contacts.manage'] } } },
        hasPermission: () => true,
        navigate: hash => navigations.push(hash),
        setStatus() {},
        showDocumentEmailModal() {},
        settings: { locale: 'en-NZ', currency: 'NZD' },
    },
    AuthPage: { render() {}, renderUserManagement() {} },
    CustomersPage: { render() {}, showForm() {} },
    VendorsPage: { render() {} },
    ItemsPage: { render() {} },
    PaymentsPage: { render() {}, showForm() {} },
    BankingPage: { render() {} },
    DepositsPage: { render() {} },
    CheckRegisterPage: { render() {} },
    CCChargesPage: { render() {} },
    JournalPage: { render() {} },
    ReportsPage: { render() {}, renderGstReturnsScreen() {}, renderGstReturnDetailScreen() {} },
    SettingsPage: { render() {} },
    IIFPage: { render() {} },
    XeroImportPage: { render() {} },
    AuditPage: { render() {} },
    PurchaseOrdersPage: { render() {}, renderDetailScreen() {} },
    BillsPage: { render() {} },
    RecurringPage: { render() {} },
    BatchPaymentsPage: { render() {} },
    CompaniesPage: { render() {} },
    EmployeesPage: { render() {} },
    PayrollPage: { render() {} },
    document: {
        documentElement: { getAttribute: () => 'light', setAttribute() {} },
        addEventListener() {},
        querySelector: () => null,
        querySelectorAll: () => [],
        createElement: () => ({ click() {}, remove() {}, style: {} }),
    },
    window: { addEventListener() {} },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { hash: '#/' },
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-16',
    gstOptionsHtml: selected => `<option value="${selected || 'GST15'}">GST 15%</option>`,
    readGstLinePayload: row => ({
        quantity: parseFloat(row.querySelector('.line-qty')?.value) || 0,
        rate: parseFloat(row.querySelector('.line-rate')?.value) || 0,
        gst_code: row.querySelector('.line-gst')?.value || 'GST15',
        gst_rate: 0.15,
    }),
    calculateGstTotals: lines => {
        const subtotal = lines.reduce((sum, line) => sum + ((line.quantity || 0) * (line.rate || 0)), 0);
        const tax_amount = subtotal * 0.15;
        return { subtotal, tax_amount, total: subtotal + tax_amount };
    },
    openModal() {},
    closeModal() {},
    toast() {},
    confirm: () => true,
    setTimeout,
    setInterval: () => 1,
    console,
    fetch: async () => ({ ok: true, headers: { get: () => null }, blob: async () => ({}) }),
    URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
    $: () => null,
    $$: () => [],
    Date,
    Intl,
    Number,
};

vm.createContext(context);
vm.runInContext(code, context);
context.App.navigate = hash => navigations.push(hash);
context.App.authState = { authenticated: true, bootstrap_required: false, user: { membership: { effective_permissions: ['sales.view', 'sales.manage', 'contacts.manage'] } } };

(async () => {
    assert.ok(context.App.routes['/invoices/detail']);
    assert.ok(context.App.routes['/estimates/detail']);
    assert.ok(context.App.routes['/credit-memos/detail']);

    await context.InvoicesPage.startNew();
    assert.deepStrictEqual(navigations, ['#/invoices/detail']);
    let html = context.InvoicesPage.renderDetailScreen();
    assert.ok(html.includes('Create & Add New'));
    assert.ok(html.includes('Create & Print / PDF'));
    assert.ok(html.includes('Create & Email'));
    assert.ok(html.includes('Back to Invoices'));

    navigations.length = 0;
    await context.InvoicesPage.open(1);
    assert.deepStrictEqual(navigations, ['#/invoices/detail']);
    html = context.InvoicesPage.renderDetailScreen();
    assert.ok(html.includes('Invoice INV-1001'));
    assert.ok(html.includes('Print / PDF'));
    assert.ok(html.includes('Email Invoice'));
    assert.ok(html.includes('Duplicate'));

    navigations.length = 0;
    await context.EstimatesPage.startNew();
    assert.deepStrictEqual(navigations, ['#/estimates/detail']);
    html = context.EstimatesPage.renderDetailScreen();
    assert.ok(html.includes('Create & Add New'));
    assert.ok(html.includes('Create & Print / PDF'));
    assert.ok(html.includes('Create & Email'));
    assert.ok(html.includes('Back to Estimates'));

    navigations.length = 0;
    await context.EstimatesPage.open(2);
    assert.deepStrictEqual(navigations, ['#/estimates/detail']);
    html = context.EstimatesPage.renderDetailScreen();
    assert.ok(html.includes('Estimate EST-1001'));
    assert.ok(html.includes('Print / PDF'));
    assert.ok(html.includes('Convert to Invoice'));

    navigations.length = 0;
    await context.CreditMemosPage.startNew();
    assert.deepStrictEqual(navigations, ['#/credit-memos/detail']);
    html = context.CreditMemosPage.renderDetailScreen();
    assert.ok(html.includes('Create & Add New'));
    assert.ok(html.includes('Create & Print / PDF'));
    assert.ok(html.includes('Create & Email'));
    assert.ok(html.includes('Back to Credit Memos'));

    navigations.length = 0;
    await context.CreditMemosPage.open(3);
    assert.deepStrictEqual(navigations, ['#/credit-memos/detail']);
    html = context.CreditMemosPage.renderDetailScreen();
    assert.ok(html.includes('Credit Memo CM-1001') || html.includes('Credit Note CM-1001'));
    assert.ok(html.includes('Print / PDF'));
    assert.ok(html.includes('Email Credit Note'));
    assert.ok(html.includes('Apply Credit'));
})().catch(err => {
    console.error(err);
    process.exit(1);
});
