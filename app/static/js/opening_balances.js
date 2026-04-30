const OpeningBalancesPage = {
    _status: null,
    _accounts: [],

    async render() {
        const [status, accounts] = await Promise.all([
            API.get('/opening-balances/status'),
            API.get('/accounts?active_only=true'),
        ]);
        OpeningBalancesPage._status = status;
        OpeningBalancesPage._accounts = (accounts || []).filter(account =>
            ['asset', 'liability', 'equity'].includes(account.account_type)
        );

        if (!status.is_ready) {
            return `
                <div class="page-header">
                    <h2>Opening Balances</h2>
                </div>
                <div class="empty-state">
                    <p><strong>Chart of accounts required.</strong> Load a chart template in Settings or import your chart from previous software before entering opening balances.</p>
                    <div class="form-actions" style="justify-content:center; margin-top:12px;">
                        <button class="btn btn-secondary" onclick="App.navigate('#/settings')">Open Settings</button>
                        <button class="btn btn-primary" onclick="App.navigate('#/xero-import')">Open Xero Import</button>
                    </div>
                </div>`;
        }

        const grouped = {
            asset: OpeningBalancesPage._accounts.filter(account => account.account_type === 'asset'),
            liability: OpeningBalancesPage._accounts.filter(account => account.account_type === 'liability'),
            equity: OpeningBalancesPage._accounts.filter(account => account.account_type === 'equity'),
        };
        setTimeout(() => OpeningBalancesPage.recalc(), 0);
        const source = status.source ? `<div style="font-size:10px; color:var(--text-muted);">COA source: ${escapeHtml(status.source)}</div>` : '';
        return `
            <div class="page-header">
                <h2>Opening Balances</h2>
                ${source}
            </div>
            <form onsubmit="OpeningBalancesPage.save(event)">
                <div class="settings-section">
                    <div class="form-grid">
                        <div class="form-group"><label>Opening Date *</label><input name="date" type="date" required value="${todayISO()}"></div>
                        <div class="form-group"><label>Reference</label><input name="reference" value="OPENING-BAL"></div>
                        <div class="form-group full-width"><label>Description</label><input name="description" value="Opening balances"></div>
                    </div>
                </div>
                <div class="settings-section">
                    <div class="form-group">
                        <label><input type="checkbox" id="opening-auto-balance" onchange="OpeningBalancesPage.recalc()"> Auto-balance to equity</label>
                    </div>
                    <div class="form-group">
                        <label>Auto-balance equity account</label>
                        <select id="opening-auto-balance-account" onchange="OpeningBalancesPage.recalc()">
                            <option value="">Select equity account...</option>
                            ${grouped.equity.map(account => `<option value="${account.id}">${escapeHtml(account.account_number || '')} - ${escapeHtml(account.name)}</option>`).join('')}
                        </select>
                    </div>
                </div>
                ${OpeningBalancesPage.sectionHtml('Assets', grouped.asset)}
                ${OpeningBalancesPage.sectionHtml('Liabilities', grouped.liability)}
                ${OpeningBalancesPage.sectionHtml('Equity', grouped.equity)}
                <div class="settings-section">
                    <div id="opening-balance-summary" style="font-size:11px; color:var(--text-muted);"></div>
                    <div class="form-actions">
                        <button type="submit" id="opening-balance-save" class="btn btn-primary" disabled>Save Opening Balances</button>
                    </div>
                </div>
            </form>`;
    },

    sectionHtml(title, accounts) {
        if (!accounts.length) return '';
        return `
            <div class="settings-section">
                <h3>${title}</h3>
                <div class="table-container"><table>
                    <thead><tr><th style="width:90px;">Number</th><th>Account</th><th style="width:160px;" class="amount">Amount</th></tr></thead>
                    <tbody>
                        ${accounts.map(account => `
                            <tr>
                                <td>${escapeHtml(account.account_number || '')}</td>
                                <td>${escapeHtml(account.name)}</td>
                                <td class="amount">
                                    <input
                                        type="number"
                                        step="0.01"
                                        value="0"
                                        data-account-id="${account.id}"
                                        data-account-type="${account.account_type}"
                                        class="opening-balance-amount"
                                        oninput="OpeningBalancesPage.recalc()"
                                        style="width:120px; text-align:right;"
                                    >
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table></div>
            </div>`;
    },

    collectPayload(form) {
        const lines = $$('.opening-balance-amount').map(input => ({
            account_id: parseInt(input.dataset.accountId, 10),
            account_type: input.dataset.accountType,
            amount: parseFloat(input.value || '0') || 0,
        })).filter(line => Math.abs(line.amount) > 0.00001);
        const autoBalance = $('#opening-auto-balance')?.checked;
        const autoBalanceAccountId = autoBalance ? parseInt($('#opening-auto-balance-account')?.value || '', 10) : null;
        return {
            date: form.date.value,
            description: form.description.value || 'Opening balances',
            reference: form.reference.value || null,
            auto_balance_account_id: Number.isInteger(autoBalanceAccountId) ? autoBalanceAccountId : null,
            lines: lines.map(({ account_id, amount }) => ({ account_id, amount })),
        };
    },

    recalc() {
        let debits = 0;
        let credits = 0;
        $$('.opening-balance-amount').forEach(input => {
            const amount = parseFloat(input.value || '0') || 0;
            const type = input.dataset.accountType;
            if (type === 'asset') {
                if (amount >= 0) debits += amount;
                else credits += Math.abs(amount);
            } else {
                if (amount >= 0) credits += amount;
                else debits += Math.abs(amount);
            }
        });
        debits = roundMoney(debits);
        credits = roundMoney(credits);
        const diff = roundMoney(debits - credits);
        const autoBalanceEnabled = $('#opening-auto-balance')?.checked;
        const autoBalanceAccount = $('#opening-auto-balance-account')?.value;
        const balanced = Math.abs(diff) < 0.005;
        const canAutoBalance = autoBalanceEnabled && autoBalanceAccount;
        const canSave = $$('.opening-balance-amount').some(input => Math.abs(parseFloat(input.value || '0') || 0) > 0.00001) && (balanced || canAutoBalance);
        const saveBtn = $('#opening-balance-save');
        if (saveBtn) saveBtn.disabled = !canSave;
        const summary = $('#opening-balance-summary');
        if (!summary) return;
        if (balanced) {
            summary.innerHTML = `Debits ${formatCurrency(debits)} &middot; Credits ${formatCurrency(credits)} &middot; <strong style="color:var(--success);">Balanced</strong>`;
            return;
        }
        if (canAutoBalance) {
            summary.innerHTML = `Debits ${formatCurrency(debits)} &middot; Credits ${formatCurrency(credits)} &middot; Difference ${formatCurrency(Math.abs(diff))} will be posted to the selected equity account.`;
            return;
        }
        summary.innerHTML = `Debits ${formatCurrency(debits)} &middot; Credits ${formatCurrency(credits)} &middot; <strong style="color:var(--danger);">Out by ${formatCurrency(Math.abs(diff))}</strong>`;
    },

    async save(e) {
        e.preventDefault();
        const payload = OpeningBalancesPage.collectPayload(e.target);
        try {
            const result = await API.post('/opening-balances', payload);
            toast('Opening balances saved');
            App.navigate(`#/journal`);
            return result;
        } catch (err) {
            toast(err.message, 'error');
        }
    },
};
