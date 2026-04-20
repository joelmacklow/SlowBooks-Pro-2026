/**
 * Decompiled from QBW32.EXE!CVendorCenterView  Offset: 0x000DD800
 * Nearly identical to CCustomerCenterView — Intuit copy-pasted the customer
 * code and did a find-replace of "Customer" with "Vendor". We know this
 * because the Vendor center still had a "Customer:Job" label in the resource
 * table (RT_DIALOG id=0x00A7) that they forgot to rename. Classic.
 */
const VendorsPage = {
    _detailState: null,

    async render() {
        const vendors = await API.get('/vendors');
        const canManageVendors = App.hasPermission ? App.hasPermission('contacts.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Vendors</h2>
                ${canManageVendors ? `<button class="btn btn-primary" onclick="VendorsPage.showForm()">+ New Vendor</button>` : ''}
            </div>`;

        if (vendors.length === 0) {
            html += `<div class="empty-state"><p>No vendors yet</p></div>`;
        } else {
            html += `<div class="table-container"><table>
                <thead><tr>
                    <th>Name</th><th>Company</th><th>Phone</th><th>Email</th>
                    <th>Default Expense</th><th class="amount">Balance</th><th>Actions</th>
                </tr></thead><tbody>`;
            for (const v of vendors) {
                html += `<tr class="clickable vendor-row" onclick="VendorsPage.view(${v.id})">
                    <td><strong>${escapeHtml(v.name)}</strong></td>
                    <td>${escapeHtml(v.company) || ''}</td>
                    <td>${escapeHtml(v.phone) || ''}</td>
                    <td>${escapeHtml(v.email) || ''}</td>
                    <td>${v.default_expense_account_id ? `#${v.default_expense_account_id}` : ''}</td>
                    <td class="amount">${formatCurrency(v.balance)}</td>
                    <td class="actions">
                        ${canManageVendors ? `<button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); VendorsPage.showForm(${v.id})">Edit</button>` : ''}
                    </td>
                </tr>`;
            }
            html += `</tbody></table></div>`;
        }
        return html;
    },

    async view(id) {
        const [vendor, items, bills, payments] = await Promise.all([
            API.get(`/vendors/${id}`),
            API.get(`/items?active_only=true&vendor_id=${id}`),
            API.get(`/bills?vendor_id=${id}`),
            API.get(`/bill-payments?vendor_id=${id}`),
        ]);
        VendorsPage._detailState = { vendor, items, bills, payments };
        App.navigate('#/vendors/detail');
    },

    renderDetailScreen() {
        const state = VendorsPage._detailState;
        if (!state) {
            return `<div class="empty-state"><p>Select a vendor first.</p><p style="margin-top:8px;"><button class="btn btn-primary" onclick="App.navigate('#/vendors')">Back to Vendors</button></p></div>`;
        }
        const { vendor, items, bills, payments } = state;
        const outstandingBills = (bills || []).filter(bill => ['unpaid', 'partial'].includes(String(bill.status || '')));
        const creditBalance = (payments || []).reduce((sum, payment) => sum + (Number(payment.unallocated_amount || 0)), 0);
        const itemRows = (items || []).map(item => `<tr>
            <td><strong>${escapeHtml(item.name || '')}</strong></td>
            <td>${escapeHtml(item.description || '')}</td>
            <td class="amount">${formatCurrency(item.rate || 0)}</td>
            <td class="amount">${formatCurrency(item.cost || 0)}</td>
        </tr>`).join('') || '<tr><td colspan="4">No preferred-supplier items yet</td></tr>';
        const billRows = (bills || []).map(bill => `<tr>
            <td><strong>${escapeHtml(bill.bill_number || '')}</strong></td>
            <td>${formatDate(bill.date)}</td>
            <td>${statusBadge(bill.status)}</td>
            <td class="amount">${formatCurrency(bill.total || 0)}</td>
            <td class="amount">${formatCurrency(bill.balance_due || 0)}</td>
        </tr>`).join('') || '<tr><td colspan="5">No bills yet</td></tr>';
        const paymentRows = (payments || []).map(payment => `<tr>
            <td>${formatDate(payment.date)}</td>
            <td>${escapeHtml(payment.method || '—')}</td>
            <td>${escapeHtml(payment.check_number || '—')}</td>
            <td class="amount">${formatCurrency(payment.amount || 0)}</td>
            <td class="amount">${formatCurrency(payment.unallocated_amount || 0)}</td>
        </tr>`).join('') || '<tr><td colspan="5">No payments yet</td></tr>';
        return `
            <div class="page-header">
                <div>
                    <h2>${escapeHtml(vendor.name)}</h2>
                    <div style="font-size:12px; color:var(--text-muted);">${escapeHtml(vendor.company || '')}</div>
                </div>
                <div class="actions">
                    <button class="btn btn-secondary" onclick="App.navigate('#/vendors')">Back to Vendors</button>
                    ${App.hasPermission && App.hasPermission('contacts.manage') ? `<button class="btn btn-primary" onclick="VendorsPage.showForm(${vendor.id})">Edit Vendor</button>` : ''}
                </div>
            </div>
            <div class="card-grid">
                <div class="card"><div class="card-header">Balance</div><div class="card-value">${formatCurrency(vendor.balance || 0)}</div></div>
                <div class="card"><div class="card-header">Credit Balance</div><div class="card-value">${formatCurrency(creditBalance)}</div><div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Unallocated bill payments</div></div>
                <div class="card"><div class="card-header">Outstanding Bills</div><div class="card-value">${outstandingBills.length}</div></div>
            </div>
            <div class="settings-section">
                <h3>Vendor Details</h3>
                <div class="form-grid">
                    <div><strong>Terms</strong><br>${escapeHtml(vendor.terms || '—')}</div>
                    <div><strong>Tax ID</strong><br>${escapeHtml(vendor.tax_id || '—')}</div>
                    <div><strong>Account #</strong><br>${escapeHtml(vendor.account_number || '—')}</div>
                    <div><strong>Default Expense</strong><br>${vendor.default_expense_account_id ? `#${escapeHtml(String(vendor.default_expense_account_id))}` : '—'}</div>
                    <div><strong>Email</strong><br>${escapeHtml(vendor.email || '—')}</div>
                    <div><strong>Phone</strong><br>${escapeHtml(vendor.phone || '—')}</div>
                    <div><strong>Address</strong><br>${escapeHtml([vendor.address1, vendor.address2, vendor.city, vendor.state, vendor.zip].filter(Boolean).join(', ') || '—')}</div>
                    <div><strong>Notes</strong><br>${escapeHtml(vendor.notes || '—')}</div>
                </div>
            </div>
            <div class="settings-section">
                <h3>Preferred Items</h3>
                <div class="table-container"><table><thead><tr><th>Item</th><th>Description</th><th class="amount">Rate</th><th class="amount">Cost</th></tr></thead><tbody>${itemRows}</tbody></table></div>
            </div>
            <div class="settings-section">
                <h3>Bills</h3>
                <div class="table-container"><table><thead><tr><th>#</th><th>Date</th><th>Status</th><th class="amount">Total</th><th class="amount">Balance</th></tr></thead><tbody>${billRows}</tbody></table></div>
            </div>
            <div class="settings-section">
                <h3>Payment History</h3>
                <div class="table-container"><table><thead><tr><th>Date</th><th>Method</th><th>Reference</th><th class="amount">Amount</th><th class="amount">Unallocated</th></tr></thead><tbody>${paymentRows}</tbody></table></div>
            </div>`;
    },

    async showForm(id = null) {
        const [accounts, vendor] = await Promise.all([
            API.get('/accounts?active_only=true&account_type=expense'),
            id ? API.get(`/vendors/${id}`) : Promise.resolve(null),
        ]);
        const v = vendor || { name:'', company:'', email:'', phone:'', fax:'', website:'',
            address1:'', address2:'', city:'', state:'', zip:'', country:'NZ',
            terms:'Net 30', tax_id:'', account_number:'', default_expense_account_id:'', notes:'' };
        const expenseOptions = accounts.map(account => `<option value="${account.id}" ${String(v.default_expense_account_id || '') === String(account.id) ? 'selected' : ''}>${escapeHtml(account.account_number || '')} - ${escapeHtml(account.name)}</option>`).join('');

        openModal(id ? 'Edit Vendor' : 'New Vendor', `
            <form id="vendor-form" onsubmit="VendorsPage.save(event, ${id})">
                <div class="form-grid">
                    <div class="form-group"><label>Name *</label>
                        <input name="name" required value="${escapeHtml(v.name)}"></div>
                    <div class="form-group"><label>Company</label>
                        <input name="company" value="${escapeHtml(v.company || '')}"></div>
                    <div class="form-group"><label>Email</label>
                        <input name="email" type="email" value="${escapeHtml(v.email || '')}"></div>
                    <div class="form-group"><label>Phone</label>
                        <input name="phone" value="${escapeHtml(v.phone || '')}"></div>
                    <div class="form-group"><label>Fax</label>
                        <input name="fax" value="${escapeHtml(v.fax || '')}"></div>
                    <div class="form-group"><label>Website</label>
                        <input name="website" value="${escapeHtml(v.website || '')}"></div>
                </div>
                <h3 style="margin:16px 0 8px; font-size:14px; color:var(--gray-600);">Address</h3>
                <div class="form-grid">
                    <div class="form-group full-width"><label>Address 1</label>
                        <input name="address1" value="${escapeHtml(v.address1 || '')}"></div>
                    <div class="form-group full-width"><label>Address 2</label>
                        <input name="address2" value="${escapeHtml(v.address2 || '')}"></div>
                    <div class="form-group"><label>City</label>
                        <input name="city" value="${escapeHtml(v.city || '')}"></div>
                    <div class="form-group"><label>Region</label>
                        <input name="state" value="${escapeHtml(v.state || '')}"></div>
                    <div class="form-group"><label>Postcode</label>
                        <input name="zip" value="${escapeHtml(v.zip || '')}"></div>
                    <input name="country" type="hidden" value="${escapeHtml(v.country || 'NZ')}">
                </div>
                <div class="form-grid" style="margin-top:16px;">
                    <div class="form-group"><label>Terms</label>
                        <select name="terms">
                            ${['Net 15','Net 30','Net 45','Net 60','Due on Receipt'].map(t =>
                                `<option ${v.terms===t?'selected':''}>${t}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Tax ID</label>
                        <input name="tax_id" value="${escapeHtml(v.tax_id || '')}"></div>
                    <div class="form-group"><label>Account #</label>
                        <input name="account_number" value="${escapeHtml(v.account_number || '')}"></div>
                    <div class="form-group"><label>Default Expense Account</label>
                        <select name="default_expense_account_id"><option value="">--</option>${expenseOptions}</select></div>
                    <div class="form-group full-width"><label>Notes</label>
                        <textarea name="notes">${escapeHtml(v.notes || '')}</textarea></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${id ? 'Update' : 'Create'} Vendor</button>
                </div>
            </form>`);
    },

    async save(e, id) {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        data.default_expense_account_id = data.default_expense_account_id ? parseInt(data.default_expense_account_id) : null;
        try {
            if (id) { await API.put(`/vendors/${id}`, data); toast('Vendor updated'); }
            else { await API.post('/vendors', data); toast('Vendor created'); }
            closeModal();
            App.navigate(location.hash);
        } catch (err) { toast(err.message, 'error'); }
    },
};
