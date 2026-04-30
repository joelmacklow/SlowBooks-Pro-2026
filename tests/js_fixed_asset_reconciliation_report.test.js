const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const reportsCode = fs.readFileSync('app/static/js/reports.js', 'utf8');

const context = {
    console,
    App: { settings: {} },
    opens: [],
    API: {
        get: async (path) => {
            if (path === '/reports/fixed-assets-reconciliation?as_of_date=2026-04-30') {
                return {
                    as_of_date: '2026-04-30',
                    assets: [{ asset_number: 'FA-0001', asset_name: 'Laptop Fleet', asset_type: 'Computer Equipment', purchase_date: '2026-04-01', purchase_price: 2000, accumulated_depreciation: 600, book_value: 1400 }],
                    total_cost: 2000,
                    total_accumulated_depreciation: 600,
                    total_book_value: 1400,
                };
            }
            throw new Error(`unexpected path ${path}`);
        },
        open: async (path, filename) => {
            context.opens.push({ path, filename });
        },
    },
    todayISO: () => '2026-04-23',
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
};

vm.createContext(context);
vm.runInContext(`${reportsCode}\nthis.ReportsPage = ReportsPage;`, context);

(async () => {
    const html = await context.ReportsPage.renderFixedAssetsReconciliationScreen();
    assert.ok(html.includes('Fixed Asset Reconciliation'));
    assert.ok(html.includes('Laptop Fleet'));
    assert.ok(html.includes('Totals'));
    assert.ok(html.includes('View / Print PDF'));
    context.ReportsPage.openReportPdf('fixed-assets-reconciliation');
    assert.deepStrictEqual(context.opens, [
        {
            path: '/reports/fixed-assets-reconciliation/pdf?as_of_date=2026-04-30',
            filename: 'FixedAssetReconciliation_2026-04-30.pdf',
        },
    ]);
})();
