const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/credit_memos.js', 'utf8')}
this.CreditMemosPage = CreditMemosPage;`;

const navigations = [];

const context = {
    console,
    Promise,
    setTimeout,
    API: {
        get: async (path) => {
            if (path === '/customers?active_only=true') return [{ id: 5, name: 'Aroha Ltd' }];
            if (path === '/items?active_only=true') return [{ id: 2, name: 'Pens', rate: 50 }];
            if (path === '/gst-codes') return [{ code: 'GST15', rate: 0.15, name: 'GST 15%' }];
            if (path === '/credit-memos/3') return {
                id: 3,
                memo_number: 'CM-1001',
                customer_id: 5,
                customer_name: 'Aroha Ltd',
                date: '2026-04-16',
                status: 'applied',
                subtotal: 50,
                tax_rate: 0.15,
                tax_amount: 7.5,
                total: 57.5,
                amount_applied: 57.5,
                balance_remaining: 0,
                notes: 'Credit note',
                lines: [{ item_id: 2, description: 'Pens', quantity: 1, rate: 50, amount: 50, gst_code: 'GST15', gst_rate: 0.15 }],
                applications: [
                    { invoice_id: 11, invoice_number: 'INV-1011', amount: 20 },
                    { invoice_id: 12, invoice_number: 'INV-1012', amount: 37.5 },
                ],
            };
            throw new Error(`unexpected path ${path}`);
        },
        post: async () => ({}),
        put: async () => ({}),
        open() {},
    },
    App: {
        navigate: hash => navigations.push(hash),
        hasPermission: () => true,
        gstCodes: [],
        settings: { prices_include_gst: 'false' },
        showDocumentEmailModal() {},
    },
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-16',
    gstOptionsHtml: () => '<option value="GST15">GST 15%</option>',
    readGstLinePayload: () => ({ quantity: 1, rate: 0, gst_code: 'GST15', gst_rate: 0.15 }),
    calculateGstTotals: lines => {
        const subtotal = lines.reduce((sum, line) => sum + ((line.quantity || 0) * (line.rate || 0)), 0);
        const tax_amount = subtotal * 0.15;
        return { subtotal, tax_amount, total: subtotal + tax_amount };
    },
    $: () => null,
    $$: () => [],
    confirm: () => true,
    toast() {},
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.CreditMemosPage.open(3);
    assert.deepStrictEqual(navigations, ['#/credit-memos/detail']);
    const detailHtml = context.CreditMemosPage.renderDetailScreen();
    assert.ok(detailHtml.includes('Applied To Invoices'));
    assert.ok(detailHtml.includes('INV-1011'));
    assert.ok(detailHtml.includes('INV-1012'));
    assert.ok(detailHtml.includes('$20.00'));
    assert.ok(detailHtml.includes('$37.50'));
})();
