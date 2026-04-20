/**
 * Decompiled from QBW32.EXE!CCreateEstimatesView  Offset: 0x00195200
 * Same form as invoices but now aligned to the purchase-order detail workflow.
 */
const EstimatesPage = {
    lineCount: 0,
    _items: [],
    _customers: [],
    _settings: {},
    _detailState: null,

    async render() {
        const estimates = await API.get('/estimates');
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Estimates</h2>
                ${canManageSales ? `<button class="btn btn-primary" onclick="EstimatesPage.startNew()">+ New Estimate</button>` : ''}
            </div>`;

        if (estimates.length === 0) {
            html += `<div class="empty-state"><p>No estimates yet</p></div>`;
        } else {
            html += `<div class="table-container"><table>
                <thead><tr>
                    <th>#</th><th>Customer</th><th>Date</th><th>Expires</th>
                    <th>Status</th><th class="amount">Total</th><th>Actions</th>
                </tr></thead><tbody>`;
            for (const est of estimates) {
                html += `<tr>
                    <td><strong>${escapeHtml(est.estimate_number)}</strong></td>
                    <td>${escapeHtml(est.customer_name || '')}</td>
                    <td>${formatDate(est.date)}</td>
                    <td>${formatDate(est.expiration_date)}</td>
                    <td>${statusBadge(est.status)}</td>
                    <td class="amount">${formatCurrency(est.total)}</td>
                    <td class="actions">
                        <button class="btn btn-sm btn-secondary" onclick="EstimatesPage.open(${est.id})">Open</button>
                    </td>
                </tr>`;
            }
            html += `</tbody></table></div>`;
        }
        return html;
    },

    async startNew(originHash = '#/estimates') {
        App.setDetailOrigin('#/estimates/detail', originHash);
        await EstimatesPage._loadEditorContext(null);
        App.navigate('#/estimates/detail');
    },

    async open(id, originHash = '#/estimates') {
        App.setDetailOrigin('#/estimates/detail', originHash);
        await EstimatesPage._loadEditorContext(id);
        App.navigate('#/estimates/detail');
    },

    async view(id) {
        await EstimatesPage.open(id);
    },

    async showForm(id = null) {
        if (id) return EstimatesPage.open(id);
        return EstimatesPage.startNew();
    },

    async _loadEditorContext(id = null) {
        const [customers, items, settings, gstCodes] = await Promise.all([
            API.get('/customers?active_only=true'),
            API.get('/items?active_only=true'),
            API.get('/settings'),
            API.get('/gst-codes'),
        ]);
        App.gstCodes = gstCodes;
        EstimatesPage._customers = customers;
        EstimatesPage._items = items;
        EstimatesPage._settings = settings;

        let est = {
            id: null,
            customer_id: '',
            estimate_number: '',
            status: 'draft',
            date: todayISO(),
            expiration_date: '',
            tax_rate: (parseFloat(settings.default_tax_rate || '0') || 0) / 100,
            notes: '',
            subtotal: 0,
            tax_amount: 0,
            total: 0,
            lines: [],
        };
        if (id) est = await API.get(`/estimates/${id}`);
        if (!est.lines || est.lines.length === 0) est.lines = [{ item_id: '', description: '', quantity: 1, rate: 0, gst_code: 'GST15' }];
        EstimatesPage.lineCount = est.lines.length;
        EstimatesPage._detailState = est;
    },

    _totals(lines) {
        return calculateGstTotals((lines || []).map(line => ({
            quantity: parseFloat(line.quantity) || 0,
            rate: parseFloat(line.rate) || 0,
            gst_code: line.gst_code || 'GST15',
            gst_rate: line.gst_rate || 0,
        })));
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
        return EstimatesPage.itemSearchValues(item).some(candidate => candidate.toLowerCase().includes(needle));
    },

    filteredItems(query, selectedItemId = null) {
        return (EstimatesPage._items || []).filter(item => {
            if (selectedItemId && String(item.id) === String(selectedItemId)) return true;
            return EstimatesPage.itemMatchesFilter(item, query);
        });
    },

    itemOptionsHtml(items, selectedItemId = null) {
        return items.map(i => `<option value="${i.id}" ${selectedItemId == i.id ? 'selected' : ''}>${EstimatesPage.itemOptionLabel(i)}</option>`).join('');
    },

    renderDetailScreen() {
        const est = EstimatesPage._detailState;
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        if (!est) {
            return `<div class="empty-state"><p>Select an estimate or create a new one first.</p><p style="margin-top:8px;"><button class="btn btn-primary" onclick="App.navigate('#/estimates')">Back to Estimates</button></p></div>`;
        }
        const totals = EstimatesPage._totals(est.lines || []);
        const canCreateCustomers = App.hasPermission ? App.hasPermission('contacts.manage') : true;
        const customerOptions = EstimatesPage.customerOptionsHtml(est.customer_id);
        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Sales</div>
                    <h2>${est.id ? `Estimate ${escapeHtml(est.estimate_number || '')}` : 'New Estimate'}</h2>
                </div>
                <div class="actions">
                    <button class="btn btn-secondary" onclick="App.navigateBackToDetailOrigin('#/estimates/detail', '#/estimates')">${App.detailBackLabel('#/estimates/detail', '#/estimates', 'Estimates')}</button>
                </div>
            </div>
            <form id="est-form" onsubmit="EstimatesPage.save(event, ${est.id || 'null'})">
                <div class="settings-section">
                    <div class="form-grid">
                        <div class="form-group"><label>Customer *</label>
                            <div style="display:flex; gap:8px; align-items:center;">
                                <select name="customer_id" required style="flex:1;" ${canManageSales ? '' : 'disabled'}><option value="">Select...</option>${customerOptions}</select>
                                ${canCreateCustomers ? `<button type="button" class="btn btn-sm btn-secondary" onclick="EstimatesPage.toggleInlineCustomer()">+ New Customer</button>` : ''}
                            </div>
                            ${canCreateCustomers ? `<div id="estimate-inline-customer" class="card" style="display:none; margin-top:8px; padding:12px;">
                                <div class="form-grid">
                                    <div class="form-group"><label>Name *</label><input name="inline_customer_name"></div>
                                    <div class="form-group"><label>Email</label><input name="inline_customer_email" type="email"></div>
                                    <div class="form-group"><label>Phone</label><input name="inline_customer_phone"></div>
                                    <div class="form-group"><label>Terms</label><select name="inline_customer_terms">${['Net 15','Net 30','Net 45','Net 60','Due on Receipt'].map(t => `<option>${t}</option>`).join('')}</select></div>
                                </div>
                                <div class="form-actions" style="margin-top:8px;"><button type="button" class="btn btn-primary" onclick="EstimatesPage.createInlineCustomer(event)">Create Customer</button></div>
                            </div>` : ''}
                        </div>
                        <div class="form-group"><label>Date *</label>
                            <input name="date" type="date" required value="${est.date || ''}" ${canManageSales ? '' : 'disabled'}></div>
                        <div class="form-group"><label>Expiration Date</label>
                            <input name="expiration_date" type="date" value="${est.expiration_date || ''}" ${canManageSales ? '' : 'disabled'}></div>
                        <div class="form-group"><label>Estimate Number</label>
                            <input value="${escapeHtml(est.estimate_number || 'Assigned on save')}" disabled></div>
                        <div class="form-group"><label>Status</label>
                            <input value="${escapeHtml(est.status || 'draft')}" disabled></div>
                        <input name="tax_rate" type="hidden" value="${(est.tax_rate * 100) || 0}">
                    </div>
                </div>
                <div class="settings-section">
                    <h3>Line Items</h3>
                    <table class="line-items-table">
                        <thead><tr><th>Item</th><th>Description</th><th class="col-qty">Qty</th><th>GST</th><th class="col-rate">Rate</th><th class="col-amount">Amount</th><th></th></tr></thead>
                        <tbody id="est-lines">
                            ${(est.lines || []).map((l, i) => EstimatesPage.lineRowHtml(i, l, EstimatesPage._items, canManageSales)).join('')}
                        </tbody>
                    </table>
                    ${canManageSales ? '<button type="button" class="btn btn-sm btn-secondary" style="margin-top:8px;" onclick="EstimatesPage.addLine()">+ Add Line</button>' : ''}
                </div>
                <div class="settings-section">
                    <div style="display:grid; grid-template-columns: 1.4fr 0.8fr; gap:16px; align-items:start;">
                        <div class="form-group"><label>Notes</label>
                            <textarea name="notes" rows="5" ${canManageSales ? '' : 'disabled'}>${escapeHtml(est.notes || '')}</textarea></div>
                        <div>
                            <div class="table-container"><table>
                                <tbody>
                                    <tr><td><strong>Subtotal</strong></td><td class="amount" id="est-subtotal">${formatCurrency(totals.subtotal)}</td></tr>
                                    <tr><td><strong>Tax</strong></td><td class="amount" id="est-tax">${formatCurrency(totals.tax_amount)}</td></tr>
                                    <tr><td><strong>Total</strong></td><td class="amount" id="est-total">${formatCurrency(totals.total)}</td></tr>
                                </tbody>
                            </table></div>
                        </div>
                    </div>
                </div>
                ${canManageSales ? `<div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.navigateBackToDetailOrigin('#/estimates/detail', '#/estimates')">Cancel</button>
                    ${est.id ? '' : `<button type="button" class="btn btn-secondary" onclick="EstimatesPage.submitWithAction(event, null, 'add-new')">Create & Add New</button>`}
                    <button type="button" class="btn btn-secondary" onclick="${est.id ? `EstimatesPage.openPdf(${est.id}, '${escapeHtml(est.estimate_number || '')}')` : `EstimatesPage.submitWithAction(event, null, 'pdf')`}">${est.id ? 'Print / PDF' : 'Create & Print / PDF'}</button>
                    <button type="button" class="btn btn-secondary" onclick="${est.id ? `EstimatesPage.emailEstimate(${est.id})` : `EstimatesPage.submitWithAction(event, null, 'email')`}">${est.id ? 'Email' : 'Create & Email'}</button>
                    ${est.id ? `${est.status !== 'converted' ? `<button type="button" class="btn btn-primary" onclick="EstimatesPage.convert(${est.id})">Convert to Invoice</button>` : ''}<button type="submit" class="btn btn-primary">Update Estimate</button>` : `<button type="submit" class="btn btn-primary">Create</button>`}
                </div>` : ''}
            </form>`;
    },

    customerOptionsHtml(selectedId = null) {
        return (EstimatesPage._customers || []).map(c => `<option value="${c.id}" ${selectedId == c.id ? 'selected' : ''}>${escapeHtml(c.name)}</option>`).join('');
    },

    toggleInlineCustomer() {
        const panel = $('#estimate-inline-customer');
        if (!panel) return;
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    },

    async createInlineCustomer(e) {
        e.preventDefault();
        const form = $('#est-form');
        try {
            const customer = await API.post('/customers', {
                name: form.inline_customer_name.value,
                email: form.inline_customer_email.value || null,
                phone: form.inline_customer_phone.value || null,
                terms: form.inline_customer_terms.value || 'Net 30',
            });
            EstimatesPage._customers.push(customer);
            EstimatesPage._customers.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
            form.customer_id.innerHTML = `<option value="">Select...</option>${EstimatesPage.customerOptionsHtml(customer.id)}`;
            form.customer_id.value = String(customer.id);
            form.inline_customer_name.value = '';
            form.inline_customer_email.value = '';
            form.inline_customer_phone.value = '';
            EstimatesPage.toggleInlineCustomer();
            toast('Customer created');
        } catch (err) { toast(err.message, 'error'); }
    },

    lineRowHtml(idx, line, items, canManage = true) {
        const itemOpts = EstimatesPage.itemOptionsHtml(items, line.item_id);
        return `<tr data-eline="${idx}">
            <td><select class="line-item" onchange="EstimatesPage.itemSelected(${idx})" onkeydown="EstimatesPage.handleItemKeydown(${idx}, event)" onblur="EstimatesPage.resetItemFilter(${idx})" ${canManage ? '' : 'disabled'}>
                <option value="">--</option>${itemOpts}</select></td>
            <td><input class="line-desc" value="${escapeHtml(line.description || '')}" ${canManage ? '' : 'disabled'}></td>
            <td><input class="line-qty" type="number" step="0.01" value="${line.quantity || 1}" oninput="EstimatesPage.recalc()" ${canManage ? '' : 'disabled'}></td>
            <td><select class="line-gst" onchange="EstimatesPage.recalc()" ${canManage ? '' : 'disabled'}>${gstOptionsHtml(line.gst_code || 'GST15')}</select></td>
            <td><input class="line-rate" type="number" step="0.01" value="${line.rate || 0}" oninput="EstimatesPage.recalc()" ${canManage ? '' : 'disabled'}></td>
            <td class="col-amount line-amount">${formatCurrency((line.quantity||1) * (line.rate||0))}</td>
            <td>${canManage ? `<button type="button" class="btn btn-sm btn-secondary" onclick="EstimatesPage.removeLine(${idx})">Remove</button>` : ''}</td>
        </tr>`;
    },

    addLine() {
        const tbody = $('#est-lines');
        const idx = EstimatesPage.lineCount++;
        tbody.insertAdjacentHTML('beforeend', EstimatesPage.lineRowHtml(idx, {}, EstimatesPage._items, true));
    },

    removeLine(idx) {
        const row = $(`[data-eline="${idx}"]`);
        if (row) row.remove();
        EstimatesPage.recalc();
    },

    itemSelected(idx) {
        const row = $(`[data-eline="${idx}"]`);
        const itemId = row.querySelector('.line-item').value;
        const item = EstimatesPage._items.find(i => i.id == itemId);
        if (item) {
            row.querySelector('.line-desc').value = item.description || item.name;
            row.querySelector('.line-rate').value = item.rate;
            EstimatesPage.recalc();
        }
    },

    applyItemFilter(idx, query) {
        const row = $(`[data-eline="${idx}"]`);
        if (!row) return;
        const itemSelect = row.querySelector('.line-item');
        if (!itemSelect) return;
        const currentValue = itemSelect.value;
        const filtered = EstimatesPage.filteredItems(query, currentValue);
        row.dataset.itemFilterQuery = query;
        itemSelect.innerHTML = `<option value="">--</option>${EstimatesPage.itemOptionsHtml(filtered, currentValue)}`;
        if (!(filtered || []).some(item => String(item.id) === String(currentValue))) {
            itemSelect.value = '';
        }
    },

    handleItemKeydown(idx, event) {
        if (event.metaKey || event.ctrlKey || event.altKey) return;
        const row = $(`[data-eline="${idx}"]`);
        if (!row) return;
        const currentQuery = row.dataset.itemFilterQuery || '';
        if (event.key === 'Escape') {
            EstimatesPage.resetItemFilter(idx);
            event.preventDefault();
            return;
        }
        if (event.key === 'Backspace') {
            EstimatesPage.applyItemFilter(idx, currentQuery.slice(0, -1));
            event.preventDefault();
            return;
        }
        if (event.key.length === 1) {
            EstimatesPage.applyItemFilter(idx, currentQuery + event.key);
            event.preventDefault();
        }
    },

    resetItemFilter(idx) {
        const row = $(`[data-eline="${idx}"]`);
        if (!row) return;
        row.dataset.itemFilterQuery = '';
        const itemSelect = row.querySelector('.line-item');
        if (!itemSelect) return;
        const currentValue = itemSelect.value;
        itemSelect.innerHTML = `<option value="">--</option>${EstimatesPage.itemOptionsHtml(EstimatesPage._items || [], currentValue)}`;
        if (currentValue) itemSelect.value = currentValue;
    },

    recalc() {
        const lines = [];
        $$('#est-lines tr').forEach(row => {
            const payload = readGstLinePayload(row);
            const amount = payload.quantity * payload.rate;
            lines.push(payload);
            const amountCell = row.querySelector('.line-amount');
            if (amountCell) amountCell.textContent = formatCurrency(amount);
        });
        const totals = calculateGstTotals(lines);
        if ($('#est-subtotal')) $('#est-subtotal').textContent = formatCurrency(totals.subtotal);
        if ($('#est-tax')) $('#est-tax').textContent = formatCurrency(totals.tax_amount);
        if ($('#est-total')) $('#est-total').textContent = formatCurrency(totals.total);
    },

    async openPdf(id, estimateNumber) {
        API.open(`/estimates/${id}/pdf`, `estimate-${estimateNumber}.pdf`);
    },

    async emailEstimate(id) {
        const est = await API.get(`/estimates/${id}`);
        const customer = est.customer_id ? await API.get(`/customers/${est.customer_id}`) : null;
        App.showDocumentEmailModal({
            title: `Email Estimate #${est.estimate_number}`,
            endpoint: `/estimates/${id}/email`,
            recipient: customer?.email || '',
            defaultSubject: `Estimate #${est.estimate_number}`,
            successMessage: 'Estimate emailed',
        });
    },

    async submitWithAction(e, id, action) {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        const form = e?.target?.form || e?.target?.closest?.('form');
        if (!form) return;
        await EstimatesPage.save({ preventDefault() {}, target: form }, id, action);
    },

    async convert(id) {
        if (!confirm('Convert this estimate to an invoice?')) return;
        try {
            const inv = await API.post(`/estimates/${id}/convert`);
            toast(`Created Invoice #${inv.invoice_number}`);
            if (typeof InvoicesPage !== 'undefined' && typeof InvoicesPage.open === 'function') {
                await InvoicesPage.open(inv.id);
            } else {
                App.navigate('#/invoices');
            }
        } catch (err) { toast(err.message, 'error'); }
    },

    async save(e, id, afterAction = null) {
        e.preventDefault();
        const form = e.target;
        const lines = [];
        $$('#est-lines tr').forEach((row, i) => {
            const item_id = row.querySelector('.line-item')?.value;
            const gst = readGstLinePayload(row);
            lines.push({
                item_id: item_id ? parseInt(item_id) : null,
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
            date: form.date.value,
            expiration_date: form.expiration_date.value || null,
            tax_rate: (parseFloat(form.tax_rate.value) || 0) / 100,
            notes: form.notes.value || null,
            lines,
        };

        try {
            let savedEstimate;
            if (id) { savedEstimate = await API.put(`/estimates/${id}`, data); toast('Estimate updated'); }
            else { savedEstimate = await API.post('/estimates', data); toast('Estimate created'); }

            if (afterAction === 'pdf' && savedEstimate?.id) {
                EstimatesPage._detailState = savedEstimate;
                App.navigate('#/estimates/detail');
                EstimatesPage.openPdf(savedEstimate.id, savedEstimate.estimate_number || 'estimate');
                return;
            }
            if (afterAction === 'email' && savedEstimate?.id) {
                EstimatesPage._detailState = savedEstimate;
                App.navigate('#/estimates/detail');
                await EstimatesPage.emailEstimate(savedEstimate.id);
                return;
            }
            if (afterAction === 'add-new') {
                await EstimatesPage._loadEditorContext(null);
                App.navigate('#/estimates/detail');
                return;
            }

            EstimatesPage._detailState = null;
            App.navigate('#/estimates');
        } catch (err) { toast(err.message, 'error'); }
    },
};
