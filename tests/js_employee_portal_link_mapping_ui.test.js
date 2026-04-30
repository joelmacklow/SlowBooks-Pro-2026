const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/employees.js', 'utf8')}\nthis.EmployeesPage = EmployeesPage;`;
let modalHtml = '';
const calls = [];
class FakeFormData {
    constructor(form) {
        this.form = form || { _formData: {} };
    }
    *entries() {
        for (const [key, value] of Object.entries(this.form._formData || {})) {
            yield [key, value];
        }
    }
}

const context = {
    API: {
        get: async (path) => {
            calls.push(['get', path]);
            if (path === '/employees/7') {
                return {
                    id: 7,
                    first_name: 'Aroha',
                    last_name: 'Ngata',
                    ird_number: '123',
                    pay_type: 'salary',
                    pay_rate: 78000,
                    tax_code: 'M',
                    kiwisaver_enrolled: true,
                    kiwisaver_rate: '0.0350',
                    student_loan: false,
                    child_support: false,
                    child_support_amount: '0.00',
                    esct_rate: '0.1750',
                    pay_frequency: 'fortnightly',
                    address1: '',
                    address2: '',
                    city: '',
                    state: '',
                    zip: '',
                    start_date: '2026-04-01',
                    end_date: '',
                };
            }
            if (path === '/employee-portal/links') {
                return [{
                    id: 11,
                    is_active: true,
                    employee: { id: 7, first_name: 'Aroha', last_name: 'Ngata' },
                    user: { id: 100, full_name: 'Aroha User', email: 'aroha@example.com' },
                }];
            }
            if (path === '/auth/users') {
                return [
                    {
                        id: 100,
                        email: 'aroha@example.com',
                        full_name: 'Aroha User',
                        is_active: true,
                        membership: { is_active: true, role_key: 'employee_self_service' },
                    },
                    {
                        id: 101,
                        email: 'wiremu@example.com',
                        full_name: 'Wiremu User',
                        is_active: true,
                        membership: { is_active: true, role_key: 'employee_self_service' },
                    },
                ];
            }
            throw new Error(`unexpected get ${path}`);
        },
        put: async (path, data) => {
            calls.push(['put', path, data]);
            if (path === '/employees/7') return { id: 7 };
            throw new Error(`unexpected put ${path}`);
        },
        post: async (path, data) => {
            calls.push(['post', path, data]);
            if (path === '/employee-portal/links/11/deactivate') return { status: 'ok' };
            if (path === '/employee-portal/links') return { id: 42 };
            throw new Error(`unexpected post ${path}`);
        },
    },
    App: {
        hasPermission(permission) { return permission === 'users.manage'; },
        navigate() {},
    },
    FormData: FakeFormData,
    closeModal() {},
    openModal(_title, html) { modalHtml = html; },
    todayISO: () => '2026-04-01',
    toast() {},
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    escapeHtml: value => String(value || ''),
    console,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.EmployeesPage.showForm(7);
    assert.ok(modalHtml.includes('Self-Service Login Mapping'));
    assert.ok(modalHtml.includes('name="portal_user_id"'));
    assert.ok(modalHtml.includes('Aroha User'));
    assert.ok(modalHtml.includes('Wiremu User'));

    await context.EmployeesPage.save({
        preventDefault() {},
        target: {
            _formData: {
                first_name: 'Aroha',
                last_name: 'Ngata',
                ird_number: '123',
                pay_type: 'salary',
                pay_rate: '78000',
                tax_code: 'M',
                kiwisaver_enrolled: 'true',
                kiwisaver_rate: '0.0350',
                student_loan: 'false',
                child_support: 'false',
                child_support_amount: '0.00',
                esct_rate: '0.1750',
                pay_frequency: 'fortnightly',
                address1: '',
                address2: '',
                city: '',
                state: '',
                zip: '',
                start_date: '2026-04-01',
                end_date: '',
                portal_user_id: '101',
            },
        },
    }, 7);

    assert.ok(calls.some(([method, path]) => method === 'put' && path === '/employees/7'));
    assert.ok(calls.some(([method, path]) => method === 'post' && path === '/employee-portal/links/11/deactivate'));
    assert.ok(calls.some(([method, path, payload]) => method === 'post' && path === '/employee-portal/links' && payload.user_id === 101 && payload.employee_id === 7));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
