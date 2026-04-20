const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/banking.js', 'utf8')}\nthis.BankingPage = BankingPage;`;

let modalHtml = '';
const posts = [];
const puts = [];
const deletes = [];
const reconcileTransactions = [{
    id: 10,
    date: '2026-04-16',
    payee: 'Caleb Macklow',
    description: 'Wages',
    reference: '',
    code: 'Wages',
    amount: -73.57,
    reconciled: false,
    matched_label: null,
    suggestions: [],
    rule_suggestion: { id: 8, name: 'Weekly wages', target_account_name: 'Wages Expense', reason: "payee contains 'caleb'" },
}];
const elements = {
    '#page-content': { innerHTML: '' },
};

const rules = [{
    id: 8,
    name: 'Weekly wages',
    priority: 5,
    direction: 'outflow',
    bank_account_id: 1,
    bank_account_name: 'ANZ Business',
    target_account_id: 477,
    target_account_name: 'Wages Expense',
    payee_contains: 'caleb',
    description_contains: null,
    reference_contains: null,
    code_equals: 'Wages',
    default_description: 'Weekly wages',
    is_active: true,
}];

const context = {
    console,
    Promise,
    API: {
        get: async (path) => {
            if (path === '/banking/accounts') return [{ id: 1, name: 'ANZ Business', balance: 1200, bank_name: 'ANZ', last_four: '1208' }];
            if (path === '/accounts?active_only=true') return [{ id: 477, account_number: '477', name: 'Wages Expense' }];
            if (path === '/banking/rules') return rules;
            if (path === '/banking/reconciliations/5/transactions') return {
                reconciliation_id: 5,
                statement_balance: -73.57,
                statement_label: 'Transactions to clear',
                import_batch_id: 'batch-2',
                cleared_total: reconcileTransactions.filter(t => t.reconciled).reduce((sum, t) => sum + t.amount, 0),
                difference: -73.57 - reconcileTransactions.filter(t => t.reconciled).reduce((sum, t) => sum + t.amount, 0),
                transactions: reconcileTransactions,
            };
            throw new Error(`unexpected get ${path}`);
        },
        post: async (path, data) => {
            posts.push({ path, data });
            if (path === '/banking/rules') return { id: 9 };
            if (path === '/banking/transactions/10/apply-rule') {
                reconcileTransactions[0].reconciled = true;
                reconcileTransactions[0].matched_label = 'Applied rule Weekly wages';
                return { status: 'coded' };
            }
            throw new Error(`unexpected post ${path}`);
        },
        put: async (path, data) => {
            puts.push({ path, data });
            return { id: 8 };
        },
        del: async (path) => {
            deletes.push(path);
            return { status: 'deleted' };
        },
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
        if (!elements[selector]) elements[selector] = { innerHTML: '', value: '', checked: false };
        return elements[selector];
    },
    $$: () => [],
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const rendered = await context.BankingPage.render();
    assert.ok(rendered.includes('Bank Rules'));

    await context.BankingPage.showRules();
    assert.ok(modalHtml.includes('Weekly wages'));
    assert.ok(modalHtml.includes('Deterministic categorization rules'));

    context.BankingPage.showRuleForm();
    assert.ok(modalHtml.includes('Payee contains'));
    assert.ok(modalHtml.includes('Target account'));

    await context.BankingPage.saveRule({
        preventDefault() {},
        target: {
            name: { value: 'Power bills' },
            priority: { value: '10' },
            direction: { value: 'outflow' },
            bank_account_id: { value: '1' },
            target_account_id: { value: '477' },
            payee_contains: { value: 'power' },
            description_contains: { value: '' },
            reference_contains: { value: '' },
            code_equals: { value: 'POWER' },
            default_description: { value: 'Power expense' },
            is_active: { checked: true },
        },
    });
    assert.ok(posts.some(call => call.path === '/banking/rules'));

    await context.BankingPage.saveRule({
        preventDefault() {},
        target: {
            name: { value: 'Weekly wages' },
            priority: { value: '5' },
            direction: { value: 'outflow' },
            bank_account_id: { value: '1' },
            target_account_id: { value: '477' },
            payee_contains: { value: 'caleb' },
            description_contains: { value: '' },
            reference_contains: { value: '' },
            code_equals: { value: 'Wages' },
            default_description: { value: 'Weekly wages' },
            is_active: { checked: true },
        },
    }, 8);
    assert.ok(puts.some(call => call.path === '/banking/rules/8'));

    await context.BankingPage.deleteRule(8);
    assert.ok(deletes.includes('/banking/rules/8'));

    await context.BankingPage.showReconcileView(5);
    assert.ok(elements['#page-content'].innerHTML.includes('Apply Rule'));
    assert.ok(elements['#page-content'].innerHTML.includes('Weekly wages'));

    await context.BankingPage.applyRule(10, 8, 5);
    assert.ok(posts.some(call => call.path === '/banking/transactions/10/apply-rule'));
    assert.ok(elements['#page-content'].innerHTML.includes('Applied rule Weekly wages'));
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
