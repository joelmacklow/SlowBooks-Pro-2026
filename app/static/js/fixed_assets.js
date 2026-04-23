const FixedAssetsPage = {
    _escapedValue(value, fallback = '') {
        return escapeHtml(value === null || value === undefined || value === '' ? fallback : String(value));
    },

    openAssetDetail(assetId) {
        const detailHash = `#/fixed-assets/detail?id=${assetId}`;
        App.setDetailOrigin(detailHash, '#/fixed-assets');
        App.navigate(detailHash);
    },

    async openEditAssetForm(assetId) {
        try {
            return await FixedAssetsPage.showAssetForm(assetId);
        } catch (err) {
            toast(err.message || 'Unable to open asset details', 'error');
            return null;
        }
    },

    _queryParam(name) {
        const hash = location.hash || '';
        const query = hash.includes('?') ? hash.split('?')[1] : '';
        return new URLSearchParams(query).get(name);
    },

    async render() {
        const [assets, assetTypes, accounts] = await Promise.all([
            API.get('/fixed-assets'),
            API.get('/fixed-assets/types'),
            API.get('/accounts?active_only=true'),
        ]);
        FixedAssetsPage._accounts = accounts || [];
        FixedAssetsPage._assetTypes = assetTypes || [];
        const rows = (assets || []).map(asset => `
            <tr>
                <td><strong>${escapeHtml(asset.name)}</strong></td>
                <td>${escapeHtml(asset.asset_type_name || '')}</td>
                <td>${formatDate(asset.purchase_date)}</td>
                <td class="amount">${formatCurrency(asset.purchase_price || 0)}</td>
                <td class="amount">${formatCurrency(asset.book_value || 0)}</td>
                <td>${escapeHtml(asset.status || '')}</td>
                <td class="actions"><button class="btn btn-sm btn-secondary" onclick="FixedAssetsPage.openAssetDetail(${asset.id})">Open</button></td>
            </tr>
        `).join('') || `<tr><td colspan="7" style="color:var(--text-muted);">No fixed assets registered yet.</td></tr>`;

        const typeRows = (assetTypes || []).map(type => `
            <tr>
                <td><strong>${escapeHtml(type.name)}</strong></td>
                <td>${type.asset_account ? `${escapeHtml(type.asset_account.account_number || '')} ${escapeHtml(type.asset_account.name || '')}` : '—'}</td>
                <td>${type.accumulated_depreciation_account ? `${escapeHtml(type.accumulated_depreciation_account.account_number || '')} ${escapeHtml(type.accumulated_depreciation_account.name || '')}` : '—'}</td>
                <td>${type.depreciation_expense_account ? `${escapeHtml(type.depreciation_expense_account.account_number || '')} ${escapeHtml(type.depreciation_expense_account.name || '')}` : '—'}</td>
                <td class="actions"><button class="btn btn-sm btn-secondary" onclick="FixedAssetsPage.showAssetTypeForm(${type.id})">Edit</button></td>
            </tr>
        `).join('') || `<tr><td colspan="5" style="color:var(--text-muted);">No asset types configured yet.</td></tr>`;

        return `
            <div class="page-header">
                <div>
                    <h2>Fixed Assets</h2>
                    <div style="font-size:11px; color:var(--text-muted);">Register assets, run depreciation, and manage disposals.</div>
                </div>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="FixedAssetsPage.downloadTemplate()">Download CSV Template</button>
                    <button class="btn btn-secondary" onclick="FixedAssetsPage.importCsv()">Import CSV</button>
                    <button class="btn btn-secondary" onclick="FixedAssetsPage.runDepreciation()">Run FY Depreciation</button>
                    <button class="btn btn-secondary" onclick="FixedAssetsPage.showAssetTypeForm()">Add Asset Type</button>
                    <button class="btn btn-primary" onclick="FixedAssetsPage.showAssetForm()">Register Asset</button>
                </div>
            </div>
            <div class="settings-section">
                <h3>Registered Assets</h3>
                <div class="table-container"><table>
                    <thead><tr><th>Asset name</th><th>Asset type</th><th>Purchase date</th><th class="amount">Purchase price</th><th class="amount">Book value</th><th>Status</th><th>Actions</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table></div>
            </div>
            <div class="settings-section">
                <div class="page-header" style="margin-bottom:8px;">
                    <h3>Asset Types & Account Mapping</h3>
                </div>
                <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">Asset types carry the fixed asset, accumulated depreciation, and depreciation expense mappings used by registration and depreciation runs.</div>
                <div class="table-container"><table>
                    <thead><tr><th>Type</th><th>Asset account</th><th>Accumulated depreciation</th><th>Depreciation expense</th><th>Actions</th></tr></thead>
                    <tbody>${typeRows}</tbody>
                </table></div>
            </div>`;
    },

    async renderDetailScreen() {
        const assetId = Number(FixedAssetsPage._queryParam('id'));
        const asset = await API.get(`/fixed-assets/${assetId}`);
        const backLabel = App.detailBackLabel(`#/fixed-assets/detail?id=${assetId}`, '#/fixed-assets', 'Fixed Assets');
        const accountLabel = (account) => account ? `${escapeHtml(account.account_number || '')} ${escapeHtml(account.name || '')}`.trim() : '—';
        return `
            <div class="page-header">
                <div>
                    <button class="btn btn-secondary" onclick="App.navigateBackToDetailOrigin('#/fixed-assets/detail?id=${assetId}', '#/fixed-assets')">${escapeHtml(backLabel)}</button>
                    <h2 style="margin-top:8px;">${escapeHtml(asset.asset_number)} ${escapeHtml(asset.name)}</h2>
                </div>
                <div class="btn-group">
                    ${asset.status === 'registered' ? `<button class="btn btn-secondary" onclick="FixedAssetsPage.showDisposeForm(${asset.id})">Sell / Dispose</button>` : ''}
                    <button class="btn btn-primary" onclick="FixedAssetsPage.openEditAssetForm(${asset.id})">Edit details</button>
                </div>
            </div>
            <div class="card-grid">
                <div class="card"><div class="card-header">Cost basis</div><div class="card-value">${formatCurrency(asset.book_value_detail.cost_basis || 0)}</div></div>
                <div class="card"><div class="card-header">Value</div><div class="card-value">${formatCurrency(asset.book_value_detail.book_value || 0)}</div></div>
                <div class="card"><div class="card-header">Accumulated depreciation</div><div class="card-value">${formatCurrency(asset.book_value_detail.accumulated_depreciation || 0)}</div></div>
                <div class="card"><div class="card-header">YTD depreciation</div><div class="card-value">${formatCurrency(asset.book_value_detail.ytd_depreciation || 0)}</div></div>
            </div>
            <div class="settings-section">
                <h3>Details</h3>
                <div class="card-grid">
                    <div class="card"><div class="card-header">Asset name</div><div>${escapeHtml(asset.name)}</div></div>
                    <div class="card"><div class="card-header">Asset number</div><div>${escapeHtml(asset.asset_number)}</div></div>
                    <div class="card"><div class="card-header">Depreciation start date</div><div>${formatDate(asset.depreciation_start_date)}</div></div>
                    <div class="card"><div class="card-header">Purchase date</div><div>${formatDate(asset.purchase_date)}</div></div>
                    <div class="card"><div class="card-header">Purchase price</div><div>${formatCurrency(asset.purchase_price || 0)}</div></div>
                    <div class="card"><div class="card-header">Prior accumulated depreciation</div><div>${formatCurrency(asset.opening_accumulated_depreciation || 0)}</div></div>
                    <div class="card"><div class="card-header">Asset type</div><div>${escapeHtml(asset.asset_type?.name || '')}</div></div>
                    <div class="card"><div class="card-header">Serial number</div><div>${escapeHtml(asset.serial_number || '-')}</div></div>
                    <div class="card"><div class="card-header">Warranty expiry</div><div>${asset.warranty_expiry ? formatDate(asset.warranty_expiry) : '-'}</div></div>
                    <div class="card"><div class="card-header">Description</div><div>${escapeHtml(asset.description || '-')}</div></div>
                    <div class="card"><div class="card-header">Source reference</div><div>${escapeHtml(asset.source_reference || '-')}</div></div>
                    <div class="card"><div class="card-header">Status</div><div>${escapeHtml(asset.status)}</div></div>
                </div>
            </div>
            <div class="settings-section">
                <h3>Accounts</h3>
                <div class="card-grid">
                    <div class="card"><div class="card-header">Asset account</div><div>${accountLabel(asset.asset_account)}</div></div>
                    <div class="card"><div class="card-header">Accumulated depreciation account</div><div>${accountLabel(asset.accumulated_depreciation_account)}</div></div>
                    <div class="card"><div class="card-header">Depreciation expense account</div><div>${accountLabel(asset.depreciation_expense_account)}</div></div>
                    <div class="card"><div class="card-header">Offset account</div><div>${accountLabel(asset.offset_account)}</div></div>
                </div>
            </div>
            <div class="settings-section">
                <h3>Book depreciation settings</h3>
                <div class="card-grid">
                    <div class="card"><div class="card-header">Depreciation start date</div><div>${formatDate(asset.depreciation_start_date)}</div></div>
                    <div class="card"><div class="card-header">Depreciation method</div><div>${escapeHtml(asset.depreciation_method)}</div></div>
                    <div class="card"><div class="card-header">Calculation basis</div><div>${escapeHtml(asset.calculation_basis)}</div></div>
                    <div class="card"><div class="card-header">Rate</div><div>${asset.rate !== null && asset.rate !== undefined ? escapeHtml(String(asset.rate)) : '-'}</div></div>
                    <div class="card"><div class="card-header">Effective life</div><div>${asset.effective_life_years || '-'}</div></div>
                    <div class="card"><div class="card-header">Cost limit</div><div>${asset.cost_limit !== null && asset.cost_limit !== undefined ? formatCurrency(asset.cost_limit) : '-'}</div></div>
                    <div class="card"><div class="card-header">Residual value</div><div>${formatCurrency(asset.residual_value || 0)}</div></div>
                    <div class="card"><div class="card-header">Last depreciation run</div><div>${asset.last_depreciation_run_date ? formatDate(asset.last_depreciation_run_date) : '-'}</div></div>
                </div>
            </div>
            <div class="settings-section">
                <h3>Value</h3>
                <div class="table-container"><table>
                    <thead><tr><th>Basis</th><th class="amount">Cost basis</th><th class="amount">Value</th><th class="amount">Accumulated depreciation</th><th class="amount">YTD depreciation</th></tr></thead>
                    <tbody>
                        <tr>
                            <td>Book</td>
                            <td class="amount">${formatCurrency(asset.book_value_detail.cost_basis || 0)}</td>
                            <td class="amount">${formatCurrency(asset.book_value_detail.book_value || 0)}</td>
                            <td class="amount">${formatCurrency(asset.book_value_detail.accumulated_depreciation || 0)}</td>
                            <td class="amount">${formatCurrency(asset.book_value_detail.ytd_depreciation || 0)}</td>
                        </tr>
                    </tbody>
                </table></div>
            </div>`;
    },

    async showAssetTypeForm(id = null) {
        const [accounts, systemRoles, assetTypes] = await Promise.all([
            API.get('/accounts?active_only=true'),
            API.get('/accounts/system-roles'),
            API.get('/fixed-assets/types'),
        ]);
        const current = id ? (assetTypes || []).find(type => type.id === id) : null;
        const defaultAccDep = (systemRoles || []).find(role => role.role_key === 'system_account_fixed_asset_accumulated_depreciation_id')?.resolved_account?.id || '';
        const defaultDepExp = (systemRoles || []).find(role => role.role_key === 'system_account_fixed_asset_depreciation_expense_id')?.resolved_account?.id || '';
        const accountOptions = (type, selectedId) => accounts
            .filter(account => account.account_type === type)
            .sort((a, b) => String(a.account_number || '').localeCompare(String(b.account_number || '')) || a.name.localeCompare(b.name))
            .map(account => `<option value="${account.id}" ${String(selectedId || '') === String(account.id) ? 'selected' : ''}>${escapeHtml(account.account_number || '')} ${escapeHtml(account.name)}</option>`)
            .join('');

        openModal(id ? 'Edit Asset Type' : 'New Asset Type', `
            <form onsubmit="FixedAssetsPage.saveAssetType(event, ${id || 'null'})">
                <div class="form-grid">
                    <div class="form-group"><label>Name *</label><input name="name" required value="${escapeHtml(current?.name || '')}"></div>
                    <div class="form-group"><label>Asset Account</label><select name="asset_account_id"><option value="">--</option>${accountOptions('asset', current?.asset_account_id)}</select></div>
                    <div class="form-group"><label>Accumulated Depreciation</label><select name="accumulated_depreciation_account_id"><option value="">--</option>${accountOptions('asset', current?.accumulated_depreciation_account_id || defaultAccDep)}</select></div>
                    <div class="form-group"><label>Depreciation Expense</label><select name="depreciation_expense_account_id"><option value="">--</option>${accountOptions('expense', current?.depreciation_expense_account_id || defaultDepExp)}</select></div>
                    <div class="form-group"><label>Default Method</label><select name="default_depreciation_method">
                        <option value="dv" ${(current?.default_depreciation_method || 'dv') === 'dv' ? 'selected' : ''}>Diminishing value</option>
                        <option value="sl" ${(current?.default_depreciation_method || '') === 'sl' ? 'selected' : ''}>Straight line</option>
                    </select></div>
                    <div class="form-group"><label>Calculation Basis</label><select name="default_calculation_basis">
                        <option value="rate" ${(current?.default_calculation_basis || 'rate') === 'rate' ? 'selected' : ''}>Rate</option>
                        <option value="effective_life" ${(current?.default_calculation_basis || '') === 'effective_life' ? 'selected' : ''}>Effective life</option>
                    </select></div>
                    <div class="form-group"><label>Default Rate</label><input name="default_rate" type="number" step="0.0001" value="${escapeHtml(current?.default_rate ?? '')}"></div>
                    <div class="form-group"><label>Effective Life (years)</label><input name="default_effective_life_years" type="number" step="0.01" value="${escapeHtml(current?.default_effective_life_years ?? '')}"></div>
                    <div class="form-group"><label>Cost Limit</label><input name="default_cost_limit" type="number" step="0.01" value="${escapeHtml(current?.default_cost_limit ?? '')}"></div>
                    <div class="form-group full-width"><label>Description</label><textarea name="description">${escapeHtml(current?.description || '')}</textarea></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${id ? 'Update' : 'Create'} Asset Type</button>
                </div>
            </form>`);
    },

    async saveAssetType(e, id) {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        ['asset_account_id', 'accumulated_depreciation_account_id', 'depreciation_expense_account_id'].forEach(key => {
            data[key] = data[key] ? Number(data[key]) : null;
        });
        try {
            if (id) await API.put(`/fixed-assets/types/${id}`, data);
            else await API.post('/fixed-assets/types', data);
            closeModal();
            App.navigate('#/fixed-assets');
        } catch (err) { toast(err.message, 'error'); }
    },

    async showAssetForm(id = null) {
        const [assetTypes, accounts, asset] = await Promise.all([
            API.get('/fixed-assets/types'),
            API.get('/accounts?active_only=true'),
            id ? API.get(`/fixed-assets/${id}`) : Promise.resolve(null),
        ]);
        const current = asset || {};
        const typeOptions = (assetTypes || []).filter(type => type.is_active !== false)
            .map(type => `<option value="${type.id}" ${String(current.asset_type?.id || current.asset_type_id || '') === String(type.id) ? 'selected' : ''}>${escapeHtml(type.name)}</option>`)
            .join('');
        const offsetOptions = (accounts || [])
            .sort((a, b) => String(a.account_number || '').localeCompare(String(b.account_number || '')) || a.name.localeCompare(b.name))
            .map(account => `<option value="${account.id}" ${String(current.offset_account_id || '') === String(account.id) ? 'selected' : ''}>${escapeHtml(account.account_number || '')} ${escapeHtml(account.name)}</option>`)
            .join('');

        openModal(id ? 'Edit Fixed Asset' : 'Register Fixed Asset', `
            <form onsubmit="FixedAssetsPage.saveAsset(event, ${id || 'null'})">
                <div class="form-grid">
                    <div class="form-group"><label>Asset Number</label><input name="asset_number" value="${FixedAssetsPage._escapedValue(current.asset_number)}"></div>
                    <div class="form-group"><label>Asset Name *</label><input name="name" required value="${FixedAssetsPage._escapedValue(current.name)}"></div>
                    <div class="form-group"><label>Asset Type *</label><select name="asset_type_id" required>${typeOptions}</select></div>
                    <div class="form-group"><label>Purchase Date *</label><input name="purchase_date" type="date" required value="${FixedAssetsPage._escapedValue(current.purchase_date || todayISO())}"></div>
                    <div class="form-group"><label>Purchase Price *</label><input name="purchase_price" type="number" step="0.01" required value="${FixedAssetsPage._escapedValue(current.purchase_price)}"></div>
                    <div class="form-group"><label>Depreciation Start Date *</label><input name="depreciation_start_date" type="date" required value="${FixedAssetsPage._escapedValue(current.depreciation_start_date || current.purchase_date || todayISO())}"></div>
                    <div class="form-group"><label>Depreciation Method</label><select name="depreciation_method">
                        <option value="dv" ${(current.depreciation_method || 'dv') === 'dv' ? 'selected' : ''}>Diminishing value</option>
                        <option value="sl" ${(current.depreciation_method || '') === 'sl' ? 'selected' : ''}>Straight line</option>
                    </select></div>
                    <div class="form-group"><label>Calculation Basis</label><select name="calculation_basis">
                        <option value="rate" ${(current.calculation_basis || 'rate') === 'rate' ? 'selected' : ''}>Rate</option>
                        <option value="effective_life" ${(current.calculation_basis || '') === 'effective_life' ? 'selected' : ''}>Effective life</option>
                    </select></div>
                    <div class="form-group"><label>Rate</label><input name="rate" type="number" step="0.0001" value="${FixedAssetsPage._escapedValue(current.rate)}"></div>
                    <div class="form-group"><label>Effective Life (years)</label><input name="effective_life_years" type="number" step="0.01" value="${FixedAssetsPage._escapedValue(current.effective_life_years)}"></div>
                    <div class="form-group"><label>Cost Limit</label><input name="cost_limit" type="number" step="0.01" value="${FixedAssetsPage._escapedValue(current.cost_limit)}"></div>
                    <div class="form-group"><label>Residual Value</label><input name="residual_value" type="number" step="0.01" value="${FixedAssetsPage._escapedValue(current.residual_value, '0')}"></div>
                    <div class="form-group"><label>Opening Accumulated Depreciation</label><input name="opening_accumulated_depreciation" type="number" step="0.01" value="${FixedAssetsPage._escapedValue(current.opening_accumulated_depreciation, '0')}"></div>
                    <div class="form-group"><label>Investment Boost</label><input name="investment_boost" type="number" step="0.01" value="${FixedAssetsPage._escapedValue(current.investment_boost)}"></div>
                    <div class="form-group"><label>Acquisition Method</label><select name="acquisition_method">
                        <option value="cash" ${(current.acquisition_method || 'cash') === 'cash' ? 'selected' : ''}>Cash</option>
                        <option value="accounts_payable" ${(current.acquisition_method || '') === 'accounts_payable' ? 'selected' : ''}>Accounts Payable</option>
                        <option value="journal" ${(current.acquisition_method || '') === 'journal' ? 'selected' : ''}>Journal</option>
                        <option value="opening_balance" ${(current.acquisition_method || '') === 'opening_balance' ? 'selected' : ''}>Opening Balance</option>
                    </select></div>
                    <div class="form-group"><label>Offset Account</label><select name="offset_account_id"><option value="">--</option>${offsetOptions}</select></div>
                    <div class="form-group"><label>Serial Number</label><input name="serial_number" value="${FixedAssetsPage._escapedValue(current.serial_number)}"></div>
                    <div class="form-group"><label>Warranty Expiry</label><input name="warranty_expiry" type="date" value="${FixedAssetsPage._escapedValue(current.warranty_expiry)}"></div>
                    <div class="form-group full-width"><label>Source Reference</label><input name="source_reference" value="${FixedAssetsPage._escapedValue(current.source_reference)}"></div>
                    <div class="form-group full-width"><label>Description</label><textarea name="description">${FixedAssetsPage._escapedValue(current.description)}</textarea></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${id ? 'Update' : 'Register'} Asset</button>
                </div>
            </form>`);
    },

    async saveAsset(e, id) {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        data.asset_type_id = Number(data.asset_type_id);
        data.offset_account_id = data.offset_account_id ? Number(data.offset_account_id) : null;
        try {
            const result = id ? await API.put(`/fixed-assets/${id}`, data) : await API.post('/fixed-assets', data);
            closeModal();
            App.navigate(`#/fixed-assets/detail?id=${result.id}`);
        } catch (err) { toast(err.message, 'error'); }
    },

    async showDisposeForm(assetId) {
        const [asset, accounts] = await Promise.all([
            API.get(`/fixed-assets/${assetId}`),
            API.get('/accounts?active_only=true'),
        ]);
        const options = (accounts || [])
            .sort((a, b) => String(a.account_number || '').localeCompare(String(b.account_number || '')) || a.name.localeCompare(b.name))
            .map(account => `<option value="${account.id}">${escapeHtml(account.account_number || '')} ${escapeHtml(account.name)}</option>`)
            .join('');
        openModal(`Dispose ${asset.asset_number}`, `
            <form onsubmit="FixedAssetsPage.disposeAsset(event, ${asset.id})">
                <div style="font-size:11px; color:var(--text-muted); margin-bottom:12px;">Current book value: <strong>${formatCurrency(asset.book_value || 0)}</strong></div>
                <div class="form-grid">
                    <div class="form-group"><label>Disposal Date *</label><input name="disposal_date" type="date" required value="${todayISO()}"></div>
                    <div class="form-group"><label>Sale Price</label><input name="sale_price" type="number" step="0.01" value="0"></div>
                    <div class="form-group"><label>Disposal Costs</label><input name="disposal_costs" type="number" step="0.01" value="0"></div>
                    <div class="form-group"><label>Proceeds Account *</label><select name="disposal_account_id" required>${options}</select></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Dispose Asset</button>
                </div>
            </form>`);
    },

    async disposeAsset(e, assetId) {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        data.disposal_account_id = Number(data.disposal_account_id);
        try {
            await API.post(`/fixed-assets/${assetId}/dispose`, data);
            closeModal();
            App.navigate(`#/fixed-assets/detail?id=${assetId}`);
        } catch (err) { toast(err.message, 'error'); }
    },

    async runDepreciation() {
        const ok = await App.confirmAction({
            title: 'Run FY Depreciation',
            message: 'Run depreciation through the end of the current financial year?',
            confirmLabel: 'Run Depreciation',
        });
        if (!ok) return;
        try {
            const result = await API.post('/fixed-assets/depreciation/run');
            toast(`Depreciation posted for ${result.assets_updated} asset(s)`);
            App.navigate('#/fixed-assets');
        } catch (err) { toast(err.message, 'error'); }
    },

    downloadTemplate() {
        API.download('/fixed-assets/import-template', 'fixed_assets_import_template.csv');
    },

    importCsv() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.csv,text/csv';
        input.onchange = async () => {
            if (!input.files || !input.files[0]) return;
            const form = new FormData();
            form.append('file', input.files[0]);
            try {
                const result = await API.postForm('/fixed-assets/import', form);
                const errorHtml = (result.errors || []).length ? `<div style="margin-top:8px; color:var(--danger);">${result.errors.map(err => escapeHtml(err)).join('<br>')}</div>` : '';
                openModal('Fixed Asset Import', `
                    <div style="font-size:11px; color:var(--text-secondary);">
                        Imported: <strong>${result.imported}</strong><br>
                        Skipped blank rows: <strong>${result.skipped}</strong><br>
                        Asset types created: <strong>${result.created_asset_types}</strong>
                        ${errorHtml}
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn-primary" onclick="closeModal(); App.navigate('#/fixed-assets')">Done</button>
                    </div>`);
                App.navigate('#/fixed-assets');
            } catch (err) { toast(err.message, 'error'); }
        };
        input.click();
    },
};

if (typeof globalThis !== 'undefined') {
    globalThis.FixedAssetsPage = FixedAssetsPage;
}
