/**
 * Decompiled from QBW32.EXE!CBankRegisterView + CReconcileWizard
 * Offset: 0x001E8400 (Register) / 0x001F1200 (Reconcile)
 * The bank register was one of the oldest views in QuickBooks, dating back
 * to the original Quicken codebase (circa 1993). You could tell because it
 * used CEditView instead of CFormView and had hardcoded column widths in
 * pixels (80, 120, 200, 80, 80, 80) that didn't scale on high-DPI displays.
 * The checkbook-style layout is preserved here for nostalgia.
 */
const BankingPage = {
    async render() {
        const accounts = await API.get('/banking/accounts');
        const canManageBanking = App.hasPermission ? App.hasPermission('banking.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Bank Accounts</h2>
                ${canManageBanking ? `<button class="btn btn-primary" onclick="BankingPage.showAccountForm()">+ New Bank Account</button>` : ''}
            </div>`;

        if (accounts.length === 0) {
            html += `<div class="empty-state"><p>No bank accounts yet</p></div>`;
        } else {
            html += `<div class="card-grid">`;
            for (const ba of accounts) {
                html += `<div class="card" style="cursor:pointer" onclick="BankingPage.viewRegister(${ba.id})">
                    <div class="card-header">${escapeHtml(ba.name)}</div>
                    <div class="card-value">${formatCurrency(ba.balance)}</div>
                    <div style="font-size:12px; color:var(--gray-400); margin-top:4px;">
                        ${escapeHtml(ba.bank_name || '')} ${ba.last_four ? '****' + ba.last_four : ''}
                    </div>
                </div>`;
            }
            html += `</div>`;
        }
        return html;
    },

    async viewRegister(bankAccountId) {
        const [ba, txns] = await Promise.all([
            API.get(`/banking/accounts/${bankAccountId}`),
            API.get(`/banking/transactions?bank_account_id=${bankAccountId}`),
        ]);

        let html = `
            <div class="page-header">
                <h2>${escapeHtml(ba.name)} Register</h2>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="App.navigate('#/banking')">Back</button>
                    ${App.hasPermission && !App.hasPermission('banking.manage') ? '' : `<button class="btn btn-primary" onclick="BankingPage.showTxnForm(${bankAccountId})">+ Transaction</button>
                    <button class="btn btn-secondary" onclick="BankingPage.showStatementImport(${bankAccountId})">Import Statement</button>
                    <button class="btn btn-secondary" onclick="BankingPage.startReconcile(${bankAccountId})">Reconcile</button>` }
                </div>
            </div>
            <div class="card" style="margin-bottom:16px;">
                <div class="card-header">Current Balance</div>
                <div class="card-value">${formatCurrency(ba.balance)}</div>
            </div>`;

        if (txns.length === 0) {
            html += `<div class="empty-state"><p>No transactions</p></div>`;
        } else {
            html += `<div class="table-container"><table>
                <thead><tr>
                    <th>Date</th><th>Payee</th><th>Description</th><th>Reference</th><th>Code</th>
                    <th class="amount">Amount</th><th>Reconciled</th>
                </tr></thead><tbody>`;
            for (const t of txns) {
                const cls = t.amount >= 0 ? 'color:var(--success)' : 'color:var(--danger)';
                html += `<tr>
                    <td>${formatDate(t.date)}</td>
                    <td>${escapeHtml(t.payee || '')}</td>
                    <td>${escapeHtml(t.description || '')}</td>
                    <td>${escapeHtml(t.reference || '')}</td>
                    <td>${escapeHtml(t.code || '')}</td>
                    <td class="amount" style="${cls}">${formatCurrency(t.amount)}</td>
                    <td>${t.reconciled ? 'R' : ''}</td>
                </tr>`;
            }
            html += `</tbody></table></div>`;
        }

        $('#page-content').innerHTML = html;
    },

    async showAccountForm() {
        const coaAccounts = await API.get('/accounts?account_type=asset');
        const opts = coaAccounts.map(a => `<option value="${a.id}">${a.account_number} - ${escapeHtml(a.name)}</option>`).join('');

        openModal('New Bank Account', `
            <form onsubmit="BankingPage.saveAccount(event)">
                <div class="form-grid">
                    <div class="form-group"><label>Account Name *</label>
                        <input name="name" required></div>
                    <div class="form-group"><label>Linked COA Account</label>
                        <select name="account_id"><option value="">--</option>${opts}</select></div>
                    <div class="form-group"><label>Bank Name</label>
                        <input name="bank_name"></div>
                    <div class="form-group"><label>Last 4 Digits</label>
                        <input name="last_four" maxlength="4"></div>
                    <div class="form-group"><label>Opening Balance</label>
                        <input name="balance" type="number" step="0.01" value="0"></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create Account</button>
                </div>
            </form>`);
    },

    async saveAccount(e) {
        e.preventDefault();
        const form = e.target;
        const data = {
            name: form.name.value,
            account_id: form.account_id.value ? parseInt(form.account_id.value) : null,
            bank_name: form.bank_name.value || null,
            last_four: form.last_four.value || null,
            balance: parseFloat(form.balance.value) || 0,
        };
        try {
            await API.post('/banking/accounts', data);
            toast('Bank account created');
            closeModal();
            App.navigate('#/banking');
        } catch (err) { toast(err.message, 'error'); }
    },

    async showTxnForm(bankAccountId) {
        const accounts = await API.get('/accounts');
        const catOpts = accounts
            .filter(a => ['expense','income','asset','liability','equity'].includes(a.account_type))
            .map(a => `<option value="${a.id}">${a.account_number} - ${escapeHtml(a.name)}</option>`).join('');

        openModal('New Transaction', `
            <form onsubmit="BankingPage.saveTxn(event, ${bankAccountId})">
                <div class="form-grid">
                    <div class="form-group"><label>Date *</label>
                        <input name="date" type="date" required value="${todayISO()}"></div>
                    <div class="form-group"><label>Amount * (negative=withdrawal)</label>
                        <input name="amount" type="number" step="0.01" required></div>
                    <div class="form-group"><label>Payee</label>
                        <input name="payee"></div>
                    <div class="form-group"><label>Reference</label>
                        <input name="reference"></div>
                    <div class="form-group"><label>Code</label>
                        <input name="code"></div>
                    <div class="form-group full-width"><label>Description</label>
                        <input name="description"></div>
                    <div class="form-group"><label>Category</label>
                        <select name="category_account_id"><option value="">--</option>${catOpts}</select></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Transaction</button>
                </div>
            </form>`);
    },

    async saveTxn(e, bankAccountId) {
        e.preventDefault();
        const form = e.target;
        const data = {
            bank_account_id: bankAccountId,
            date: form.date.value,
            amount: parseFloat(form.amount.value),
            payee: form.payee.value || null,
            description: form.description.value || null,
            reference: form.reference.value || null,
            code: form.code.value || null,
            check_number: null,
            category_account_id: form.category_account_id.value ? parseInt(form.category_account_id.value) : null,
        };
        try {
            await API.post('/banking/transactions', data);
            toast('Transaction saved');
            closeModal();
            BankingPage.viewRegister(bankAccountId);
        } catch (err) { toast(err.message, 'error'); }
    },

    async startReconcile(bankAccountId) {
        openModal('Begin Reconciliation', `
            <form onsubmit="BankingPage.createReconciliation(event, ${bankAccountId})">
                <p style="margin-bottom:12px; font-size:11px; color:var(--gray-500);">
                    Enter the ending date and balance from your bank statement.
                </p>
                <div class="form-grid">
                    <div class="form-group"><label>Statement Date *</label>
                        <input name="statement_date" type="date" required value="${todayISO()}"></div>
                    <div class="form-group"><label>Statement Ending Balance *</label>
                        <input name="statement_balance" type="number" step="0.01" required></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Begin Reconciliation</button>
                </div>
            </form>`);
    },

    async createReconciliation(e, bankAccountId) {
        e.preventDefault();
        const form = e.target;
        try {
            const recon = await API.post('/banking/reconciliations', {
                bank_account_id: bankAccountId,
                statement_date: form.statement_date.value,
                statement_balance: parseFloat(form.statement_balance.value),
            });
            closeModal();
            BankingPage.showReconcileView(recon.id);
        } catch (err) { toast(err.message, 'error'); }
    },

    renderMatchActions(transaction, reconId) {
        if (transaction.matched_label) {
            return `<div style="font-size:11px; color:var(--success); font-weight:700;">${escapeHtml(transaction.matched_label)}</div>`;
        }
        const suggestionHtml = (transaction.suggestions || []).slice(0, 2).map(candidate => `
            <button class="btn btn-sm btn-secondary" type="button" onclick="BankingPage.approveMatch(${transaction.id}, '${candidate.kind}', ${candidate.target_id}, ${reconId})">
                ${escapeHtml(candidate.document_number || candidate.label)}
            </button>`).join('');
        return `
            <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
                ${suggestionHtml || '<span style="font-size:11px; color:var(--text-muted);">No likely matches yet</span>'}
                <button class="btn btn-sm btn-primary" type="button" onclick="BankingPage.showMatchModal(${reconId}, ${transaction.id})">Find & Match</button>
            </div>`;
    },

    async showReconcileView(reconId) {
        const data = await API.get(`/banking/reconciliations/${reconId}/transactions`);
        BankingPage._reconcileContext = { reconId, data };
        const diffColor = Math.abs(data.difference) < 0.01 ? 'var(--success)' : 'var(--danger)';
        const rows = data.transactions.map(t => {
            const amtCls = t.amount >= 0 ? 'color:var(--success)' : 'color:var(--danger)';
            const rowStyle = t.reconciled ? 'style="background:var(--primary-light);"' : '';
            return `<tr ${rowStyle}>
                <td><input type="checkbox" ${t.reconciled ? 'checked' : ''}
                    onchange="BankingPage.toggleCleared(${reconId}, ${t.id}, this)"></td>
                <td>${formatDate(t.date)}</td>
                <td>
                    <div>${escapeHtml(t.payee || '')}</div>
                    <div style="font-size:11px; color:var(--text-muted);">${escapeHtml(t.description || '')}</div>
                </td>
                <td>${escapeHtml(t.reference || '')}</td>
                <td>${escapeHtml(t.code || '')}</td>
                <td class="amount" style="${amtCls}">${formatCurrency(t.amount)}</td>
                <td>${BankingPage.renderMatchActions(t, reconId)}</td>
            </tr>`;
        }).join('');

        $('#page-content').innerHTML = `
            <div class="page-header">
                <h2>Reconcile Account</h2>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="App.navigate('#/banking')">Cancel</button>
                    <button class="btn btn-primary" id="recon-finish-btn" onclick="BankingPage.finishReconcile(${reconId})"
                        ${Math.abs(data.difference) < 0.01 ? '' : 'disabled'}>Finish Reconciliation</button>
                </div>
            </div>
            <div class="card-grid" style="margin-bottom:16px;">
                <div class="card"><div class="card-header">Statement Balance</div>
                    <div class="card-value">${formatCurrency(data.statement_balance)}</div></div>
                <div class="card"><div class="card-header">Cleared Balance</div>
                    <div class="card-value" id="recon-cleared">${formatCurrency(data.cleared_total)}</div></div>
                <div class="card"><div class="card-header">Difference</div>
                    <div class="card-value" id="recon-diff" style="color:${diffColor}">${formatCurrency(data.difference)}</div></div>
            </div>
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">
                Suggested matches use amount, direction, payee/description, reference, and code. Every match still requires your approval.
            </div>
            <div class="table-container"><table>
                <thead><tr><th style="width:30px;"></th><th>Date</th><th>Payee / Description</th><th>Reference</th><th>Code</th><th class="amount">Amount</th><th>Find & Match</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="7" style="text-align:center;">No transactions</td></tr>'}</tbody>
            </table></div>`;
    },

    async toggleCleared(reconId, txnId, checkbox) {
        try {
            await API.post(`/banking/reconciliations/${reconId}/toggle/${txnId}`);
            await BankingPage.showReconcileView(reconId);
        } catch (err) {
            checkbox.checked = !checkbox.checked;
            toast(err.message, 'error');
        }
    },

    async finishReconcile(reconId) {
        if (!confirm('Mark this reconciliation as complete?')) return;
        try {
            await API.post(`/banking/reconciliations/${reconId}/complete`);
            toast('Reconciliation completed');
            App.navigate('#/banking');
        } catch (err) { toast(err.message, 'error'); }
    },

    async showMatchModal(reconId, txnId) {
        const [suggestionData, accounts] = await Promise.all([
            API.get(`/banking/transactions/${txnId}/suggestions`),
            API.get('/accounts?active_only=true'),
        ]);
        BankingPage._matchModalAccounts = accounts;
        const txn = suggestionData.transaction;
        const directionLabel = suggestionData.direction === 'inflow' ? 'outstanding invoices' : 'outstanding bills';
        const suggestionHtml = (suggestionData.suggestions || []).map(candidate => `
            <div class="card" style="padding:10px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">
                    <div>
                        <div style="font-weight:700;">${escapeHtml(candidate.label)}</div>
                        <div style="font-size:11px; color:var(--text-muted);">Open ${formatCurrency(candidate.open_amount)} · ${escapeHtml((candidate.reasons || []).join(', '))}</div>
                    </div>
                    <button class="btn btn-sm btn-primary" type="button" onclick="BankingPage.approveMatch(${txnId}, '${candidate.kind}', ${candidate.target_id}, ${reconId})">Approve</button>
                </div>
            </div>`).join('') || '<div style="font-size:11px; color:var(--text-muted);">No likely matches found.</div>';
        const accountOptions = accounts.map(account => `<option value="${account.id}">${escapeHtml(account.account_number || '')} - ${escapeHtml(account.name)}</option>`).join('');
        openModal('Find & Match Statement Line', `
            <div style="margin-bottom:12px;">
                <strong>${escapeHtml(txn.payee || 'Statement line')}</strong><br>
                <span style="font-size:11px; color:var(--text-muted);">${formatDate(txn.date)} · ${escapeHtml(txn.description || '')}</span><br>
                <span style="font-size:11px; color:var(--text-muted);">Reference: ${escapeHtml(txn.reference || '—')} · Code: ${escapeHtml(txn.code || '—')}</span><br>
                <span style="font-size:11px; color:var(--text-muted);">Amount: ${formatCurrency(txn.amount)}</span>
            </div>
            <div class="settings-section" style="margin-bottom:12px;">
                <h3>Likely ${escapeHtml(directionLabel)}</h3>
                ${suggestionHtml}
            </div>
            <div class="settings-section" style="margin-bottom:12px;">
                <h3>Search ${escapeHtml(directionLabel)}</h3>
                <div style="display:flex; gap:8px; margin-bottom:8px;">
                    <input id="bank-match-query-${txnId}" placeholder="Search payee, amount, reference, description, or code" style="flex:1;">
                    <button class="btn btn-secondary" type="button" onclick="BankingPage.searchMatches(${txnId}, ${reconId})">Search</button>
                </div>
                <div id="bank-match-results-${txnId}" style="font-size:11px; color:var(--text-muted);">Search outstanding ${escapeHtml(directionLabel)} to review more choices.</div>
            </div>
            <div class="settings-section">
                <h3>Code to account</h3>
                <div class="form-grid">
                    <div class="form-group full-width"><label>Account</label>
                        <select id="bank-code-account-${txnId}"><option value="">Select account...</option>${accountOptions}</select></div>
                    <div class="form-group full-width"><label>Description</label>
                        <input id="bank-code-description-${txnId}" value="${escapeHtml(txn.description || txn.payee || '')}"></div>
                </div>
                <div class="form-actions">
                    <button class="btn btn-primary" type="button" onclick="BankingPage.codeTransaction(${txnId}, ${reconId})">Code transaction</button>
                    <button class="btn btn-secondary" type="button" onclick="closeModal()">Close</button>
                </div>
            </div>`);
    },

    async searchMatches(txnId, reconId) {
        const queryEl = $(`#bank-match-query-${txnId}`);
        const resultsEl = $(`#bank-match-results-${txnId}`);
        const query = queryEl ? queryEl.value : '';
        try {
            const data = await API.get(`/banking/transactions/${txnId}/search?query=${encodeURIComponent(query)}`);
            const rows = (data.candidates || []).map(candidate => `
                <div class="card" style="padding:10px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">
                        <div>
                            <div style="font-weight:700;">${escapeHtml(candidate.label)}</div>
                            <div style="font-size:11px; color:var(--text-muted);">Open ${formatCurrency(candidate.open_amount)} · ${escapeHtml((candidate.reasons || []).join(', '))}</div>
                        </div>
                        <button class="btn btn-sm btn-primary" type="button" onclick="BankingPage.approveMatch(${txnId}, '${candidate.kind}', ${candidate.target_id}, ${reconId})">Approve</button>
                    </div>
                </div>`).join('');
            resultsEl.innerHTML = rows || '<div style="font-size:11px; color:var(--text-muted);">No matches found.</div>';
        } catch (err) {
            resultsEl.innerHTML = `<div style="font-size:11px; color:var(--danger);">${escapeHtml(err.message)}</div>`;
        }
    },

    async approveMatch(txnId, kind, targetId, reconId) {
        try {
            await API.post(`/banking/transactions/${txnId}/approve-match`, { match_kind: kind, target_id: targetId });
            toast('Statement line matched');
            closeModal();
            await BankingPage.showReconcileView(reconId);
        } catch (err) { toast(err.message, 'error'); }
    },

    async codeTransaction(txnId, reconId) {
        const accountEl = $(`#bank-code-account-${txnId}`);
        const descEl = $(`#bank-code-description-${txnId}`);
        if (!accountEl || !accountEl.value) {
            toast('Select an account to code this transaction', 'error');
            return;
        }
        try {
            await API.post(`/banking/transactions/${txnId}/code`, {
                account_id: parseInt(accountEl.value),
                description: descEl ? descEl.value || null : null,
            });
            toast('Statement line coded');
            closeModal();
            await BankingPage.showReconcileView(reconId);
        } catch (err) { toast(err.message, 'error'); }
    },

    async showStatementImport(bankAccountId) {
        openModal('Import Bank Statement', `
            <form onsubmit="BankingPage.previewStatement(event, ${bankAccountId})">
                <div class="form-group">
                    <label>Select OFX, QFX, or CSV file from your bank</label>
                    <input type="file" name="file" accept=".ofx,.qfx,.csv,text/csv" required id="statement-file">
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Preview Import</button>
                </div>
            </form>
            <div id="statement-preview" style="margin-top:12px;"></div>`);
    },

    async previewStatement(e, bankAccountId) {
        e.preventDefault();
        const file = $('#statement-file').files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const data = await API.postForm('/bank-import/preview', formData);
            let rows = (data.transactions || []).map((t) => `<tr>
                <td>${formatDate(t.date)}</td>
                <td>${escapeHtml(t.payee || '')}</td>
                <td>${escapeHtml(t.description || '')}</td>
                <td>${escapeHtml(t.reference || '')}</td>
                <td>${escapeHtml(t.code || '')}</td>
                <td class="amount" style="${t.amount >= 0 ? 'color:var(--success)' : 'color:var(--danger)'}">${formatCurrency(t.amount)}</td>
            </tr>`).join('');
            $('#statement-preview').innerHTML = `
                <div style="margin-bottom:8px; font-size:11px;">
                    <strong>${data.transactions.length}</strong> transactions found via ${escapeHtml((data.format || '').toUpperCase()) || 'statement import'}.
                </div>
                <div class="table-container" style="max-height:300px; overflow-y:auto;"><table>
                    <thead><tr><th>Date</th><th>Payee</th><th>Description</th><th>Reference</th><th>Code</th><th class="amount">Amount</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table></div>
                <div class="form-actions" style="margin-top:12px;">
                    <button class="btn btn-primary" type="button" onclick="BankingPage.confirmStatementImport(${bankAccountId})">Import ${data.transactions.length} Transactions</button>
                </div>`;
        } catch (err) {
            $('#statement-preview').innerHTML = `<div style="color:var(--danger); font-size:11px;">${escapeHtml(err.message)}</div>`;
        }
    },

    async confirmStatementImport(bankAccountId) {
        try {
            const formData = new FormData();
            formData.append('file', $('#statement-file').files[0]);
            const data = await API.postForm(`/bank-import/import/${bankAccountId}`, formData);
            toast(`Imported ${data.imported} transactions (${data.skipped_duplicates} duplicates skipped)`);
            closeModal();
            BankingPage.viewRegister(bankAccountId);
        } catch (err) { toast(err.message, 'error'); }
    },
};
