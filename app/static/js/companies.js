/**
 * Multi-Company — switch between company databases
 * Feature 16: Company list and creation UI
 */
const CompaniesPage = {
    _databaseNameTouched: false,
    _lastSuggestedDatabaseName: '',

    async render() {
        const canManageCompanies = App.hasPermission ? App.hasPermission('companies.manage') : true;
        const companies = await API.get('/companies');
        let html = `
            <div class="page-header">
                <h2>Company Files</h2>
                ${canManageCompanies ? `<button class="btn btn-primary" onclick="CompaniesPage.showCreate()">+ New Company</button>` : ''}
            </div>
            <p style="font-size:11px;color:var(--text-muted);margin-bottom:12px;">
                Each company uses a separate PostgreSQL database. Switch between companies below.
            </p>`;

        if (companies.length === 0) {
            html += '<div class="empty-state"><p>No additional companies created</p></div>';
        } else {
            html += '<div class="card-grid">';
            for (const c of companies) {
                html += `<div class="card" style="cursor:pointer;" onclick="CompaniesPage.switchTo('${escapeHtml(c.database_name)}')">
                    <div class="card-header">${escapeHtml(c.name)}${c.is_default ? ' <span class="badge badge-draft">Default</span>' : ''}</div>
                    <div style="font-size:10px;color:var(--text-muted);">${escapeHtml(c.database_name)}</div>
                    ${c.description ? `<div style="font-size:11px;margin-top:4px;">${escapeHtml(c.description)}</div>` : ''}
                    <div style="font-size:9px;color:var(--text-light);margin-top:4px;">Last accessed: ${c.last_accessed ? formatDate(c.last_accessed) : 'Never'}</div>
                </div>`;
            }
            html += '</div>';
        }
        return html;
    },

    suggestDatabaseName(name) {
        return String(name || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '')
            .replace(/_+/g, '_')
            .slice(0, 63);
    },

    handleCompanyNameInput(input) {
        const databaseInput = input?.form?.database_name;
        if (!databaseInput) return;
        const suggestion = CompaniesPage.suggestDatabaseName(input.value);
        const currentValue = databaseInput.value || '';
        if (!CompaniesPage._databaseNameTouched || currentValue === '' || currentValue === CompaniesPage._lastSuggestedDatabaseName) {
            databaseInput.value = suggestion;
            CompaniesPage._lastSuggestedDatabaseName = suggestion;
            CompaniesPage._databaseNameTouched = false;
        }
    },

    handleDatabaseNameInput(input) {
        CompaniesPage._databaseNameTouched = true;
    },

    showCreate() {
        CompaniesPage._databaseNameTouched = false;
        CompaniesPage._lastSuggestedDatabaseName = '';
        openModal('New Company', `
            <form onsubmit="CompaniesPage.create(event)">
                <div class="form-grid">
                    <div class="form-group"><label>Company Name *</label>
                        <input name="name" required oninput="CompaniesPage.handleCompanyNameInput(this)"></div>
                    <div class="form-group"><label>Database Name *</label>
                        <input name="database_name" required pattern="[a-z0-9_]+" title="Lowercase letters, numbers, underscores only" oninput="CompaniesPage.handleDatabaseNameInput(this)"></div>
                    <div class="form-group full-width"><label>Description</label>
                        <textarea name="description"></textarea></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create Company</button>
                </div>
            </form>`);
    },

    async create(e) {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        try {
            await API.post('/companies', data);
            toast('Company created');
            closeModal();
            App.navigate('#/companies');
        } catch (err) { toast(err.message, 'error'); }
    },

    switchTo(dbName) {
        // Store selected company in localStorage
        localStorage.setItem('slowbooks_company', dbName);
        toast(`Switched to ${dbName}. Reload to apply.`);
        // In a full implementation, this would reload with X-Company-Id header
        location.reload();
    },
};
