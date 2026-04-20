const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/vendors.js', 'utf8')}\nthis.VendorsPage = VendorsPage;`;

const context = {
    console,
    API: {
        get: async (path) => {
            if (path === '/vendors/4') {
                return {
                    id: 4,
                    name: 'Harbour Supplies',
                    company: 'Harbour Supplies Ltd',
                    email: 'ap@harbour.test',
                    phone: '09 555 000',
                    terms: 'Net 30',
                    tax_id: 'GST123',
                    account_number: 'V-200',
                    default_expense_account_id: 600,
                    address1: '8 Depot Road',
                    address2: '',
                    city: 'Auckland',
                    state: 'Auckland',
                    zip: '1010',
                    notes: 'Prefers Friday delivery',
                    balance: 287.5,
                };
            }
            if (path === '/items?active_only=true&vendor_id=4') return [
                { id: 10, name: 'Printer Paper', description: 'A4 reams', rate: 20, cost: 12.5 },
                { id: 11, name: 'Pens', description: 'Blue pens', rate: 8, cost: 3.5 },
            ];
            if (path === '/bills?vendor_id=4') return [
                { id: 21, bill_number: 'B-001', date: '2026-04-20', status: 'unpaid', total: 115, balance_due: 115 },
                { id: 22, bill_number: 'B-002', date: '2026-04-18', status: 'paid', total: 172.5, balance_due: 0 },
            ];
            if (path === '/bill-payments?vendor_id=4') return [
                { id: 31, date: '2026-04-21', method: 'EFT', check_number: 'BP-1', amount: 200, unallocated_amount: 42.5 },
            ];
            if (path === '/vendors') return [];
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
    $: () => null,
    $$: () => [],
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.VendorsPage.view(4);
    assert.strictEqual(context.App.navigateCalls[0], '#/vendors/detail');

    const html = context.VendorsPage.renderDetailScreen();
    assert.ok(html.includes('Harbour Supplies'));
    assert.ok(html.includes('Printer Paper'));
    assert.ok(html.includes('Pens'));
    assert.ok(html.includes('B-001'));
    assert.ok(html.includes('B-002'));
    assert.ok(html.includes('$42.50'));
    assert.ok(html.includes('Unallocated bill payments'));
    assert.ok(html.includes('ItemsPage.showForm(10)'));
    assert.ok(html.includes('ItemsPage.showForm(11)'));
    assert.ok(html.includes('BillsPage.view(21)'));
    assert.ok(html.includes('BillsPage.view(22)'));
})();
