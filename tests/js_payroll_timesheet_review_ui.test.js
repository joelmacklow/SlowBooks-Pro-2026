const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function createPayrollContext(overrides = {}) {
    const calls = [];
    let modalHtml = '';
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
                        lines: [{ work_date: '2026-04-01', entry_mode: 'duration', duration_hours: '8.00', notes: 'Shift' }],
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
            navigate() {},
            hasPermission(permission) {
                if (overrides.permissions) return overrides.permissions.includes(permission);
                return true;
            },
            confirmAction: async () => true,
        },
        todayISO: () => '2026-04-01',
        formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
        formatDate: value => String(value || ''),
        escapeHtml: value => String(value || ''),
        openModal: (_title, html) => { modalHtml = html; },
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
    return { context, calls, getModalHtml: () => modalHtml, elements };
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
    assert.ok(admin.calls.some(([kind, path]) => kind === 'get' && path.includes('/timesheets/periods?period_start=2026-04-01&period_end=2026-04-07')));
    assert.ok(admin.getModalHtml().includes('Submitted'));

    await admin.context.PayrollPage.showTimesheetPayRunReview(2);
    assert.ok(admin.calls.some(([kind, path]) => kind === 'get' && path === '/timesheets/pay-runs/2'));
    assert.ok(admin.getModalHtml().includes('Submitted'));

    await admin.context.PayrollPage.showTimesheetDetail(5);
    assert.ok(admin.calls.some(([kind, path]) => kind === 'get' && path === '/timesheets/5'));
    assert.ok(admin.getModalHtml().includes('Correct'));
    assert.ok(admin.getModalHtml().includes('Audit'));

    await admin.context.PayrollPage.showTimesheetAudit(5);
    assert.ok(admin.calls.some(([kind, path]) => kind === 'get' && path === '/timesheets/5/audit'));
    assert.ok(admin.getModalHtml().includes('create'));

    admin.elements['timesheet-correction-lines-5'] = {
        querySelectorAll() {
            return [{
                querySelector(selector) {
                    const values = {
                        'input[name="work_date"]': { value: '2026-04-01' },
                        'select[name="entry_mode"]': { value: 'duration' },
                        'input[name="duration_hours"]': { value: '8.25' },
                        'input[name="start_time"]': { value: '' },
                        'input[name="end_time"]': { value: '' },
                        'input[name="break_minutes"]': { value: '0' },
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
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'put' && path === '/timesheets/5' && payload.lines[0].duration_hours === '8.25'));

    await admin.context.PayrollPage.approveTimesheet(5);
    assert.ok(admin.calls.some(([kind, path]) => kind === 'post' && path === '/timesheets/5/approve'));

    await admin.context.PayrollPage.rejectTimesheet(5);
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'post' && path === '/timesheets/5/reject' && payload.reason === 'Needs adjustment'));

    await admin.context.PayrollPage.bulkApproveTimesheets([11, 12]);
    assert.ok(admin.calls.some(([kind, path, payload]) => kind === 'post' && path === '/timesheets/bulk-approve' && payload.timesheet_ids.length === 2));

    admin.context.PayrollPage.exportTimesheetPeriodCsv('2026-04-01', '2026-04-07');
    assert.ok(admin.calls.some(([kind, path, filename]) => kind === 'open' && path === '/timesheets/export?period_start=2026-04-01&period_end=2026-04-07' && filename === 'Timesheets_2026-04-01_2026-04-07.csv'));
})().catch(err => {
    console.error(err);
    process.exit(1);
});
