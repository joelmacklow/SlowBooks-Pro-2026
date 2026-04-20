/**
 * Decompiled from QBW32.EXE!CPreferencesDialog  Offset: 0x0023F800
 * Original: tabbed dialog (IDD_PREFERENCES) with 12 tabs. We condensed
 * everything into a single page because nobody needs 12 tabs for
 * company name and tax rate. The registry writes at 0x00240200 are now
 * PostgreSQL INSERTs. Progress.
 */
const SettingsPage = {
    async render() {
        const s = await API.get('/settings');
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
                            ${s.company_logo_path ? `<img src="${escapeHtml(s.company_logo_path)}" style="max-width:200px; max-height:80px; margin-bottom:8px; display:block;">` : ''}
                            <input type="file" id="logo-upload" accept="image/*" onchange="SettingsPage.uploadLogo(this)">
                            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">PNG, JPG, or SVG. Max 200x80px recommended.</div>
                        </div>
                    </div>
                </div>

                <div class="settings-section">
                    <h3>Invoice Defaults</h3>
                    <div class="form-grid">
                        <div class="form-group"><label>Default Terms</label>
                            <select name="default_terms">
                                ${['Net 15','Net 30','Net 45','Net 60','Due on Receipt'].map(t =>
                                    `<option ${s.default_terms===t?'selected':''}>${t}</option>`).join('')}
                            </select></div>
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
                            <input name="financial_year_start" type="date" value="${escapeHtml(s.financial_year_start || '')}"></div>
                        <div class="form-group"><label>Financial Year End</label>
                            <input name="financial_year_end" type="date" value="${escapeHtml(s.financial_year_end || '')}"></div>
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
                            <input type="date" value="${escapeHtml(s.org_lock_date || '')}" disabled></div>
                        <div class="form-group"><label>Effective Lock</label>
                            <input type="date" value="${escapeHtml(s.effective_lock_date || '')}" disabled></div>
                    </div>
                    ${s.effective_lock_layer ? `<div style="font-size:10px; color:var(--text-muted); margin-top:8px;">Current blocking layer: ${escapeHtml(s.effective_lock_layer)}</div>` : ''}
                </div>

                <div class="settings-section">
                    <h3>Email (SMTP)</h3>
                    <div style="font-size:10px; color:var(--text-muted); margin-bottom:8px;">
                        Configure SMTP for sending invoices by email. SMTP passwords are managed via the <code>SMTP_PASSWORD</code> environment variable, not stored in SlowBooks settings.
                    </div>
                    ${s.smtp_password_notice ? `<div style="font-size:10px; margin-bottom:8px; color:var(--text-muted);">${escapeHtml(s.smtp_password_notice)}</div>` : ''}
                    <div class="form-grid">
                        <div class="form-group"><label>SMTP Host</label>
                            <input name="smtp_host" value="${escapeHtml(s.smtp_host || '')}" placeholder="smtp.gmail.com"></div>
                        <div class="form-group"><label>SMTP Port</label>
                            <input name="smtp_port" type="number" value="${escapeHtml(s.smtp_port || '587')}"></div>
                        <div class="form-group"><label>Username</label>
                            <input name="smtp_user" value="${escapeHtml(s.smtp_user || '')}"></div>
                        <div class="form-group"><label>Password</label>
                            <input name="smtp_password" type="password" value=""
                                placeholder="Managed via SMTP_PASSWORD environment variable" autocomplete="new-password"></div>
                        <div class="form-group"><label>From Email</label>
                            <input name="smtp_from_email" type="email" value="${escapeHtml(s.smtp_from_email || '')}"></div>
                        <div class="form-group"><label>From Name</label>
                            <input name="smtp_from_name" value="${escapeHtml(s.smtp_from_name || '')}"></div>
                        <div class="form-group"><label>Use TLS</label>
                            <select name="smtp_use_tls">
                                <option value="true" ${s.smtp_use_tls !== 'false' ? 'selected' : ''}>Yes</option>
                                <option value="false" ${s.smtp_use_tls === 'false' ? 'selected' : ''}>No</option>
                            </select></div>
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
