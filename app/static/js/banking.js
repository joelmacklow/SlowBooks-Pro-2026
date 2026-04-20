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
                <div class="btn-group">
                    ${canManageBanking ? `<button class="btn btn-secondary" onclick="BankingPage.showRules()">Bank Rules</button>` : ''}
                    ${canManageBanking ? `<button class="btn btn-primary" onclick="BankingPage.showAccountForm()">+ New Bank Account</button>` : ''}
                </div>
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

    async showRules() {
        const [rules, bankAccounts, accounts] = await Promise.all([
            API.get('/banking/rules'),
            API.get('/banking/accounts'),
            API.get('/accounts?active_only=true'),
        ]);
        BankingPage._bankRuleSupport = { bankAccounts, accounts, rules };
        const rows = rules.map(rule => `
            <tr>
                <td>${escapeHtml(rule.name)}</td>
                <td>${rule.priority}</td>
                <td>${escapeHtml(rule.direction)}</td>
                <td>${escapeHtml(rule.bank_account_name || 'All accounts')}</td>
                <td>${escapeHtml(rule.target_account_name || '')}</td>
                <td>${rule.is_active ? 'Active' : 'Disabled'}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" type="button" onclick="BankingPage.editRule(${rule.id})">Edit</button>
                    <button class="btn btn-sm btn-secondary" type="button" onclick="BankingPage.deleteRule(${rule.id})">Delete</button>
                </td>
            </tr>`).join('');
        openModal('Bank Rules', `
            <div class="page-header" style="margin-bottom:12px;">
                <h3 style="margin:0;">Deterministic categorization rules</h3>
                <button class="btn btn-primary" type="button" onclick="BankingPage.showRuleForm()">+ New Rule</button>
            </div>
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:12px;">
                Rules suggest accounts for imported bank lines in explicit priority order. They never post journals until you apply them.
            </div>
            <div class="table-container"><table>
                <thead><tr><th>Name</th><th>Priority</th><th>Direction</th><th>Bank Account</th><th>Target Account</th><th>Status</th><th></th></tr></thead>
                <tbody>${rows || '<tr><td colspan="7" style="text-align:center;">No bank rules yet</td></tr>'}</tbody>
            </table></div>
            <div class="form-actions" style="margin-top:12px;">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>`);
    },

    showRuleForm(ruleId = null) {
        const support = BankingPage._bankRuleSupport || { bankAccounts: [], accounts: [], rules: [] };
        const rule = support.rules.find(item => item.id === ruleId) || null;
        const bankAccountOptions = support.bankAccounts.map(account => (
            `<option value="${account.id}" ${rule && rule.bank_account_id === account.id ? 'selected' : ''}>${escapeHtml(account.name)}</option>`
        )).join('');
        const accountOptions = support.accounts.map(account => (
            `<option value="${account.id}" ${rule && rule.target_account_id === account.id ? 'selected' : ''}>${escapeHtml(account.account_number || '')} - ${escapeHtml(account.name)}</option>`
        )).join('');
        openModal(rule ? 'Edit Bank Rule' : 'New Bank Rule', `
            <form onsubmit="BankingPage.saveRule(event, ${rule ? rule.id : 'null'})">
                <div class="form-grid">
                    <div class="form-group"><label>Name *</label><input name="name" required value="${escapeHtml(rule ? rule.name : '')}"></div>
                    <div class="form-group"><label>Priority *</label><input name="priority" type="number" required value="${rule ? rule.priority : 100}"></div>
                    <div class="form-group"><label>Direction *</label>
                        <select name="direction">
                            <option value="any" ${!rule || rule.direction === 'any' ? 'selected' : ''}>Any</option>
                            <option value="inflow" ${rule && rule.direction === 'inflow' ? 'selected' : ''}>Inflow</option>
                            <option value="outflow" ${rule && rule.direction === 'outflow' ? 'selected' : ''}>Outflow</option>
                        </select>
                    </div>
                    <div class="form-group"><label>Bank account scope</label>
                        <select name="bank_account_id"><option value="">All bank accounts</option>${bankAccountOptions}</select>
                    </div>
                    <div class="form-group full-width"><label>Target account *</label>
                        <select name="target_account_id" required><option value="">Select account...</option>${accountOptions}</select>
                    </div>
                    <div class="form-group"><label>Payee contains</label><input name="payee_contains" value="${escapeHtml(rule ? rule.payee_contains || '' : '')}"></div>
                    <div class="form-group"><label>Description contains</label><input name="description_contains" value="${escapeHtml(rule ? rule.description_contains || '' : '')}"></div>
                    <div class="form-group"><label>Reference contains</label><input name="reference_contains" value="${escapeHtml(rule ? rule.reference_contains || '' : '')}"></div>
                    <div class="form-group"><label>Code equals</label><input name="code_equals" value="${escapeHtml(rule ? rule.code_equals || '' : '')}"></div>
                    <div class="form-group full-width"><label>Default description</label><input name="default_description" value="${escapeHtml(rule ? rule.default_description || '' : '')}"></div>
                    <div class="form-group"><label><input name="is_active" type="checkbox" ${!rule || rule.is_active ? 'checked' : ''}> Active</label></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="BankingPage.showRules()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${rule ? 'Save Rule' : 'Create Rule'}</button>
                </div>
            </form>`);
    },

    async saveRule(e, ruleId = null) {
        e.preventDefault();
        const form = e.target;
        const data = {
            name: form.name.value,
            priority: parseInt(form.priority.value || '100', 10),
            direction: form.direction.value,
            bank_account_id: form.bank_account_id.value ? parseInt(form.bank_account_id.value, 10) : null,
            target_account_id: parseInt(form.target_account_id.value, 10),
            payee_contains: form.payee_contains.value || null,
            description_contains: form.description_contains.value || null,
            reference_contains: form.reference_contains.value || null,
            code_equals: form.code_equals.value || null,
            default_description: form.default_description.value || null,
            is_active: !!form.is_active.checked,
        };
        try {
            if (ruleId) {
                await API.put(`/banking/rules/${ruleId}`, data);
            } else {
                await API.post('/banking/rules', data);
            }
            toast(ruleId ? 'Bank rule updated' : 'Bank rule created');
            await BankingPage.showRules();
        } catch (err) { toast(err.message, 'error'); }
    },

    editRule(ruleId) {
        BankingPage.showRuleForm(ruleId);
    },

    async deleteRule(ruleId) {
        if (!confirm('Delete this bank rule?')) return;
        try {
            await API.del(`/banking/rules/${ruleId}`);
            toast('Bank rule deleted');
            await BankingPage.showRules();
        } catch (err) { toast(err.message, 'error'); }
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
        const ruleSuggestion = transaction.rule_suggestion ? `
            <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin-bottom:6px;">
                <span style="font-size:11px; color:var(--primary); font-weight:700;">Rule: ${escapeHtml(transaction.rule_suggestion.name)}</span>
                <span style="font-size:11px; color:var(--text-muted);">${escapeHtml(transaction.rule_suggestion.target_account_name || '')}</span>
                ${transaction.rule_suggestion.reason ? `<span style="font-size:11px; color:var(--text-muted);">${escapeHtml(transaction.rule_suggestion.reason)}</span>` : ''}
                <button class="btn btn-sm btn-primary" type="button" onclick="BankingPage.applyRule(${transaction.id}, ${transaction.rule_suggestion.id}, ${reconId})">Apply Rule</button>
            </div>` : '';
        const suggestionHtml = (transaction.suggestions || []).slice(0, 2).map(candidate => `
            <button class="btn btn-sm btn-secondary" type="button" onclick="BankingPage.approveMatch(${transaction.id}, '${candidate.kind}', ${candidate.target_id}, ${reconId})">
                ${escapeHtml(candidate.document_number || candidate.label)}
            </button>`).join('');
        return `
            <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
                ${ruleSuggestion}
                ${suggestionHtml || '<span style="font-size:11px; color:var(--text-muted);">No likely matches yet</span>'}
                <button class="btn btn-sm btn-primary" type="button" onclick="BankingPage.showMatchModal(${reconId}, ${transaction.id})">Find & Match</button>
                <button class="btn btn-sm btn-secondary" type="button" onclick="BankingPage.showSplitCodeModal(${transaction.id}, ${reconId})">Split Code</button>
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
                    <button class="btn btn-secondary" onclick="BankingPage.cancelReconcile(${reconId})">Cancel</button>
                    <button class="btn btn-primary" id="recon-finish-btn" onclick="BankingPage.finishReconcile(${reconId})"
                        ${Math.abs(data.difference) < 0.01 ? '' : 'disabled'}>Finish Reconciliation</button>
                </div>
            </div>
            <div class="card-grid" style="margin-bottom:16px;">
                <div class="card"><div class="card-header">${escapeHtml(data.statement_label || 'Statement Balance')}</div>
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

    async cancelReconcile(reconId) {
        const data = BankingPage._reconcileContext?.data;
        if (data?.import_batch_id) {
            if (!confirm('Cancel this imported reconciliation and remove the staged imported transactions?')) return;
            try {
                await API.post(`/banking/reconciliations/${reconId}/cancel`);
                toast('Imported reconciliation cancelled');
                App.navigate('#/banking');
            } catch (err) { toast(err.message, 'error'); }
            return;
        }
        App.navigate('#/banking');
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

    async showSplitCodeModal(txnId, reconId) {
        const [suggestionData, accounts] = await Promise.all([
            API.get(`/banking/transactions/${txnId}/suggestions`),
            API.get('/accounts?active_only=true'),
        ]);
        BankingPage._splitCodeAccounts = accounts.filter(account => ['expense', 'income', 'asset', 'liability', 'equity', 'cogs'].includes(account.account_type));
        const txn = suggestionData.transaction;
        openModal('Split Code Statement Line', `
            <div style="margin-bottom:12px;">
                <strong>${escapeHtml(txn.payee || 'Statement line')}</strong><br>
                <span style="font-size:11px; color:var(--text-muted);">${formatDate(txn.date)} · ${escapeHtml(txn.description || '')}</span><br>
                <span style="font-size:11px; color:var(--text-muted);">Reference: ${escapeHtml(txn.reference || '—')} · Code: ${escapeHtml(txn.code || '—')}</span><br>
                <span style="font-size:11px; color:var(--text-muted);">Amount to split: ${formatCurrency(Math.abs(txn.amount || 0))}</span>
            </div>
            <div id="split-code-lines"></div>
            <button class="btn btn-sm btn-secondary" type="button" style="margin-bottom:12px;" onclick="BankingPage.addSplitCodeLine()">+ Add Split Line</button>
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:12px;">Split total: <span id="split-code-total">${formatCurrency(0)}</span></div>
            <div class="form-actions">
                <button class="btn btn-secondary" type="button" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" type="button" onclick="BankingPage.submitSplitCode(${txnId}, ${reconId}, ${Math.abs(txn.amount || 0)})">Apply Split Coding</button>
            </div>`);
        BankingPage._splitCodeLineCount = 0;
        BankingPage.addSplitCodeLine();
        BankingPage.addSplitCodeLine();
    },

    splitCodeLineHtml(idx) {
        const options = (BankingPage._splitCodeAccounts || []).map(account =>
            `<option value="${account.id}">${escapeHtml(account.account_number || '')} - ${escapeHtml(account.name)}</option>`
        ).join('');
        return `<div class="form-grid split-code-line" data-split-line="${idx}" style="margin-bottom:8px;">
            <div class="form-group"><label>Account</label><select class="split-account"><option value="">Select account...</option>${options}</select></div>
            <div class="form-group"><label>Amount</label><input class="split-amount" type="number" step="0.01" value="0" oninput="BankingPage.recalcSplitCode()"></div>
            <div class="form-group full-width"><label>Description</label><input class="split-description"></div>
            <div class="form-group"><button class="btn btn-sm btn-secondary" type="button" onclick="BankingPage.removeSplitCodeLine(${idx})">Remove</button></div>
        </div>`;
    },

    addSplitCodeLine() {
        const idx = BankingPage._splitCodeLineCount++;
        $('#split-code-lines').insertAdjacentHTML('beforeend', BankingPage.splitCodeLineHtml(idx));
    },

    removeSplitCodeLine(idx) {
        const row = $(`[data-split-line="${idx}"]`);
        if (row) row.remove();
        BankingPage.recalcSplitCode();
    },

    recalcSplitCode() {
        let total = 0;
        $$('.split-code-line').forEach((row) => {
            total += parseFloat(row.querySelector('.split-amount')?.value) || 0;
        });
        const totalEl = $('#split-code-total');
        if (totalEl) totalEl.textContent = formatCurrency(total);
    },

    async submitSplitCode(txnId, reconId, absoluteAmount) {
        const splits = $$('.split-code-line')
            .map((row) => ({
                account_id: row.querySelector('.split-account')?.value ? parseInt(row.querySelector('.split-account').value, 10) : null,
                amount: parseFloat(row.querySelector('.split-amount')?.value) || 0,
                description: row.querySelector('.split-description')?.value || null,
            }))
            .filter((line) => line.account_id && line.amount > 0);
        if (splits.length < 2) {
            toast('Add at least two split lines', 'error');
            return;
        }
        const total = splits.reduce((sum, line) => sum + line.amount, 0);
        if (Math.abs(total - absoluteAmount) > 0.009) {
            toast('Split lines must total the statement amount exactly', 'error');
            return;
        }
        try {
            await API.post(`/banking/transactions/${txnId}/code-split`, { splits });
            toast('Statement line split coded');
            closeModal();
            await BankingPage.showReconcileView(reconId);
        } catch (err) { toast(err.message, 'error'); }
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

    async applyRule(txnId, ruleId, reconId) {
        try {
            await API.post(`/banking/transactions/${txnId}/apply-rule`, { rule_id: ruleId });
            toast('Bank rule applied');
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
            if (data.statement_date && data.statement_total !== undefined && data.statement_total !== null) {
                const recon = await API.post('/banking/reconciliations', {
                    bank_account_id: bankAccountId,
                    statement_date: data.statement_date,
                    statement_balance: data.statement_total,
                    import_batch_id: data.import_batch_id || null,
                });
                closeModal();
                await BankingPage.showReconcileView(recon.id);
                return;
            }
            closeModal();
            BankingPage.viewRegister(bankAccountId);
        } catch (err) { toast(err.message, 'error'); }
    },
};
