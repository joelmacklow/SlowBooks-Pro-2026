/**
 * Batch Payment Application — apply payments to multiple invoices
 * Feature 7: UI shows open invoices with editable amounts
 */
const BatchPaymentsPage = {
    receiptBankAccounts(accounts = []) {
        return (accounts || []).filter(account => {
            const label = `${account.account_number || ''} ${account.name || ''}`.toLowerCase();
            return !label.includes('undeposited') && !label.includes('receipt clearing');
        });
    },

    depositFieldState(method, accounts = []) {
        const normalizedMethod = String(method || '').trim().toLowerCase();
        const isCash = normalizedMethod === 'cash';
        const bankAccounts = BatchPaymentsPage.receiptBankAccounts(accounts);
        return {
            blankLabel: isCash
                ? 'Undeposited Funds / Receipt Clearing (recommended for cash)'
                : 'Select bank account for remittance',
            defaultAccountId: isCash ? '' : String(bankAccounts[0]?.id || ''),
            helpText: isCash
                ? 'Use cash only for physical takings that still need to be banked through Make Deposits.'
                : 'Use this screen for exceptional remittance-style allocation. Most EFT and EFTPOS receipts should be matched during bank reconciliation instead.',
        };
    },

    markDepositSelectionManual() {
        const depositSelect = $('#batch-payment-deposit-to');
        if (depositSelect) depositSelect.dataset.autoSelected = 'false';
    },

    syncMethodDefaults(accounts = null) {
        const methodSelect = $('#batch-payment-method');
        const depositSelect = $('#batch-payment-deposit-to');
        const hint = $('#batch-payment-hint');
        if (!methodSelect || !depositSelect) return;

        const availableAccounts = accounts || Array.from(depositSelect.options || [])
            .filter(option => option.value)
            .map(option => ({ id: option.value }));
        const state = BatchPaymentsPage.depositFieldState(methodSelect.value, availableAccounts);
        if (depositSelect.options?.length) {
            depositSelect.options[0].textContent = state.blankLabel;
        }
        if (hint) hint.textContent = state.helpText;

        if (state.defaultAccountId) {
            if (!depositSelect.value || depositSelect.dataset.autoSelected === 'true') {
                depositSelect.value = state.defaultAccountId;
                depositSelect.dataset.autoSelected = 'true';
            }
            return;
        }

        if (depositSelect.dataset.autoSelected === 'true') {
            depositSelect.value = '';
        }
        depositSelect.dataset.autoSelected = 'false';
    },

    async render() {
        const [invoices, accounts] = await Promise.all([
            API.get('/invoices'),
            API.get('/accounts?account_type=asset'),
        ]);
        const openInv = invoices.filter(i => i.balance_due > 0 && i.status !== 'void');

        // Group by customer
        const byCustomer = {};
        for (const inv of openInv) {
            const cname = inv.customer_name || 'Unknown';
            if (!byCustomer[cname]) byCustomer[cname] = [];
            byCustomer[cname].push(inv);
        }

        const bankAccounts = BatchPaymentsPage.receiptBankAccounts(accounts);
        const acctOpts = bankAccounts.map(a => `<option value="${a.id}">${escapeHtml(a.account_number || '')} - ${escapeHtml(a.name)}</option>`).join('');
        const initialState = BatchPaymentsPage.depositFieldState('EFT', bankAccounts);

        let html = `
            <div class="page-header">
                <h2>Bulk Receipt Allocation</h2>
            </div>
            <form onsubmit="BatchPaymentsPage.save(event)">
                <div class="card" style="margin-bottom:16px;">
                    <div style="font-size:12px; color:var(--text-muted); line-height:1.5;">
                        Use bulk receipt allocation when a remittance covers many invoices. For day-to-day EFT and EFTPOS receipts, prefer matching imported bank transactions during reconciliation.
                    </div>
                </div>
                <div class="form-grid">
                    <div class="form-group"><label>Payment Date *</label>
                        <input name="date" type="date" required value="${todayISO()}"></div>
                    <div class="form-group"><label>Deposit To</label>
                        <select id="batch-payment-deposit-to" name="deposit_to_account_id" data-auto-selected="false" onchange="BatchPaymentsPage.markDepositSelectionManual()"><option value="">${escapeHtml(initialState.blankLabel)}</option>${acctOpts}</select>
                        <div id="batch-payment-hint" style="margin-top:6px; font-size:11px; color:var(--text-muted);">${escapeHtml(initialState.helpText)}</div></div>
                    <div class="form-group"><label>Method</label>
                        <select id="batch-payment-method" name="method" onchange="BatchPaymentsPage.syncMethodDefaults()">
                            <option value="EFT">EFT</option><option value="EFTPOS/Card">EFTPOS/Card</option><option value="Cash">Cash</option>
                            <option value="Other">Other</option>
                        </select></div>
                    <div class="form-group"><label>Reference</label>
                        <input name="reference"></div>
                </div>
                <div style="margin:8px 0;"><button type="button" class="btn btn-sm btn-secondary" onclick="BatchPaymentsPage.selectAll()">Select All</button></div>`;

        if (Object.keys(byCustomer).length === 0) {
            html += '<div class="empty-state"><p>No open invoices to pay</p></div>';
        } else {
            html += '<div class="table-container"><table><thead><tr><th></th><th>Invoice</th><th>Customer</th><th>Due</th><th class="amount">Balance</th><th class="amount">Payment</th></tr></thead><tbody>';
            for (const [cname, invs] of Object.entries(byCustomer)) {
                html += `<tr style="background:var(--toolbar-bg);"><td colspan="6" style="font-weight:700;font-size:11px;padding:3px 10px;">${escapeHtml(cname)}</td></tr>`;
                for (const inv of invs) {
                    html += `<tr>
                        <td><input type="checkbox" class="batch-check" data-inv="${inv.id}" data-cust="${inv.customer_id}" data-bal="${inv.balance_due}"></td>
                        <td><strong>${escapeHtml(inv.invoice_number)}</strong></td>
                        <td>${escapeHtml(cname)}</td>
                        <td>${formatDate(inv.due_date)}</td>
                        <td class="amount">${formatCurrency(inv.balance_due)}</td>
                        <td><input type="number" step="0.01" class="batch-amt" data-inv="${inv.id}" data-cust="${inv.customer_id}" value="0" style="width:80px;"></td>
                    </tr>`;
                }
            }
            html += '</tbody></table></div>';
        }

        html += `<div id="batch-total" style="margin-top:12px;font-size:16px;font-weight:700;color:var(--qb-navy);">Total: $0.00</div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">Create Receipt Allocations</button>
            </div></form>`;

        if (typeof setTimeout === 'function') {
            setTimeout(() => BatchPaymentsPage.syncMethodDefaults(bankAccounts), 0);
        } else {
            BatchPaymentsPage.syncMethodDefaults(bankAccounts);
        }
        return html;
    },

    selectAll() {
        $$('.batch-check').forEach(cb => {
            cb.checked = true;
            const inv = cb.dataset.inv;
            const amtInput = $(`.batch-amt[data-inv="${inv}"]`);
            if (amtInput) amtInput.value = cb.dataset.bal;
        });
        BatchPaymentsPage.recalc();
    },

    recalc() {
        let total = 0;
        $$('.batch-amt').forEach(input => { total += parseFloat(input.value) || 0; });
        const el = $('#batch-total');
        if (el) el.textContent = `Total: ${formatCurrency(total)}`;
    },

    async save(e) {
        e.preventDefault();
        const form = e.target;
        const allocations = [];
        $$('.batch-amt').forEach(input => {
            const amt = parseFloat(input.value) || 0;
            if (amt > 0) {
                allocations.push({
                    customer_id: parseInt(input.dataset.cust),
                    invoice_id: parseInt(input.dataset.inv),
                    amount: amt,
                });
            }
        });
        if (allocations.length === 0) { toast('Enter payment amounts', 'error'); return; }

        try {
            const result = await API.post('/batch-payments', {
                date: form.date.value,
                deposit_to_account_id: form.deposit_to_account_id.value ? parseInt(form.deposit_to_account_id.value) : null,
                method: form.method.value,
                reference: form.reference.value || null,
                allocations,
            });
            toast(`${result.payments_created} payment(s) created`);
            App.navigate('#/batch-payments');
        } catch (err) { toast(err.message, 'error'); }
    },
};

// Wire up recalc after page loads
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('batch-check')) {
        const inv = e.target.dataset.inv;
        const amtInput = $(`.batch-amt[data-inv="${inv}"]`);
        if (amtInput) amtInput.value = e.target.checked ? e.target.dataset.bal : '0';
        BatchPaymentsPage.recalc();
    }
});
document.addEventListener('input', (e) => {
    if (e.target.classList.contains('batch-amt')) BatchPaymentsPage.recalc();
});
