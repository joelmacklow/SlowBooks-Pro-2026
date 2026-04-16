const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/bills.js', 'utf8')}
this.BillsPage = BillsPage;`;

const navigations = [];
const loaded = [];
let modalHtml = '';

const context = {
    console,
    Promise,
    API: {
        get: async (path) => {
            if (path === '/bills') {
                return [{
                    id: 11,
                    bill_number: 'B-0011',
                    vendor_name: 'Harbour Supplies',
                    date: '2026-04-17',
                    due_date: '2026-04-30',
                    status: 'unpaid',
                    total: 115,
                    balance_due: 115,
                    po_id: 7,
                }];
            }
            if (path === '/bills/11') {
                return {
                    id: 11,
                    bill_number: 'B-0011',
                    vendor_name: 'Harbour Supplies',
                    date: '2026-04-17',
                    due_date: '2026-04-30',
                    status: 'unpaid',
                    total: 115,
                    amount_paid: 0,
                    balance_due: 115,
                    po_id: 7,
                    lines: [{ description: 'Pens', quantity: 2, rate: 50, amount: 100 }],
                };
            }
            throw new Error(`unexpected path ${path}`);
        },
    },
    App: {
        navigate: hash => navigations.push(hash),
    },
    PurchaseOrdersPage: {
        _loadEditorContext: async id => loaded.push(id),
    },
    openModal: (_title, html) => { modalHtml = html; },
    closeModal() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    confirm: () => true,
    toast() {},
    $: () => null,
    $$: () => [],
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const listHtml = await context.BillsPage.render();
    assert.ok(listHtml.includes('Purchase Order'));
    assert.ok(listHtml.includes('BillsPage.openPurchaseOrder(7)'));

    await context.BillsPage.view(11);
    assert.ok(modalHtml.includes('Purchase Order'));
    assert.ok(modalHtml.includes('BillsPage.openPurchaseOrder(7)'));

    await context.BillsPage.openPurchaseOrder(7);
    assert.deepStrictEqual(loaded, [7]);
    assert.deepStrictEqual(navigations, ['#/purchase-orders/detail']);
})().catch(err => {
    console.error(err);
    process.exit(1);
});
