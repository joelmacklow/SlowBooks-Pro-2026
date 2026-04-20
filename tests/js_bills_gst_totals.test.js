const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/bills.js', 'utf8')}\nthis.BillsPage = BillsPage;`;

let modalHtml = '';
const elements = {
    '#bill-lines': { innerHTML: '', insertAdjacentHTML(_where, html) { this.innerHTML += html; } },
    '#bill-subtotal': { textContent: '' },
    '#bill-tax': { textContent: '' },
    '#bill-total': { textContent: '' },
};
const billRows = [{
    querySelector(sel) {
        if (sel === '.line-item') return { value: '1' };
        if (sel === '.line-desc') return { value: 'Paper' };
        if (sel === '.line-qty') return { value: '2' };
        if (sel === '.line-gst') return { value: 'GST15' };
        if (sel === '.line-rate') return { value: '10' };
        if (sel === '.line-amount') return { textContent: '' };
        return null;
    },
}];

const context = {
    console,
    Promise,
    API: {
        get: async (path) => {
            if (path === '/vendors?active_only=true') return [{ id: 7, name: 'Harbour Supplies' }];
            if (path === '/items?active_only=true') return [{ id: 1, name: 'Paper', description: 'Printer paper', rate: 10 }];
            if (path === '/accounts?account_type=expense') return [{ id: 600, name: 'Office Expense' }];
            if (path === '/gst-codes') return [
                { code: 'GST15', name: 'GST 15%', rate: 0.15, category: 'taxable' },
                { code: 'NO_GST', name: 'No GST', rate: 0, category: 'no_gst' },
            ];
            if (path === '/bills/5') {
                return {
                    id: 5,
                    bill_number: 'B-100',
                    vendor_name: 'Harbour Supplies',
                    date: '2026-04-20',
                    due_date: '2026-05-20',
                    status: 'unpaid',
                    subtotal: 100,
                    tax_amount: 15,
                    total: 115,
                    amount_paid: 0,
                    balance_due: 115,
                    lines: [{ description: 'Printer paper', quantity: 1, gst_code: 'GST15', rate: 100, amount: 100 }],
                };
            }
            throw new Error(`unexpected get ${path}`);
        },
        post: async () => ({ id: 1 }),
    },
    App: { gstCodes: [], hasPermission: () => true, navigate() {} },
    openModal: (_title, html) => { modalHtml = html; },
    closeModal() {},
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    formatDate: value => String(value || ''),
    statusBadge: value => value,
    gstOptionsHtml(selectedCode = 'GST15') {
        return (context.App.gstCodes || []).map(g => `<option value="${g.code}" ${g.code === selectedCode ? 'selected' : ''}>${g.name}</option>`).join('');
    },
    readGstLinePayload(row) {
        const code = row.querySelector('.line-gst').value;
        const gst = (context.App.gstCodes || []).find(item => item.code === code) || { rate: 0 };
        return {
            quantity: parseFloat(row.querySelector('.line-qty').value) || 0,
            rate: parseFloat(row.querySelector('.line-rate').value) || 0,
            gst_code: code,
            gst_rate: gst.rate,
        };
    },
    calculateGstTotals(lines) {
        let subtotal = 0;
        let tax = 0;
        let total = 0;
        for (const line of lines) {
            const net = (line.quantity || 0) * (line.rate || 0);
            const lineTax = net * (line.gst_code === 'GST15' ? 0.15 : 0);
            subtotal += net;
            tax += lineTax;
            total += net + lineTax;
        }
        return { subtotal, tax_amount: tax, total };
    },
    todayISO: () => '2026-04-20',
    toast() {},
    confirm: () => true,
    $: (selector) => elements[selector],
    $$: (selector) => selector === '#bill-lines tr' ? billRows : [],
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.BillsPage.showForm();
    assert.ok(modalHtml.includes('Subtotal'));
    assert.ok(modalHtml.includes('GST'));
    assert.ok(modalHtml.includes('Grand Total'));
    assert.strictEqual(elements['#bill-subtotal'].textContent, '$20.00');
    assert.strictEqual(elements['#bill-tax'].textContent, '$3.00');
    assert.strictEqual(elements['#bill-total'].textContent, '$23.00');

    await context.BillsPage.view(5);
    assert.ok(modalHtml.includes('Grand Total'));
    assert.ok(modalHtml.includes('Printer paper'));
    assert.ok(modalHtml.includes('GST15'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
