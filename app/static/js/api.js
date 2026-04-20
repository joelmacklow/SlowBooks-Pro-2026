/**
 * Decompiled from QBW32.EXE!CQBNetworkLayer  Offset: 0x002A1000
 * Original used named pipes (\\.\pipe\QuickBooks) for IPC to the
 * QBDBMgrN.exe database server process. This is the modern equivalent
 * rebuilt on top of fetch(). The named pipe protocol was a nightmare to
 * reverse — 47 different message types, all packed structs with no padding.
 */
const API = {
    shouldPromptForClosingDatePassword(status, detail, headers = {}) {
        return (
            status === 403
            && !headers['X-Closing-Date-Password']
            && typeof detail === 'string'
            && detail.includes('company admin lock date')
            && detail.includes('override password')
        );
    },

    authHeaders(path = '') {
        const token = typeof localStorage !== 'undefined' ? localStorage.getItem('slowbooks-auth-token') : null;
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const selectedCompany = typeof localStorage !== 'undefined' ? localStorage.getItem('slowbooks_company') : null;
        if (selectedCompany && !path.startsWith('/auth/') && !path.startsWith('/companies')) {
            headers['X-Company-Database'] = selectedCompany;
        }
        return headers;
    },

    async _parseError(res) {
        const err = await res.json().catch(async () => ({ detail: await res.text().catch(() => res.statusText) }));
        return err.detail || 'Request failed';
    },

    async raw(method, path, { body = null, headers = {} } = {}) {
        const opts = {
            method,
            headers: { ...this.authHeaders(path), ...headers },
        };
        if (body !== null) {
            if (typeof FormData !== 'undefined' && body instanceof FormData) {
                opts.body = body;
            } else {
                opts.headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify(body);
            }
        }
        const res = await fetch(`/api${path}`, opts);
        if (!res.ok) {
            const detail = await this._parseError(res);
            if (this.shouldPromptForClosingDatePassword(res.status, detail, opts.headers) && typeof App !== 'undefined' && typeof App.promptClosingDatePassword === 'function') {
                const overridePassword = await App.promptClosingDatePassword(detail);
                if (overridePassword) {
                    return this.raw(method, path, {
                        body,
                        headers: { ...headers, 'X-Closing-Date-Password': overridePassword },
                    });
                }
            }
            if (res.status === 401 && typeof App !== 'undefined' && typeof App.handleUnauthorized === 'function') {
                App.handleUnauthorized(path, detail || 'Authentication required');
            }
            throw new Error(detail || 'Request failed');
        }
        return res;
    },

    async request(method, path, body = null) {
        const res = await this.raw(method, path, { body });
        return res.json();
    },

    get(path) { return this.request('GET', path); },
    post(path, data) { return this.request('POST', path, data); },
    put(path, data) { return this.request('PUT', path, data); },
    del(path) { return this.request('DELETE', path); },
    async postForm(path, formData) {
        const res = await this.raw('POST', path, { body: formData });
        return res.json();
    },
    async download(path, fallbackName = 'download.bin') {
        const res = await this.raw('GET', path);
        const disposition = res.headers.get('Content-Disposition');
        let filename = fallbackName;
        if (disposition) {
            const match = disposition.match(/filename="?([^\"]+)"?/);
            if (match) filename = match[1];
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    },
    async open(path, fallbackName = 'document.bin') {
        const res = await this.raw('GET', path);
        const disposition = res.headers.get('Content-Disposition');
        let filename = fallbackName;
        if (disposition) {
            const match = disposition.match(/filename="?([^\"]+)"?/);
            if (match) filename = match[1];
        }
        const blob = await res.blob();
        const objectSource = typeof File !== 'undefined'
            ? new File([blob], filename, { type: blob.type || 'application/octet-stream' })
            : blob;
        const url = URL.createObjectURL(objectSource);
        const opened = typeof window !== 'undefined' && typeof window.open === 'function' ? window.open(url, '_blank') : null;
        if (!opened) {
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.click();
        }
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
    },
};
