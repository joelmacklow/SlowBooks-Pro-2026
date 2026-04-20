const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/banking.js', 'utf8')}\nthis.BankingPage = BankingPage;`;

let modalHtml = '';
const posts = [];
const reconcileTransactions = [{
    id: 10,
    date: '2026-04-16',
    payee: 'Learn Innovatio',
    description: 'Learning Inn',
    reference: 'Inv 8746',
    code: 'Wheel Align',
    amount: 53.91,
    reconciled: false,
    matched_label: null,
    suggestions: [{ kind: 'invoice', target_id: 7, document_number: 'INV-8746', label: 'Invoice INV-8746 · Learn Innovations Limited' }],
    rule_suggestion: null,
}];
const elements = {
    '#page-content': { innerHTML: '' },
    '#statement-file': { files: [{}] },
    '#split-code-lines': { innerHTML: '', insertAdjacentHTML(_where, html) { this.innerHTML += html; } },
    '#split-code-total': { textContent: '' },
    '#split-code-subtotal': { textContent: '' },
    '#split-code-tax': { textContent: '' },
    '#split-code-grand-total': { textContent: '' },
    '#split-code-use-purchase-gst': { checked: true },
};

const context = {
    console,
    Promise,
    FormData: class {
        constructor() { this.data = []; }
        append(key, value) { this.data.push([key, value]); }
    },
    API: {
        get: async (path) => {
            if (path === '/banking/accounts/1') return { id: 1, name: 'ANZ Business Account', balance: 5774.25, bank_name: 'ANZ', last_four: '1208' };
            if (path === '/banking/transactions?bank_account_id=1') return [{ id: 9, date: '2026-04-16', payee: 'Learn Innovatio', description: 'Learning Inn', reference: 'Inv 8746', code: 'Wheel Align', amount: 53.91, reconciled: false }];
            if (path === '/accounts') return [
                { id: 21, account_number: '090', name: 'Business Bank Account', account_type: 'asset' },
                { id: 477, account_number: '477', name: 'Wages Expense', account_type: 'expense' },
            ];
            if (path === '/banking/reconciliations/5/transactions' || path === '/banking/reconciliations/6/transactions') return {
                reconciliation_id: 5,
                statement_balance: 53.91,
                statement_label: 'Transactions to clear',
                import_batch_id: 'batch-1',
                cleared_total: reconcileTransactions.filter(t => t.reconciled).reduce((sum, t) => sum + t.amount, 0),
                difference: 53.91 - reconcileTransactions.filter(t => t.reconciled).reduce((sum, t) => sum + t.amount, 0),
                transactions: reconcileTransactions,
            };
            if (path === '/banking/transactions/10/suggestions') return {
                direction: 'inflow',
                transaction: {
                    id: 10,
                    date: '2026-04-16',
                    payee: 'Learn Innovatio',
                    description: 'Learning Inn',
                    reference: 'Inv 8746',
                    code: 'Wheel Align',
                    amount: -53.91,
                },
                suggestions: [{
                    kind: 'invoice',
                    target_id: 7,
                    label: 'Invoice INV-8746 · Learn Innovations Limited',
                    document_number: 'INV-8746',
                    open_amount: 53.91,
                    reasons: ['exact amount', 'reference/number match'],
                }],
            };
            if (path === '/accounts?active_only=true') return [
                { id: 477, account_number: '477', name: 'Wages Expense' },
                { id: 985, account_number: '985', name: 'Owner Drawings' },
            ];
            if (path === '/banking/transactions/10/search?query=8746') return {
                direction: 'inflow',
                query: '8746',
                candidates: [{ kind: 'invoice', target_id: 7, label: 'Invoice INV-8746 · Learn Innovations Limited', open_amount: 53.91, reasons: ['reference/number match'] }],
            };
            throw new Error(`unexpected get ${path}`);
        },
        post: async (path, data) => {
            posts.push({ path, data });
            if (path === '/banking/transactions/10/approve-match') {
                reconcileTransactions[0].reconciled = true;
                reconcileTransactions[0].matched_label = 'Invoice INV-8746';
                return { status: 'matched' };
            }
            if (path === '/banking/transactions/10/code') {
                reconcileTransactions[0].reconciled = true;
                reconcileTransactions[0].matched_label = 'Coded to Wages Expense';
                return { status: 'coded' };
            }
            if (path === '/banking/transactions/10/code-split') {
                reconcileTransactions[0].reconciled = true;
                reconcileTransactions[0].matched_label = 'Split coded across 2 accounts';
                return { status: 'coded' };
            }
            if (path === '/banking/reconciliations/5/cancel') return { status: 'cancelled', removed_transactions: 1 };
            if (path === '/banking/reconciliations/5/toggle/10') return { id: 10, reconciled: true };
            if (path === '/banking/reconciliations') return { id: 6, import_batch_id: data ? data.import_batch_id : null };
            return { id: 1 };
        },
        postForm: async () => ({ imported: 1, skipped_duplicates: 0, total: 1, format: 'csv', statement_date: '2026-04-16', statement_total: 53.91, statement_balance: 1000.00, import_batch_id: 'batch-1' }),
    },
    App: {
        hasPermission: () => true,
        navigate() {},
        gstCodes: [
            { code: 'GST15', name: 'GST 15%', rate: 0.15, category: 'taxable' },
            { code: 'NO_GST', name: 'No GST', rate: 0, category: 'no_gst' },
        ],
    },
    openModal: (_title, html) => { modalHtml = html; },
    closeModal() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
    gstOptionsHtml(selectedCode = 'GST15') {
        return context.App.gstCodes.map(g => `<option value="${g.code}" ${g.code === selectedCode ? 'selected' : ''}>${g.name}</option>`).join('');
    },
    calculateGstTotals(lines) {
        let subtotal = 0;
        let tax = 0;
        let total = 0;
        for (const line of lines) {
            const gross = Number(line.rate || 0) * Number(line.quantity || 0);
            const lineTax = line.gst_code === 'GST15' ? Math.round((gross * 0.15 / 1.15) * 100) / 100 : 0;
            subtotal += gross - lineTax;
            tax += lineTax;
            total += gross;
        }
        return { subtotal, tax_amount: tax, total };
    },
    todayISO: () => '2026-04-17',
    toast() {},
    confirm: () => true,
    $: (selector) => {
        if (!elements[selector]) elements[selector] = { innerHTML: '', value: '', checked: false, style: {} };
        return elements[selector];
    },
    $$: () => [],
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.BankingPage.viewRegister(1);
    assert.ok(elements['#page-content'].innerHTML.includes('Reference'));
    assert.ok(elements['#page-content'].innerHTML.includes('Code'));
    assert.ok(!elements['#page-content'].innerHTML.includes('Check #'));
    assert.ok(elements['#page-content'].innerHTML.includes('Inv 8746'));

    await context.BankingPage.showTxnForm(1);
    assert.ok(modalHtml.includes('<label>Reference</label>'));
    assert.ok(modalHtml.includes('<label>Code</label>'));
    assert.ok(!modalHtml.includes('Check #'));

    await context.BankingPage.saveTxn({
        preventDefault() {},
        target: {
            date: { value: '2026-04-17' },
            amount: { value: '53.91' },
            payee: { value: 'Learn Innovatio' },
            description: { value: 'Learning Inn' },
            reference: { value: 'Inv 8746' },
            code: { value: 'Wheel Align' },
            category_account_id: { value: '477' },
        },
    }, 1);
    const saveCall = posts.find(call => call.path === '/banking/transactions');
    assert.strictEqual(saveCall.data.reference, 'Inv 8746');
    assert.strictEqual(saveCall.data.code, 'Wheel Align');
    assert.strictEqual(saveCall.data.check_number, null);

    await context.BankingPage.showReconcileView(5);
    assert.ok(elements['#page-content'].innerHTML.includes('Find & Match'));
    assert.ok(elements['#page-content'].innerHTML.includes('Split Code'));
    assert.ok(elements['#page-content'].innerHTML.includes('Transactions to clear'));
    assert.ok(elements['#page-content'].innerHTML.includes('INV-8746'));
    assert.ok(!elements['#page-content'].innerHTML.includes('Check #'));
    assert.ok(elements['#page-content'].innerHTML.includes('flex-wrap:wrap'));
    assert.ok(!elements['#page-content'].innerHTML.includes('flex-direction:column'));

    await context.BankingPage.showMatchModal(5, 10);
    assert.ok(modalHtml.includes('Search payee, amount, reference, description, or code'));
    assert.ok(modalHtml.includes('Wages Expense'));
    assert.ok(modalHtml.includes('reference/number match'));

    await context.BankingPage.showSplitCodeModal(10, 5);
    assert.ok(modalHtml.includes('Apply Split Coding'));
    assert.ok(modalHtml.includes('Amount to split'));
    assert.ok(modalHtml.includes('Allocate purchase GST on split lines'));
    const splitRows = [
        {
            querySelector(sel) {
                if (sel === '.split-account') return { value: '477' };
                if (sel === '.split-amount') return { value: '30' };
                if (sel === '.split-gst') return { value: 'GST15' };
                if (sel === '.split-description') return { value: 'Part A' };
                return null;
            },
        },
        {
            querySelector(sel) {
                if (sel === '.split-account') return { value: '985' };
                if (sel === '.split-amount') return { value: '23.91' };
                if (sel === '.split-gst') return { value: 'NO_GST' };
                if (sel === '.split-description') return { value: 'Part B' };
                return null;
            },
        },
    ];
    context.$$ = (selector) => {
        if (selector === '.split-code-line') return splitRows;
        if (selector === '.split-gst-field') return [{ style: {} }, { style: {} }];
        if (selector === '.split-code-gst-summary') return [{ style: {} }, { style: {} }, { style: {} }];
        return [];
    };
    await context.BankingPage.submitSplitCode(10, 5, 53.91);
    assert.ok(posts.some(call => call.path === '/banking/transactions/10/code-split'));
    const splitPost = posts.find(call => call.path === '/banking/transactions/10/code-split');
    assert.strictEqual(splitPost.data.use_purchase_gst, true);
    assert.strictEqual(splitPost.data.splits[0].gst_code, 'GST15');
    assert.ok(elements['#page-content'].innerHTML.includes('Split coded across 2 accounts'));

    reconcileTransactions[0].reconciled = false;
    reconcileTransactions[0].matched_label = null;
    await context.BankingPage.cancelReconcile(5);
    assert.ok(posts.some(call => call.path === '/banking/reconciliations/5/cancel'));

    elements['#bank-match-query-10'] = { value: '8746' };
    elements['#bank-match-results-10'] = { innerHTML: '' };
    await context.BankingPage.searchMatches(10, 5);
    assert.ok(elements['#bank-match-results-10'].innerHTML.includes('INV-8746'));

    elements['#bank-code-account-10'] = { value: '477' };
    elements['#bank-code-description-10'] = { value: 'Weekly wages' };
    await context.BankingPage.codeTransaction(10, 5);
    assert.ok(posts.some(call => call.path === '/banking/transactions/10/code'));
    assert.ok(elements['#page-content'].innerHTML.includes('checked'));
    reconcileTransactions[0].reconciled = false;
    reconcileTransactions[0].matched_label = null;

    await context.BankingPage.approveMatch(10, 'invoice', 7, 5);
    assert.ok(posts.some(call => call.path === '/banking/transactions/10/approve-match'));
    assert.ok(elements['#page-content'].innerHTML.includes('checked'));

    await context.BankingPage.confirmStatementImport(1);
    const reconCreateCall = posts.find(call => call.path === '/banking/reconciliations');
    assert.strictEqual(reconCreateCall.data.statement_date, '2026-04-16');
    assert.strictEqual(reconCreateCall.data.statement_balance, 53.91);
    assert.strictEqual(reconCreateCall.data.import_batch_id, 'batch-1');
    assert.ok(posts.some(call => call.path === '/banking/reconciliations'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
