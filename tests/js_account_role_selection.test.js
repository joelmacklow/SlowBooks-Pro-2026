const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/payments.js', 'utf8')}\nthis.PaymentsPage = PaymentsPage;`;
let modalHtml = '';

const context = {
    API: {
        get: async (path) => {
            if (path === '/customers?active_only=true') {
                return [{ id: 1, name: 'Aroha Ltd' }];
            }
            if (path === '/accounts') {
                return [
                    { id: 11, name: 'Business Bank Account', account_type: 'asset', account_number: '090' },
                    { id: 12, name: 'Receipt Clearing', account_type: 'asset', account_number: '615' },
                    { id: 13, name: 'Trade Creditors', account_type: 'liability', account_number: '810' },
                ];
            }
            throw new Error(`unexpected path ${path}`);
        },
    },
    openModal: (_title, html) => { modalHtml = html; },
    closeModal() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    todayISO: () => '2026-04-01',
    toast() {},
    App: { navigate() {} },
    $$: () => [],
    $: () => null,
    console,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.PaymentsPage.showForm();
    assert.ok(modalHtml.includes('Business Bank Account'));
    assert.ok(modalHtml.includes('Receipt Clearing'));
    assert.ok(!modalHtml.includes('Trade Creditors'));
})().catch(err => {
    console.error(err);
    process.exit(1);
});
