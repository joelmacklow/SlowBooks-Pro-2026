const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/invoices.js', 'utf8')}\nthis.InvoicesPage = InvoicesPage;`;

const invoiceRows = [
    {
        id: 1,
        invoice_number: 'INV-1001',
        customer_id: 10,
        customer_name: 'Beta Ltd',
        status: 'sent',
        date: '2026-04-01',
        due_date: '2026-04-10',
        total: 300,
        amount_paid: 0,
        balance_due: 300,
        reminder_count: 2,
        reminder_summary: '2 sent',
        lines: [],
    },
    {
        id: 2,
        invoice_number: 'INV-1002',
        customer_id: 11,
        customer_name: 'Acme Ltd',
        status: 'partial',
        date: '2026-04-19',
        due_date: '2026-05-01',
        total: 450,
        amount_paid: 125,
        balance_due: 325,
        reminder_count: 0,
        reminder_summary: '',
        lines: [],
    },
    {
        id: 3,
        invoice_number: 'INV-1003',
        customer_id: 12,
        customer_name: 'Gamma Ltd',
        status: 'sent',
        date: '2026-03-20',
        due_date: '2026-04-01',
        total: 80,
        amount_paid: 0,
        balance_due: 80,
        reminder_count: 0,
        reminder_summary: 'Turned off',
        invoice_reminders_enabled: false,
        lines: [],
    },
];

const filterEl = { value: '' };
const contentEl = { innerHTML: '' };
const context = {
    console,
    Promise,
    setTimeout,
    API: {
        get: async (path) => {
            if (path === '/invoices') return invoiceRows;
            return [];
        },
    },
    App: {
        hasPermission: () => true,
        setDetailOrigin() {},
        navigate() {},
        gstCodes: [],
        settings: { prices_include_gst: 'false' },
        showDocumentEmailModal() {},
    },
    openModal() {},
    closeModal() {},
    toast() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-21',
    gstOptionsHtml: () => '<option value="GST15">GST 15%</option>',
    readGstLinePayload: () => ({ quantity: 0, rate: 0, gst_code: 'GST15', gst_rate: 0.15 }),
    calculateGstTotals: () => ({ subtotal: 0, tax_amount: 0, total: 0 }),
    $: selector => {
        if (selector === '#inv-status-filter') return filterEl;
        if (selector === '#page-content') return contentEl;
        return null;
    },
    $$: () => [],
    confirm: () => true,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    let html = await context.InvoicesPage.render();
    assert.ok(html.includes('value="overdue"'));
    assert.ok(html.includes('Overdue by'));
    assert.ok(html.includes('Reminders'));
    assert.ok(html.includes('invoice-due-date--overdue'));
    assert.ok(html.includes('11 days'));
    assert.ok(html.includes('20 days'));
    assert.ok(html.includes('2 sent'));
    assert.ok(html.includes('Turned off'));

    const overdueOnly = context.InvoicesPage.filteredInvoices(invoiceRows, 'overdue');
    assert.strictEqual(JSON.stringify(overdueOnly.map(inv => inv.id)), JSON.stringify([1, 3]));

    const sortedByCustomer = context.InvoicesPage.sortInvoices(invoiceRows, 'customer_name', 'asc');
    assert.strictEqual(JSON.stringify(sortedByCustomer.map(inv => inv.id)), JSON.stringify([2, 1, 3]));

    const sortedByOverdue = context.InvoicesPage.sortInvoices(invoiceRows, 'overdue_days', 'desc');
    assert.strictEqual(JSON.stringify(sortedByOverdue.map(inv => inv.id)), JSON.stringify([3, 1, 2]));

    filterEl.value = 'overdue';
    context.InvoicesPage._listState = { invoices: invoiceRows, statusFilter: '', sortKey: 'invoice_number', sortDirection: 'asc' };
    context.InvoicesPage.applyFilter();
    assert.ok(contentEl.innerHTML.includes('INV-1001'));
    assert.ok(contentEl.innerHTML.includes('INV-1003'));
    assert.ok(!contentEl.innerHTML.includes('INV-1002'));

    context.InvoicesPage._listState.statusFilter = '';
    context.InvoicesPage._listState.sortKey = 'customer_name';
    context.InvoicesPage._listState.sortDirection = 'asc';
    context.InvoicesPage.sortBy('customer_name');
    assert.strictEqual(context.InvoicesPage._listState.sortDirection, 'desc');
})();
