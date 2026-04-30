const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/opening_balances.js', 'utf8')}\nthis.OpeningBalancesPage = OpeningBalancesPage;`;

let status = { is_ready: false, source: null };
let accounts = [];
let lastPost = null;
const saveButton = { disabled: false };
const summaryEl = { innerHTML: '' };
const autoBalanceCheckbox = { checked: false };
const autoBalanceAccount = { value: '' };
const inputs = [];

const context = {
    API: {
        get: async (path) => {
            if (path === '/opening-balances/status') return status;
            if (path === '/accounts?active_only=true') return accounts;
            throw new Error(`Unexpected GET ${path}`);
        },
        post: async (path, payload) => {
            lastPost = { path, payload };
            return { journal: { id: 1 } };
        },
    },
    App: { navigate() {} },
    escapeHtml: value => String(value || ''),
    formatCurrency: value => `$${Number(value).toFixed(2)}`,
    todayISO: () => '2026-04-18',
    toast() {},
    roundMoney: value => Math.round((Number(value) + Number.EPSILON) * 100) / 100,
    setTimeout,
    $$: (selector) => selector === '.opening-balance-amount' ? inputs : [],
    $: (selector) => {
        if (selector === '#opening-balance-save') return saveButton;
        if (selector === '#opening-balance-summary') return summaryEl;
        if (selector === '#opening-auto-balance') return autoBalanceCheckbox;
        if (selector === '#opening-auto-balance-account') return autoBalanceAccount;
        return null;
    },
    console,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    let html = await context.OpeningBalancesPage.render();
    assert.ok(html.includes('Chart of accounts required'));
    assert.ok(html.includes('Open Settings'));

    status = { is_ready: true, source: 'template:xero' };
    accounts = [
        { id: 1, account_number: '090', name: 'Bank', account_type: 'asset' },
        { id: 2, account_number: '900', name: 'Loan', account_type: 'liability' },
        { id: 3, account_number: '970', name: 'Owner Funds', account_type: 'equity' },
    ];
    html = await context.OpeningBalancesPage.render();
    assert.ok(html.includes('Opening Balances'));
    assert.ok(html.includes('Auto-balance to equity'));
    assert.ok(html.includes('Bank'));

    inputs.length = 0;
    inputs.push(
        { value: '100', dataset: { accountId: '1', accountType: 'asset' } },
        { value: '0', dataset: { accountId: '2', accountType: 'liability' } },
        { value: '0', dataset: { accountId: '3', accountType: 'equity' } },
    );
    autoBalanceCheckbox.checked = false;
    autoBalanceAccount.value = '';
    context.OpeningBalancesPage.recalc();
    assert.strictEqual(saveButton.disabled, true);
    assert.ok(summaryEl.innerHTML.includes('Out by'));

    autoBalanceCheckbox.checked = true;
    autoBalanceAccount.value = '3';
    context.OpeningBalancesPage.recalc();
    assert.strictEqual(saveButton.disabled, false);
    assert.ok(summaryEl.innerHTML.includes('will be posted'));

    const payload = context.OpeningBalancesPage.collectPayload({
        date: { value: '2026-04-01' },
        description: { value: 'Opening balances' },
        reference: { value: 'OB-2026' },
    });
    assert.strictEqual(payload.auto_balance_account_id, 3);
    assert.strictEqual(payload.lines.length, 1);

    await context.OpeningBalancesPage.save({
        preventDefault() {},
        target: {
            date: { value: '2026-04-01' },
            description: { value: 'Opening balances' },
            reference: { value: 'OB-2026' },
        },
    });
    assert.strictEqual(lastPost.path, '/opening-balances');
})();
