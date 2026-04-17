const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/invoices.js', 'utf8')}
this.InvoicesPage = InvoicesPage;`;

const posts = [];
const navigations = [];

const context = {
    console,
    Promise,
    setTimeout,
    API: {
        get: async (path) => {
            if (path === '/customers?active_only=true') return [{ id: 5, name: 'Aroha Ltd', terms: 'Net 30', email: 'customer@example.com' }];
            if (path === '/items?active_only=true') return [{ id: 2, name: 'Pens', description: 'Pens', rate: 50 }];
            if (path === '/settings') return { default_terms: 'Net 30', default_tax_rate: '15', invoice_notes: 'Default invoice notes' };
            if (path === '/gst-codes') return [{ code: 'GST15', rate: 0.15, name: 'GST 15%' }];
            if (path === '/invoices/1') return {
                id: 1,
                invoice_number: 'INV-1001',
                customer_id: 5,
                customer_name: 'Aroha Ltd',
                date: '2026-04-16',
                due_date: '2026-04-30',
                terms: 'Net 30',
                status: 'draft',
                subtotal: 100,
                tax_rate: 0.15,
                tax_amount: 15,
                total: 115,
                amount_paid: 0,
                balance_due: 115,
                notes: 'Invoice notes',
                applied_credits: [{ credit_memo_id: 3, credit_memo_number: 'CM-1001', amount: 57.5 }],
                lines: [{ item_id: 2, description: 'Pens', quantity: 2, rate: 50, amount: 100, gst_code: 'GST15', gst_rate: 0.15 }],
            };
            if (path === '/credit-memos?customer_id=5&status=issued') return [
                { id: 3, memo_number: 'CM-1001', customer_id: 5, status: 'issued', balance_remaining: 57.5, total: 57.5 },
            ];
            throw new Error(`unexpected path ${path}`);
        },
        post: async (path, data) => {
            posts.push([path, data]);
            return {};
        },
        put: async () => ({}),
        open() {},
    },
    App: {
        navigate: hash => navigations.push(hash),
        hasPermission: () => true,
        gstCodes: [],
        settings: { prices_include_gst: 'false' },
        showDocumentEmailModal() {},
    },
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-16',
    gstOptionsHtml: () => '<option value="GST15">GST 15%</option>',
    readGstLinePayload: () => ({ quantity: 1, rate: 0, gst_code: 'GST15', gst_rate: 0.15 }),
    calculateGstTotals: lines => {
        const subtotal = lines.reduce((sum, line) => sum + ((line.quantity || 0) * (line.rate || 0)), 0);
        const tax_amount = subtotal * 0.15;
        return { subtotal, tax_amount, total: subtotal + tax_amount };
    },
    $: () => null,
    $$: () => [],
    confirm: () => true,
    toast() {},
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.InvoicesPage.open(1);
    let detailHtml = context.InvoicesPage.renderDetailScreen();
    assert.ok(detailHtml.includes('Available Credit Notes'));
    assert.ok(detailHtml.includes('CM-1001'));
    assert.ok(detailHtml.includes('$57.50'));
    assert.ok(detailHtml.includes('Apply Credit'));
    assert.ok(detailHtml.includes('Applied Credit Notes'));
    assert.ok(detailHtml.includes('CM-1001'));

    await context.InvoicesPage.applyCreditMemo(3, 57.5, 1);
    assert.strictEqual(JSON.stringify(posts), JSON.stringify([[
        '/credit-memos/3/apply',
        { invoice_id: 1, amount: 57.5 },
    ]]));
    assert.deepStrictEqual(navigations, ['#/invoices/detail', '#/invoices/detail']);
})();
