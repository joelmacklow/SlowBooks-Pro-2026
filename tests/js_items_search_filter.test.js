const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const itemsCode = fs.readFileSync('app/static/js/items.js', 'utf8');

const apiCalls = [];
const tableWrap = { innerHTML: '' };
const pageContent = {
    innerHTML: '',
    querySelector(selector) {
        return selector === '#items-table-wrap' ? tableWrap : null;
    },
};

const context = {
    API: {
        get: async (path) => {
            apiCalls.push(path);
            if (path === '/items') {
                return [
                    { id: 1, code: '100-20', name: 'Pens', item_type: 'service', description: 'Blue pens', rate: 12.5, cost: 7.25 },
                    { id: 2, code: '200-10', name: 'Paper', item_type: 'product', description: 'A4 paper', rate: 6, cost: 2 },
                ];
            }
            if (path === '/items?search=Paper') {
                return [
                    { id: 2, code: '200-10', name: 'Paper', item_type: 'product', description: 'A4 paper', rate: 6, cost: 2 },
                ];
            }
            if (path === '/items?search=P') {
                return [
                    { id: 1, code: '100-20', name: 'Pens', item_type: 'service', description: 'Blue pens', rate: 12.5, cost: 7.25 },
                    { id: 2, code: '200-10', name: 'Paper', item_type: 'product', description: 'A4 paper', rate: 6, cost: 2 },
                ];
            }
            if (path === '/items?search=Pe') {
                return [
                    { id: 1, code: '100-20', name: 'Pens', item_type: 'service', description: 'Blue pens', rate: 12.5, cost: 7.25 },
                ];
            }
            if (path === '/items?search=100-20') {
                return [
                    { id: 1, code: '100-20', name: 'Pens', item_type: 'service', description: 'Blue pens', rate: 12.5, cost: 7.25 },
                ];
            }
            if (path === '/items?search=Missing') {
                return [];
            }
            throw new Error(`unexpected path ${path}`);
        },
    },
    App: { navigate() {}, hasPermission: () => true },
    openModal() {},
    closeModal() {},
    toast() {},
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    location: { hash: '#/items' },
    $: selector => selector === '#page-content' ? pageContent : null,
    console,
};

vm.createContext(context);
vm.runInContext(`${itemsCode}\nthis.ItemsPage = ItemsPage;`, context);

(async () => {
    const html = await context.ItemsPage.render();
    assert.ok(html.includes('placeholder="Search by code or name"'));
    assert.ok(html.includes('Pens'));
    assert.ok(html.includes('Paper'));
    assert.ok(html.includes('id="items-table-wrap"'));
    assert.strictEqual(apiCalls[0], '/items');

    await context.ItemsPage.applySearch('P');
    assert.strictEqual(apiCalls[1], '/items?search=P');
    assert.ok(tableWrap.innerHTML.includes('Pens'));
    assert.ok(tableWrap.innerHTML.includes('Paper'));

    await context.ItemsPage.applySearch('Pe');
    assert.strictEqual(apiCalls[2], '/items?search=Pe');
    assert.ok(tableWrap.innerHTML.includes('Pens'));
    assert.ok(!tableWrap.innerHTML.includes('Paper'));

    await context.ItemsPage.applySearch('Paper');
    assert.strictEqual(apiCalls[3], '/items?search=Paper');
    assert.ok(tableWrap.innerHTML.includes('Paper'));
    assert.ok(!tableWrap.innerHTML.includes('Pens'));

    await context.ItemsPage.applySearch('100-20');
    assert.strictEqual(apiCalls[4], '/items?search=100-20');
    assert.ok(tableWrap.innerHTML.includes('Pens'));

    await context.ItemsPage.applySearch('Missing');
    assert.strictEqual(apiCalls[5], '/items?search=Missing');
    assert.ok(tableWrap.innerHTML.includes('No items match this search'));
})();
