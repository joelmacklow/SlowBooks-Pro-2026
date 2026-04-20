const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/invoices.js', 'utf8')}\nthis.InvoicesPage = InvoicesPage;`;

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

context.InvoicesPage._items = [
    { id: 2, code: '100-20', name: 'Pens', description: 'Pens', rate: 50 },
    { id: 3, code: '200-10', name: 'Paper', description: 'Paper', rate: 10 },
    { id: 4, code: null, name: 'Stapler', description: 'Stapler', rate: 25 },
];

const label = context.InvoicesPage.itemOptionLabel(context.InvoicesPage._items[0]);
assert.ok(label.includes('100-20'));
assert.ok(label.includes('Pens'));

const byCode = context.InvoicesPage.filteredItems('100', null);
assert.deepStrictEqual(byCode.map(item => item.name), ['Pens']);

const byName = context.InvoicesPage.filteredItems('pap', null);
assert.deepStrictEqual(byName.map(item => item.name), ['Paper']);

const html = context.InvoicesPage.lineRowHtml(0, { item_id: 2, item_filter_query: '100', description: '', quantity: 1, rate: 50, gst_code: 'GST15' }, context.InvoicesPage._items, true);
assert.ok(html.includes('Filter by code or name'));
assert.ok(html.includes('100-20'));
assert.ok(!html.includes('Paper'));
