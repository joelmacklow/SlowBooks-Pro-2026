const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/timesheets_self_service.js', 'utf8')}\nthis.TimesheetSelfServicePage = TimesheetSelfServicePage;`;

function buildContext({ hash = '#/my-timesheets', timesheets = [] } = {}) {
    const posts = [];
    const navigations = [];
    const context = {
        console,
        Promise,
        location: { hash },
        URLSearchParams,
        API: {
            get: async (path) => {
                if (path === '/timesheets/self') return timesheets;
                throw new Error(`unexpected get ${path}`);
            },
            post: async (path, payload) => {
                posts.push([path, payload]);
                return { id: 99 };
            },
            put: async () => { throw new Error('unexpected put'); },
            download: async () => { throw new Error('unexpected download'); },
        },
        App: { navigate: (hashValue) => navigations.push(hashValue) },
        toast() {},
        escapeHtml: value => String(value || ''),
        formatDate: value => String(value || ''),
        formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
        document: {
            getElementById: () => null,
        },
    };
    vm.createContext(context);
    vm.runInContext(code, context);
    return { context, posts, navigations };
}

function makeRow(values) {
    const fields = {
        'input[name="work_date"]': { value: values.work_date || '2026-04-01' },
        'input[name="start_time"]': { value: values.start_time || '' },
        'input[name="end_time"]': { value: values.end_time || '' },
        'input[name="break_hours"]': { value: String(values.break_hours ?? '0') },
        'input[name="calculated_hours"]': { value: values.calculated_hours || '' },
        'input[name="notes"]': { value: values.notes || '' },
    };
    return {
        querySelector(selector) {
            return fields[selector] || null;
        },
    };
}

(async () => {
    {
        const { context } = buildContext();
        const html = await context.TimesheetSelfServicePage.renderTimesheets();
        assert.ok(html.includes('Enter start/end times with break hours'));
        assert.ok(html.includes('name="start_time"'));
        assert.ok(html.includes('name="end_time"'));
        assert.ok(html.includes('name="break_hours"'));
        assert.ok(html.includes('name="calculated_hours"'));
        assert.ok(!html.includes('name="duration_hours"'));
        assert.ok(!html.includes('name="entry_mode"'));
        assert.ok(html.includes('readonly'));
        assert.ok(html.includes('Break (hrs)'));
        assert.ok(html.includes('timesheet-lines-table'));
    }

    {
        const { context, posts, navigations } = buildContext();
        const tableRow = makeRow({
            work_date: '2026-04-01',
            start_time: '08:00',
            end_time: '16:30',
            break_hours: 0.5,
            notes: 'Shift',
        });
        context.document.getElementById = (id) => {
            if (id === 'self-timesheet-create-lines') {
                return {
                    querySelectorAll() {
                        return [tableRow];
                    },
                };
            }
            return null;
        };

        context.TimesheetSelfServicePage.refreshLineCalculation(tableRow);
        assert.strictEqual(tableRow.querySelector('input[name="calculated_hours"]').value, '8.00');

        await context.TimesheetSelfServicePage.createTimesheet({
            preventDefault() {},
            target: {
                period_start: { value: '2026-04-01' },
                period_end: { value: '2026-04-07' },
            },
        });

        assert.strictEqual(posts.length, 1);
        assert.strictEqual(posts[0][0], '/timesheets/self');
        assert.strictEqual(posts[0][1].period_start, '2026-04-01');
        assert.strictEqual(posts[0][1].lines[0].start_time, '08:00');
        assert.strictEqual(posts[0][1].lines[0].end_time, '16:30');
        assert.strictEqual(posts[0][1].lines[0].break_minutes, 30);
        assert.strictEqual(posts[0][1].lines[0].entry_mode, 'start_end');
        assert.ok(!Object.prototype.hasOwnProperty.call(posts[0][1].lines[0], 'duration_hours'));
        assert.deepStrictEqual(navigations, ['#/my-timesheets?id=99']);
    }
})().catch(err => {
    console.error(err);
    process.exit(1);
});
