const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/purchase_orders.js', 'utf8')}
this.PurchaseOrdersPage = PurchaseOrdersPage;`;

const opened = [];
const emailCalls = [];
const posts = [];
const navigations = [];

const lineRows = [{
    querySelector(selector) {
        const values = {
            '.line-item': { value: '2' },
            '.line-desc': { value: 'Pens' },
            '.line-qty': { value: '2' },
            '.line-gst': { value: 'GST15' },
            '.line-rate': { value: '15' },
        };
        return values[selector] || null;
    },
}];

const context = {
    console,
    Promise,
    setTimeout,
    API: {
        get: async (path) => {
            if (path === '/purchase-orders/9') return { id: 9, po_number: 'PO-0009', vendor_id: 1 };
            if (path === '/vendors/1') return { id: 1, name: 'Harbour Supplies', email: 'vendor@example.com' };
            throw new Error(`unexpected path ${path}`);
        },
        post: async (path, data) => {
            posts.push([path, data]);
            return { id: 9, po_number: 'PO-0009', vendor_id: 1, status: 'draft', lines: [] };
        },
        put: async () => { throw new Error('unexpected put'); },
        open: (path, filename) => opened.push([path, filename]),
    },
    App: {
        navigate: hash => navigations.push(hash),
        showDocumentEmailModal: payload => emailCalls.push(payload),
    },
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-17',
    gstOptionsHtml: () => '<option value="GST15">GST 15%</option>',
    readGstLinePayload: (row) => ({
        quantity: parseFloat(row.querySelector('.line-qty')?.value) || 0,
        rate: parseFloat(row.querySelector('.line-rate')?.value) || 0,
        gst_code: row.querySelector('.line-gst')?.value || 'GST15',
        gst_rate: 0.15,
    }),
    calculateGstTotals: () => ({ subtotal: 30, tax_amount: 4.5, total: 34.5 }),
    $: () => null,
    $$: selector => selector === '#po-lines tr' ? lineRows : [],
    toast() {},
};

vm.createContext(context);
vm.runInContext(code, context);

function makeForm() {
    return {
        vendor_id: { value: '1' },
        date: { value: '2026-04-17' },
        expected_date: { value: '2026-04-20' },
        ship_to: { value: '1 Queen Street\nAuckland Auckland 1010' },
        notes: { value: 'Handle with care' },
    };
}

(async () => {
    context.PurchaseOrdersPage._settings = { default_tax_rate: '15' };
    context.PurchaseOrdersPage._deliveryLocations = [{ label: 'HQ', value: '1 Queen Street\nAuckland Auckland 1010' }];
    context.PurchaseOrdersPage._detailState = { id: null, status: 'draft', po_number: '', vendor_id: '', date: '2026-04-17', expected_date: '', ship_to: '1 Queen Street\nAuckland Auckland 1010', notes: '', lines: [] };

    await context.PurchaseOrdersPage.save({ preventDefault() {}, target: makeForm() }, null, 'pdf');
    assert.strictEqual(posts.length, 1);
    assert.strictEqual(posts[0][0], '/purchase-orders');
    assert.deepStrictEqual(opened, [['/purchase-orders/9/pdf', 'purchase-order-PO-0009.pdf']]);
    assert.deepStrictEqual(navigations, ['#/purchase-orders/detail']);

    opened.length = 0;
    navigations.length = 0;

    await context.PurchaseOrdersPage.save({ preventDefault() {}, target: makeForm() }, null, 'email');
    assert.strictEqual(posts.length, 2);
    assert.deepStrictEqual(emailCalls.map(call => [call.endpoint, call.recipient]), [
        ['/purchase-orders/9/email', 'vendor@example.com'],
    ]);
    assert.deepStrictEqual(navigations, ['#/purchase-orders/detail']);
})().catch(err => {
    console.error(err);
    process.exit(1);
});
