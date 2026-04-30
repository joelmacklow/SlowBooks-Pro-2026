/**
 * Decompiled from QBW32.EXE!CPreferencesDialog  Offset: 0x0023F800
 * Original: tabbed dialog (IDD_PREFERENCES) with 12 tabs. We condensed
 * everything into a single page because nobody needs 12 tabs for
 * company name and tax rate. The registry writes at 0x00240200 are now
 * PostgreSQL INSERTs. Progress.
 */
const SettingsPage = {
    _defaultPaymentTerms() {
        return [
            { label: 'Net 15', rule: 'net:15' },
            { label: 'Net 30', rule: 'net:30' },
            { label: 'Net 45', rule: 'net:45' },
            { label: 'Net 60', rule: 'net:60' },
            { label: 'Due on Receipt', rule: 'days:0' },
        ];
    },

    _parsePaymentTermsConfig(value) {
        const raw = String(value || '').trim();
        if (!raw) return SettingsPage._defaultPaymentTerms();
        const terms = raw.split(/\r?\n/)
            .map(line => line.trim())
            .filter(Boolean)
            .map(line => {
                if (line.includes('|')) {
                    const [label, rule] = line.split('|', 2);
                    return { label: label.trim(), rule: (rule || '').trim() || 'manual' };
                }
                if (line.includes('=')) {
                    const [label, rule] = line.split('=', 2);
                    return { label: label.trim(), rule: (rule || '').trim() || 'manual' };
                }
                return { label: line, rule: 'manual' };
            })
            .filter(term => term.label);
        return terms.length ? terms : SettingsPage._defaultPaymentTerms();
    },

    _monthOptions() {
        return [
            ['01', 'January'], ['02', 'February'], ['03', 'March'], ['04', 'April'],
            ['05', 'May'], ['06', 'June'], ['07', 'July'], ['08', 'August'],
            ['09', 'September'], ['10', 'October'], ['11', 'November'], ['12', 'December'],
        ];
    },

    _parseFinancialYearBoundary(value) {
        const raw = String(value || '');
        if (raw.length === 5 && raw.includes('-')) return { month: raw.slice(0, 2), day: raw.slice(3, 5) };
        if (raw.length >= 10 && raw.includes('-')) return { month: raw.slice(5, 7), day: raw.slice(8, 10) };
        return { month: '', day: '' };
    },

    _financialYearSelectHtml(prefix, value) {
        const boundary = SettingsPage._parseFinancialYearBoundary(value);
        const dayOptions = Array.from({ length: 31 }, (_value, idx) => String(idx + 1).padStart(2, '0'))
            .map(day => `<option value="${day}" ${boundary.day === day ? 'selected' : ''}>${day}</option>`).join('');
        const monthOptions = SettingsPage._monthOptions()
            .map(([month, label]) => `<option value="${month}" ${boundary.month === month ? 'selected' : ''}>${label}</option>`).join('');
        return `
            <div style="display:flex; gap:8px;">
                <select name="${prefix}_day"><option value="">Day...</option>${dayOptions}</select>
                <select name="${prefix}_month"><option value="">Month...</option>${monthOptions}</select>
            </div>`;
    },

    async render() {
        const s = await API.get('/settings');
        const paymentTerms = SettingsPage._parsePaymentTermsConfig(s.payment_terms_config);
        setTimeout(() => SettingsPage.loadBackups(), 0);
        setTimeout(() => SettingsPage.loadInvoiceReminderRules(), 0);
        return `
            <div class="page-header">
                <h2>Company Settings</h2>
                <div style="font-size:10px; color:var(--text-muted);">
                    CPreferencesDialog — IDD_PREFERENCES @ 0x0023F800
                </div>
            </div>
            <form id="settings-form" onsubmit="SettingsPage.save(event)">
                <div class="settings-section">
                    <h3>Company Information</h3>
                    <div class="form-grid">
                        <div class="form-group full-width"><label>Company Name *</label>
                            <input name="company_name" value="${escapeHtml(s.company_name || '')}" required></div>
                        <div class="form-group"><label>Address Line 1</label>
                            <input name="company_address1" value="${escapeHtml(s.company_address1 || '')}"></div>
                        <div class="form-group"><label>Address Line 2</label>
                            <input name="company_address2" value="${escapeHtml(s.company_address2 || '')}"></div>
                        <div class="form-group"><label>City</label>
                            <input name="company_city" value="${escapeHtml(s.company_city || '')}"></div>
                        <div class="form-group"><label>Region</label>
                            <input name="company_state" value="${escapeHtml(s.company_state || '')}"></div>
                        <div class="form-group"><label>Postcode</label>
                            <input name="company_zip" value="${escapeHtml(s.company_zip || '')}"></div>
                        <div class="form-group"><label>Phone</label>
                            <input name="company_phone" value="${escapeHtml(s.company_phone || '')}"></div>
                        <div class="form-group"><label>Email</label>
                            <input name="company_email" type="email" value="${escapeHtml(s.company_email || '')}"></div>
                        <div class="form-group"><label>Website</label>
                            <input name="company_website" value="${escapeHtml(s.company_website || '')}"></div>
                        <div class="form-group"><label>IRD / GST Number</label>
                            <input name="company_tax_id" value="${escapeHtml(s.company_tax_id || '')}"></div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3>Company Logo</h3>
                    <div class="form-grid">
                        <div class="form-group">
                            ${s.company_logo_data_uri || s.company_logo_path ? `<img src="${escapeHtml(s.company_logo_data_uri || s.company_logo_path)}" style="max-width:200px; max-height:80px; margin-bottom:8px; display:block;">` : ''}
                            <input type="file" id="logo-upload" accept="image/png,image/jpeg,image/gif" onchange="SettingsPage.uploadLogo(this)">
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">PNG, JPG/JPEG, or GIF. Max 200x80px recommended.</div>
                        </div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3>Payment Terms & Document Sequencing</h3>
                    <div class="form-grid">
                        <div class="form-group"><label>Default Terms</label>
                            <select name="default_terms">
                                ${paymentTerms.map(({ label: t }) =>
                                    `<option ${s.default_terms===t?'selected':''}>${t}</option>`).join('')}
                            </select></div>
                        <div class="form-group full-width"><label>Payment Terms</label>
                            <textarea name="payment_terms_config" rows="6" placeholder="Net 30|net:30&#10;Due on Receipt|days:0&#10;Due 1st of next month|next_month_day:1">${escapeHtml(s.payment_terms_config || '')}</textarea>
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">One term per line. Use <code>Label|rule</code>. Supported rules: <code>net:30</code>, <code>days:0</code>, <code>next_month_day:1</code>.</div></div>
                        <div class="form-group"><label>Default Tax Rate (%)</label>
                            <input name="default_tax_rate" type="number" step="0.01" value="${s.default_tax_rate || '0.0'}"></div>
                        <div class="form-group"><label>Invoice Prefix</label>
                            <input name="invoice_prefix" value="${escapeHtml(s.invoice_prefix || '')}" placeholder="e.g. INV-"></div>
                        <div class="form-group"><label>Next Invoice #</label>
                            <input name="invoice_next_number" value="${escapeHtml(s.invoice_next_number || '1001')}"></div>
                        <div class="form-group"><label>Estimate Prefix</label>
                            <input name="estimate_prefix" value="${escapeHtml(s.estimate_prefix || '')}" placeholder="e.g. E-"></div>
                        <div class="form-group"><label>Next Estimate #</label>
                            <input name="estimate_next_number" value="${escapeHtml(s.estimate_next_number || '1001')}"></div>
                        <div class="form-group"><label>Credit Note Prefix</label>
                            <input name="credit_memo_prefix" value="${escapeHtml(s.credit_memo_prefix || 'CM-')}" placeholder="e.g. CM-"></div>
                        <div class="form-group"><label>Next Credit Note #</label>
                            <input name="credit_memo_next_number" value="${escapeHtml(s.credit_memo_next_number || '0001')}"></div>
                        <div class="form-group"><label>Purchase Order Prefix</label>
                            <input name="purchase_order_prefix" value="${escapeHtml(s.purchase_order_prefix || 'PO-')}" placeholder="e.g. PO-"></div>
                        <div class="form-group"><label>Next Purchase Order #</label>
                            <input name="purchase_order_next_number" value="${escapeHtml(s.purchase_order_next_number || '0001')}"></div>
                        <div class="form-group full-width"><label>Default Invoice Notes</label>
                            <textarea name="invoice_notes">${escapeHtml(s.invoice_notes || '')}</textarea></div>
                        <div class="form-group full-width"><label>Invoice Footer</label>
                            <input name="invoice_footer" value="${escapeHtml(s.invoice_footer || '')}"></div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3>Localization</h3>
                    <div class="form-grid">
                        <div class="form-group"><label>Country</label>
                            <select name="country">
                                <option value="NZ" ${s.country === 'NZ' ? 'selected' : ''}>New Zealand</option>
                            </select></div>
                        <div class="form-group"><label>Tax Regime</label>
                            <select name="tax_regime">
                                <option value="NZ" ${s.tax_regime === 'NZ' ? 'selected' : ''}>New Zealand GST</option>
                            </select></div>
                        <div class="form-group"><label>Currency</label>
                            <select name="currency">
                                <option value="NZD" ${s.currency === 'NZD' ? 'selected' : ''}>NZD</option>
                            </select></div>
                        <div class="form-group"><label>Locale</label>
                            <input name="locale" value="${escapeHtml(s.locale || 'en-NZ')}"></div>
                        <div class="form-group"><label>Timezone</label>
                            <input name="timezone" value="${escapeHtml(s.timezone || 'Pacific/Auckland')}"></div>
                        <div class="form-group"><label>IRD Number</label>
                            <input name="ird_number" value="${escapeHtml(s.ird_number || '')}"></div>
                        <div class="form-group"><label>GST Number</label>
                            <input name="gst_number" value="${escapeHtml(s.gst_number || '')}"></div>
                        <div class="form-group"><label>GST Registered</label>
                            <select name="gst_registered">
                                <option value="false" ${s.gst_registered !== 'true' ? 'selected' : ''}>No</option>
                                <option value="true" ${s.gst_registered === 'true' ? 'selected' : ''}>Yes</option>
                            </select></div>
                        <div class="form-group"><label>GST Accounting Basis</label>
                            <select name="gst_basis">
                                <option value="invoice" ${s.gst_basis !== 'payments' ? 'selected' : ''}>Invoice</option>
                                <option value="payments" ${s.gst_basis === 'payments' ? 'selected' : ''}>Payments</option>
                            </select>
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">Use the basis selected when registering for GST with IRD.</div></div>
                        <div class="form-group"><label>GST Period</label>
                            <select name="gst_period">
                                ${['monthly','two-monthly','six-monthly'].map(period =>
                                    `<option value="${period}" ${s.gst_period===period?'selected':''}>${period}</option>`).join('')}
                            </select></div>
                        <div class="form-group"><label>Prices Include GST</label>
                            <select name="prices_include_gst">
                                <option value="false" ${s.prices_include_gst !== 'true' ? 'selected' : ''}>No</option>
                                <option value="true" ${s.prices_include_gst === 'true' ? 'selected' : ''}>Yes</option>
                            </select></div>
                        <div class="form-group"><label>Financial Year Start</label>
                            ${SettingsPage._financialYearSelectHtml('financial_year_start', s.financial_year_start)}
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">Set the recurring day/month that each financial year begins on.</div></div>
                        <div class="form-group"><label>Financial Year End</label>
                            ${SettingsPage._financialYearSelectHtml('financial_year_end', s.financial_year_end)}
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">Use the recurring day/month boundary, e.g. 31 March for a 1 April to 31 March year.</div></div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3>Payroll Filing Contact</h3>
                    <div style="font-size:10px; color:var(--text-muted); margin-bottom:8px;">
                        Used for Employment Information and employee filing exports. Falls back to company details if left blank.
                    </div>
                    <div class="form-grid">
                        <div class="form-group"><label>Contact Name</label>
                            <input name="payroll_contact_name" value="${escapeHtml(s.payroll_contact_name || '')}"></div>
                        <div class="form-group"><label>Contact Phone</label>
                            <input name="payroll_contact_phone" value="${escapeHtml(s.payroll_contact_phone || '')}"></div>
                        <div class="form-group"><label>Contact Email</label>
                            <input name="payroll_contact_email" type="email" value="${escapeHtml(s.payroll_contact_email || '')}"></div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3>Company Admin Lock</h3>
                    <div style="font-size:10px; color:var(--text-muted); margin-bottom:8px;">
                        Company admins can block modifications before this date. Organization locks are managed separately from the Company Files admin surface.
                    </div>
                    <div class="form-grid">
                        <div class="form-group"><label>Closing Date</label>
                            <input name="closing_date" type="date" value="${escapeHtml(s.closing_date || '')}"></div>
                        <div class="form-group"><label>Password (optional)</label>
                            <input name="closing_date_password" type="password" value="${escapeHtml(s.closing_date_password || '')}"
                                placeholder="Enter a new password to set or change the override"></div>
                        <div class="form-group"><label>Organization Lock</label>
                            <input value="${escapeHtml(s.org_lock_date || 'Not set')}" readonly>
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">Set by organization admins from Company Files. It applies across the whole company and cannot be bypassed by the company override password.</div></div>
                        <div class="form-group"><label>Effective Lock</label>
                            <input value="${escapeHtml(s.effective_lock_date || 'Not set')}" readonly>
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">The stricter of the company-admin lock and organization lock. Transactions on or before this date are blocked.</div></div>
                    </div>
                    ${s.effective_lock_layer ? `<div style="font-size:10px; color:var(--text-muted); margin-top:8px;">Current blocking layer: ${escapeHtml(s.effective_lock_layer)}</div>` : ''}
                </div>

                <div class="settings-section">
                    <h3>Email (SMTP)</h3>
                    <div style="font-size:10px; color:var(--text-muted); margin-bottom:8px;">
                        SMTP delivery is managed from the server <code>.env</code> file so browser users cannot redirect outbound mail settings.
                    </div>
                    ${s.smtp_password_notice ? `<div style="font-size:10px; margin-bottom:8px; color:var(--text-muted);">${escapeHtml(s.smtp_password_notice)}</div>` : ''}
                    <div class="form-grid">
                        <div class="form-group"><label>SMTP Host</label>
                            <input value="${escapeHtml(s.smtp_host || 'Configured in .env')}" readonly></div>
                        <div class="form-group"><label>SMTP Port</label>
                            <input value="${escapeHtml(s.smtp_port || 'Configured in .env')}" readonly></div>
                        <div class="form-group"><label>Username</label>
                            <input value="${escapeHtml(s.smtp_user || 'Configured in .env')}" readonly></div>
                        <div class="form-group"><label>From Email</label>
                            <input value="${escapeHtml(s.smtp_from_email || 'Configured in .env')}" readonly></div>
                        <div class="form-group"><label>From Name</label>
                            <input value="${escapeHtml(s.smtp_from_name || 'Configured in .env')}" readonly></div>
                        <div class="form-group"><label>Use TLS</label>
                            <input value="${s.smtp_use_tls === 'false' ? 'No' : 'Yes'}" readonly></div>
                    </div>
                    <button type="button" class="btn btn-sm btn-secondary" onclick="SettingsPage.testEmail()" style="margin-top:8px;">
                        Send Test Email</button>
                </div>

                <div class="settings-section">
                    <h3>Approved PO Delivery Locations</h3>
                    <div style="font-size:10px; color:var(--text-muted); margin-bottom:8px;">
                        Admin-only list of company-approved delivery locations for purchase orders. Enter one location per block: optional location name on the first line, then the delivery address lines beneath it. Leave a blank line between locations. The primary company address is approved automatically.
                    </div>
                    <div class="form-grid">
                        <div class="form-group full-width"><label>Approved PO Delivery Locations</label>
                            <textarea name="purchase_order_delivery_locations" rows="8" placeholder="Warehouse&#10;8 Depot Road&#10;Wellington Wellington 6011&#10;&#10;Christchurch Office&#10;55 Moorhouse Avenue&#10;Christchurch Canterbury 8011">${escapeHtml(s.purchase_order_delivery_locations || '')}</textarea></div>
                    </div>
                </div>


                <div class="settings-section">
                    <h3>Invoice Reminders</h3>
                    <div style="font-size:10px; color:var(--text-muted); margin-bottom:8px;">
                        Configure company-wide invoice reminder rules. Rules can trigger before or after the due date and will be used by future automated reminder workflows.
                    </div>
                    <div style="display:flex; gap:8px; margin-bottom:12px;">
                        <button type="button" class="btn btn-secondary" onclick="SettingsPage.showReminderRuleForm()">Add Reminder Rule</button>
                    </div>
                    <div id="invoice-reminder-rules-list">
                        <div style="font-size:11px; color:var(--text-muted);">Loading reminder rules…</div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3>Backup / Restore</h3>
                    <div style="display:flex; gap:8px; margin-bottom:12px;">
                        <button type="button" class="btn btn-primary" onclick="SettingsPage.createBackup()">Create Backup</button>
                    </div>
                    <div id="backup-list"></div>
                </div>

                <div class="settings-section">
                    <h3>Demo Data</h3>
                    <div style="font-size:10px; color:var(--text-muted); margin-bottom:8px;">
                        Load the built-in NZ demo business for evaluation or training, including the seeded ANZ bank account and sample customer/vendor banking transactions. Safe to rerun; the seed script skips when the demo business already exists.
                    </div>
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        <button type="button" class="btn btn-secondary" onclick="SettingsPage.loadDemoData()">Load NZ Demo Data</button>
                        <button type="button" class="btn btn-secondary" onclick="SettingsPage.loadChartTemplate('xero')">Load Xero Sample Default Chart</button>
                        <button type="button" class="btn btn-secondary" onclick="SettingsPage.loadChartTemplate('mas')">Load MAS Chart of Accounts</button>
                    </div>
                </div>

                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Save Settings</button>
                </div>
            </form>`;
    },

    async save(e) {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        const startDay = data.financial_year_start_day || '';
        const startMonth = data.financial_year_start_month || '';
        const endDay = data.financial_year_end_day || '';
        const endMonth = data.financial_year_end_month || '';
        data.financial_year_start = startDay && startMonth ? `${startMonth}-${startDay}` : '';
        data.financial_year_end = endDay && endMonth ? `${endMonth}-${endDay}` : '';
        delete data.financial_year_start_day;
        delete data.financial_year_start_month;
        delete data.financial_year_end_day;
        delete data.financial_year_end_month;
        // Remove file input from data
        delete data.file;
        try {
            const settings = await API.put('/settings', data);
            if (typeof App !== 'undefined') App.settings = settings;
            toast('Settings saved');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async uploadLogo(input) {
        if (!input.files[0]) return;
        const formData = new FormData();
        formData.append('file', input.files[0]);
        try {
            const data = await API.postForm('/uploads/logo', formData);
            toast('Logo uploaded');
            App.navigate('#/settings');
        } catch (err) { toast(err.message, 'error'); }
    },

    async testEmail() {
        try {
            await API.post('/settings/test-email');
            toast('Test email sent');
        } catch (err) { toast(err.message, 'error'); }
    },

    async createBackup() {
        try {
            const result = await API.post('/backups');
            toast(`Backup created: ${result.filename}`);
            SettingsPage.loadBackups();
        } catch (err) { toast(err.message, 'error'); }
    },


    formatReminderRuleTiming(rule) {
        const offset = Number(rule.day_offset || 0);
        if (offset === 0) return 'On due date';
        const unit = offset === 1 ? 'day' : 'days';
        return rule.timing_direction === 'before_due'
            ? `${offset} ${unit} before due`
            : `${offset} ${unit} overdue`;
    },

    renderInvoiceReminderRulesMarkup(rules) {
        if (!Array.isArray(rules) || rules.length === 0) {
            return '<div style="font-size:11px; color:var(--text-muted);">No invoice reminder rules yet.</div>';
        }
        return `<div class="table-container"><table>
            <thead><tr><th>Name</th><th>Timing</th><th>Status</th><th>Subject</th><th>Actions</th></tr></thead>
            <tbody>${rules.map(rule => `<tr>
                <td><strong>${escapeHtml(rule.name || '')}</strong></td>
                <td>${escapeHtml(SettingsPage.formatReminderRuleTiming(rule))}</td>
                <td>${rule.is_enabled ? 'Enabled' : 'Disabled'}</td>
                <td>${escapeHtml(rule.subject_template || '')}</td>
                <td class="actions">
                    <button class="btn btn-sm btn-secondary" type="button" onclick="SettingsPage.showReminderRuleForm(${rule.id})">Edit</button>
                    <button class="btn btn-sm btn-secondary" type="button" onclick="SettingsPage.deleteReminderRule(${rule.id})">Delete</button>
                </td>
            </tr>`).join('')}</tbody>
        </table></div>`;
    },

    async loadInvoiceReminderRules() {
        const listEl = typeof $ === 'function' ? $('#invoice-reminder-rules-list') : null;
        if (!listEl) return;
        try {
            const rules = await API.get('/settings/invoice-reminder-rules');
            SettingsPage._invoiceReminderRules = Array.isArray(rules) ? rules : [];
            listEl.innerHTML = SettingsPage.renderInvoiceReminderRulesMarkup(SettingsPage._invoiceReminderRules);
        } catch (err) {
            listEl.innerHTML = `<div style="font-size:11px; color:var(--danger);">${escapeHtml(err.message || 'Failed to load reminder rules')}</div>`;
        }
    },

    showReminderRuleForm(id = null) {
        const existing = (SettingsPage._invoiceReminderRules || []).find(rule => rule.id === id) || null;
        const rule = existing || {
            name: '',
            timing_direction: 'before_due',
            day_offset: 3,
            is_enabled: true,
            sort_order: (SettingsPage._invoiceReminderRules || []).length,
            subject_template: '',
            body_template: '',
        };
        openModal(existing ? 'Edit Invoice Reminder Rule' : 'New Invoice Reminder Rule', `
            <form onsubmit="SettingsPage.saveReminderRule(event, ${existing ? existing.id : 'null'})">
                <div class="form-grid">
                    <div class="form-group"><label>Name</label>
                        <input name="name" value="${escapeHtml(rule.name || '')}" placeholder="Optional – auto-generated if blank"></div>
                    <div class="form-group"><label>Timing</label>
                        <select name="timing_direction">
                            <option value="before_due" ${rule.timing_direction === 'before_due' ? 'selected' : ''}>Before due date</option>
                            <option value="after_due" ${rule.timing_direction === 'after_due' ? 'selected' : ''}>After due date</option>
                        </select></div>
                    <div class="form-group"><label>Day Offset</label>
                        <input name="day_offset" type="number" min="0" max="365" value="${Number(rule.day_offset || 0)}" required></div>
                    <div class="form-group"><label>Sort Order</label>
                        <input name="sort_order" type="number" min="0" value="${Number(rule.sort_order || 0)}"></div>
                    <div class="form-group"><label>Enabled</label>
                        <label style="display:flex; gap:8px; align-items:center; min-height:34px;">
                            <input name="is_enabled" type="checkbox" ${rule.is_enabled !== false ? 'checked' : ''}>
                            <span>Rule is enabled</span>
                        </label></div>
                    <div class="form-group full-width"><label>Subject Template</label>
                        <input name="subject_template" value="${escapeHtml(rule.subject_template || '')}" placeholder="Optional – defaults if blank"></div>
                    <div class="form-group full-width"><label>Body Template</label>
                        <textarea name="body_template" rows="6" placeholder="Optional – defaults if blank">${escapeHtml(rule.body_template || '')}</textarea></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${existing ? 'Update' : 'Create'} Rule</button>
                </div>
            </form>`);
    },

    async saveReminderRule(e, id = null) {
        e.preventDefault();
        const form = e.target;
        const data = {
            name: form.name.value || null,
            timing_direction: form.timing_direction.value,
            day_offset: parseInt(form.day_offset.value, 10) || 0,
            sort_order: form.sort_order.value === '' ? null : (parseInt(form.sort_order.value, 10) || 0),
            is_enabled: !!form.is_enabled.checked,
            subject_template: form.subject_template.value || null,
            body_template: form.body_template.value || null,
        };
        try {
            if (id) {
                await API.put(`/settings/invoice-reminder-rules/${id}`, data);
                toast('Invoice reminder rule updated');
            } else {
                await API.post('/settings/invoice-reminder-rules', data);
                toast('Invoice reminder rule created');
            }
            closeModal();
            await SettingsPage.loadInvoiceReminderRules();
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async deleteReminderRule(id) {
        if (typeof confirm === 'function' && !confirm('Delete this invoice reminder rule?')) return;
        try {
            await API.del(`/settings/invoice-reminder-rules/${id}`);
            toast('Invoice reminder rule deleted');
            await SettingsPage.loadInvoiceReminderRules();
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async loadDemoData() {
        try {
            await API.post('/settings/load-demo-data');
            toast('NZ demo data loaded, including the ANZ bank account');
        } catch (err) { toast(err.message, 'error'); }
    },

    async loadChartTemplate(templateKey) {
        try {
            const result = await API.post(`/settings/load-chart-template/${templateKey}`);
            toast(`${result.template_label} loaded`);
        } catch (err) { toast(err.message, 'error'); }
    },

    async downloadBackup(filename) {
        try {
            await API.download(`/backups/download/${filename}`, filename);
        } catch (err) { toast(err.message, 'error'); }
    },

    async loadBackups() {
        try {
            const backups = await API.get('/backups');
            const el = $('#backup-list');
            if (!el) return;
            if (backups.length === 0) {
                el.innerHTML = '<div style="font-size:11px; color:var(--text-muted);">No backups yet.</div>';
                return;
            }
            el.innerHTML = `<div class="table-container"><table>
                <thead><tr><th>Filename</th><th>Size</th><th>Created</th><th>Actions</th></tr></thead>
                <tbody>${backups.map(b => `<tr>
                    <td>${escapeHtml(b.filename)}</td>
                    <td>${(b.file_size / 1024).toFixed(1)} KB</td>
                    <td>${formatDate(b.created_at)}</td>
                    <td class="actions">
                        <button class="btn btn-sm btn-secondary" onclick="SettingsPage.downloadBackup('${encodeURIComponent(b.filename)}')">Download</button>
                    </td>
                </tr>`).join('')}</tbody>
            </table></div>`;
        } catch (e) { /* ignore */ }
    },
};
