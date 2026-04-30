const AuthPage = {
    formatPermissionLabel(permissionKey) {
        if (!permissionKey) return '';
        const parts = String(permissionKey).split('.');
        const action = parts.pop();
        const subject = parts
            .join(' ')
            .replaceAll('_', ' ')
            .split(' ')
            .filter(Boolean)
            .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
            .join(' ');
        const actionLabel = action
            ? action.charAt(0).toUpperCase() + action.slice(1).replaceAll('_', ' ')
            : '';
        return [actionLabel, subject].filter(Boolean).join(' ');
    },

    renderPermissionSummary(permissionKeys) {
        return (permissionKeys || []).map((permission) => escapeHtml(AuthPage.formatPermissionLabel(permission))).join(', ');
    },

    bootstrapTokenFromLocation() {
        if (typeof location === 'undefined') return '';
        const hash = String(location.hash || '');
        const query = hash.includes('?')
            ? hash.split('?').slice(1).join('?')
            : String(location.search || '').replace(/^\?/, '');
        if (!query) return '';
        for (const part of query.split('&')) {
            const [rawKey, rawValue = ''] = part.split('=');
            if (decodeURIComponent(rawKey || '') === 'bootstrap_token') {
                return decodeURIComponent(rawValue.replace(/\+/g, ' '));
            }
        }
        return '';
    },

    async render() {
        const state = App.authState && Object.prototype.hasOwnProperty.call(App.authState, 'authenticated')
            ? App.authState
            : await API.get('/auth/me');
        App.setAuthState(state);
        if (typeof App.syncAuthUI === 'function') App.syncAuthUI();
        if (typeof App.syncNavVisibility === 'function') App.syncNavVisibility();
        if (state.authenticated) {
            return `
                <div class="page-header">
                    <h2>Signed In</h2>
                </div>
                <div class="empty-state">
                    <p>You are already signed in as <strong>${escapeHtml(state.user.full_name)}</strong>.</p>
                    <p style="margin-top:8px;"><button class="btn btn-primary" onclick="App.navigate('#/')">Go to Dashboard</button></p>
                </div>`;
        }
        if (state.bootstrap_required) {
            return AuthPage.renderBootstrapForm();
        }
        return AuthPage.renderLoginForm();
    },

    renderLoginForm() {
        return `
            <div class="page-header">
                <h2>Sign In</h2>
            </div>
            <form onsubmit="AuthPage.login(event)">
                <div class="settings-section" style="max-width:420px; margin:0 auto;">
                    <div class="form-grid">
                        <div class="form-group full-width"><label>Email</label><input name="email" type="email" required></div>
                        <div class="form-group full-width"><label>Password</label><input name="password" type="password" required></div>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">Sign In</button>
                    </div>
                </div>
            </form>`;
    },

    renderBootstrapForm() {
        const bootstrapToken = AuthPage.bootstrapTokenFromLocation();
        return `
            <div class="page-header">
                <h2>Create First Admin</h2>
            </div>
            <div class="settings-section" style="max-width:480px; margin:0 auto;">
                <div style="font-size:11px; color:var(--text-muted); margin-bottom:12px;">
                    No users exist yet. Create the first admin to activate protected payroll and admin features. If you opened a bootstrap setup URL from the terminal or container logs, the token will be prefilled below.
                </div>
                <form onsubmit="AuthPage.bootstrapAdmin(event)">
                    <div class="form-grid">
                        <div class="form-group full-width"><label>Full Name</label><input name="full_name" required></div>
                        <div class="form-group full-width"><label>Email</label><input name="email" type="email" required></div>
                        <div class="form-group full-width"><label>Password</label><input name="password" type="password" minlength="8" required></div>
                        <div class="form-group full-width"><label>Bootstrap Token</label><input name="bootstrap_token" type="text" autocomplete="off" placeholder="Required for remote setup; check the terminal or container logs" value="${escapeHtml(bootstrapToken)}"></div>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">Create First Admin</button>
                    </div>
                </form>
            </div>`;
    },

    async login(e) {
        e.preventDefault();
        const form = new FormData(e.target);
        try {
            const response = await API.post('/auth/login', {
                email: form.get('email'),
                password: form.get('password'),
            });
            App.setAuthState({ authenticated: true, bootstrap_required: false, user: response.user });
            await App.loadSettings();
            if (typeof App.syncAuthUI === 'function') App.syncAuthUI();
            if (typeof App.syncNavVisibility === 'function') App.syncNavVisibility();
            App.navigate('#/');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async bootstrapAdmin(e) {
        e.preventDefault();
        const form = new FormData(e.target);
        const bootstrapToken = String(form.get('bootstrap_token') || AuthPage.bootstrapTokenFromLocation() || '').trim();
        try {
            const responseRaw = await API.raw('POST', '/auth/bootstrap-admin', {
                body: {
                    full_name: form.get('full_name'),
                    email: form.get('email'),
                    password: form.get('password'),
                },
                headers: bootstrapToken ? { 'X-Bootstrap-Token': bootstrapToken } : {},
            });
            const response = await responseRaw.json();
            App.setAuthState({ authenticated: true, bootstrap_required: false, user: response.user });
            await App.loadSettings();
            if (typeof App.syncAuthUI === 'function') App.syncAuthUI();
            if (typeof App.syncNavVisibility === 'function') App.syncNavVisibility();
            App.navigate('#/');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async logout() {
        try {
            await API.post('/auth/logout');
        } catch (_err) {
            // Ignore logout transport failures; local session should still clear.
        }
        App.setAuthState({ authenticated: false, bootstrap_required: false, user: null });
        App.settings = {};
        if (typeof App.syncAuthUI === 'function') App.syncAuthUI();
        if (typeof App.syncNavVisibility === 'function') App.syncNavVisibility();
        App.navigate('#/login');
    },

    async renderUserManagement() {
        const [users, meta, links] = await Promise.all([
            API.get('/auth/users'),
            API.get('/auth/meta'),
            API.get('/employee-portal/links'),
        ]);
        let employees = [];
        let employeeLoadError = '';
        try {
            employees = await API.get('/employees?active_only=true');
        } catch (err) {
            employeeLoadError = err.message || 'Unable to load employee list';
        }
        AuthPage._usersCache = users;
        AuthPage._metaCache = meta;
        AuthPage._employeeLinksCache = links;
        AuthPage._employeeListCache = employees;
        return `
            <div class="page-header">
                <h2>Users & Access</h2>
                <button class="btn btn-primary" onclick="AuthPage.showUserForm()">New User</button>
            </div>
            <div class="settings-section">
                <h3>Role Templates</h3>
                <div style="font-size:10px; color:var(--text-muted); margin-bottom:10px;">
                    Start from a role template, then use allow/deny overrides when responsibilities need finer separation than a coarse fixed role.
                </div>
                <div class="card-grid">
                    ${meta.roles.map(role => `
                        <div class="card">
                            <div class="card-header">${escapeHtml(role.label)}</div>
                            <div style="font-size:11px; margin-bottom:6px;">${escapeHtml(role.description)}</div>
                            <div style="font-size:10px; color:var(--text-muted);">${AuthPage.renderPermissionSummary(role.permissions) || 'No permissions by default'}</div>
                        </div>`).join('')}
                </div>
            </div>
            <div class="settings-section">
                <h3>Current Users</h3>
                <div class="table-container"><table>
                    <thead><tr><th>User</th><th>Role</th><th>Overrides</th><th>Status</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${users.map((user, index) => `
                            <tr>
                                <td>
                                    <strong>${escapeHtml(user.full_name)}</strong><br>
                                    <span style="font-size:10px; color:var(--text-muted);">${escapeHtml(user.email)}</span>
                                </td>
                                <td>${escapeHtml(user.membership.role_key)}</td>
                                <td style="font-size:10px; color:var(--text-muted);">
                                    ${AuthPage.renderPermissionSummary(user.membership.allow_permissions.concat(user.membership.deny_permissions)) || 'None'}<br>
                                    <span style="color:var(--text-light);">Companies: ${escapeHtml((user.company_memberships || []).map((membership) => membership.company_scope).join(', ') || user.membership.company_scope)}</span>
                                </td>
                                <td>${user.is_active && user.membership.is_active ? 'Active' : 'Inactive'}</td>
                                <td class="actions"><button class="btn btn-sm btn-secondary" onclick="AuthPage.showUserForm(${index})">Edit</button></td>
                            </tr>`).join('')}
                    </tbody>
                </table></div>
            </div>
            <div class="settings-section">
                <h3>Employee Portal Links</h3>
                <div style="font-size:10px; color:var(--text-muted); margin-bottom:10px;">
                    Link a user login to one active employee record so self-service timesheet and payslip routes resolve ownership safely.
                </div>
                ${AuthPage.renderEmployeeLinkForm(users, employees, links, employeeLoadError)}
                <div class="table-container" style="margin-top:10px;"><table>
                    <thead><tr><th>User</th><th>Employee</th><th>Company Scope</th><th>Status</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${AuthPage.renderEmployeeLinkRows(links)}
                    </tbody>
                </table></div>
            </div>`;
    },

    renderEmployeeLinkRows(links = []) {
        if (!links.length) {
            return '<tr><td colspan="5" style="font-size:11px; color:var(--text-muted);">No active employee links.</td></tr>';
        }
        return links.map((link) => `
            <tr>
                <td>
                    <strong>${escapeHtml(link.user?.full_name || `User #${link.user?.id || ''}`)}</strong><br>
                    <span style="font-size:10px; color:var(--text-muted);">${escapeHtml(link.user?.email || '')}</span>
                </td>
                <td>
                    <strong>${escapeHtml(`${link.employee?.first_name || ''} ${link.employee?.last_name || ''}`.trim() || `Employee #${link.employee?.id || ''}`)}</strong><br>
                    <span style="font-size:10px; color:var(--text-muted);">Employee ID: ${escapeHtml(String(link.employee?.id || ''))}</span>
                </td>
                <td>${escapeHtml(link.company_scope || '__current__')}</td>
                <td>${link.is_active ? 'Active' : 'Inactive'}</td>
                <td class="actions">
                    ${link.is_active ? `<button class="btn btn-sm btn-danger" onclick="AuthPage.deactivateEmployeeLink(${link.id})">Deactivate</button>` : '—'}
                </td>
            </tr>
        `).join('');
    },

    renderEmployeeLinkForm(users = [], employees = [], links = [], employeeLoadError = '') {
        const activeLinkUserIds = new Set((links || []).filter((link) => link.is_active).map((link) => link.user?.id));
        const eligibleUsers = (users || [])
            .filter((user) => user?.is_active && user?.membership?.is_active)
            .filter((user) => !activeLinkUserIds.has(user.id))
            .sort((a, b) => (a.full_name || '').localeCompare(b.full_name || ''));

        const preferredUsers = eligibleUsers.filter((user) => user.membership?.role_key === 'employee_self_service');
        const userOptions = (preferredUsers.length ? preferredUsers : eligibleUsers).map((user) => `
            <option value="${user.id}">
                ${escapeHtml(user.full_name)} (${escapeHtml(user.email)}) — ${escapeHtml(user.membership?.role_key || 'user')}
            </option>
        `).join('');

        const employeeOptions = (employees || [])
            .filter((employee) => employee?.is_active !== false)
            .sort((a, b) => `${a.first_name || ''} ${a.last_name || ''}`.localeCompare(`${b.first_name || ''} ${b.last_name || ''}`))
            .map((employee) => `<option value="${employee.id}">${escapeHtml(`${employee.first_name || ''} ${employee.last_name || ''}`.trim())} (ID ${employee.id})</option>`)
            .join('');

        if (!userOptions) {
            return `<div style="font-size:11px; color:var(--text-muted);">No active users are available for new employee links.</div>`;
        }

        return `
            <form onsubmit="AuthPage.createEmployeeLink(event)">
                <div class="form-grid">
                    <div class="form-group">
                        <label>User Login</label>
                        <select name="user_id" required>${userOptions}</select>
                    </div>
                    <div class="form-group">
                        <label>Employee</label>
                        ${employeeOptions
                            ? `<select name="employee_id" required>${employeeOptions}</select>`
                            : `<input type="number" min="1" step="1" name="employee_id" required placeholder="Employee ID">`}
                        ${employeeLoadError ? `<div style="margin-top:4px; font-size:10px; color:var(--text-muted);">Employee list unavailable: ${escapeHtml(employeeLoadError)}. Enter employee ID manually if needed.</div>` : ''}
                    </div>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Link User to Employee</button>
                </div>
            </form>
        `;
    },

    async createEmployeeLink(e) {
        e.preventDefault();
        const form = e.target;
        const userId = Number(form.user_id?.value || '');
        const employeeId = Number(form.employee_id?.value || '');
        if (!Number.isFinite(userId) || userId <= 0 || !Number.isFinite(employeeId) || employeeId <= 0) {
            toast('Select a valid user and employee', 'error');
            return;
        }
        try {
            await API.post('/employee-portal/links', {
                user_id: userId,
                employee_id: employeeId,
            });
            toast('Employee portal link created');
            App.navigate('#/users-access');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async deactivateEmployeeLink(linkId) {
        const confirmed = await App.confirm('Deactivate Link', 'Deactivate this employee portal link? The user will lose self-service access.');
        if (!confirmed) return;
        try {
            await API.post(`/employee-portal/links/${linkId}/deactivate`, {});
            toast('Employee portal link deactivated');
            App.navigate('#/users-access');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    showUserForm(index = null) {
        const user = index === null ? null : AuthPage._usersCache[index];
        const meta = AuthPage._metaCache || { roles: [], permissions: [], company_scopes: [] };
        const allow = new Set(user?.membership?.allow_permissions || []);
        const deny = new Set(user?.membership?.deny_permissions || []);
        const companyScopes = new Set((user?.company_memberships || []).map((membership) => membership.company_scope));
        openModal(user ? `Edit ${user.full_name}` : 'New User', `
            <form onsubmit="AuthPage.saveUser(event, ${index === null ? 'null' : index})">
                <div class="form-grid">
                    <div class="form-group full-width"><label>Full Name</label><input name="full_name" required value="${escapeHtml(user?.full_name || '')}"></div>
                    <div class="form-group full-width"><label>Email</label><input name="email" type="email" ${user ? 'disabled' : 'required'} value="${escapeHtml(user?.email || '')}"></div>
                    <div class="form-group full-width"><label>Password ${user ? '(optional)' : ''}</label><input name="password" type="password" ${user ? '' : 'required'} minlength="8"></div>
                    <div class="form-group full-width"><label>Role Template</label>
                        <select name="role_key">${meta.roles.map(role => `<option value="${role.key}" ${user?.membership?.role_key === role.key ? 'selected' : ''}>${escapeHtml(role.label)}</option>`).join('')}</select>
                    </div>
                </div>
                <div class="settings-section">
                    <h3>Allow Overrides</h3>
                    <div class="card-grid">${meta.permissions.map(permission => `<label class="card" style="cursor:pointer;"><input type="checkbox" name="allow_permissions" value="${permission.key}" ${allow.has(permission.key) ? 'checked' : ''}> <strong>${escapeHtml(AuthPage.formatPermissionLabel(permission.key))}</strong><div style="font-size:10px; color:var(--text-muted); margin-top:4px;">${escapeHtml(permission.description)}</div></label>`).join('')}</div>
                </div>
                <div class="settings-section">
                    <h3>Deny Overrides</h3>
                    <div class="card-grid">${meta.permissions.map(permission => `<label class="card" style="cursor:pointer;"><input type="checkbox" name="deny_permissions" value="${permission.key}" ${deny.has(permission.key) ? 'checked' : ''}> <strong>${escapeHtml(AuthPage.formatPermissionLabel(permission.key))}</strong><div style="font-size:10px; color:var(--text-muted); margin-top:4px;">${escapeHtml(permission.description)}</div></label>`).join('')}</div>
                </div>
                <div class="settings-section">
                    <h3>Company Access</h3>
                    <div class="card-grid">${(meta.company_scopes || []).map(scope => `<label class="card" style="cursor:pointer;"><input type="checkbox" name="company_scopes" value="${scope.key}" ${(!user && scope.key === '__current__') || companyScopes.has(scope.key) ? 'checked' : ''}> <strong>${escapeHtml(scope.label)}</strong><div style="font-size:10px; color:var(--text-muted); margin-top:4px;">${escapeHtml(scope.database_name)}${scope.is_default ? ' — Default company' : ''}</div></label>`).join('')}</div>
                </div>
                <div class="form-grid">
                    <div class="form-group"><label><input type="checkbox" name="is_active" ${user ? (user.is_active ? 'checked' : '') : 'checked'}> User Active</label></div>
                    <div class="form-group"><label><input type="checkbox" name="membership_active" ${user ? (user.membership.is_active ? 'checked' : '') : 'checked'}> Membership Active</label></div>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${user ? 'Update User' : 'Create User'}</button>
                </div>
            </form>`);
    },

    async saveUser(e, index) {
        e.preventDefault();
        const form = e.target;
        const collect = (name) => Array.from(form.querySelectorAll(`input[name="${name}"]:checked`)).map((el) => el.value);
        const payload = {
            full_name: form.full_name.value,
            role_key: form.role_key.value,
            allow_permissions: collect('allow_permissions'),
            deny_permissions: collect('deny_permissions'),
            company_scopes: collect('company_scopes'),
            is_active: !!form.is_active.checked,
            membership_active: !!form.membership_active.checked,
        };
        if (form.password.value) payload.password = form.password.value;
        try {
            if (index === null) {
                payload.email = form.email.value;
                await API.post('/auth/users', payload);
                toast('User created');
            } else {
                const user = AuthPage._usersCache[index];
                await API.put(`/auth/users/${user.id}`, payload);
                toast('User updated');
            }
            closeModal();
            App.navigate('#/users-access');
        } catch (err) {
            toast(err.message, 'error');
        }
    },
};
