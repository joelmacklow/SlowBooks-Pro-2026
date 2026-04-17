/**
 * Decompiled from QBW32.EXE!CCreateInvoicesView  Offset: 0x0015E400
 * This was the crown jewel of QB2003 — the "Create Invoices" form with
 * the yellow-tinted paper background texture (resource RT_BITMAP id=0x012C).
 * Line items were rendered in a custom owner-draw CListCtrl subclass called
 * CQBGridCtrl. We're using a detail-page workflow aligned with purchase orders.
 */
const InvoicesPage = {
    lineCount: 0,
    _customers: [],
    _items: [],
    _settings: {},
    _detailState: null,
    _availableCredits: [],

    async render() {
        const invoices = await API.get('/invoices');
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Invoices</h2>
                ${canManageSales ? `<button class="btn btn-primary" onclick="InvoicesPage.startNew()">+ New Invoice</button>` : ''}
            </div>
            <div class="toolbar">
                <select id="inv-status-filter" onchange="InvoicesPage.applyFilter()">
                    <option value="">All Statuses</option>
                    <option value="draft">Draft</option>
                    <option value="sent">Sent</option>
                    <option value="partial">Partial</option>
                    <option value="paid">Paid</option>
                    <option value="void">Void</option>
                </select>
            </div>`;

        if (invoices.length === 0) {
            html += `<div class="empty-state"><p>No invoices yet</p></div>`;
        } else {
            html += `<div class="table-container"><table>
                <thead><tr>
                    <th>#</th><th>Customer</th><th>Date</th><th>Due Date</th>
                    <th>Status</th><th class="amount">Total</th><th class="amount">Balance</th><th>Actions</th>
                </tr></thead><tbody id="inv-tbody">`;
            for (const inv of invoices) {
                html += `<tr class="inv-row" data-status="${inv.status}">
                    <td><strong>${escapeHtml(inv.invoice_number)}</strong></td>
                    <td>${escapeHtml(inv.customer_name || '')}</td>
                    <td>${formatDate(inv.date)}</td>
                    <td>${formatDate(inv.due_date)}</td>
                    <td>${statusBadge(inv.status)}</td>
                    <td class="amount">${formatCurrency(inv.total)}</td>
                    <td class="amount">${formatCurrency(inv.balance_due)}</td>
                    <td class="actions">
                        <button class="btn btn-sm btn-secondary" onclick="InvoicesPage.open(${inv.id})">Open</button>
                    </td>
                </tr>`;
            }
            html += `</tbody></table></div>`;
        }
        return html;
    },

    applyFilter() {
        const status = $('#inv-status-filter')?.value;
        $$('.inv-row').forEach(row => {
            row.style.display = (!status || row.dataset.status === status) ? '' : 'none';
        });
    },

    async startNew() {
        await InvoicesPage._loadEditorContext(null);
        App.navigate('#/invoices/detail');
    },

    async open(id) {
        await InvoicesPage._loadEditorContext(id);
        App.navigate('#/invoices/detail');
    },

    async view(id) {
        await InvoicesPage.open(id);
    },

    async showForm(id = null) {
        if (id) return InvoicesPage.open(id);
        return InvoicesPage.startNew();
    },

    async _loadEditorContext(id = null) {
        const [customers, items, settings, gstCodes] = await Promise.all([
            API.get('/customers?active_only=true'),
            API.get('/items?active_only=true'),
            API.get('/settings'),
            API.get('/gst-codes'),
        ]);
        App.gstCodes = gstCodes;
        InvoicesPage._customers = customers;
        InvoicesPage._items = items;
        InvoicesPage._settings = settings;

        let inv = {
            id: null,
            customer_id: '',
            invoice_number: '',
            status: 'draft',
            date: todayISO(),
            due_date: '',
            terms: settings.default_terms || 'Net 30',
            po_number: '',
            tax_rate: (parseFloat(settings.default_tax_rate || '0') || 0) / 100,
            notes: settings.invoice_notes || '',
            subtotal: 0,
            tax_amount: 0,
            total: 0,
            amount_paid: 0,
            balance_due: 0,
            lines: [],
        };
        if (id) inv = await API.get(`/invoices/${id}`);
        if (!inv.lines || inv.lines.length === 0) inv.lines = [{ item_id: '', description: '', quantity: 1, rate: 0, gst_code: 'GST15' }];
        InvoicesPage.lineCount = inv.lines.length;
        InvoicesPage._detailState = inv;
        InvoicesPage._availableCredits = inv.customer_id
            ? (await API.get(`/credit-memos?customer_id=${inv.customer_id}&status=issued`)).filter(cm => Number(cm.balance_remaining || 0) > 0)
            : [];
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
        const inv = InvoicesPage._detailState;
        const canManageSales = App.hasPermission ? App.hasPermission('sales.manage') : true;
        if (!inv) {
            return `<div class="empty-state"><p>Select an invoice or create a new one first.</p><p style="margin-top:8px;"><button class="btn btn-primary" onclick="App.navigate('#/invoices')">Back to Invoices</button></p></div>`;
        }
        const totals = InvoicesPage._totals(inv.lines || []);
        const canCreateCustomers = App.hasPermission ? App.hasPermission('contacts.manage') : true;
        const customerOptions = InvoicesPage.customerOptionsHtml(inv.customer_id);
        const availableCredits = (InvoicesPage._availableCredits || []).filter(cm => Number(cm.balance_remaining || 0) > 0);
        return `
            <div class="page-header">
                <div>
                    <div style="font-size:10px; color:var(--text-muted);">Sales</div>
                    <h2>${inv.id ? `Invoice ${escapeHtml(inv.invoice_number || '')}` : 'New Invoice'}</h2>
                </div>
                <div class="actions">
                    <button class="btn btn-secondary" onclick="App.navigate('#/invoices')">Back to Invoices</button>
                </div>
            </div>
            <form id="invoice-form" onsubmit="InvoicesPage.save(event, ${inv.id || 'null'})">
                <div class="settings-section">
                    <div class="form-grid">
                        <div class="form-group"><label>Customer *</label>
                            <div style="display:flex; gap:8px; align-items:center;">
                                <select name="customer_id" required onchange="InvoicesPage.customerSelected(this.value)" style="flex:1;" ${canManageSales ? '' : 'disabled'}><option value="">Select...</option>${customerOptions}</select>
                                ${canCreateCustomers ? `<button type="button" class="btn btn-sm btn-secondary" onclick="InvoicesPage.toggleInlineCustomer()">+ New Customer</button>` : ''}
                            </div>
                            ${canCreateCustomers ? `<div id="invoice-inline-customer" class="card" style="display:none; margin-top:8px; padding:12px;">
                                <div class="form-grid">
                                    <div class="form-group"><label>Name *</label><input name="inline_customer_name"></div>
                                    <div class="form-group"><label>Email</label><input name="inline_customer_email" type="email"></div>
                                    <div class="form-group"><label>Phone</label><input name="inline_customer_phone"></div>
                                    <div class="form-group"><label>Terms</label><select name="inline_customer_terms">${['Net 15','Net 30','Net 45','Net 60','Due on Receipt'].map(t => `<option>${t}</option>`).join('')}</select></div>
                                </div>
                                <div class="form-actions" style="margin-top:8px;"><button type="button" class="btn btn-primary" onclick="InvoicesPage.createInlineCustomer(event)">Create Customer</button></div>
                            </div>` : ''}
                        </div>
                        <div class="form-group"><label>Date *</label>
                            <input name="date" type="date" required value="${inv.date || ''}" ${canManageSales ? '' : 'disabled'}></div>
                        <div class="form-group"><label>Due Date</label>
                            <input name="due_date" type="date" value="${inv.due_date || ''}" ${canManageSales ? '' : 'disabled'}></div>
                        <div class="form-group"><label>Terms</label>
                            <select name="terms" id="invoice-terms" ${canManageSales ? '' : 'disabled'}>
                                ${['Net 15','Net 30','Net 45','Net 60','Due on Receipt'].map(t => `<option value="${t}" ${inv.terms===t?'selected':''}>${t}</option>`).join('')}
                            </select></div>
                        <div class="form-group"><label>Invoice Number</label>
                            <input value="${escapeHtml(inv.invoice_number || 'Assigned on save')}" disabled></div>
                        <div class="form-group"><label>Status</label>
                            <input value="${escapeHtml(inv.status || 'draft')}" disabled></div>
                        <div class="form-group"><label>PO #</label>
                            <input name="po_number" value="${escapeHtml(inv.po_number || '')}" ${canManageSales ? '' : 'disabled'}></div>
                        <input name="tax_rate" type="hidden" value="${(inv.tax_rate * 100) || 0}">
                    </div>
                </div>
                <div class="settings-section">
                    <h3>Line Items</h3>
                    <table class="line-items-table">
                        <thead><tr><th>Item</th><th>Description</th><th class="col-qty">Qty</th><th>GST</th><th class="col-rate">Rate</th><th class="col-amount">Amount</th><th></th></tr></thead>
                        <tbody id="inv-lines">
                            ${(inv.lines || []).map((l, i) => InvoicesPage.lineRowHtml(i, l, InvoicesPage._items, canManageSales)).join('')}
                        </tbody>
                    </table>
                    ${canManageSales ? '<button type="button" class="btn btn-sm btn-secondary" style="margin-top:8px;" onclick="InvoicesPage.addLine()">+ Add Line</button>' : ''}
                </div>
                <div class="settings-section">
                    <div style="display:grid; grid-template-columns: 1.4fr 0.8fr; gap:16px; align-items:start;">
                        <div class="form-group"><label>Notes</label>
                            <textarea name="notes" rows="5" ${canManageSales ? '' : 'disabled'}>${escapeHtml(inv.notes || '')}</textarea></div>
                        <div>
                            <div class="table-container"><table>
                                <tbody>
                                    <tr><td><strong>Subtotal</strong></td><td class="amount" id="inv-subtotal">${formatCurrency(totals.subtotal)}</td></tr>
                                    <tr><td><strong>Tax</strong></td><td class="amount" id="inv-tax">${formatCurrency(totals.tax_amount)}</td></tr>
                                    <tr><td><strong>Total</strong></td><td class="amount" id="inv-total">${formatCurrency(totals.total)}</td></tr>
                                    ${inv.id ? `<tr><td><strong>Paid</strong></td><td class="amount">${formatCurrency(inv.amount_paid || 0)}</td></tr>
                                    <tr><td><strong>Balance Due</strong></td><td class="amount">${formatCurrency(inv.balance_due || 0)}</td></tr>` : ''}
                                </tbody>
                            </table></div>
                        </div>
                    </div>
                </div>
                ${inv.id && inv.customer_id && availableCredits.length ? `<div class="settings-section">
                    <h3>Available Credit Notes</h3>
                    <div class="table-container"><table>
                        <thead><tr><th>Credit Note</th><th class="amount">Remaining</th><th></th></tr></thead>
                        <tbody>
                            ${availableCredits.map(cm => `<tr>
                                <td><strong>${escapeHtml(cm.memo_number)}</strong></td>
                                <td class="amount">${formatCurrency(cm.balance_remaining)}</td>
                                <td class="actions"><button type="button" class="btn btn-sm btn-secondary" onclick="InvoicesPage.applyCreditMemo(${cm.id}, ${Number(cm.balance_remaining || 0)}, ${inv.id})">Apply Credit</button></td>
                            </tr>`).join('')}
                        </tbody>
                    </table></div>
                </div>` : ''}
                ${canManageSales ? `<div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.navigate('#/invoices')">Cancel</button>
                    ${inv.id ? '' : `<button type="button" class="btn btn-secondary" onclick="InvoicesPage.submitWithAction(event, null, 'add-new')">Create & Add New</button>`}
                    <button type="button" class="btn btn-secondary" onclick="${inv.id ? `InvoicesPage.openPdf(${inv.id}, '${escapeHtml(inv.invoice_number || '')}')` : `InvoicesPage.submitWithAction(event, null, 'pdf')`}">${inv.id ? 'Print / PDF' : 'Create & Print / PDF'}</button>
                    <button type="button" class="btn btn-secondary" onclick="${inv.id ? `InvoicesPage.emailInvoice(${inv.id})` : `InvoicesPage.submitWithAction(event, null, 'email')`}">${inv.id ? 'Email Invoice' : 'Create & Email'}</button>
                    ${inv.id ? `<button type="button" class="btn btn-secondary" onclick="InvoicesPage.duplicate(${inv.id})">Duplicate</button>
                    ${inv.status === 'draft' ? `<button type="button" class="btn btn-primary" onclick="InvoicesPage.markSent(${inv.id})">Mark Sent</button>` : ''}
                    ${inv.status !== 'void' ? `<button type="button" class="btn btn-danger" onclick="InvoicesPage.void(${inv.id})">Void Invoice</button>` : ''}
                    <button type="submit" class="btn btn-primary">Update Invoice</button>` : `<button type="submit" class="btn btn-primary">Create</button>`}
                </div>` : ''}
            </form>`;
    },

    customerOptionsHtml(selectedId = null) {
        return (InvoicesPage._customers || []).map(c => `<option value="${c.id}" ${selectedId == c.id ? 'selected' : ''}>${escapeHtml(c.name)}</option>`).join('');
    },

    customerSelected(customerId) {
        const customer = InvoicesPage._customers.find(c => c.id == customerId);
        const termsField = $('#invoice-terms');
        if (customer && termsField && customer.terms) {
            termsField.value = customer.terms;
        }
    },

    toggleInlineCustomer() {
        const panel = $('#invoice-inline-customer');
        if (!panel) return;
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    },

    async createInlineCustomer(e) {
        e.preventDefault();
        const form = $('#invoice-form');
        try {
            const customer = await API.post('/customers', {
                name: form.inline_customer_name.value,
                email: form.inline_customer_email.value || null,
                phone: form.inline_customer_phone.value || null,
                terms: form.inline_customer_terms.value || 'Net 30',
            });
            InvoicesPage._customers.push(customer);
            InvoicesPage._customers.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
            form.customer_id.innerHTML = `<option value="">Select...</option>${InvoicesPage.customerOptionsHtml(customer.id)}`;
            form.customer_id.value = String(customer.id);
            InvoicesPage.customerSelected(customer.id);
            form.inline_customer_name.value = '';
            form.inline_customer_email.value = '';
            form.inline_customer_phone.value = '';
            InvoicesPage.toggleInlineCustomer();
            toast('Customer created');
        } catch (err) { toast(err.message, 'error'); }
    },

    lineRowHtml(idx, line, items, canManage = true) {
        const itemOpts = items.map(i => `<option value="${i.id}" ${line.item_id==i.id?'selected':''}>${escapeHtml(i.name)}</option>`).join('');
        return `<tr data-line="${idx}">
            <td><select class="line-item" onchange="InvoicesPage.itemSelected(${idx})" ${canManage ? '' : 'disabled'}>
                <option value="">--</option>${itemOpts}</select></td>
            <td><input class="line-desc" value="${escapeHtml(line.description || '')}" ${canManage ? '' : 'disabled'}></td>
            <td><input class="line-qty" type="number" step="0.01" value="${line.quantity || 1}" oninput="InvoicesPage.recalc()" ${canManage ? '' : 'disabled'}></td>
            <td><select class="line-gst" onchange="InvoicesPage.recalc()" ${canManage ? '' : 'disabled'}>${gstOptionsHtml(line.gst_code || 'GST15')}</select></td>
            <td><input class="line-rate" type="number" step="0.01" value="${line.rate || 0}" oninput="InvoicesPage.recalc()" ${canManage ? '' : 'disabled'}></td>
            <td class="col-amount line-amount">${formatCurrency((line.quantity||1) * (line.rate||0))}</td>
            <td>${canManage ? `<button type="button" class="btn btn-sm btn-secondary" onclick="InvoicesPage.removeLine(${idx})">Remove</button>` : ''}</td>
        </tr>`;
    },

    addLine() {
        const tbody = $('#inv-lines');
        const idx = InvoicesPage.lineCount++;
        tbody.insertAdjacentHTML('beforeend', InvoicesPage.lineRowHtml(idx, {}, InvoicesPage._items, true));
    },

    removeLine(idx) {
        const row = $(`[data-line="${idx}"]`);
        if (row) row.remove();
        InvoicesPage.recalc();
    },

    itemSelected(idx) {
        const row = $(`[data-line="${idx}"]`);
        const itemId = row.querySelector('.line-item').value;
        const item = InvoicesPage._items.find(i => i.id == itemId);
        if (item) {
            row.querySelector('.line-desc').value = item.description || item.name;
            row.querySelector('.line-rate').value = item.rate;
            InvoicesPage.recalc();
        }
    },

    recalc() {
        const lines = [];
        $$('#inv-lines tr').forEach(row => {
            const payload = readGstLinePayload(row);
            const amount = payload.quantity * payload.rate;
            lines.push(payload);
            const amountCell = row.querySelector('.line-amount');
            if (amountCell) amountCell.textContent = formatCurrency(amount);
        });
        const totals = calculateGstTotals(lines);
        if ($('#inv-subtotal')) $('#inv-subtotal').textContent = formatCurrency(totals.subtotal);
        if ($('#inv-tax')) $('#inv-tax').textContent = formatCurrency(totals.tax_amount);
        if ($('#inv-total')) $('#inv-total').textContent = formatCurrency(totals.total);
    },

    async openPdf(id, invoiceNumber) {
        API.open(`/invoices/${id}/pdf`, `invoice-${invoiceNumber}.pdf`);
    },

    async emailInvoice(id) {
        const inv = await API.get(`/invoices/${id}`);
        const customer = inv.customer_id ? await API.get(`/customers/${inv.customer_id}`) : null;
        App.showDocumentEmailModal({
            title: `Email Invoice #${inv.invoice_number}`,
            endpoint: `/invoices/${id}/email`,
            recipient: customer?.email || '',
            defaultSubject: `Invoice #${inv.invoice_number}`,
            successMessage: 'Invoice emailed',
        });
    },

    async submitWithAction(e, id, action) {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        const form = e?.target?.form || e?.target?.closest?.('form');
        if (!form) return;
        await InvoicesPage.save({ preventDefault() {}, target: form }, id, action);
    },

    async void(id) {
        if (!confirm('Void this invoice? This cannot be undone.')) return;
        try {
            await API.post(`/invoices/${id}/void`);
            toast('Invoice voided');
            await InvoicesPage.open(id);
        } catch (err) { toast(err.message, 'error'); }
    },

    async markSent(id) {
        try {
            await API.post(`/invoices/${id}/send`);
            toast('Invoice marked as sent');
            await InvoicesPage.open(id);
        } catch (err) { toast(err.message, 'error'); }
    },

    async duplicate(id) {
        try {
            const inv = await API.post(`/invoices/${id}/duplicate`);
            toast(`Duplicated as Invoice #${inv.invoice_number}`);
            await InvoicesPage.open(inv.id);
        } catch (err) { toast(err.message, 'error'); }
    },

    async applyCreditMemo(cmId, amount, invoiceId) {
        try {
            await API.post(`/credit-memos/${cmId}/apply`, {
                invoice_id: invoiceId,
                amount,
            });
            toast('Credit applied');
            await InvoicesPage.open(invoiceId);
        } catch (err) { toast(err.message, 'error'); }
    },

    async save(e, id, afterAction = null) {
        e.preventDefault();
        const form = e.target;
        const lines = [];
        $$('#inv-lines tr').forEach((row, i) => {
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
            due_date: form.due_date.value || null,
            terms: form.terms.value,
            po_number: form.po_number.value || null,
            tax_rate: (parseFloat(form.tax_rate.value) || 0) / 100,
            notes: form.notes.value || null,
            lines,
        };

        try {
            let savedInv;
            if (id) { savedInv = await API.put(`/invoices/${id}`, data); toast('Invoice updated'); }
            else { savedInv = await API.post('/invoices', data); toast('Invoice created'); }

            if (afterAction === 'pdf' && savedInv?.id) {
                InvoicesPage._detailState = savedInv;
                App.navigate('#/invoices/detail');
                InvoicesPage.openPdf(savedInv.id, savedInv.invoice_number || 'invoice');
                return;
            }
            if (afterAction === 'email' && savedInv?.id) {
                InvoicesPage._detailState = savedInv;
                App.navigate('#/invoices/detail');
                await InvoicesPage.emailInvoice(savedInv.id);
                return;
            }
            if (afterAction === 'add-new') {
                await InvoicesPage._loadEditorContext(null);
                App.navigate('#/invoices/detail');
                return;
            }

            InvoicesPage._detailState = null;
            App.navigate('#/invoices');
        } catch (err) { toast(err.message, 'error'); }
    },
};
