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
}];
const elements = {
    '#page-content': { innerHTML: '' },
};

const context = {
    console,
    Promise,
    API: {
        get: async (path) => {
            if (path === '/banking/accounts/1') return { id: 1, name: 'ANZ Business Account', balance: 5774.25, bank_name: 'ANZ', last_four: '1208' };
            if (path === '/banking/transactions?bank_account_id=1') return [{ id: 9, date: '2026-04-16', payee: 'Learn Innovatio', description: 'Learning Inn', reference: 'Inv 8746', code: 'Wheel Align', amount: 53.91, reconciled: false }];
            if (path === '/accounts') return [
                { id: 21, account_number: '090', name: 'Business Bank Account', account_type: 'asset' },
                { id: 477, account_number: '477', name: 'Wages Expense', account_type: 'expense' },
            ];
            if (path === '/banking/reconciliations/5/transactions') return {
                reconciliation_id: 5,
                statement_balance: 53.91,
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
                    amount: 53.91,
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
            if (path === '/banking/reconciliations/5/toggle/10') return { id: 10, reconciled: true };
            return { id: 1 };
        },
        postForm: async () => ({ imported: 1, skipped_duplicates: 0, total: 1, format: 'csv' }),
    },
    App: { hasPermission: () => true, navigate() {} },
    openModal: (_title, html) => { modalHtml = html; },
    closeModal() {},
    escapeHtml: value => String(value || ''),
    formatDate: value => String(value || ''),
    formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
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
    assert.ok(elements['#page-content'].innerHTML.includes('INV-8746'));
    assert.ok(!elements['#page-content'].innerHTML.includes('Check #'));
    assert.ok(elements['#page-content'].innerHTML.includes('flex-wrap:wrap'));
    assert.ok(!elements['#page-content'].innerHTML.includes('flex-direction:column'));

    await context.BankingPage.showMatchModal(5, 10);
    assert.ok(modalHtml.includes('Search payee, amount, reference, description, or code'));
    assert.ok(modalHtml.includes('Wages Expense'));
    assert.ok(modalHtml.includes('reference/number match'));

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
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
