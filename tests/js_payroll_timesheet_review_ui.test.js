const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function createPayrollContext(overrides = {}) {
    const calls = [];
    const navigations = [];
    const backLabelCalls = [];
    const elements = {};
    const context = {
        API: {
            get: async (path) => {
                calls.push(['get', path]);
                if (path === '/payroll') {
                    return [
                        { id: 1, status: 'draft', tax_year: 2027, pay_date: '2026-04-15', total_gross: 4200, total_net: 2922.13, total_taxes: 1277.87, stubs: [] },
                        { id: 2, status: 'processed', tax_year: 2027, pay_date: '2026-04-29', total_gross: 4200, total_net: 2922.13, total_taxes: 1277.87, stubs: [] },
                    ];
                }
                if (path === '/employees?active_only=true') {
                    return [{ id: 1, first_name: 'Aroha', last_name: 'Ngata', pay_type: 'salary', pay_frequency: 'fortnightly' }];
                }
                if (path === '/payroll/2/filing/history') {
                    return [{ filing_type: 'employment_information', status: 'generated', changed_since_source: false }];
                }
                if (path.startsWith('/timesheets/periods?')) {
                    return {
                        period_start: '2026-04-01',
                        period_end: '2026-04-07',
                        submitted: [{ id: 11, employee_id: 7, period_start: '2026-04-01', period_end: '2026-04-07', status: 'submitted', total_hours: '8.00' }],
                        approved: [{ id: 12, employee_id: 8, period_start: '2026-04-01', period_end: '2026-04-07', status: 'approved', total_hours: '7.50' }],
                        draft: [],
                        rejected: [],
                        locked: [],
                    };
                }
                if (path === '/timesheets/pay-runs/2') {
                    return {
                        period_start: '2026-04-01',
                        period_end: '2026-04-07',
                        pay_run_id: 2,
                        submitted: [{ id: 21, employee_id: 9, period_start: '2026-04-01', period_end: '2026-04-07', status: 'submitted', total_hours: '8.00' }],
                        approved: [],
                        draft: [],
                        rejected: [],
                        locked: [],
                    };
                }
                if (path === '/timesheets/5') {
                    return {
                        id: 5,
                        period_start: '2026-04-01',
                        period_end: '2026-04-07',
                        status: 'submitted',
                        total_hours: '8.00',
                        lines: [{ work_date: '2026-04-01', entry_mode: 'start_end', start_time: '2026-04-01T08:00:00', end_time: '2026-04-01T16:30:00', break_minutes: 30, notes: 'Shift' }],
                        audit_events: [{ id: 1, action: 'create', status_from: null, status_to: 'draft', reason: null }],
                    };
                }
                if (path === '/timesheets/5/audit') {
                    return [{ id: 1, action: 'create', status_from: null, status_to: 'draft', reason: null }];
                }
                throw new Error(`unexpected get ${path}`);
            },
            post: async (path, payload) => {
                calls.push(['post', path, payload]);
                return {};
            },
            put: async (path, payload) => {
                calls.push(['put', path, payload]);
                return {};
            },
            open: (path, filename) => {
                calls.push(['open', path, filename]);
            },
            download: async () => {},
        },
        App: {
            navigate(hash) {
                navigations.push(['navigate', hash]);
                context.location.hash = hash;
            },
            openDetail(detailHash, originHash) {
                navigations.push(['openDetail', detailHash, originHash]);
                context.location.hash = detailHash;
            },
            detailBackLabel(detailHash, fallbackHash, fallbackLabel = 'Previous') {
                backLabelCalls.push([detailHash, fallbackHash, fallbackLabel]);
                if (fallbackHash === '#/payroll') return 'Back to Payroll';
                if (String(fallbackHash || '').includes('mode=detail')) return 'Back to Timesheet Detail';
                return 'Back to Timesheet Review';
            },
            navigateBackToDetailOrigin(detailHash, fallbackHash) {
                navigations.push(['back', detailHash, fallbackHash]);
                context.location.hash = detailHash;
            },
            hasPermission(permission) {
                if (overrides.permissions) return overrides.permissions.includes(permission);
                return true;
            },
            confirmAction: async () => true,
        },
        location: { hash: '#/payroll' },
        todayISO: () => '2026-04-01',
        formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
        formatDate: value => String(value || ''),
        escapeHtml: value => String(value || ''),
        openModal() {},
        closeModal() {},
        toast() {},
        confirm: () => true,
        prompt: () => 'Needs adjustment',
        document: {
            getElementById(id) {
                return elements[id] || null;
            },
        },
        $: (selector) => {
            if (selector && selector.startsWith('#')) {
                return elements[selector.slice(1)] || null;
            }
            return null;
        },
        $$: () => [],
        console,
    };
    vm.createContext(context);
    const code = `${fs.readFileSync('app/static/js/payroll.js', 'utf8')}\nthis.PayrollPage = PayrollPage;`;
    vm.runInContext(code, context);
    return { context, calls, navigations, backLabelCalls, getHash: () => context.location.hash, elements };
}

(async () => {
    const admin = createPayrollContext({ permissions: ['payroll.view', 'payroll.create', 'payroll.process', 'timesheets.manage', 'timesheets.approve', 'timesheets.export'] });
    const adminHtml = await admin.context.PayrollPage.render();
    assert.ok(adminHtml.includes('Timesheet Review'));
    assert.ok(adminHtml.includes('Review Period'));
    assert.ok(adminHtml.includes('Export CSV'));
    assert.ok(adminHtml.includes('Timesheets'));
    assert.ok(adminHtml.includes('New Pay Run'));
    assert.ok(admin.calls.some(([kind, path]) => kind === 'get' && path === '/payroll'));
    assert.ok(admin.calls.some(([kind, path]) => kind === 'get' && path === '/employees?active_only=true'));

    const viewer = createPayrollContext({ permissions: ['payroll.view', 'payroll.create', 'payroll.process'] });
    const viewerHtml = await viewer.context.PayrollPage.render();
    assert.ok(!viewerHtml.includes('Timesheet Review'));
    assert.ok(!viewerHtml.includes('Timesheets'));

    admin.elements['timesheet-review-period-start'] = { value: '2026-04-01' };
    admin.elements['timesheet-review-period-end'] = { value: '2026-04-07' };
    await admin.context.PayrollPage.showTimesheetPeriodReview();
    assert.deepStrictEqual(admin.navigations.pop(), ['openDetail', '#/payroll/timesheets?mode=period&period_start=2026-04-01&period_end=2026-04-07', '#/payroll']);
    assert.strictEqual(admin.getHash(), '#/payroll/timesheets?mode=period&period_start=2026-04-01&period_end=2026-04-07');
    let html = await admin.context.PayrollPage.renderTimesheetReviewScreen();
    assert.ok(html.includes('Timesheet Review'));
    assert.ok(html.includes('Period 2026-04-01 → 2026-04-07'));
    assert.ok(html.includes('Review Period'));
    assert.ok(html.includes('Export CSV'));
    assert.ok(html.includes('Bulk Approve Submitted'));
    assert.ok(html.includes('PayrollPage.showTimesheetDetail(11)'));
    assert.deepStrictEqual(admin.backLabelCalls.pop(), ['#/payroll/timesheets?mode=period&period_start=2026-04-01&period_end=2026-04-07', '#/payroll', 'Payroll']);

    await admin.context.PayrollPage.bulkApproveTimesheets([11, 12]);
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'post' && path === '/timesheets/bulk-approve' && payload.timesheet_ids.length === 2));
    assert.strictEqual(admin.getHash(), '#/payroll/timesheets?mode=period&period_start=2026-04-01&period_end=2026-04-07');
    admin.context.PayrollPage.exportTimesheetPeriodCsv('2026-04-01', '2026-04-07');
    assert.ok(admin.calls.some(([kind, path, filename]) => kind === 'open' && path === '/timesheets/export?period_start=2026-04-01&period_end=2026-04-07' && filename === 'Timesheets_2026-04-01_2026-04-07.csv'));

    await admin.context.PayrollPage.showTimesheetPayRunReview(2);
    assert.deepStrictEqual(admin.navigations.pop(), ['openDetail', '#/payroll/timesheets?mode=payrun&run_id=2', '#/payroll']);
    assert.strictEqual(admin.getHash(), '#/payroll/timesheets?mode=payrun&run_id=2');
    html = await admin.context.PayrollPage.renderTimesheetReviewScreen();
    assert.ok(html.includes('Timesheet Review — Pay Run 2'));
    assert.ok(html.includes('PayrollPage.showTimesheetDetail(21)'));
    assert.deepStrictEqual(admin.backLabelCalls.pop(), ['#/payroll/timesheets?mode=payrun&run_id=2', '#/payroll', 'Payroll']);

    await admin.context.PayrollPage.showTimesheetDetail(5);
    assert.deepStrictEqual(admin.navigations.pop(), ['openDetail', '#/payroll/timesheets?mode=detail&id=5', '#/payroll/timesheets?mode=payrun&run_id=2']);
    assert.strictEqual(admin.getHash(), '#/payroll/timesheets?mode=detail&id=5');
    html = await admin.context.PayrollPage.renderTimesheetReviewScreen();
    assert.ok(html.includes('Timesheet #5'));
    assert.ok(html.includes('Correct'));
    assert.ok(html.includes('Approve'));
    assert.ok(html.includes('Reject'));
    assert.ok(html.includes('Open Audit'));
    assert.ok(html.includes('timesheet-lines-table'));
    assert.ok(html.includes('create'));
    assert.deepStrictEqual(admin.backLabelCalls.pop(), ['#/payroll/timesheets?mode=detail&id=5', '#/payroll/timesheets?mode=period', 'Timesheet Review']);

    await admin.context.PayrollPage.openTimesheetCorrection(5);
    assert.deepStrictEqual(admin.navigations.pop(), ['openDetail', '#/payroll/timesheets?mode=correct&id=5', '#/payroll/timesheets?mode=detail&id=5']);
    assert.strictEqual(admin.getHash(), '#/payroll/timesheets?mode=correct&id=5');
    html = await admin.context.PayrollPage.renderTimesheetReviewScreen();
    assert.ok(html.includes('Correct Timesheet #5'));
    assert.ok(html.includes('Reason'));
    assert.ok(html.includes('Save Correction'));
    assert.ok(html.includes('Add Line'));
    assert.ok(html.includes("App.navigateBackToDetailOrigin('#/payroll/timesheets?mode=correct&id=5', '#/payroll/timesheets?mode=detail&id=5')"));
    assert.deepStrictEqual(admin.backLabelCalls.pop(), ['#/payroll/timesheets?mode=correct&id=5', '#/payroll/timesheets?mode=detail&id=5', 'Timesheet Detail']);

    await admin.context.PayrollPage.showTimesheetAudit(5);
    assert.deepStrictEqual(admin.navigations.pop(), ['openDetail', '#/payroll/timesheets?mode=audit&id=5', '#/payroll/timesheets?mode=correct&id=5']);
    assert.strictEqual(admin.getHash(), '#/payroll/timesheets?mode=audit&id=5');
    html = await admin.context.PayrollPage.renderTimesheetReviewScreen();
    assert.ok(html.includes('Timesheet Audit #5'));
    assert.ok(html.includes('create'));
    assert.deepStrictEqual(admin.backLabelCalls.pop(), ['#/payroll/timesheets?mode=audit&id=5', '#/payroll/timesheets?mode=period', 'Timesheet Review']);

    admin.elements['timesheet-correction-lines-5'] = {
        querySelectorAll() {
            return [{
                querySelector(selector) {
                    const values = {
                        'input[name="work_date"]': { value: '2026-04-01' },
                        'input[name="start_time"]': { value: '08:00' },
                        'input[name="end_time"]': { value: '16:30' },
                        'input[name="break_hours"]': { value: '0.50' },
                        'input[name="calculated_hours"]': { value: '8.00' },
                        'input[name="notes"]': { value: 'Adjusted' },
                    };
                    return values[selector] || null;
                },
            }];
        },
    };
    await admin.context.PayrollPage.submitTimesheetCorrection(
        { preventDefault() {}, target: { reason: { value: 'Adjusted after review' } } },
        5,
    );
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'put' && path === '/timesheets/5' && payload.reason === 'Adjusted after review'));
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'put' && path === '/timesheets/5' && payload.lines[0].start_time === '08:00'));
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'put' && path === '/timesheets/5' && payload.lines[0].end_time === '16:30'));
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'put' && path === '/timesheets/5' && payload.lines[0].break_minutes === 30));
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'put' && path === '/timesheets/5' && payload.lines[0].entry_mode === 'start_end'));
    assert.strictEqual(admin.getHash(), '#/payroll/timesheets?mode=detail&id=5');
    assert.ok(admin.navigations.some(([kind, hash]) => kind === 'navigate' && hash === '#/payroll/timesheets?mode=detail&id=5'));

    await admin.context.PayrollPage.approveTimesheet(5);
    assert.ok(admin.calls.some(([kind, path]) => kind === 'post' && path === '/timesheets/5/approve'));

    await admin.context.PayrollPage.rejectTimesheet(5);
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'post' && path === '/timesheets/5/reject' && payload.reason === 'Needs adjustment'));

    await admin.context.PayrollPage.bulkApproveTimesheets([11, 12]);
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'post' && path === '/timesheets/bulk-approve' && payload.timesheet_ids.length === 2));
})().catch(err => {
    console.error(err);
    process.exit(1);
});
