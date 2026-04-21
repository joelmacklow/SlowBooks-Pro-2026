const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = [
    fs.readFileSync('app/static/js/app.js', 'utf8'),
    fs.readFileSync('app/static/js/recurring.js', 'utf8'),
    'this.App = App; this.RecurringPage = RecurringPage;',
].join('\n');

const navigations = [];
const posts = [];
const elements = {
    '#recurring-frequency': { value: 'monthly' },
    '#recurring-start-date': { value: '2026-04-16' },
    '#recurring-terms': { value: 'Net 30' },
    '#rec-next-invoice-date': { value: '', textContent: '' },
    '#rec-invoice-due-preview': { value: '', textContent: '' },
};

const context = {
    API: {
        get: async (path) => {
            if (path === '/recurring') return [{ id: 7, customer_name: 'Aroha Ltd', frequency: 'monthly', next_due: '2026-05-01', is_active: true, invoices_created: 3 }];
            if (path === '/recurring/7') return {
                id: 7,
                customer_id: 5,
                customer_name: 'Aroha Ltd',
                frequency: 'monthly',
                start_date: '2026-04-01',
                end_date: '',
                next_due: '2026-05-01',
                is_active: true,
                terms: 'Net 30',
                tax_rate: 0.15,
                notes: 'Recurring notes',
                invoices_created: 3,
                lines: [{ item_id: 2, description: 'Pens', quantity: 2, rate: 50, gst_code: 'GST15', gst_rate: 0.15 }],
            };
            if (path === '/customers?active_only=true') return [{ id: 5, name: 'Aroha Ltd', terms: 'Net 30' }];
            if (path === '/items?active_only=true') return [{ id: 2, code: '100-20', name: 'Pens', description: 'Pens', rate: 50 }];
            if (path === '/settings') return { default_terms: 'Net 30', default_tax_rate: '15', payment_terms_config: 'Net 30|net:30\nDue 1st of next month|next_month_day:1' };
            if (path === '/gst-codes') return [{ code: 'GST15', rate: 0.15, name: 'GST 15%' }];
            throw new Error(`unexpected get ${path}`);
        },
        post: async (path, body) => {
            posts.push({ path, body });
            if (path === '/recurring') return { id: 9, ...body, next_due: body.start_date, is_active: true, invoices_created: 0 };
            if (path === '/recurring/generate') return { invoices_created: 2 };
            return {};
        },
        put: async () => ({}),
        del: async () => ({}),
    },
    App: {
        authState: { authenticated: true, bootstrap_required: false, user: { membership: { effective_permissions: ['sales.view', 'sales.manage'] } } },
        hasPermission: () => true,
        navigate: hash => navigations.push(hash),
        setStatus() {},
        settings: { locale: 'en-NZ', currency: 'NZD' },
    },
    AuthPage: { render() {}, renderUserManagement() {} },
    CustomersPage: { render() {} },
    VendorsPage: { render() {} },
    ItemsPage: { render() {} },
    InvoicesPage: { render() {}, renderDetailScreen() {} },
    EstimatesPage: { render() {}, renderDetailScreen() {} },
    PaymentsPage: { render() {} },
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
    CreditMemosPage: { render() {}, renderDetailScreen() {} },
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
    $: selector => elements[selector] || null,
    $$: selector => selector === '#rec-lines tr' ? [{
        querySelector(sel) {
            const values = {
                '.line-item': { value: '2' },
                '.line-desc': { value: 'Pens' },
                '.line-qty': { value: '2' },
                '.line-gst': { value: 'GST15' },
                '.line-rate': { value: '50' },
            };
            return values[sel] || null;
        },
    }] : [],
    Date,
    Intl,
    Number,
};

vm.createContext(context);
vm.runInContext(code, context);
context.App.navigate = hash => navigations.push(hash);
context.App.authState = { authenticated: true, bootstrap_required: false, user: { membership: { effective_permissions: ['sales.view', 'sales.manage'] } } };

(async () => {
    assert.ok(context.App.routes['/recurring/detail']);

    const listHtml = await context.RecurringPage.render();
    assert.ok(listHtml.includes('Generate Due Now'));
    assert.ok(listHtml.includes("RecurringPage.open(7)"));

    await context.RecurringPage.startNew();
    assert.deepStrictEqual(navigations, ['#/recurring/detail']);
    let html = context.RecurringPage.renderDetailScreen();
    assert.ok(html.includes('New Recurring Invoice'));
    assert.ok(html.includes('Create & Add New'));
    assert.ok(html.includes('Back to Recurring Invoices'));
    assert.ok(html.includes('Next Invoice Date'));
    assert.ok(html.includes('Invoice Due Date'));

    navigations.length = 0;
    await context.RecurringPage.open(7);
    assert.deepStrictEqual(navigations, ['#/recurring/detail']);
    html = context.RecurringPage.renderDetailScreen();
    assert.ok(html.includes('Edit Recurring Invoice'));
    assert.ok(html.includes('Invoices Created'));
    assert.ok(html.includes('Recurring notes'));

    const unchangedPreview = context.RecurringPage.schedulePreview({
        id: 7,
        frequency: 'monthly',
        start_date: '2026-04-01',
        next_due: '2026-05-01',
        terms: 'Net 30',
    });
    assert.strictEqual(unchangedPreview.nextInvoiceDate, '2026-05-01');
    assert.strictEqual(unchangedPreview.invoiceDueDate, '2026-05-31');

    const weeklyPreview = context.RecurringPage.schedulePreview({
        id: 7,
        frequency: 'weekly',
        start_date: '2026-04-01',
        next_due: '2026-05-01',
        terms: 'Net 30',
    });
    assert.strictEqual(weeklyPreview.nextInvoiceDate, '2026-04-22');

    const firstOfMonthPreview = context.RecurringPage.schedulePreview({
        id: null,
        frequency: 'monthly',
        start_date: '2026-04-16',
        next_due: null,
        terms: 'Due 1st of next month',
    });
    assert.strictEqual(firstOfMonthPreview.nextInvoiceDate, '2026-04-16');
    assert.strictEqual(firstOfMonthPreview.invoiceDueDate, '2026-05-01');

    await context.RecurringPage.generateNow();
    assert.strictEqual(posts[0].path, '/recurring/generate');

    await context.RecurringPage.save({
        preventDefault() {},
        target: {
            customer_id: { value: '5' },
            frequency: { value: 'monthly' },
            start_date: { value: '2026-04-16' },
            end_date: { value: '' },
            terms: { value: 'Net 30' },
            tax_rate: { value: '15' },
            notes: { value: 'Recurring note' },
        },
    }, null);
    assert.strictEqual(posts[1].path, '/recurring');
    assert.strictEqual(posts[1].body.frequency, 'monthly');
    assert.strictEqual(posts[1].body.customer_id, 5);
})();
