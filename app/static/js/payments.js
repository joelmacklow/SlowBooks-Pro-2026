/**
 * Decompiled from QBW32.EXE!CReceivePaymentsView  Offset: 0x001A4200
 * The payment allocation grid in the original was a custom MFC control
 * called CQBPaymentGrid that would auto-fill oldest invoices first when
 * you typed a payment amount (FIFO allocation via CQBAllocList::AutoApply
 * at 0x001A2800). We kept the manual allocation approach because the auto
 * version had a known bug with credit memos that Intuit never fixed.
 */
const PaymentsPage = {
    receiptBankAccounts(accounts = []) {
        return (accounts || []).filter(account => {
            if (!account) return false;
            if (account.account_type && account.account_type !== 'asset') return false;
            const label = `${account.account_number || ''} ${account.name || ''}`.toLowerCase();
            return !label.includes('undeposited') && !label.includes('receipt clearing');
        });
    },

    depositFieldState(method, accounts = []) {
        const normalizedMethod = String(method || '').trim().toLowerCase();
        const isCash = normalizedMethod === 'cash';
        const bankAccounts = PaymentsPage.receiptBankAccounts(accounts);
        return {
            blankLabel: isCash
                ? 'Undeposited Funds / Receipt Clearing (recommended for cash)'
                : 'Match from bank feed later / choose bank now',
            defaultAccountId: isCash ? '' : String(bankAccounts[0]?.id || ''),
            helpText: isCash
                ? 'Use cash for notes/coins you will bank later. Leave Deposit To blank to hold the receipt in Undeposited Funds / Receipt Clearing until you make a deposit.'
                : 'For EFT or EFTPOS/card, most NZ businesses match the invoice from imported bank transactions. If you already know the remittance, record it straight to the bank account that received it.',
        };
    },

    markDepositSelectionManual() {
        const depositSelect = $('#payment-deposit-to');
        if (depositSelect) depositSelect.dataset.autoSelected = 'false';
    },

    syncMethodDefaults(accounts = null) {
        const methodSelect = $('#payment-method');
        const depositSelect = $('#payment-deposit-to');
        const hint = $('#payment-method-hint');
        if (!methodSelect || !depositSelect) return;

        const availableAccounts = accounts || Array.from(depositSelect.options || [])
            .filter(option => option.value)
            .map(option => ({ id: option.value }));
        const state = PaymentsPage.depositFieldState(methodSelect.value, availableAccounts);
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
        const payments = await API.get('/payments');
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Customer Receipts</h2>
                ${canManageSales ? `<button class="btn btn-primary" onclick="PaymentsPage.showForm()">+ Record Receipt</button>` : ''}
            </div>`;

        if (payments.length === 0) {
            html += `<div class="empty-state"><p>No customer receipts recorded yet</p></div>`;
        } else {
            html += `<div class="table-container"><table>
                <thead><tr>
                    <th>Date</th><th>Customer</th><th>Method</th><th>Reference</th>
                    <th class="amount">Amount</th><th>Actions</th>
                </tr></thead><tbody>`;
            for (const p of payments) {
                html += `<tr>
                    <td>${formatDate(p.date)}</td>
                    <td>${escapeHtml(p.customer_name || '')}</td>
                    <td>${escapeHtml(p.method || '')}${p.is_voided ? ' <span style="color:var(--danger);font-weight:700;">[VOID]</span>' : ''}</td>
                    <td>${escapeHtml(p.reference || p.check_number || '')}</td>
                    <td class="amount">${formatCurrency(p.amount)}</td>
                    <td class="actions">
                        <button class="btn btn-sm btn-secondary" onclick="PaymentsPage.view(${p.id})">View</button>
                    </td>
                </tr>`;
            }
            html += `</tbody></table></div>`;
        }
        return html;
    },

    async view(id) {
        const p = await API.get(`/payments/${id}`);
        let allocHtml = '';
        const checkHtml = p.check_number ? `<strong>Check #:</strong> ${escapeHtml(p.check_number)}<br>` : '';
        const referenceHtml = p.reference ? `<strong>Reference:</strong> ${escapeHtml(p.reference)}<br>` : '';
        const notesHtml = p.notes ? `<strong>Notes:</strong> ${escapeHtml(p.notes)}<br>` : '';
        if (p.allocations.length) {
            allocHtml = `<h4 style="margin:12px 0 8px;">Applied to Invoices</h4>
                <div class="table-container"><table><thead><tr>
                <th>Invoice</th><th class="amount">Amount</th></tr></thead><tbody>`;
            for (const a of p.allocations) {
                allocHtml += `<tr><td>#${a.invoice_id}</td><td class="amount">${formatCurrency(a.amount)}</td></tr>`;
            }
            allocHtml += `</tbody></table></div>`;
        }

        openModal('Receipt Details', `
            <div style="margin-bottom:12px;">
                <strong>Customer:</strong> ${escapeHtml(p.customer_name || '')}<br>
                <strong>Date:</strong> ${formatDate(p.date)}<br>
                <strong>Amount:</strong> ${formatCurrency(p.amount)}<br>
                <strong>Method:</strong> ${escapeHtml(p.method || 'N/A')}<br>
                ${checkHtml}
                ${referenceHtml}
                ${notesHtml}
                ${p.is_voided ? '<div style="margin-top:8px; color:var(--danger); font-weight:700;">This payment has been voided.</div>' : ''}
            </div>
            ${allocHtml}
            <div class="form-actions">
                ${!p.is_voided && (App.hasPermission ? App.hasPermission('sales.manage') : true) ? `<button class="btn btn-danger" onclick="PaymentsPage.void(${p.id})">Void Payment</button>` : ''}
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>`);
    },

    async void(id) {
        if (!confirm('Void this payment? Invoice balances will be restored and a reversing journal will be posted.')) return;
        try {
            await API.post(`/payments/${id}/void`);
            toast('Payment voided');
            closeModal();
            App.navigate(location.hash);
        } catch (err) { toast(err.message, 'error'); }
    },

    _invoices: [],

    async showForm() {
        const [customers, accounts] = await Promise.all([
            API.get('/customers?active_only=true'),
            API.get('/accounts'),
        ]);
        const bankAccts = PaymentsPage.receiptBankAccounts(accounts);

        const custOpts = customers.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
        const bankOpts = bankAccts.map(a => `<option value="${a.id}">${escapeHtml(a.account_number || '')} - ${escapeHtml(a.name)}</option>`).join('');
        const initialState = PaymentsPage.depositFieldState('', bankAccts);

        openModal('Record Receipt', `
            <form id="payment-form" onsubmit="PaymentsPage.save(event)">
                <div class="card" style="margin-bottom:16px;">
                    <div style="font-size:12px; color:var(--text-muted); line-height:1.5;">
                        Most NZ EFT and EFTPOS receipts are best matched from the bank feed when the statement line arrives.
                        Record a payment here when you already know the remittance, or when you are handling cash that needs to sit in receipt clearing until deposit.
                    </div>
                </div>
                <div class="form-grid">
                    <div class="form-group"><label>Customer *</label>
                        <select name="customer_id" required onchange="PaymentsPage.loadInvoices(this.value)">
                            <option value="">Select...</option>${custOpts}</select></div>
                    <div class="form-group"><label>Date *</label>
                        <input name="date" type="date" required value="${todayISO()}"></div>
                    <div class="form-group"><label>Amount *</label>
                        <input name="amount" type="number" step="0.01" required></div>
                    <div class="form-group"><label>Method</label>
                        <select id="payment-method" name="method" onchange="PaymentsPage.syncMethodDefaults()">
                            <option value="">--</option>
                            <option>EFT</option><option>EFTPOS/Card</option><option>Cash</option><option>Other</option>
                        </select></div>
                    <div class="form-group"><label>Reference</label>
                        <input name="reference"></div>
                    <div class="form-group"><label>Deposit To</label>
                        <select id="payment-deposit-to" name="deposit_to_account_id" data-auto-selected="false" onchange="PaymentsPage.markDepositSelectionManual()">
                            <option value="">${escapeHtml(initialState.blankLabel)}</option>${bankOpts}</select>
                        <div id="payment-method-hint" style="margin-top:6px; font-size:11px; color:var(--text-muted);">${escapeHtml(initialState.helpText)}</div></div>
                    <div class="form-group full-width"><label>Notes</label>
                        <textarea name="notes"></textarea></div>
                </div>
                <div id="payment-invoices" style="margin-top:16px;"></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Record Payment</button>
                </div>
            </form>`);
        if (typeof setTimeout === 'function') {
            setTimeout(() => PaymentsPage.syncMethodDefaults(bankAccts), 0);
        } else {
            PaymentsPage.syncMethodDefaults(bankAccts);
        }
    },

    async loadInvoices(customerId) {
        if (!customerId) { $('#payment-invoices').innerHTML = ''; return; }
        const invoices = await API.get(`/invoices?customer_id=${customerId}&status=sent`);
        const partial = await API.get(`/invoices?customer_id=${customerId}&status=partial`);
        PaymentsPage._invoices = [...invoices, ...partial].filter(i => i.balance_due > 0);

        if (PaymentsPage._invoices.length === 0) {
            $('#payment-invoices').innerHTML = '<p style="color:var(--gray-400);">No outstanding invoices</p>';
            return;
        }

        let html = `<h4 style="margin-bottom:8px;">Apply to Invoices</h4>
            <div class="table-container"><table><thead><tr>
            <th>Invoice</th><th>Date</th><th class="amount">Balance</th><th class="amount">Apply</th>
            </tr></thead><tbody>`;
        for (const inv of PaymentsPage._invoices) {
            html += `<tr>
                <td>#${escapeHtml(inv.invoice_number)}</td>
                <td>${formatDate(inv.date)}</td>
                <td class="amount">${formatCurrency(inv.balance_due)}</td>
                <td><input class="alloc-amount" data-invoice="${inv.id}" data-max="${inv.balance_due}"
                    type="number" step="0.01" min="0" max="${inv.balance_due}"
                    style="width:100px; padding:4px 8px; border:1px solid var(--gray-300); border-radius:4px;"></td>
            </tr>`;
        }
        html += `</tbody></table></div>`;
        $('#payment-invoices').innerHTML = html;
    },

    async save(e) {
        e.preventDefault();
        const form = e.target;
        const allocations = [];
        $$('.alloc-amount').forEach(input => {
            const amt = parseFloat(input.value);
            if (amt > 0) {
                allocations.push({ invoice_id: parseInt(input.dataset.invoice), amount: amt });
            }
        });

        const data = {
            customer_id: parseInt(form.customer_id.value),
            date: form.date.value,
            amount: parseFloat(form.amount.value),
            method: form.method.value || null,
            check_number: null,
            reference: form.reference.value || null,
            deposit_to_account_id: form.deposit_to_account_id.value ? parseInt(form.deposit_to_account_id.value) : null,
            notes: form.notes.value || null,
            allocations,
        };

        try {
            await API.post('/payments', data);
            toast('Receipt recorded');
            closeModal();
            App.navigate(location.hash);
        } catch (err) { toast(err.message, 'error'); }
    },
};
