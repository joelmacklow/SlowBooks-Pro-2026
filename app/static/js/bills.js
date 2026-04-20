/**
 * Bills & Bill Payments — Accounts Payable workflow
 * Feature 1: Enter bills, pay bills
 */
const BillsPage = {
    async render() {
        const bills = await API.get('/bills');
        const canManagePurchasing = App.hasPermission ? App.hasPermission('purchasing.manage') : true;
        let html = `
            <div class="page-header">
                <h2>Bills (Accounts Payable)</h2>
                <div class="btn-group">
                    ${canManagePurchasing ? `<button class="btn btn-primary" onclick="BillsPage.showForm()">+ Enter Bill</button>
                    <button class="btn btn-secondary" onclick="BillsPage.showPayForm()">Pay Bills</button>` : ''}
                </div>
            </div>
            <div class="toolbar">
                <select id="bill-status-filter" onchange="BillsPage.applyFilter()">
                    <option value="">All Statuses</option>
                    <option value="unpaid">Unpaid</option>
                    <option value="partial">Partial</option>
                    <option value="paid">Paid</option>
                    <option value="void">Void</option>
                </select>
            </div>`;

        if (bills.length === 0) {
            html += '<div class="empty-state"><p>No bills entered yet</p></div>';
        } else {
            html += `<div class="table-container"><table>
                <thead><tr><th>Bill #</th><th>Vendor</th><th>Date</th><th>Due</th><th>Status</th>
                <th class="amount">Total</th><th class="amount">Balance</th><th>Actions</th></tr></thead><tbody id="bill-tbody">`;
            for (const b of bills) {
                html += `<tr class="bill-row" data-status="${b.status}">
                    <td><strong>${escapeHtml(b.bill_number)}</strong></td>
                    <td>${escapeHtml(b.vendor_name || '')}</td>
                    <td>${formatDate(b.date)}</td>
                    <td>${formatDate(b.due_date)}</td>
                    <td>${statusBadge(b.status)}</td>
                    <td class="amount">${formatCurrency(b.total)}</td>
                    <td class="amount">${formatCurrency(b.balance_due)}</td>
                    <td class="actions">
                        ${b.po_id ? `<button class="btn btn-sm btn-secondary" onclick="BillsPage.openPurchaseOrder(${b.po_id})">Purchase Order</button>` : ''}
                        <button class="btn btn-sm btn-secondary" onclick="BillsPage.view(${b.id})">View</button>
                        ${canManagePurchasing && b.status !== 'void' && b.status !== 'paid' ? `<button class="btn btn-sm btn-danger" onclick="BillsPage.void(${b.id})">Void</button>` : ''}
                    </td>
                </tr>`;
            }
            html += '</tbody></table></div>';
        }
        return html;
    },

    applyFilter() {
        const status = $('#bill-status-filter')?.value;
        $$('.bill-row').forEach(row => {
            row.style.display = (!status || row.dataset.status === status) ? '' : 'none';
        });
    },

    async view(id) {
        const bill = await API.get(`/bills/${id}`);
        let linesHtml = bill.lines.map(l =>
            `<tr><td>${escapeHtml(l.description || '')}</td><td class="amount">${l.quantity}</td>
             <td>${escapeHtml(l.gst_code || '')}</td><td class="amount">${formatCurrency(l.rate)}</td><td class="amount">${formatCurrency(l.amount)}</td></tr>`
        ).join('');

        openModal(`Bill ${bill.bill_number}`, `
            <div style="margin-bottom:12px;">
                <strong>Vendor:</strong> ${escapeHtml(bill.vendor_name || '')}<br>
                <strong>Date:</strong> ${formatDate(bill.date)}<br>
                <strong>Due:</strong> ${formatDate(bill.due_date)}<br>
                <strong>Status:</strong> ${statusBadge(bill.status)}<br>
                ${bill.po_id ? `<strong>Purchase Order:</strong> <button type="button" class="btn btn-sm btn-secondary" onclick="BillsPage.openPurchaseOrder(${bill.po_id})">Open PO</button>` : ''}
            </div>
            <div class="table-container"><table>
                <thead><tr><th>Description</th><th class="amount">Qty</th><th>GST</th><th class="amount">Rate</th><th class="amount">Amount</th></tr></thead>
                <tbody>${linesHtml}</tbody>
            </table></div>
            <div class="invoice-totals">
                <div class="total-row"><span class="label">Subtotal</span><span class="value">${formatCurrency(bill.subtotal)}</span></div>
                <div class="total-row"><span class="label">GST</span><span class="value">${formatCurrency(bill.tax_amount)}</span></div>
                <div class="total-row grand-total"><span class="label">Grand Total</span><span class="value">${formatCurrency(bill.total)}</span></div>
                <div class="total-row"><span class="label">Paid</span><span class="value">${formatCurrency(bill.amount_paid)}</span></div>
                <div class="total-row grand-total"><span class="label">Balance</span><span class="value">${formatCurrency(bill.balance_due)}</span></div>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>`);
    },

    async openPurchaseOrder(poId) {
        if (!poId) return;
        if (typeof closeModal === 'function') closeModal();
        if (typeof PurchaseOrdersPage !== 'undefined' && typeof PurchaseOrdersPage._loadEditorContext === 'function') {
            await PurchaseOrdersPage._loadEditorContext(poId);
            App.navigate('#/purchase-orders/detail');
            return;
        }
        if (typeof PurchaseOrdersPage !== 'undefined' && typeof PurchaseOrdersPage.open === 'function') {
            await PurchaseOrdersPage.open(poId);
            return;
        }
        App.navigate('#/purchase-orders');
    },

    _items: [],
    _filteredItems: [],
    lineCount: 0,

    async showForm() {
        const [vendors, items, accounts, gstCodes] = await Promise.all([
            API.get('/vendors?active_only=true'),
            API.get('/items?active_only=true'),
            API.get('/accounts?account_type=expense'),
            API.get('/gst-codes'),
        ]);
        App.gstCodes = gstCodes;
        BillsPage._items = items;
        BillsPage._filteredItems = items;
        BillsPage.lineCount = 1;

        const vendorOpts = vendors.map(v => `<option value="${v.id}">${escapeHtml(v.name)}</option>`).join('');
        const itemOpts = BillsPage.itemOptionsHtml();

        openModal('Enter Bill', `
            <form onsubmit="BillsPage.save(event)">
                <div class="form-grid">
                    <div class="form-group"><label>Vendor *</label>
                        <select name="vendor_id" required onchange="BillsPage.vendorSelected(this.value)"><option value="">Select...</option>${vendorOpts}</select></div>
                    <div class="form-group"><label>Bill Number *</label>
                        <input name="bill_number" required></div>
                    <div class="form-group"><label>Date *</label>
                        <input name="date" type="date" required value="${todayISO()}"></div>
                    <div class="form-group"><label>Terms</label>
                        <select name="terms">
                            ${['Net 15','Net 30','Net 45','Net 60','Due on Receipt'].map(t =>
                                `<option ${t==='Net 30'?'selected':''}>${t}</option>`).join('')}
                        </select></div>
                </div>
                <h3 style="margin:12px 0 8px;font-size:14px;">Line Items</h3>
                <table class="line-items-table">
                    <thead><tr><th>Item</th><th>Description</th><th class="col-qty">Qty</th><th>GST</th><th class="col-rate">Rate</th><th class="col-amount">Amount</th></tr></thead>
                    <tbody id="bill-lines">
                        <tr data-billline="0">
                            <td><select class="line-item" onchange="BillsPage.itemSelected(0)"><option value="">--</option>${itemOpts}</select></td>
                            <td><input class="line-desc"></td>
                            <td><input class="line-qty" type="number" step="0.01" value="1" oninput="BillsPage.recalc()"></td>
                            <td><select class="line-gst" onchange="BillsPage.recalc()">${gstOptionsHtml('GST15')}</select></td>
                            <td><input class="line-rate" type="number" step="0.01" value="0" oninput="BillsPage.recalc()"></td>
                            <td class="col-amount line-amount">$0.00</td>
                        </tr>
                    </tbody>
                </table>
                <button type="button" class="btn btn-sm btn-secondary" style="margin-top:8px;" onclick="BillsPage.addLine()">+ Add Line</button>
                <div class="settings-section" style="margin-top:12px;">
                    <div style="display:grid; grid-template-columns: 1.4fr 0.8fr; gap:16px; align-items:start;">
                        <div class="form-group"><label>Notes</label>
                            <textarea name="notes"></textarea></div>
                        <div>
                            <div class="table-container"><table>
                                <tbody>
                                    <tr><td><strong>Subtotal</strong></td><td class="amount" id="bill-subtotal">${formatCurrency(0)}</td></tr>
                                    <tr><td><strong>GST</strong></td><td class="amount" id="bill-tax">${formatCurrency(0)}</td></tr>
                                    <tr><td><strong>Grand Total</strong></td><td class="amount" id="bill-total">${formatCurrency(0)}</td></tr>
                                </tbody>
                            </table></div>
                        </div>
                    </div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Bill</button>
                </div>
            </form>`);
        BillsPage.recalc();
    },

    itemOptionsHtml(selectedId = null) {
        return (BillsPage._filteredItems || []).map(i => (
            `<option value="${i.id}" ${selectedId == i.id ? 'selected' : ''}>${escapeHtml(i.name)}</option>`
        )).join('');
    },

    vendorSelected(vendorId) {
        const numericVendorId = vendorId ? parseInt(vendorId, 10) : null;
        BillsPage._filteredItems = numericVendorId
            ? (BillsPage._items || []).filter(item => item.vendor_id === numericVendorId)
            : (BillsPage._items || []);
        $$('#bill-lines tr').forEach((row) => {
            const itemSelect = row.querySelector('.line-item');
            if (!itemSelect) return;
            const currentValue = itemSelect.value;
            itemSelect.innerHTML = `<option value="">--</option>${BillsPage.itemOptionsHtml(currentValue)}`;
            if (!(BillsPage._filteredItems || []).some(item => String(item.id) === String(currentValue))) {
                itemSelect.value = '';
                if (row.querySelector('.line-desc')) row.querySelector('.line-desc').value = '';
                if (row.querySelector('.line-rate')) row.querySelector('.line-rate').value = 0;
            }
        });
        BillsPage.recalc();
    },

    addLine() {
        const idx = BillsPage.lineCount++;
        const itemOpts = BillsPage.itemOptionsHtml();
        $('#bill-lines').insertAdjacentHTML('beforeend', `
            <tr data-billline="${idx}">
                <td><select class="line-item" onchange="BillsPage.itemSelected(${idx})"><option value="">--</option>${itemOpts}</select></td>
                <td><input class="line-desc"></td>
                <td><input class="line-qty" type="number" step="0.01" value="1" oninput="BillsPage.recalc()"></td>
                <td><select class="line-gst" onchange="BillsPage.recalc()">${gstOptionsHtml('GST15')}</select></td>
                <td><input class="line-rate" type="number" step="0.01" value="0" oninput="BillsPage.recalc()"></td>
                <td class="col-amount line-amount">$0.00</td>
            </tr>`);
        BillsPage.recalc();
    },

    itemSelected(idx) {
        const row = $(`[data-billline="${idx}"]`);
        const itemId = row?.querySelector('.line-item')?.value;
        const item = BillsPage._items.find(i => i.id == itemId);
        if (item && row) {
            row.querySelector('.line-desc').value = item.description || item.name;
            row.querySelector('.line-rate').value = item.rate || 0;
            BillsPage.recalc();
        }
    },

    recalc() {
        const lines = [];
        $$('#bill-lines tr').forEach((row) => {
            const payload = readGstLinePayload(row);
            lines.push(payload);
            const amountCell = row.querySelector('.line-amount');
            if (amountCell) amountCell.textContent = formatCurrency(payload.quantity * payload.rate);
        });
        const totals = calculateGstTotals(lines);
        if ($('#bill-subtotal')) $('#bill-subtotal').textContent = formatCurrency(totals.subtotal);
        if ($('#bill-tax')) $('#bill-tax').textContent = formatCurrency(totals.tax_amount);
        if ($('#bill-total')) $('#bill-total').textContent = formatCurrency(totals.total);
    },

    async save(e) {
        e.preventDefault();
        const form = e.target;
        const lines = [];
        $$('#bill-lines tr').forEach((row, i) => {
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
            await API.post('/bills', {
                vendor_id: parseInt(form.vendor_id.value),
                bill_number: form.bill_number.value,
                date: form.date.value,
                terms: form.terms.value,
                notes: form.notes.value || null,
                lines,
            });
            toast('Bill saved');
            closeModal();
            App.navigate('#/bills');
        } catch (err) { toast(err.message, 'error'); }
    },

    async void(id) {
        if (!confirm('Void this bill?')) return;
        try {
            await API.post(`/bills/${id}/void`);
            toast('Bill voided');
            App.navigate('#/bills');
        } catch (err) { toast(err.message, 'error'); }
    },

    async showPayForm() {
        const [vendors, bills, accounts] = await Promise.all([
            API.get('/vendors?active_only=true'),
            API.get('/bills?status=unpaid'),
            API.get('/accounts?account_type=asset'),
        ]);
        const partials = await API.get('/bills?status=partial');
        const openBills = [...bills, ...partials];

        const vendorOpts = vendors.map(v => `<option value="${v.id}">${escapeHtml(v.name)}</option>`).join('');
        const acctOpts = accounts.map(a => `<option value="${a.id}">${escapeHtml(a.name)}</option>`).join('');

        let billRows = openBills.map(b => `
            <tr>
                <td><input type="checkbox" class="pay-check" data-bill="${b.id}" data-balance="${b.balance_due}"></td>
                <td>${escapeHtml(b.bill_number)}</td>
                <td>${escapeHtml(b.vendor_name || '')}</td>
                <td>${formatDate(b.due_date)}</td>
                <td class="amount">${formatCurrency(b.balance_due)}</td>
                <td><input type="number" step="0.01" class="pay-amount" data-bill="${b.id}" value="0" style="width:80px;"></td>
            </tr>`).join('');

        if (!billRows) billRows = '<tr><td colspan="6" style="color:var(--text-muted);">No open bills</td></tr>';

        openModal('Pay Bills', `
            <form onsubmit="BillsPage.savePay(event)">
                <div class="form-grid">
                    <div class="form-group"><label>Pay From Account</label>
                        <select name="pay_from_account_id"><option value="">Select...</option>${acctOpts}</select></div>
                    <div class="form-group"><label>Date *</label>
                        <input name="date" type="date" required value="${todayISO()}"></div>
                    <div class="form-group"><label>Method</label>
                        <select name="method">
                            <option value="EFT">EFT</option><option value="Cash">Cash</option>
                            <option value="Credit">Credit</option>
                        </select></div>
                    <div class="form-group"><label>Reference</label>
                        <input name="check_number"></div>
                </div>
                <div class="table-container" style="margin-top:12px;"><table>
                    <thead><tr><th style="width:30px;"></th><th>Bill #</th><th>Vendor</th><th>Due</th>
                    <th class="amount">Balance</th><th class="amount">Payment</th></tr></thead>
                    <tbody>${billRows}</tbody>
                </table></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Pay Selected Bills</button>
                </div>
            </form>`);

        // Auto-fill payment amount on check
        $$('.pay-check').forEach(cb => {
            cb.addEventListener('change', () => {
                const billId = cb.dataset.bill;
                const amtInput = $(`.pay-amount[data-bill="${billId}"]`);
                amtInput.value = cb.checked ? cb.dataset.balance : '0';
            });
        });
    },

    async savePay(e) {
        e.preventDefault();
        const form = e.target;
        const allocations = [];
        let total = 0;
        $$('.pay-amount').forEach(input => {
            const amt = parseFloat(input.value) || 0;
            if (amt > 0) {
                allocations.push({ bill_id: parseInt(input.dataset.bill), amount: amt });
                total += amt;
            }
        });
        if (allocations.length === 0) { toast('Select bills to pay', 'error'); return; }

        // Get vendor from first bill
        const firstBill = await API.get(`/bills/${allocations[0].bill_id}`);

        try {
            await API.post('/bill-payments', {
                vendor_id: firstBill.vendor_id,
                date: form.date.value,
                amount: total,
                method: form.method.value,
                check_number: form.check_number.value || null,
                pay_from_account_id: form.pay_from_account_id.value ? parseInt(form.pay_from_account_id.value) : null,
                allocations,
            });
            toast('Bills paid');
            closeModal();
            App.navigate('#/bills');
        } catch (err) { toast(err.message, 'error'); }
    },
};
