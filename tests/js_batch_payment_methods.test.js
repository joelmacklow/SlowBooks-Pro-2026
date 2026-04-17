const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/batch_payments.js', 'utf8')}
this.BatchPaymentsPage = BatchPaymentsPage;`;

const context = {
    console,
    Promise,
    API: {
        get: async (path) => {
            if (path === '/invoices') return [{ id: 5, invoice_number: 'INV-5', customer_id: 1, customer_name: 'Aroha Ltd', due_date: '2026-04-30', balance_due: 125, status: 'sent' }];
            if (path === '/accounts?account_type=asset') return [{ id: 21, name: 'Operating Account' }];
            throw new Error(`unexpected path ${path}`);
        },
    },
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    todayISO: () => '2026-04-17',
    toast() {},
    App: { navigate() {} },
    $: () => null,
    $$: () => [],
    document: { addEventListener() {} },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const html = await context.BatchPaymentsPage.render();
    assert.ok(html.includes('<option value="EFT">EFT</option>'));
    assert.ok(html.includes('<option value="Cash">Cash</option>'));
    assert.ok(html.includes('<option value="Credit">Credit</option>'));
    assert.ok(!html.includes('<option value="check">Check</option>'));
    assert.ok(!html.includes('<option value="ach">ACH</option>'));
    assert.ok(!html.includes('Credit Card'));
})().catch(err => {
    console.error(err);
    process.exit(1);
});
