/**
 * Credit Memos — issue credits against customers, apply to invoices
 * Feature 5: Credit memo UI aligned to the purchase-order detail workflow
 */
const CreditMemosPage = {
    _customers: [],
    _items: [],
    _detailState: null,
    lineCount: 0,

    async render() {
        const memos = await API.get('/credit-memos');
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Credit Memos</h2>
                ${canManageSales ? `<button class="btn btn-primary" onclick="CreditMemosPage.startNew()">+ New Credit Memo</button>` : ''}
            </div>`;

        if (memos.length === 0) {
            html += '<div class="empty-state"><p>No credit memos yet</p></div>';
        } else {
            html += `<div class="table-container"><table>
                <thead><tr><th>#</th><th>Customer</th><th>Date</th><th>Status</th>
                <th class="amount">Total</th><th class="amount">Remaining</th><th>Actions</th></tr></thead><tbody>`;
            for (const m of memos) {
                html += `<tr>
                    <td><strong>${escapeHtml(m.memo_number)}</strong></td>
                    <td>${escapeHtml(m.customer_name || '')}</td>
                    <td>${formatDate(m.date)}</td>
                    <td>${statusBadge(m.status)}</td>
                    <td class="amount">${formatCurrency(m.total)}</td>
                    <td class="amount">${formatCurrency(m.balance_remaining)}</td>
                    <td class="actions">
                        <button class="btn btn-sm btn-secondary" onclick="CreditMemosPage.open(${m.id})">Open</button>
                        ${canManageSales && m.status === 'issued' ? `<button class="btn btn-sm btn-primary" onclick="CreditMemosPage.showApply(${m.id})">Apply</button>` : ''}
                    </td>
                </tr>`;
            }
            html += '</tbody></table></div>';
        }
        return html;
    },

    async startNew() {
        await CreditMemosPage._loadEditorContext(null);
        App.navigate('#/credit-memos/detail');
    },

    async open(id) {
        await CreditMemosPage._loadEditorContext(id);
        App.navigate('#/credit-memos/detail');
    },

    async showForm(id = null) {
        if (id) return CreditMemosPage.open(id);
        return CreditMemosPage.startNew();
    },

    async _loadEditorContext(id = null) {
        const [customers, items, gstCodes] = await Promise.all([
            API.get('/customers?active_only=true'),
            API.get('/items?active_only=true'),
            API.get('/gst-codes'),
        ]);
        App.gstCodes = gstCodes;
        CreditMemosPage._customers = customers;
        CreditMemosPage._items = items;

        let memo = {
            id: null,
            customer_id: '',
            memo_number: '',
            status: 'issued',
            original_invoice_id: null,
            date: todayISO(),
            subtotal: 0,
            tax_rate: 0,
            tax_amount: 0,
            total: 0,
            amount_applied: 0,
            balance_remaining: 0,
            notes: '',
            lines: [],
        };
        if (id) memo = await API.get(`/credit-memos/${id}`);
        if (!memo.lines || memo.lines.length === 0) memo.lines = [{ item_id: '', description: '', quantity: 1, rate: 0, gst_code: 'GST15' }];
        CreditMemosPage.lineCount = memo.lines.length;
        CreditMemosPage._detailState = memo;
    },

    _totals(lines) {
        return calculateGstTotals((lines || []).map(line => ({
            quantity: parseFloat(line.quantity) || 0,
            rate: parseFloat(line.rate) || 0,
            gst_code: line.gst_code || 'GST15',
            gst_rate: line.gst_rate || 0,
        })));
    },

    renderDetailScreen() {
        const memo = CreditMemosPage._detailState;
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        if (!memo) {
            return `<div class="empty-state"><p>Select a credit memo or create a new one first.</p><p style="margin-top:8px;"><button class="btn btn-primary" onclick="App.navigate('#/credit-memos')">Back to Credit Memos</button></p></div>`;
        }
        const totals = CreditMemosPage._totals(memo.lines || []);
        const customerOptions = CreditMemosPage._customers.map(c => `<option value="${c.id}" ${memo.customer_id==c.id?'selected':''}>${escapeHtml(c.name)}</option>`).join('');
        const applications = memo.applications || [];
        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Sales</div>
                    <h2>${memo.id ? `Credit Memo ${escapeHtml(memo.memo_number || '')}` : 'New Credit Memo'}</h2>
                </div>
                <div class="actions">
                    <button class="btn btn-secondary" onclick="App.navigate('#/credit-memos')">Back to Credit Memos</button>
                </div>
            </div>
            <form onsubmit="CreditMemosPage.save(event, ${memo.id || 'null'})">
                <div class="settings-section">
                    <div class="form-grid">
                        <div class="form-group"><label>Customer *</label>
                            <select name="customer_id" required ${canManageSales ? '' : 'disabled'}><option value="">Select...</option>${customerOptions}</select></div>
                        <div class="form-group"><label>Date *</label>
                            <input name="date" type="date" required value="${memo.date || ''}" ${canManageSales ? '' : 'disabled'}></div>
                        <div class="form-group"><label>Memo Number</label>
                            <input value="${escapeHtml(memo.memo_number || 'Assigned on save')}" disabled></div>
                        <div class="form-group"><label>Status</label>
                            <input value="${escapeHtml(memo.status || 'issued')}" disabled></div>
                        <input name="tax_rate" type="hidden" value="${(memo.tax_rate * 100) || 0}">
                    </div>
                </div>
                <div class="settings-section">
                    <h3>Credit Lines</h3>
                    <table class="line-items-table">
                        <thead><tr><th>Item</th><th>Description</th><th class="col-qty">Qty</th><th>GST</th><th class="col-rate">Rate</th><th class="col-amount">Amount</th><th></th></tr></thead>
                        <tbody id="cm-lines">
                            ${(memo.lines || []).map((l, i) => CreditMemosPage.lineRowHtml(i, l, CreditMemosPage._items, canManageSales)).join('')}
                        </tbody>
                    </table>
                    ${canManageSales ? '<button type="button" class="btn btn-sm btn-secondary" style="margin-top:8px;" onclick="CreditMemosPage.addLine()">+ Add Line</button>' : ''}
                </div>
                <div class="settings-section">
                    <div style="display:grid; grid-template-columns: 1.4fr 0.8fr; gap:16px; align-items:start;">
                        <div class="form-group"><label>Notes</label>
                            <textarea name="notes" rows="5" ${canManageSales ? '' : 'disabled'}>${escapeHtml(memo.notes || '')}</textarea></div>
                        <div>
                            <div class="table-container"><table>
                                <tbody>
                                    <tr><td><strong>Subtotal</strong></td><td class="amount" id="cm-subtotal">${formatCurrency(totals.subtotal)}</td></tr>
                                    <tr><td><strong>Tax</strong></td><td class="amount" id="cm-tax">${formatCurrency(totals.tax_amount)}</td></tr>
                                    <tr><td><strong>Total</strong></td><td class="amount" id="cm-total">${formatCurrency(totals.total)}</td></tr>
                                    ${memo.id ? `<tr><td><strong>Applied</strong></td><td class="amount">${formatCurrency(memo.amount_applied || 0)}</td></tr>
                                    <tr><td><strong>Remaining</strong></td><td class="amount">${formatCurrency(memo.balance_remaining || 0)}</td></tr>` : ''}
                                </tbody>
                            </table></div>
                        </div>
                    </div>
                </div>
                ${memo.id && applications.length ? `<div class="settings-section">
                    <h3>Applied To Invoices</h3>
                    <div class="table-container"><table>
                        <thead><tr><th>Invoice</th><th class="amount">Applied Amount</th></tr></thead>
                        <tbody>
                            ${applications.map(application => `<tr>
                                <td><strong>${escapeHtml(application.invoice_number || `Invoice #${application.invoice_id}`)}</strong></td>
                                <td class="amount">${formatCurrency(application.amount)}</td>
                            </tr>`).join('')}
                        </tbody>
                    </table></div>
                </div>` : ''}
                ${canManageSales ? `<div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.navigate('#/credit-memos')">Cancel</button>
                    ${memo.id ? '' : `<button type="button" class="btn btn-secondary" onclick="CreditMemosPage.submitWithAction(event, null, 'add-new')">Create & Add New</button>`}
                    <button type="button" class="btn btn-secondary" onclick="${memo.id ? `CreditMemosPage.openPdf(${memo.id}, '${escapeHtml(memo.memo_number || '')}')` : `CreditMemosPage.submitWithAction(event, null, 'pdf')`}">${memo.id ? 'Print / PDF' : 'Create & Print / PDF'}</button>
                    <button type="button" class="btn btn-secondary" onclick="${memo.id ? `CreditMemosPage.emailCreditMemo(${memo.id})` : `CreditMemosPage.submitWithAction(event, null, 'email')`}">${memo.id ? 'Email Credit Note' : 'Create & Email'}</button>
                    ${memo.id && memo.status === 'issued' ? `<button type="button" class="btn btn-primary" onclick="CreditMemosPage.showApply(${memo.id})">Apply Credit</button>` : ''}
                    <button type="submit" class="btn btn-primary">${memo.id ? 'Update Credit Memo' : 'Create'}</button>
                </div>` : ''}
            </form>`;
    },

    lineRowHtml(idx, line, items, canManage = true) {
        const itemOpts = items.map(i => `<option value="${i.id}" ${line.item_id==i.id?'selected':''}>${escapeHtml(i.name)}</option>`).join('');
        return `<tr data-cmline="${idx}">
            <td><select class="line-item" onchange="CreditMemosPage.itemSelected(${idx})" ${canManage ? '' : 'disabled'}><option value="">--</option>${itemOpts}</select></td>
            <td><input class="line-desc" value="${escapeHtml(line.description || '')}" ${canManage ? '' : 'disabled'}></td>
            <td><input class="line-qty" type="number" step="0.01" value="${line.quantity || 1}" oninput="CreditMemosPage.recalc()" ${canManage ? '' : 'disabled'}></td>
            <td><select class="line-gst" onchange="CreditMemosPage.recalc()" ${canManage ? '' : 'disabled'}>${gstOptionsHtml(line.gst_code || 'GST15')}</select></td>
            <td><input class="line-rate" type="number" step="0.01" value="${line.rate || 0}" oninput="CreditMemosPage.recalc()" ${canManage ? '' : 'disabled'}></td>
            <td class="col-amount line-amount">${formatCurrency((line.quantity||1) * (line.rate||0))}</td>
            <td>${canManage ? `<button type="button" class="btn btn-sm btn-secondary" onclick="CreditMemosPage.removeLine(${idx})">Remove</button>` : ''}</td>
        </tr>`;
    },

    addLine() {
        const idx = CreditMemosPage.lineCount++;
        $('#cm-lines').insertAdjacentHTML('beforeend', CreditMemosPage.lineRowHtml(idx, {}, CreditMemosPage._items, true));
    },

    removeLine(idx) {
        const row = $(`[data-cmline="${idx}"]`);
        if (row) row.remove();
        CreditMemosPage.recalc();
    },

    itemSelected(idx) {
        const row = $(`[data-cmline="${idx}"]`);
        const item = CreditMemosPage._items.find(i => i.id == row.querySelector('.line-item').value);
        if (item) {
            row.querySelector('.line-desc').value = item.description || item.name;
            row.querySelector('.line-rate').value = item.rate;
            CreditMemosPage.recalc();
        }
    },

    recalc() {
        const lines = [];
        $$('#cm-lines tr').forEach((row) => {
            const payload = readGstLinePayload(row);
            const amount = payload.quantity * payload.rate;
            lines.push(payload);
            const amountCell = row.querySelector('.line-amount');
            if (amountCell) amountCell.textContent = formatCurrency(amount);
        });
        const totals = calculateGstTotals(lines);
        if ($('#cm-subtotal')) $('#cm-subtotal').textContent = formatCurrency(totals.subtotal);
        if ($('#cm-tax')) $('#cm-tax').textContent = formatCurrency(totals.tax_amount);
        if ($('#cm-total')) $('#cm-total').textContent = formatCurrency(totals.total);
    },

    async openPdf(id, memoNumber) {
        API.open(`/credit-memos/${id}/pdf`, `credit-memo-${memoNumber}.pdf`);
    },

    async emailCreditMemo(id) {
        const memo = await API.get(`/credit-memos/${id}`);
        const customer = memo.customer_id ? await API.get(`/customers/${memo.customer_id}`) : null;
        App.showDocumentEmailModal({
            title: `Email Credit Note #${memo.memo_number}`,
            endpoint: `/credit-memos/${id}/email`,
            recipient: customer?.email || '',
            defaultSubject: `Credit Note #${memo.memo_number}`,
            successMessage: 'Credit note emailed',
        });
    },

    async submitWithAction(e, id, action) {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        const form = e?.target?.form || e?.target?.closest?.('form');
        if (!form) return;
        await CreditMemosPage.save({ preventDefault() {}, target: form }, id, action);
    },

    async save(e, id = null, afterAction = null) {
        e.preventDefault();
        const form = e.target;
        const lines = [];
        $$('#cm-lines tr').forEach((row, i) => {
            const gst = readGstLinePayload(row);
            lines.push({
                item_id: row.querySelector('.line-item')?.value ? parseInt(row.querySelector('.line-item').value) : null,
                description: row.querySelector('.line-desc')?.value || '',
                quantity: gst.quantity,
                rate: gst.rate,
                gst_code: gst.gst_code,
                gst_rate: gst.gst_rate,
                line_order: i,
            });
        });
        try {
            let savedMemo;
            const payload = {
                customer_id: parseInt(form.customer_id.value),
                date: form.date.value,
                tax_rate: (parseFloat(form.tax_rate.value) || 0) / 100,
                notes: form.notes.value || null,
                lines,
            };
            if (id) { savedMemo = await API.put(`/credit-memos/${id}`, payload); toast('Credit memo updated'); }
            else { savedMemo = await API.post('/credit-memos', payload); toast('Credit memo created'); }

            if (afterAction === 'pdf' && savedMemo?.id) {
                CreditMemosPage._detailState = savedMemo;
                App.navigate('#/credit-memos/detail');
                CreditMemosPage.openPdf(savedMemo.id, savedMemo.memo_number || 'credit-memo');
                return;
            }
            if (afterAction === 'email' && savedMemo?.id) {
                CreditMemosPage._detailState = savedMemo;
                App.navigate('#/credit-memos/detail');
                await CreditMemosPage.emailCreditMemo(savedMemo.id);
                return;
            }
            if (afterAction === 'add-new') {
                await CreditMemosPage._loadEditorContext(null);
                App.navigate('#/credit-memos/detail');
                return;
            }

            CreditMemosPage._detailState = null;
            App.navigate('#/credit-memos');
        } catch (err) { toast(err.message, 'error'); }
    },

    async showApply(cmId) {
        const cm = await API.get(`/credit-memos/${cmId}`);
        const invoices = await API.get(`/invoices?customer_id=${cm.customer_id}`);
        const openInv = invoices.filter(i => i.status !== 'void' && i.status !== 'paid' && i.balance_due > 0);

        let rows = openInv.map(inv => `
            <tr>
                <td>${escapeHtml(inv.invoice_number)}</td>
                <td class="amount">${formatCurrency(inv.balance_due)}</td>
                <td><input type="number" step="0.01" class="apply-amt" data-inv="${inv.id}" value="0" style="width:80px;"></td>
            </tr>`).join('');
        if (!rows) rows = '<tr><td colspan="3">No open invoices for this customer</td></tr>';

        openModal(`Apply Credit ${cm.memo_number}`, `
            <p style="margin-bottom:8px;">Credit remaining: <strong>${formatCurrency(cm.balance_remaining)}</strong></p>
            <div class="table-container"><table>
                <thead><tr><th>Invoice</th><th class="amount">Balance</th><th class="amount">Apply</th></tr></thead>
                <tbody>${rows}</tbody>
            </table></div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="CreditMemosPage.doApply(${cmId})">Apply Credit</button>
            </div>`);
    },

    async doApply(cmId) {
        const inputs = $$('.apply-amt');
        for (const input of inputs) {
            const amt = parseFloat(input.value) || 0;
            if (amt > 0) {
                try {
                    await API.post(`/credit-memos/${cmId}/apply`, {
                        invoice_id: parseInt(input.dataset.inv), amount: amt,
                    });
                } catch (err) { toast(err.message, 'error'); return; }
            }
        }
        toast('Credit applied');
        closeModal();
        await CreditMemosPage.open(cmId);
    },
};
