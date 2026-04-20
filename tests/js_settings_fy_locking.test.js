const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/settings.js', 'utf8')}\nthis.SettingsPage = SettingsPage;`;

const context = {
    console,
    Promise,
    API: {
        get: async (path) => {
            if (path === '/settings') return {
                company_name: 'SlowBooks NZ',
                default_terms: 'Net 30',
                default_tax_rate: '15',
                invoice_prefix: '',
                invoice_next_number: '1001',
                estimate_prefix: 'E-',
                estimate_next_number: '1001',
                invoice_notes: '',
                invoice_footer: '',
                country: 'NZ',
                tax_regime: 'NZ',
                currency: 'NZD',
                locale: 'en-NZ',
                timezone: 'Pacific/Auckland',
                gst_registered: 'true',
                gst_basis: 'invoice',
                gst_period: 'two-monthly',
                prices_include_gst: 'false',
                financial_year_start: '04-01',
                financial_year_end: '03-31',
                closing_date: '2026-02-28',
                org_lock_date: '2026-03-31',
                effective_lock_date: '2026-03-31',
                effective_lock_layer: 'org_admin',
                closing_date_password: '',
                smtp_password_notice: '',
                purchase_order_delivery_locations: '',
            };
            if (path === '/settings/invoice-reminder-rules') return [];
            if (path === '/backups') return [];
            throw new Error(`unexpected path ${path}`);
        },
    },
    escapeHtml: value => String(value || ''),
    formatDate: value => value || '',
    toast() {},
    setTimeout(fn) { return fn(); },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const html = await context.SettingsPage.render();
    assert.ok(html.includes('Financial Year Start'));
    assert.ok(html.includes('Financial Year End'));
    assert.ok(html.includes('name="financial_year_start_day"'));
    assert.ok(html.includes('name="financial_year_start_month"'));
    assert.ok(html.includes('name="financial_year_end_day"'));
    assert.ok(html.includes('name="financial_year_end_month"'));
    assert.ok(html.includes('<option value="01" selected>01</option>'));
    assert.ok(html.includes('<option value="04" selected>April</option>'));
    assert.ok(html.includes('<option value="03" selected>March</option>'));
    assert.ok(html.includes('Company Admin Lock'));
    assert.ok(html.includes('Organization Lock'));
    assert.ok(html.includes('cannot be bypassed by the company override password'));
    assert.ok(html.includes('The stricter of the company-admin lock and organization lock'));
    assert.ok(html.includes('2026-03-31'));
})();
