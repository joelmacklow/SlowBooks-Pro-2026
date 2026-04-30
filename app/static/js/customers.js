/**
 * Decompiled from QBW32.EXE!CCustomerCenterView  Offset: 0x000D9200
 * Original was a CFormView with a CListCtrl (report mode) and a tabbed
 * detail panel on the right. The "Customer:Job" hierarchy was stored as
 * a colon-delimited string in CUST.DAT field 0x02 — e.g. "Smith:Kitchen Remodel".
 * We flattened this because nobody actually liked that feature.
 */
const CustomersPage = {
    _detailState: null,
    _defaultPaymentTerms() {
        return ['Net 15', 'Net 30', 'Net 45', 'Net 60', 'Due on Receipt'];
    },

    _paymentTermLabels(settings = {}) {
        const raw = String(settings.payment_terms_config || '').trim();
        if (!raw) return CustomersPage._defaultPaymentTerms();
        const labels = raw.split(/\r?\n/)
            .map(line => line.trim())
            .filter(Boolean)
            .map(line => line.includes('|') ? line.split('|', 1)[0].trim() : (line.includes('=') ? line.split('=', 1)[0].trim() : line))
            .filter(Boolean);
        return labels.length ? labels : CustomersPage._defaultPaymentTerms();
    },

    async render() {
        const customers = await API.get('/customers');
        const canManageCustomers = App.hasPermission ? App.hasPermission('contacts.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Customers</h2>
                ${canManageCustomers ? `<button class="btn btn-primary" onclick="CustomersPage.showForm()">+ New Customer</button>` : ''}
            </div>
            <div class="toolbar">
                <input type="text" placeholder="Search customers..." id="customer-search"
                    oninput="CustomersPage.filter(this.value)">
            </div>`;

        if (customers.length === 0) {
            html += `<div class="empty-state"><p>No customers yet</p></div>`;
        } else {
            html += `<div class="table-container"><table>
                <thead><tr>
                    <th>Name</th><th>Company</th><th>Phone</th><th>Email</th>
                    <th class="amount">Balance</th><th>Actions</th>
                </tr></thead>
                <tbody id="customer-tbody">`;
            for (const c of customers) {
                html += `<tr class="clickable customer-row" data-name="${escapeHtml(c.name).toLowerCase()}" onclick="CustomersPage.view(${c.id})">
                    <td><strong>${escapeHtml(c.name)}</strong></td>
                    <td>${escapeHtml(c.company) || ''}</td>
                    <td>${escapeHtml(c.phone) || ''}</td>
                    <td>${escapeHtml(c.email) || ''}</td>
                    <td class="amount">${formatCurrency(c.balance)}</td>
                    <td class="actions">
                        ${canManageCustomers ? `<button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); CustomersPage.showForm(${c.id})">Edit</button>` : ''}
                    </td>
                </tr>`;
            }
            html += `</tbody></table></div>`;
        }
        return html;
    },

    async view(id) {
        const [customer, invoices, estimates, creditMemos] = await Promise.all([
            API.get(`/customers/${id}`),
            API.get(`/invoices?customer_id=${id}`),
            API.get(`/estimates?customer_id=${id}`),
            API.get(`/credit-memos?customer_id=${id}`),
        ]);
        CustomersPage._detailState = { customer, invoices, estimates, creditMemos };
        App.navigate('#/customers/detail');
    },

    renderDetailScreen() {
        const state = CustomersPage._detailState;
        if (!state) {
            return `<div class="empty-state"><p>Select a customer first.</p><p style="margin-top:8px;"><button class="btn btn-primary" onclick="App.navigate('#/customers')">Back to Customers</button></p></div>`;
        }
        const { customer, invoices, estimates, creditMemos } = state;
        const outstandingBalance = (invoices || []).reduce((total, inv) => {
            const status = String(inv.status || '').toLowerCase();
            return ['sent', 'partial'].includes(status)
                ? total + Number(inv.balance_due || 0)
                : total;
        }, 0);
        const invoiceRows = invoices.map(inv => `<tr>
            <td><button class="btn btn-link" onclick="InvoicesPage.open(${inv.id}, '#/customers/detail')">${escapeHtml(inv.invoice_number)}</button></td>
            <td>${formatDate(inv.date)}</td>
            <td>${statusBadge(inv.status)}</td>
            <td class="amount">${formatCurrency(inv.total)}</td>
            <td class="amount">${formatCurrency(inv.balance_due)}</td>
        </tr>`).join('') || '<tr><td colspan="5">No invoices yet</td></tr>';
        const estimateRows = estimates.map(est => `<tr>
            <td><button class="btn btn-link" onclick="EstimatesPage.open(${est.id}, '#/customers/detail')">${escapeHtml(est.estimate_number)}</button></td>
            <td>${formatDate(est.date)}</td>
            <td>${statusBadge(est.status)}</td>
            <td class="amount">${formatCurrency(est.total)}</td>
        </tr>`).join('') || '<tr><td colspan="4">No estimates yet</td></tr>';
        const creditRows = creditMemos.map(memo => `<tr>
            <td><button class="btn btn-link" onclick="CreditMemosPage.open(${memo.id}, '#/customers/detail')">${escapeHtml(memo.memo_number)}</button></td>
            <td>${formatDate(memo.date)}</td>
            <td>${statusBadge(memo.status)}</td>
            <td class="amount">${formatCurrency(memo.total)}</td>
            <td class="amount">${formatCurrency(memo.balance_remaining)}</td>
        </tr>`).join('') || '<tr><td colspan="5">No credit notes yet</td></tr>';
        return `
            <div class="page-header">
                <div>
                    <h2>${escapeHtml(customer.name)}</h2>
                    <div style="font-size:12px; color:var(--text-muted);">${escapeHtml(customer.company || '')}</div>
                </div>
                <div class="actions">
                    <button class="btn btn-secondary" onclick="App.navigate('#/customers')">Back to Customers</button>
                    ${App.hasPermission && App.hasPermission('contacts.manage') ? `<button class="btn btn-primary" onclick="CustomersPage.showForm(${customer.id})">Edit Customer</button>` : ''}
                </div>
            </div>
            <div class="card-grid">
                <div class="card"><div class="card-header">Balance</div><div class="card-value">${formatCurrency(outstandingBalance)}</div></div>
                <div class="card"><div class="card-header">Email</div><div>${escapeHtml(customer.email || '—')}</div></div>
                <div class="card"><div class="card-header">Phone</div><div>${escapeHtml(customer.phone || customer.mobile || '—')}</div></div>
            </div>
            <div class="settings-section">
                <h3>Customer Details</h3>
                <div class="form-grid">
                    <div><strong>Terms</strong><br>${escapeHtml(customer.terms || '—')}</div>
                    <div><strong>Tax ID</strong><br>${escapeHtml(customer.tax_id || '—')}</div>
                    <div><strong>Billing</strong><br>${escapeHtml([customer.bill_address1, customer.bill_address2, customer.bill_city, customer.bill_state, customer.bill_zip].filter(Boolean).join(', ') || '—')}</div>
                    <div><strong>Shipping</strong><br>${escapeHtml([customer.ship_address1, customer.ship_address2, customer.ship_city, customer.ship_state, customer.ship_zip].filter(Boolean).join(', ') || '—')}</div>
                </div>
            </div>
            <div class="settings-section">
                <h3>Customer Communications</h3>
                <div class="form-grid">
                    <div><strong>Invoice Reminders</strong><br>${customer.invoice_reminders_enabled !== false ? 'Enabled' : 'Disabled'}</div>
                    <div><strong>Monthly Statements</strong><br>${customer.monthly_statements_enabled ? 'Enabled' : 'Disabled'}</div>
                </div>
            </div>
            <div class="settings-section">
                <h3>Invoice History</h3>
                <div class="table-container"><table><thead><tr><th>#</th><th>Date</th><th>Status</th><th class="amount">Total</th><th class="amount">Balance</th></tr></thead><tbody>${invoiceRows}</tbody></table></div>
            </div>
            <div class="settings-section">
                <h3>Estimates</h3>
                <div class="table-container"><table><thead><tr><th>#</th><th>Date</th><th>Status</th><th class="amount">Total</th></tr></thead><tbody>${estimateRows}</tbody></table></div>
            </div>
            <div class="settings-section">
                <h3>Credit Notes</h3>
                <div class="table-container"><table><thead><tr><th>#</th><th>Date</th><th>Status</th><th class="amount">Total</th><th class="amount">Remaining</th></tr></thead><tbody>${creditRows}</tbody></table></div>
            </div>`;
    },

    filter(query) {
        const q = query.toLowerCase();
        $$('.customer-row').forEach(row => {
            row.style.display = row.dataset.name.includes(q) ? '' : 'none';
        });
    },

    async showForm(id = null) {
        let c = { name: '', company: '', email: '', invoice_reminders_enabled: true, monthly_statements_enabled: false, phone: '', mobile: '', fax: '', website: '',
            bill_address1: '', bill_address2: '', bill_city: '', bill_state: '', bill_zip: '', bill_country: 'NZ',
            ship_address1: '', ship_address2: '', ship_city: '', ship_state: '', ship_zip: '', ship_country: 'NZ',
            terms: 'Net 30', credit_limit: '', tax_id: '', is_taxable: true, notes: '' };
        if (id) c = await API.get(`/customers/${id}`);
        let settings = {};
        try {
            settings = await API.get('/settings/public');
        } catch (_err) {}
        if (!id && settings.default_terms) c.terms = settings.default_terms;
        const termOptions = CustomersPage._paymentTermLabels(settings).map(t =>
            `<option ${c.terms===t?'selected':''}>${t}</option>`).join('');

        const title = id ? 'Edit Customer' : 'New Customer';
        openModal(title, `
            <form id="customer-form" onsubmit="CustomersPage.save(event, ${id})">
                <div class="form-grid">
                    <div class="form-group"><label>Name *</label>
                        <input name="name" required value="${escapeHtml(c.name)}"></div>
                    <div class="form-group"><label>Company</label>
                        <input name="company" value="${escapeHtml(c.company || '')}"></div>
                    <div class="form-group"><label>Email</label>
                        <input name="email" type="email" value="${escapeHtml(c.email || '')}"></div>
                    <div class="form-group"><label>Phone</label>
                        <input name="phone" value="${escapeHtml(c.phone || '')}"></div>
                    <div class="form-group"><label>Mobile</label>
                        <input name="mobile" value="${escapeHtml(c.mobile || '')}"></div>
                    <div class="form-group"><label>Fax</label>
                        <input name="fax" value="${escapeHtml(c.fax || '')}"></div>
                    <div class="form-group"><label>Website</label>
                        <input name="website" value="${escapeHtml(c.website || '')}"></div>
                    <div class="form-group"><label>Terms</label>
                        <select name="terms">
                            ${termOptions}
                        </select></div>
                    <div class="form-group full-width">
                        <label>Customer Communications</label>
                        <div class="card" style="padding:12px; display:grid; gap:10px;">
                            <label style="display:flex; gap:8px; align-items:flex-start;">
                                <input name="invoice_reminders_enabled" type="checkbox" ${c.invoice_reminders_enabled !== false ? 'checked' : ''} style="margin-top:2px;">
                                <span>
                                    <strong>Invoice Reminders</strong><br>
                                    <span style="font-size:10px; color:var(--text-muted);">Allow company invoice reminders for this customer.</span>
                                </span>
                            </label>
                            <label style="display:flex; gap:8px; align-items:flex-start;">
                                <input name="monthly_statements_enabled" type="checkbox" ${c.monthly_statements_enabled ? 'checked' : ''} style="margin-top:2px;">
                                <span>
                                    <strong>Monthly Statements</strong><br>
                                    <span style="font-size:10px; color:var(--text-muted);">Include this customer in monthly statement runs even when balance is zero.</span>
                                </span>
                            </label>
                        </div>
                    </div>
                </div>
                <h3 style="margin:16px 0 8px; font-size:14px; color:var(--gray-600);">Billing Address</h3>
                <div class="form-grid">
                    <div class="form-group full-width"><label>Address 1</label>
                        <input name="bill_address1" value="${escapeHtml(c.bill_address1 || '')}"></div>
                    <div class="form-group full-width"><label>Address 2</label>
                        <input name="bill_address2" value="${escapeHtml(c.bill_address2 || '')}"></div>
                    <div class="form-group"><label>City</label>
                        <input name="bill_city" value="${escapeHtml(c.bill_city || '')}"></div>
                    <div class="form-group"><label>Region</label>
                        <input name="bill_state" value="${escapeHtml(c.bill_state || '')}"></div>
                    <div class="form-group"><label>Postcode</label>
                        <input name="bill_zip" value="${escapeHtml(c.bill_zip || '')}"></div>
                    <input name="bill_country" type="hidden" value="${escapeHtml(c.bill_country || 'NZ')}">
                </div>
                <h3 style="margin:16px 0 8px; font-size:14px; color:var(--gray-600);">Shipping Address</h3>
                <div class="form-grid">
                    <div class="form-group full-width"><label>Address 1</label>
                        <input name="ship_address1" value="${escapeHtml(c.ship_address1 || '')}"></div>
                    <div class="form-group full-width"><label>Address 2</label>
                        <input name="ship_address2" value="${escapeHtml(c.ship_address2 || '')}"></div>
                    <div class="form-group"><label>City</label>
                        <input name="ship_city" value="${escapeHtml(c.ship_city || '')}"></div>
                    <div class="form-group"><label>Region</label>
                        <input name="ship_state" value="${escapeHtml(c.ship_state || '')}"></div>
                    <div class="form-group"><label>Postcode</label>
                        <input name="ship_zip" value="${escapeHtml(c.ship_zip || '')}"></div>
                    <input name="ship_country" type="hidden" value="${escapeHtml(c.ship_country || 'NZ')}">
                </div>
                <div class="form-grid" style="margin-top:16px;">
                    <div class="form-group"><label>Tax ID</label>
                        <input name="tax_id" value="${escapeHtml(c.tax_id || '')}"></div>
                    <div class="form-group"><label>Credit Limit</label>
                        <input name="credit_limit" type="number" step="0.01" value="${c.credit_limit || ''}"></div>
                    <div class="form-group full-width"><label>Notes</label>
                        <textarea name="notes">${escapeHtml(c.notes || '')}</textarea></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${id ? 'Update' : 'Create'} Customer</button>
                </div>
            </form>`);
    },

    async save(e, id) {
        e.preventDefault();
        const form = new FormData(e.target);
        const data = Object.fromEntries(form.entries());
        data.invoice_reminders_enabled = !!e.target.invoice_reminders_enabled.checked;
        data.monthly_statements_enabled = !!e.target.monthly_statements_enabled.checked;
        if (data.credit_limit) data.credit_limit = parseFloat(data.credit_limit);
        else delete data.credit_limit;

        try {
            if (id) {
                await API.put(`/customers/${id}`, data);
                toast('Customer updated');
            } else {
                await API.post('/customers', data);
                toast('Customer created');
            }
            closeModal();
            App.navigate(location.hash);
        } catch (err) {
            toast(err.message, 'error');
        }
    },
};
