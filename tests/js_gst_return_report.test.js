const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/reports.js', 'utf8')}\nthis.ReportsPage = ReportsPage;`;
const calls = [];
const downloads = [];
const navigations = [];
const posts = [];
let gstReturnConfirmed = false;
const elements = {
    '#gst-box9-adjustments': { value: '5.00' },
    '#gst-box13-adjustments': { value: '2.00' },
};

const context = {
    console,
    Date,
    Math,
    Promise,
    setTimeout,
    URLSearchParams,
    API: {
        get: async (path) => {
            calls.push(path);
            if (path === '/reports/gst-return/overview') {
                return {
                    open_periods: [
                        {
                            start_date: '2026-04-01',
                            end_date: '2026-09-30',
                            period_label: '1 Apr 2026 - 30 Sep 2026',
                            due_date: '2026-10-28',
                            status: 'due',
                            box9_adjustments: '0.00',
                            box13_adjustments: '0.00',
                            net_gst: null,
                        },
                    ],
                    historical_groups: [
                        {
                            label: '2026 financial year',
                            returns: [
                                {
                                    start_date: '2025-10-01',
                                    end_date: '2026-03-31',
                                    period_label: '1 Oct 2025 - 31 Mar 2026',
                                    due_date: '2026-05-07',
                                    status: 'confirmed',
                                    box9_adjustments: '0.00',
                                    box13_adjustments: '0.00',
                                    net_gst: 15,
                                },
                            ],
                        },
                    ],
                };
            }
            if (path.startsWith('/reports/gst-return/transactions?')) {
                return {
                    page: 2,
                    page_size: 1,
                    total_count: 2,
                    total_pages: 2,
                    items: [
                        {
                            date: '2026-04-02',
                            source_type: 'invoice',
                            number: '1002',
                            name: 'Aroha Ltd',
                            standard_gross: 230,
                            zero_rated: 0,
                            excluded: 0,
                        },
                    ],
                };
            }
            if (path.startsWith('/reports/gst-return?')) {
                return {
                    start_date: '2026-04-01',
                    end_date: '2026-04-30',
                    gst_basis: 'invoice',
                    gst_period: 'two-monthly',
                    boxes: { 5: 115, 6: 0, 7: 115, 8: 15, 9: 5, 10: 20, 11: 0, 12: 0, 13: 2, 14: 2, 15: 18 },
                    net_position: 'payable',
                    output_gst: 20,
                    input_gst: 2,
                    net_gst: 18,
                    return_confirmation: gstReturnConfirmed
                        ? { status: 'confirmed', confirmed_at: '2026-05-01T10:00:00', due_date: '2026-05-28', box9_adjustments: '5.00', box13_adjustments: '2.00' }
                        : { status: 'draft', confirmed_at: null, due_date: '2026-05-28', box9_adjustments: '5.00', box13_adjustments: '2.00' },
                    settlement: gstReturnConfirmed
                        ? { status: 'unsettled', expected_bank_amount: -18, candidates: [] }
                        : { status: 'awaiting_return_confirmation', expected_bank_amount: -18, candidates: [] },
                };
            }
            throw new Error(`unexpected get ${path}`);
        },
        download: async (path, filename) => {
            downloads.push({ path, filename });
        },
        post: async (path, body) => {
            posts.push({ path, body });
            if (path === '/reports/gst-return/confirm') {
                gstReturnConfirmed = true;
                return { status: 'confirmed', confirmed_at: '2026-05-01T10:00:00', due_date: '2026-05-28', box9_adjustments: '5.00', box13_adjustments: '2.00' };
            }
            throw new Error(`unexpected post ${path}`);
        },
    },
    App: {
        navigate: (hash) => navigations.push(hash),
    },
    toast() {},
    $: (selector) => elements[selector],
    escapeHtml: (value) => String(value ?? ''),
    formatCurrency: (value) => `$${Number(value).toFixed(2)}`,
    formatDate: (value) => value,
    todayISO: () => '2026-04-30',
    location: { hash: '#/reports/gst-return' },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const html = await context.ReportsPage.render();
    assert.ok(html.includes('GST Return'));
    assert.ok(!html.includes('Sales Tax'));
    assert.ok(html.includes("ReportsPage.gstReturn()"));

    context.ReportsPage.gstReturn();
    assert.deepStrictEqual(navigations, ['#/reports/gst-return']);

    const overviewHtml = await context.ReportsPage.renderGstReturnsScreen();
    assert.ok(calls.includes('/reports/gst-return/overview'));
    assert.ok(overviewHtml.includes('Historical Returns'));
    assert.ok(overviewHtml.includes('2026 financial year'));
    assert.ok(overviewHtml.includes('1 Oct 2025 - 31 Mar 2026'));

    context.location.hash = '#/reports/gst-return/detail';
    context.ReportsPage._gstDetailState = {
        start_date: '2026-04-01',
        end_date: '2026-04-30',
        box9_adjustments: '5.00',
        box13_adjustments: '2.00',
        tab: 'summary',
        page: 1,
        page_size: 1,
    };
    let detailHtml = await context.ReportsPage.renderGstReturnDetailScreen();
    assert.ok(detailHtml.includes('Confirm GST Return'));
    assert.ok(detailHtml.includes('Download GST101A PDF'));
    assert.ok(detailHtml.includes('disabled'));
    assert.ok(detailHtml.includes('Awaiting return confirmation'));

    await context.ReportsPage.confirmGstReturn();
    assert.strictEqual(JSON.stringify(posts), JSON.stringify([
        {
            path: '/reports/gst-return/confirm',
            body: {
                start_date: '2026-04-01',
                end_date: '2026-04-30',
                box9_adjustments: '5.00',
                box13_adjustments: '2.00',
            },
        },
    ]));

    context.ReportsPage._gstDetailState.tab = 'transactions';
    context.ReportsPage._gstDetailState.page = 2;
    detailHtml = await context.ReportsPage.renderGstReturnDetailScreen();
    assert.ok(detailHtml.includes('Transactions'));
    assert.ok(detailHtml.includes('Showing 2-2 of 2'));
    assert.ok(calls.some(path => path.includes('/reports/gst-return/transactions?')));
    assert.ok(calls.some(path => path.includes('page=2')));
    assert.ok(calls.some(path => path.includes('page_size=1')));
    assert.ok(detailHtml.includes('1002'));

    context.ReportsPage._gstDetailState.tab = 'summary';
    detailHtml = await context.ReportsPage.renderGstReturnDetailScreen();
    assert.ok(detailHtml.includes('Return confirmed'));
    assert.ok(!detailHtml.includes('Confirm GST Return'));

    context.ReportsPage.downloadGstReturnPdf();
    assert.deepStrictEqual(downloads, [
        {
            path: '/reports/gst-return/pdf?start_date=2026-04-01&end_date=2026-04-30&box9_adjustments=5.00&box13_adjustments=2.00',
            filename: 'GST101A_2026-04-01_2026-04-30.pdf',
        },
    ]);
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
