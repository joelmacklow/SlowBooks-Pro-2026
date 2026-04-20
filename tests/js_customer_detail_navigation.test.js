const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/customers.js', 'utf8')}\nthis.CustomersPage = CustomersPage;`;

const context = {
    console,
    API: {
        get: async (path) => {
            if (path === '/customers/7') {
                return {
                    id: 7,
                    name: 'Aroha Ltd',
                    company: 'Aroha Holdings',
                    email: 'admin@aroha.test',
                    invoice_reminders_enabled: false,
                    monthly_statements_enabled: true,
                    phone: '021 123 456',
                    mobile: null,
                    terms: 'Net 30',
                    tax_id: 'NZBN123',
                    bill_address1: '1 Queen St',
                    bill_address2: '',
                    bill_city: 'Auckland',
                    bill_state: 'Auckland',
                    bill_zip: '1010',
                    ship_address1: '',
                    ship_address2: '',
                    ship_city: '',
                    ship_state: '',
                    ship_zip: '',
                    balance: 10.0,
                };
            }
            if (path === '/invoices?customer_id=7') return [
                { id: 9, invoice_number: '1009', date: '2026-04-20', status: 'sent', total: 115, balance_due: 115 },
                { id: 10, invoice_number: '1010', date: '2026-04-18', status: 'partial', total: 90, balance_due: 40 },
                { id: 11, invoice_number: '1011', date: '2026-04-10', status: 'paid', total: 75, balance_due: 0 },
            ];
            if (path === '/estimates?customer_id=7') return [{ id: 2, estimate_number: 'E-101', date: '2026-04-18', status: 'pending', total: 57.5 }];
            if (path === '/credit-memos?customer_id=7') return [{ id: 3, memo_number: 'CM-0001', date: '2026-04-19', status: 'issued', total: 57.5, balance_remaining: 57.5 }];
            if (path === '/customers') return [];
            throw new Error(`unexpected get ${path}`);
        },
    },
    App: {
        navigateCalls: [],
        navigate(hash) { this.navigateCalls.push(hash); },
        hasPermission() { return true; },
    },
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    formatDate: value => String(value || ''),
    statusBadge: value => `<span>${value}</span>`,
    openModal() {},
    closeModal() {},
    toast() {},
    todayISO: () => '2026-04-20',
    $: () => null,
    $$: () => [],
    InvoicesPage: { view() {} },
    EstimatesPage: { view() {} },
    CreditMemosPage: { open() {} },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.CustomersPage.view(7);
    assert.strictEqual(context.App.navigateCalls[0], '#/customers/detail');

    const html = context.CustomersPage.renderDetailScreen();
    assert.ok(html.includes('Aroha Ltd'));
    assert.ok(html.includes('Aroha Holdings'));
    assert.ok(html.includes('1009'));
    assert.ok(html.includes('E-101'));
    assert.ok(html.includes('CM-0001'));
    assert.ok(html.includes('$115.00'));
    assert.ok(html.includes('$155.00'));
    assert.ok(html.includes('Customer Communications'));
    assert.ok(html.includes('Invoice Reminders'));
    assert.ok(html.includes('Disabled'));
    assert.ok(html.includes('Monthly Statements'));
    assert.ok(html.includes('Enabled'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
