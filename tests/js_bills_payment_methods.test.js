const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/bills.js', 'utf8')}
this.BillsPage = BillsPage;`;
let modalHtml = '';

const context = {
    console,
    Promise,
    API: {
        get: async (path) => {
            if (path === '/vendors?active_only=true') return [{ id: 1, name: 'Harbour Supplies' }];
            if (path === '/bills?status=unpaid') return [{ id: 11, bill_number: 'B-0011', vendor_id: 1, vendor_name: 'Harbour Supplies', due_date: '2026-04-30', balance_due: 115 }];
            if (path === '/bills?status=partial') return [];
            if (path === '/accounts?account_type=asset') return [{ id: 21, name: 'Operating Account' }];
            throw new Error(`unexpected path ${path}`);
        },
    },
    openModal: (_title, html) => { modalHtml = html; },
    closeModal() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    todayISO: () => '2026-04-17',
    toast() {},
    App: { navigate() {}, hasPermission: () => true },
    $: () => null,
    $$: () => [],
    confirm: () => true,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.BillsPage.showPayForm();
    assert.ok(modalHtml.includes('<option value="EFT">EFT</option>'));
    assert.ok(modalHtml.includes('<option value="Cash">Cash</option>'));
    assert.ok(modalHtml.includes('<option value="Credit">Credit</option>'));
    assert.ok(!modalHtml.includes('<option value="check">Check</option>'));
    assert.ok(!modalHtml.includes('<option value="ach">ACH</option>'));
    assert.ok(!modalHtml.includes('Check #'));
    assert.ok(modalHtml.includes('<label>Reference</label>'));
})().catch(err => {
    console.error(err);
    process.exit(1);
});
