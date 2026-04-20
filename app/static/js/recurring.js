/**
 * Recurring Invoices — schedule automatic invoice generation
 * Feature 2: Weekly/monthly/quarterly/yearly templates
 */
const RecurringPage = {
    _items: [],
    _customers: [],
    _settings: {},
    _detailState: null,
    lineCount: 0,

    async render() {
        const recs = await API.get('/recurring');
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Recurring Invoices</h2>
                <div class="btn-group">
                    ${canManageSales ? `<button class="btn btn-primary" onclick="RecurringPage.startNew()">+ New Recurring</button>
                    <button class="btn btn-secondary" onclick="RecurringPage.generateNow()">Generate Due Now</button>` : ''}
                </div>
            </div>`;

        if (recs.length === 0) {
            html += '<div class="empty-state"><p>No recurring invoices set up</p></div>';
        } else {
            html += `<div class="table-container"><table>
                <thead><tr><th>Customer</th><th>Frequency</th><th>Next Due</th><th>Active</th><th>Created</th><th>Actions</th></tr></thead><tbody>`;
            for (const r of recs) {
                html += `<tr>
                    <td><strong>${escapeHtml(r.customer_name || '')}</strong></td>
                    <td>${r.frequency}</td>
                    <td>${formatDate(r.next_due)}</td>
                    <td>${r.is_active ? '<span class="badge badge-paid">Active</span>' : '<span class="badge badge-draft">Inactive</span>'}</td>
                    <td style="font-family:var(--font-mono);">${r.invoices_created}</td>
                    <td class="actions">
                        ${canManageSales ? `<button class="btn btn-sm btn-secondary" onclick="RecurringPage.open(${r.id})">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="RecurringPage.del(${r.id})">Delete</button>` : ''}
                    </td>
                </tr>`;
            }
            html += '</tbody></table></div>';
        }
        return html;
    },

    async startNew(originHash = '#/recurring') {
        App.setDetailOrigin('#/recurring/detail', originHash);
        await RecurringPage._loadEditorContext(null);
        App.navigate('#/recurring/detail');
    },

    async open(id, originHash = '#/recurring') {
        App.setDetailOrigin('#/recurring/detail', originHash);
        await RecurringPage._loadEditorContext(id);
        App.navigate('#/recurring/detail');
    },

    async showForm(id = null) {
        if (id) return RecurringPage.open(id);
        return RecurringPage.startNew();
    },

    async _loadEditorContext(id = null) {
        const [customers, items, settings, gstCodes] = await Promise.all([
            API.get('/customers?active_only=true'),
            API.get('/items?active_only=true'),
            API.get('/settings'),
            API.get('/gst-codes'),
        ]);
        App.gstCodes = gstCodes;
        RecurringPage._items = items;
        RecurringPage._customers = customers;
        RecurringPage._settings = settings;

        let rec = {
            id: null,
            customer_id: '',
            frequency: 'monthly',
            start_date: todayISO(),
            end_date: '',
            terms: settings.default_terms || 'Net 30',
            tax_rate: (parseFloat(settings.default_tax_rate || '0') || 0) / 100,
            notes: '',
            lines: [],
        };
        if (id) rec = await API.get(`/recurring/${id}`);
        if (!rec.lines || rec.lines.length === 0) rec.lines = [{ item_id: '', description: '', quantity: 1, rate: 0, gst_code: 'GST15' }];
        RecurringPage.lineCount = rec.lines.length;
        RecurringPage._detailState = rec;
    },

    _totals(lines) {
        return calculateGstTotals((lines || []).map(line => ({
            quantity: parseFloat(line.quantity) || 0,
            rate: parseFloat(line.rate) || 0,
            gst_code: line.gst_code || 'GST15',
            gst_rate: line.gst_rate || 0,
        })));
    },

    customerOptionsHtml(selectedId = null) {
        return (RecurringPage._customers || []).map(c => `<option value="${c.id}" ${selectedId == c.id ? 'selected' : ''}>${escapeHtml(c.name)}</option>`).join('');
    },

    itemOptionLabel(item) {
        return item.code ? `${escapeHtml(item.code)} — ${escapeHtml(item.name)}` : escapeHtml(item.name);
    },

    itemSearchValues(item) {
        const values = [];
        if (item?.code) values.push(String(item.code));
        if (item?.name) values.push(String(item.name));
        if (item?.code && item?.name) values.push(`${item.code} — ${item.name}`);
        return [...new Set(values)];
    },

    itemMatchesFilter(item, query) {
        const needle = String(query || '').trim().toLowerCase();
        if (!needle) return true;
        return RecurringPage.itemSearchValues(item).some(candidate => candidate.toLowerCase().includes(needle));
    },

    filteredItems(query, selectedItemId = null) {
        return (RecurringPage._items || []).filter(item => {
            if (selectedItemId && String(item.id) === String(selectedItemId)) return true;
            return RecurringPage.itemMatchesFilter(item, query);
        });
    },

    itemOptionsHtml(items, selectedItemId = null) {
        return items.map(i => `<option value="${i.id}" ${selectedItemId == i.id ? 'selected' : ''}>${RecurringPage.itemOptionLabel(i)}</option>`).join('');
    },

    renderDetailScreen() {
        const rec = RecurringPage._detailState;
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        if (!rec) {
            return `<div class="empty-state"><p>Select a recurring invoice or create a new one first.</p><p style="margin-top:8px;"><button class="btn btn-primary" onclick="App.navigate('#/recurring')">Back to Recurring Invoices</button></p></div>`;
        }
        const totals = RecurringPage._totals(rec.lines || []);
        const customerOptions = RecurringPage.customerOptionsHtml(rec.customer_id);
        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Sales</div>
                    <h2>${rec.id ? 'Edit Recurring Invoice' : 'New Recurring Invoice'}</h2>
                </div>
                <div class="actions">
                    <button class="btn btn-secondary" onclick="App.navigateBackToDetailOrigin('#/recurring/detail', '#/recurring')">${App.detailBackLabel('#/recurring/detail', '#/recurring', 'Recurring Invoices')}</button>
                </div>
            </div>
            <form id="recurring-form" onsubmit="RecurringPage.save(event, ${rec.id || 'null'})">
                <div class="settings-section">
                    <div class="form-grid">
                        <div class="form-group"><label>Customer *</label>
                            <select name="customer_id" required onchange="RecurringPage.customerSelected(this.value)" ${canManageSales ? '' : 'disabled'}><option value="">Select...</option>${customerOptions}</select></div>
                        <div class="form-group"><label>Frequency *</label>
                            <select name="frequency" ${canManageSales ? '' : 'disabled'}>
                                ${['weekly','monthly','quarterly','yearly'].map(f =>
                                    `<option value="${f}" ${rec.frequency===f?'selected':''}>${f}</option>`).join('')}
                            </select></div>
                        <div class="form-group"><label>Start Date *</label>
                            <input name="start_date" type="date" required value="${rec.start_date || ''}" ${canManageSales ? '' : 'disabled'}></div>
                        <div class="form-group"><label>End Date</label>
                            <input name="end_date" type="date" value="${rec.end_date || ''}" ${canManageSales ? '' : 'disabled'}></div>
                        <div class="form-group"><label>Terms</label>
                            <select name="terms" id="recurring-terms" ${canManageSales ? '' : 'disabled'}>
                                ${['Net 15','Net 30','Net 45','Net 60','Due on Receipt'].map(t =>
                                    `<option value="${t}" ${rec.terms===t?'selected':''}>${t}</option>`).join('')}
                            </select></div>
                        <div class="form-group"><label>Next Due</label>
                            <input value="${escapeHtml(rec.next_due || rec.start_date || 'Calculated on save')}" disabled></div>
                        <div class="form-group"><label>Status</label>
                            <input value="${rec.is_active === false ? 'inactive' : 'active'}" disabled></div>
                        <div class="form-group"><label>Invoices Created</label>
                            <input value="${escapeHtml(String(rec.invoices_created || 0))}" disabled></div>
                        <input name="tax_rate" type="hidden" value="${(parseFloat(rec.tax_rate || 0) * 100) || 0}">
                    </div>
                </div>
                <div class="settings-section">
                    <h3>Line Items</h3>
                    <table class="line-items-table">
                        <thead><tr><th>Item</th><th>Description</th><th class="col-qty">Qty</th><th>GST</th><th class="col-rate">Rate</th><th class="col-amount">Amount</th><th></th></tr></thead>
                        <tbody id="rec-lines">
                            ${(rec.lines || []).map((l, i) => RecurringPage.lineRowHtml(i, l, RecurringPage._items, canManageSales)).join('')}
                        </tbody>
                    </table>
                    ${canManageSales ? '<button type="button" class="btn btn-sm btn-secondary" style="margin-top:8px;" onclick="RecurringPage.addLine()">+ Add Line</button>' : ''}
                </div>
                <div class="settings-section">
                    <div style="display:grid; grid-template-columns: 1.4fr 0.8fr; gap:16px; align-items:start;">
                        <div class="form-group"><label>Notes</label>
                            <textarea name="notes" rows="5" ${canManageSales ? '' : 'disabled'}>${escapeHtml(rec.notes || '')}</textarea></div>
                        <div>
                            <div class="table-container"><table>
                                <tbody>
                                    <tr><td><strong>Subtotal</strong></td><td class="amount" id="rec-subtotal">${formatCurrency(totals.subtotal)}</td></tr>
                                    <tr><td><strong>Tax</strong></td><td class="amount" id="rec-tax">${formatCurrency(totals.tax_amount)}</td></tr>
                                    <tr><td><strong>Template Total</strong></td><td class="amount" id="rec-total">${formatCurrency(totals.total)}</td></tr>
                                </tbody>
                            </table></div>
                        </div>
                    </div>
                </div>
                ${canManageSales ? `<div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.navigateBackToDetailOrigin('#/recurring/detail', '#/recurring')">Cancel</button>
                    ${rec.id ? '' : `<button type="button" class="btn btn-secondary" onclick="RecurringPage.submitWithAction(event, null, 'add-new')">Create & Add New</button>`}
                    <button type="submit" class="btn btn-primary">${rec.id ? 'Update Recurring Invoice' : 'Create'}</button>
                </div>` : ''}
            </form>`;
    },

    customerSelected(customerId) {
        const customer = RecurringPage._customers.find(c => c.id == customerId);
        const termsField = $('#recurring-terms');
        if (customer && termsField && customer.terms) {
            termsField.value = customer.terms;
        }
    },

    lineRowHtml(idx, line, items, canManage = true) {
        const itemOpts = RecurringPage.itemOptionsHtml(items, line.item_id);
        return `<tr data-recline="${idx}">
            <td><select class="line-item" onchange="RecurringPage.itemSelected(${idx})" onkeydown="RecurringPage.handleItemKeydown(${idx}, event)" onblur="RecurringPage.resetItemFilter(${idx})" ${canManage ? '' : 'disabled'}><option value="">--</option>${itemOpts}</select></td>
            <td><input class="line-desc" value="${escapeHtml(line.description || '')}" ${canManage ? '' : 'disabled'}></td>
            <td><input class="line-qty" type="number" step="0.01" value="${line.quantity || 1}" oninput="RecurringPage.recalc()" ${canManage ? '' : 'disabled'}></td>
            <td><select class="line-gst" onchange="RecurringPage.recalc()" ${canManage ? '' : 'disabled'}>${gstOptionsHtml(line.gst_code || 'GST15')}</select></td>
            <td><input class="line-rate" type="number" step="0.01" value="${line.rate || 0}" oninput="RecurringPage.recalc()" ${canManage ? '' : 'disabled'}></td>
            <td class="col-amount line-amount">${formatCurrency((line.quantity||1) * (line.rate||0))}</td>
            <td>${canManage ? `<button type="button" class="btn btn-sm btn-secondary" onclick="RecurringPage.removeLine(${idx})">Remove</button>` : ''}</td>
        </tr>`;
    },

    addLine() {
        const tbody = $('#rec-lines');
        const idx = RecurringPage.lineCount++;
        tbody.insertAdjacentHTML('beforeend', RecurringPage.lineRowHtml(idx, {}, RecurringPage._items, true));
    },

    removeLine(idx) {
        const row = $(`[data-recline="${idx}"]`);
        if (row) row.remove();
        RecurringPage.recalc();
    },

    itemSelected(idx) {
        const row = $(`[data-recline="${idx}"]`);
        const itemId = row.querySelector('.line-item').value;
        const item = RecurringPage._items.find(i => i.id == itemId);
        if (item) {
            row.querySelector('.line-desc').value = item.description || item.name;
            row.querySelector('.line-rate').value = item.rate;
            RecurringPage.recalc();
        }
    },

    applyItemFilter(idx, query) {
        const row = $(`[data-recline="${idx}"]`);
        if (!row) return;
        const itemSelect = row.querySelector('.line-item');
        if (!itemSelect) return;
        const currentValue = itemSelect.value;
        const filtered = RecurringPage.filteredItems(query, currentValue);
        row.dataset.itemFilterQuery = query;
        itemSelect.innerHTML = `<option value="">--</option>${RecurringPage.itemOptionsHtml(filtered, currentValue)}`;
        if (!(filtered || []).some(item => String(item.id) === String(currentValue))) {
            itemSelect.value = '';
        }
    },

    handleItemKeydown(idx, event) {
        if (event.metaKey || event.ctrlKey || event.altKey) return;
        const row = $(`[data-recline="${idx}"]`);
        if (!row) return;
        const currentQuery = row.dataset.itemFilterQuery || '';
        if (event.key === 'Escape') {
            RecurringPage.resetItemFilter(idx);
            event.preventDefault();
            return;
        }
        if (event.key === 'Backspace') {
            RecurringPage.applyItemFilter(idx, currentQuery.slice(0, -1));
            event.preventDefault();
            return;
        }
        if (event.key.length === 1) {
            RecurringPage.applyItemFilter(idx, currentQuery + event.key);
            event.preventDefault();
        }
    },

    resetItemFilter(idx) {
        const row = $(`[data-recline="${idx}"]`);
        if (!row) return;
        row.dataset.itemFilterQuery = '';
        const itemSelect = row.querySelector('.line-item');
        if (!itemSelect) return;
        const currentValue = itemSelect.value;
        itemSelect.innerHTML = `<option value="">--</option>${RecurringPage.itemOptionsHtml(RecurringPage._items || [], currentValue)}`;
        if (currentValue) itemSelect.value = currentValue;
    },

    recalc() {
        const lines = [];
        $$('#rec-lines tr').forEach(row => {
            const payload = readGstLinePayload(row);
            const amount = payload.quantity * payload.rate;
            lines.push(payload);
            const amountCell = row.querySelector('.line-amount');
            if (amountCell) amountCell.textContent = formatCurrency(amount);
        });
        const totals = calculateGstTotals(lines);
        if ($('#rec-subtotal')) $('#rec-subtotal').textContent = formatCurrency(totals.subtotal);
        if ($('#rec-tax')) $('#rec-tax').textContent = formatCurrency(totals.tax_amount);
        if ($('#rec-total')) $('#rec-total').textContent = formatCurrency(totals.total);
    },

    async submitWithAction(e, id, action) {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        const form = e?.target?.form || e?.target?.closest?.('form');
        if (!form) return;
        await RecurringPage.save({ preventDefault() {}, target: form }, id, action);
    },

    async save(e, id, afterAction = null) {
        e.preventDefault();
        const form = e.target;
        const lines = [];
        $$('#rec-lines tr').forEach((row, i) => {
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
        const data = {
            customer_id: parseInt(form.customer_id.value),
            frequency: form.frequency.value,
            start_date: form.start_date.value,
            end_date: form.end_date.value || null,
            terms: form.terms.value,
            tax_rate: (parseFloat(form.tax_rate.value) || 0) / 100,
            notes: form.notes.value || null,
            lines,
        };
        try {
            if (id) {
                await API.put(`/recurring/${id}`, data);
                toast('Recurring updated');
                RecurringPage._detailState = null;
                App.navigate('#/recurring');
                return;
            }
            await API.post('/recurring', data);
            toast('Recurring created');
            if (afterAction === 'add-new') {
                await RecurringPage._loadEditorContext(null);
                App.navigate('#/recurring/detail');
                return;
            }
            RecurringPage._detailState = null;
            App.navigate('#/recurring');
        } catch (err) { toast(err.message, 'error'); }
    },

    async del(id) {
        if (!confirm('Delete this recurring invoice?')) return;
        try {
            await API.del(`/recurring/${id}`);
            toast('Deleted');
            App.navigate('#/recurring');
        } catch (err) { toast(err.message, 'error'); }
    },

    async generateNow() {
        try {
            const result = await API.post('/recurring/generate');
            toast(`Generated ${result.invoices_created} invoice(s)`);
            App.navigate('#/recurring');
        } catch (err) { toast(err.message, 'error'); }
    },
};
