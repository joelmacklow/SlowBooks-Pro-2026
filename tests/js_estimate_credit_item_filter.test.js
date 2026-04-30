const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = [
    fs.readFileSync('app/static/js/estimates.js', 'utf8'),
    fs.readFileSync('app/static/js/credit_memos.js', 'utf8'),
    'this.EstimatesPage = EstimatesPage; this.CreditMemosPage = CreditMemosPage;',
].join('\n');

const context = {
    console,
    Promise,
    setTimeout,
    API: { get: async () => [] },
    App: { hasPermission: () => true, gstCodes: [], settings: { prices_include_gst: 'false' }, showDocumentEmailModal() {} },
    openModal() {},
    closeModal() {},
    toast() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-16',
    gstOptionsHtml: () => '<option value="GST15">GST 15%</option>',
    readGstLinePayload: () => ({ quantity: 0, rate: 0, gst_code: 'GST15', gst_rate: 0.15 }),
    calculateGstTotals: () => ({ subtotal: 0, tax_amount: 0, total: 0 }),
    $: () => null,
    $$: () => [],
    confirm: () => true,
};

vm.createContext(context);
vm.runInContext(code, context);

const items = [
    { id: 2, code: '100-20', name: 'Pens', description: 'Pens', rate: 50 },
    { id: 3, code: '200-10', name: 'Paper', description: 'Paper', rate: 10 },
    { id: 4, code: null, name: 'Stapler', description: 'Stapler', rate: 25 },
];

context.EstimatesPage._items = items;
context.CreditMemosPage._items = items;

assert.strictEqual(JSON.stringify(context.EstimatesPage.itemSearchValues(items[0])), JSON.stringify(['100-20', 'Pens', '100-20 — Pens']));
assert.deepStrictEqual(context.EstimatesPage.filteredItems('100', null).map(item => item.id), [2]);
assert.deepStrictEqual(context.EstimatesPage.filteredItems('Paper', null).map(item => item.id), [3]);
let html = context.EstimatesPage.lineRowHtml(0, { item_id: 2, description: '', quantity: 1, rate: 50, gst_code: 'GST15' }, items, true);
assert.ok(html.includes('<select class="line-item"'));
assert.ok(html.includes('100-20'));
assert.ok(html.includes('Paper'));

assert.strictEqual(JSON.stringify(context.CreditMemosPage.itemSearchValues(items[0])), JSON.stringify(['100-20', 'Pens', '100-20 — Pens']));
assert.deepStrictEqual(context.CreditMemosPage.filteredItems('100', null).map(item => item.id), [2]);
assert.deepStrictEqual(context.CreditMemosPage.filteredItems('Paper', null).map(item => item.id), [3]);
html = context.CreditMemosPage.lineRowHtml(0, { item_id: 2, description: '', quantity: 1, rate: 50, gst_code: 'GST15' }, items, true);
assert.ok(html.includes('<select class="line-item"'));
assert.ok(html.includes('100-20'));
assert.ok(html.includes('Paper'));
