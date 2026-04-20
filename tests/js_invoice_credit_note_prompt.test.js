const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/invoices.js', 'utf8')}
this.InvoicesPage = InvoicesPage;`;

let modalHtml = '';
const posts = [];
const gets = [];
const navigations = [];
const detailOrigins = {};

const context = {
    console,
    Promise,
    setTimeout,
    API: {
        get: async (path) => {
            gets.push(path);
            if (path === '/customers?active_only=true') return [{ id: 5, name: 'Aroha Ltd', terms: 'Net 30', email: 'customer@example.com' }];
            if (path === '/items?active_only=true') return [{ id: 2, name: 'Pens', description: 'Pens', rate: 50 }];
            if (path === '/settings') return { default_terms: 'Net 30', default_tax_rate: '15', invoice_notes: 'Default invoice notes' };
            if (path === '/gst-codes') return [{ code: 'GST15', rate: 0.15, name: 'GST 15%' }];
            if (path === '/credit-memos?customer_id=5&status=issued') return [
                { id: 3, memo_number: 'CM-1001', customer_id: 5, status: 'issued', balance_remaining: 57.5, total: 57.5 },
                { id: 4, memo_number: 'CM-1002', customer_id: 5, status: 'issued', balance_remaining: 20, total: 20 },
            ];
            if (path === '/invoices/9') return {
                id: 9,
                invoice_number: 'INV-1009',
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
                amount_paid: 57.5,
                balance_due: 57.5,
                notes: '',
                lines: [{ item_id: 2, description: 'Pens', quantity: 2, rate: 50, amount: 100, gst_code: 'GST15', gst_rate: 0.15 }],
            };
            throw new Error(`unexpected path ${path}`);
        },
        post: async (path, data) => {
            posts.push([path, data]);
            if (path === '/invoices') {
                return {
                    id: 9,
                    invoice_number: 'INV-1009',
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
                    notes: '',
                    lines: [],
                };
            }
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
        setDetailOrigin(detailHash, originHash = null) { detailOrigins[detailHash] = originHash; },
        getDetailOrigin(detailHash) { return detailOrigins[detailHash] || null; },
        detailBackLabel(_detailHash, _fallbackHash, fallback = 'Previous') { return `Back to ${fallback}`; },
        navigateBackToDetailOrigin(detailHash, fallbackHash) { navigations.push(detailOrigins[detailHash] || fallbackHash); },
    },
    openModal: (_title, html) => { modalHtml = html; },
    closeModal() {},
    toast() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    statusBadge: value => String(value || ''),
    todayISO: () => '2026-04-16',
    gstOptionsHtml: () => '<option value="GST15">GST 15%</option>',
    readGstLinePayload: row => ({
        quantity: parseFloat(row.querySelector('.line-qty')?.value) || 0,
        rate: parseFloat(row.querySelector('.line-rate')?.value) || 0,
        gst_code: row.querySelector('.line-gst')?.value || 'GST15',
        gst_rate: 0.15,
    }),
    calculateGstTotals: lines => {
        const subtotal = lines.reduce((sum, line) => sum + ((line.quantity || 0) * (line.rate || 0)), 0);
        const tax_amount = subtotal * 0.15;
        return { subtotal, tax_amount, total: subtotal + tax_amount };
    },
    $: () => null,
    $$: selector => selector === '#inv-lines tr' ? [{
        querySelector(sel) {
            const values = {
                '.line-item': { value: '2' },
                '.line-desc': { value: 'Pens' },
                '.line-qty': { value: '2' },
                '.line-gst': { value: 'GST15' },
                '.line-rate': { value: '50' },
            };
            return values[sel] || null;
        },
    }] : [],
    confirm: () => true,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.InvoicesPage.startNew();
    await context.InvoicesPage.customerSelected(5);
    assert.ok(gets.includes('/credit-memos?customer_id=5&status=issued'));
    assert.ok(modalHtml.toLowerCase().includes('available credit notes'));
    assert.ok(modalHtml.includes('Apply Full Credit on Save'));
    assert.ok(modalHtml.includes('Set Partial Credit Amounts'));

    context.InvoicesPage.prepareFullCreditApplication();
    await context.InvoicesPage.save({
        preventDefault() {},
        target: {
            customer_id: { value: '5' },
            date: { value: '2026-04-16' },
            due_date: { value: '2026-04-30' },
            terms: { value: 'Net 30' },
            po_number: { value: '' },
            tax_rate: { value: '15' },
            notes: { value: '' },
        },
    }, null);

    assert.strictEqual(JSON.stringify(posts), JSON.stringify([
        ['/invoices', {
            customer_id: 5,
            date: '2026-04-16',
            due_date: '2026-04-30',
            terms: 'Net 30',
            po_number: null,
            tax_rate: 0.15,
            notes: null,
            lines: [{ item_id: 2, description: 'Pens', quantity: 2, rate: 50, gst_code: 'GST15', gst_rate: 0.15, line_order: 0 }],
        }],
        ['/credit-memos/3/apply', { invoice_id: 9, amount: 57.5 }],
        ['/credit-memos/4/apply', { invoice_id: 9, amount: 20 }],
    ]));
    assert.deepStrictEqual(navigations, ['#/invoices/detail', '#/invoices']);
})();
