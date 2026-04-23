const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const fixedAssetsCode = fs.readFileSync('app/static/js/fixed_assets.js', 'utf8');

const context = {
    console,
    location: { hash: '#/fixed-assets' },
    __navigations: [],
    __detailOrigins: [],
    API: {
        get: async (path) => {
            if (path === '/fixed-assets') {
                return [
                    { id: 1, name: 'BMW 123D', asset_type_name: 'Motor Vehicles', purchase_date: '2024-09-02', purchase_price: 6082.61, book_value: 3512.70, status: 'registered' },
                ];
            }
            if (path === '/fixed-assets/types') {
                return [
                    {
                        id: 10,
                        name: 'Motor Vehicles',
                        asset_account: { account_number: '730', name: 'Motor Vehicles' },
                        accumulated_depreciation_account: { account_number: '731', name: 'Less Accumulated Depreciation' },
                        depreciation_expense_account: { account_number: '416', name: 'Depreciation' },
                    },
                ];
            }
            if (path === '/accounts?active_only=true') return [];
            if (path === '/fixed-assets/1') {
                return {
                    id: 1,
                    asset_number: 'FA-0051',
                    name: 'BMW 123D',
                    status: 'registered',
                    purchase_date: '2024-09-02',
                    purchase_price: 6082.61,
                    depreciation_start_date: '2024-09-02',
                    depreciation_method: 'dv',
                    calculation_basis: 'rate',
                    rate: 30,
                    effective_life_years: null,
                    residual_value: 0,
                    opening_accumulated_depreciation: 0,
                    serial_number: '',
                    warranty_expiry: null,
                    description: '',
                    source_reference: '',
                    asset_type: { id: 10, name: 'Motor Vehicles' },
                    asset_account: { account_number: '730', name: 'Motor Vehicles' },
                    accumulated_depreciation_account: { account_number: '731', name: 'Less Accumulated Depreciation' },
                    depreciation_expense_account: { account_number: '416', name: 'Depreciation' },
                    book_value_detail: { cost_basis: 6082.61, book_value: 3512.70, accumulated_depreciation: 2569.91, ytd_depreciation: 1505.45 },
                };
            }
            throw new Error(`unexpected path ${path}`);
        },
    },
    App: {
        navigate(hash) { context.__navigations.push(hash); },
        setDetailOrigin(detailHash, originHash) { context.__detailOrigins.push([detailHash, originHash]); },
        detailBackLabel() { return 'Back to Fixed Assets'; },
    },
    openModal() {},
    closeModal() {},
    toast() {},
    todayISO: () => '2026-04-23',
    URLSearchParams,
    escapeHtml: value => {
        if (!value) return '';
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    },
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    formatDate: value => String(value || ''),
    FormData,
    document: { createElement: () => ({ click() {} }) },
};

vm.createContext(context);
vm.runInContext(`${fixedAssetsCode}\nthis.FixedAssetsPage = FixedAssetsPage;\nthis.__fixedAssetsGlobalMatch = (typeof globalThis !== 'undefined' && globalThis.FixedAssetsPage === FixedAssetsPage);`, context);

(async () => {
    assert.strictEqual(context.__fixedAssetsGlobalMatch, true);
    const listHtml = await context.FixedAssetsPage.render();
    assert.ok(listHtml.includes('Register Asset'));
    assert.ok(listHtml.includes('BMW 123D'));
    assert.ok(listHtml.includes('Asset Types & Account Mapping'));
    assert.ok(listHtml.includes('onclick="FixedAssetsPage.openAssetDetail(1)"'));

    context.FixedAssetsPage.openAssetDetail(1);
    assert.deepStrictEqual(context.__detailOrigins, [['#/fixed-assets/detail?id=1', '#/fixed-assets']]);
    assert.deepStrictEqual(context.__navigations, ['#/fixed-assets/detail?id=1']);

    context.location.hash = '#/fixed-assets/detail?id=1';
    const detailHtml = await context.FixedAssetsPage.renderDetailScreen();
    assert.ok(detailHtml.includes('Current book value') === false);
    assert.ok(detailHtml.includes('Book depreciation settings'));
    assert.ok(detailHtml.includes('Sell / Dispose'));
    assert.ok(detailHtml.includes('Current Earnings') === false);
    assert.ok(detailHtml.includes('onclick="FixedAssetsPage.openEditAssetForm(1)"'));

    const editCalls = [];
    context.FixedAssetsPage.showAssetForm = async (id) => { editCalls.push(id); };
    await context.FixedAssetsPage.openEditAssetForm(1);
    assert.deepStrictEqual(editCalls, [1]);

    const toasts = [];
    context.toast = (message, tone) => { toasts.push([message, tone]); };
    context.FixedAssetsPage.showAssetForm = async () => { throw new Error('boom'); };
    await context.FixedAssetsPage.openEditAssetForm(1);
    assert.deepStrictEqual(toasts, [['boom', 'error']]);
})();
