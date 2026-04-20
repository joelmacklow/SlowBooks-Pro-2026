const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const itemsCode = fs.readFileSync('app/static/js/items.js', 'utf8');
const purchaseOrdersCode = fs.readFileSync('app/static/js/purchase_orders.js', 'utf8');

let itemModalHtml = '';
const itemPosts = [];

const itemContext = {
    API: {
        get: async (path) => {
            if (path === '/accounts') {
                return [
                    { id: 10, account_type: 'income', account_number: '200', name: 'Sales' },
                    { id: 11, account_type: 'expense', account_number: '500', name: 'Supplies' },
                ];
            }
            if (path === '/vendors?active_only=true') {
                return [
                    { id: 1, name: 'Harbour Supplies' },
                    { id: 2, name: 'Office Goods' },
                ];
            }
            throw new Error(`unexpected path ${path}`);
        },
        post: async (path, data) => {
            itemPosts.push([path, data]);
            return { id: 7, ...data };
        },
        put: async () => ({}),
    },
    App: { navigate() {}, hasPermission: () => true },
    openModal: (_title, html) => { itemModalHtml = html; },
    closeModal() {},
    toast() {},
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    location: { hash: '#/items' },
    FormData: class {
        constructor(target) { this.target = target; }
        entries() { return Object.entries(this.target.data); }
    },
    console,
};

vm.createContext(itemContext);
vm.runInContext(`${itemsCode}\nthis.ItemsPage = ItemsPage;`, itemContext);

const poCode = `${purchaseOrdersCode}\nthis.PurchaseOrdersPage = PurchaseOrdersPage;`;
const poContext = {
    console,
    Promise,
    setTimeout,
    API: {
        get: async (path) => {
            if (path === '/purchase-orders') return [];
            if (path === '/vendors?active_only=true') return [{ id: 1, name: 'Harbour Supplies' }, { id: 2, name: 'Office Goods' }];
            if (path === '/items?active_only=true') {
                return [
                    { id: 2, code: '100-20', name: 'Pens', description: 'Pens', cost: 15, vendor_id: 1 },
                    { id: 3, code: '200-10', name: 'Paper', description: 'Paper', cost: 6, vendor_id: 2 },
                    { id: 4, code: '300-01', name: 'Stapler', description: 'Stapler', cost: 12, vendor_id: null },
                ];
            }
            if (path === '/settings/public') return { default_tax_rate: '15', prices_include_gst: 'false' };
            if (path === '/gst-codes') return [{ code: 'GST15', rate: 0.15, name: 'GST 15%' }];
            if (path === '/purchase-orders/delivery-locations') return [{ label: 'HQ', value: '1 Queen Street\nAuckland Auckland 1010' }];
            throw new Error(`unexpected path ${path}`);
        },
        post: async () => ({}),
        put: async () => ({}),
        open() {},
    },
    App: {
        navigate() {},
        hasPermission: () => true,
        gstCodes: [],
        settings: { prices_include_gst: 'false' },
        showDocumentEmailModal() {},
    },
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-17',
    gstOptionsHtml: () => '<option value="GST15">GST 15%</option>',
    readGstLinePayload: () => ({ quantity: 1, rate: 0, gst_code: 'GST15', gst_rate: 0.15 }),
    calculateGstTotals: () => ({ subtotal: 0, tax_amount: 0, total: 0 }),
    $: () => null,
    $$: () => [],
    confirm: () => true,
    toast() {},
};

vm.createContext(poContext);
vm.runInContext(poCode, poContext);

(async () => {
    await itemContext.ItemsPage.showForm();
    assert.ok(itemModalHtml.includes('<label>Code</label>'));
    assert.ok(itemModalHtml.includes('<label>Preferred Vendor</label>'));
    assert.ok(itemModalHtml.includes('Harbour Supplies'));

    await itemContext.ItemsPage.save({
        preventDefault() {},
        target: {
            code: { value: '100-20' },
            name: { value: 'Pens' },
            item_type: { value: 'service' },
            description: { value: 'Blue pens' },
            rate: { value: '12.5' },
            cost: { value: '7.25' },
            income_account_id: { value: '10' },
            expense_account_id: { value: '11' },
            vendor_id: { value: '1' },
            is_taxable: { checked: true },
        },
    }, null);
    assert.strictEqual(itemPosts.length, 1);
    assert.strictEqual(itemPosts[0][0], '/items');
    assert.strictEqual(itemPosts[0][1].code, '100-20');
    assert.strictEqual(itemPosts[0][1].name, 'Pens');
    assert.strictEqual(itemPosts[0][1].item_type, 'service');
    assert.strictEqual(itemPosts[0][1].description, 'Blue pens');
    assert.strictEqual(itemPosts[0][1].rate, 12.5);
    assert.strictEqual(itemPosts[0][1].cost, 7.25);
    assert.strictEqual(itemPosts[0][1].income_account_id, 10);
    assert.strictEqual(itemPosts[0][1].expense_account_id, 11);
    assert.strictEqual(itemPosts[0][1].vendor_id, 1);
    assert.strictEqual(itemPosts[0][1].is_taxable, true);

    await poContext.PurchaseOrdersPage._loadEditorContext(null);
    poContext.PurchaseOrdersPage._detailState.vendor_id = 1;
    const vendorOneLine = poContext.PurchaseOrdersPage.lineHtml(0, { item_id: '', description: '', quantity: 1, rate: 0, gst_code: 'GST15' }, poContext.PurchaseOrdersPage._itemsForVendor(1), true);
    assert.ok(vendorOneLine.includes('Pens'));
    assert.ok(vendorOneLine.includes('100-20'));
    assert.ok(!vendorOneLine.includes('Paper'));

    poContext.PurchaseOrdersPage._detailState.vendor_id = 2;
    const vendorTwoLine = poContext.PurchaseOrdersPage.lineHtml(0, { item_id: '', description: '', quantity: 1, rate: 0, gst_code: 'GST15' }, poContext.PurchaseOrdersPage._itemsForVendor(2), true);
    assert.ok(vendorTwoLine.includes('Paper'));
    assert.ok(vendorTwoLine.includes('200-10'));
    assert.ok(!vendorTwoLine.includes('Pens'));

    const byVendorAndCode = poContext.PurchaseOrdersPage._filteredItemsForLine(1, '100', null);
    assert.deepStrictEqual(byVendorAndCode.map(item => item.name), ['Pens']);
    const byVendorAndName = poContext.PurchaseOrdersPage._filteredItemsForLine(2, 'pap', null);
    assert.deepStrictEqual(byVendorAndName.map(item => item.name), ['Paper']);
})().catch(err => {
    console.error(err);
    process.exit(1);
});
