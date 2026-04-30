const TimesheetSelfServicePage = {
    _hashParams() {
        const hash = String(location.hash || '');
        const query = hash.includes('?') ? hash.split('?').slice(1).join('?') : '';
        return new URLSearchParams(query);
    },

    _selectedTimesheetId() {
        const id = Number(TimesheetSelfServicePage._hashParams().get('id') || '');
        return Number.isFinite(id) && id > 0 ? id : null;
    },

    _statusTone(status) {
        const normalized = String(status || '').toLowerCase();
        if (normalized === 'approved' || normalized === 'locked') return '#1f6f43';
        if (normalized === 'submitted') return '#1d4d7a';
        if (normalized === 'rejected') return '#8a2d2d';
        return 'var(--text-primary)';
    },

    _timeInputValue(value) {
        const raw = value == null ? '' : String(value).trim();
        if (!raw) return '';
        const match = raw.match(/\b(\d{2}:\d{2})/);
        if (match) return match[1];
        return raw.length > 5 ? raw.slice(0, 5) : raw;
    },

    _minutesFromTime(value) {
        const raw = TimesheetSelfServicePage._timeInputValue(value);
        if (!raw) return null;
        const [hours, minutes] = raw.split(':').map(Number);
        if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return null;
        return (hours * 60) + minutes;
    },

    _lineMode(line = {}) {
        return String(line.entry_mode || (line.start_time || line.end_time ? 'start_end' : 'duration')).trim().toLowerCase() || 'duration';
    },

    _lineHoursDisplay(line = {}) {
        const mode = TimesheetSelfServicePage._lineMode(line);
        if (mode === 'duration') {
            const duration = Number(line.duration_hours);
            return Number.isFinite(duration) && duration > 0 ? duration.toFixed(2) : '';
        }
        const start = TimesheetSelfServicePage._minutesFromTime(line.start_time);
        const end = TimesheetSelfServicePage._minutesFromTime(line.end_time);
        const breakMinutes = Number(line.break_minutes || 0);
        if (start == null || end == null || end <= start || !Number.isFinite(breakMinutes) || breakMinutes < 0) return '';
        const workedMinutes = end - start - breakMinutes;
        return workedMinutes > 0 ? (workedMinutes / 60).toFixed(2) : '';
    },

    _lineRows(lines = []) {
        const source = Array.isArray(lines) && lines.length
            ? lines
            : [{ work_date: '', entry_mode: 'start_end', duration_hours: '', start_time: '', end_time: '', break_minutes: 0, notes: '' }];
        return source.map((line) => `
            <tr>
                <td><input type="date" name="work_date" value="${escapeHtml(line.work_date || '')}" required oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
                <td>
                    <select name="entry_mode" onchange="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))">
                        <option value="start_end" ${TimesheetSelfServicePage._lineMode(line) === 'start_end' ? 'selected' : ''}>Start / End</option>
                        <option value="duration" ${TimesheetSelfServicePage._lineMode(line) === 'duration' ? 'selected' : ''}>Duration</option>
                    </select>
                </td>
                <td><input type="number" name="duration_hours" min="0.01" max="24" step="0.01" value="${escapeHtml(String(line.duration_hours ?? ''))}" oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
                <td><input type="time" name="start_time" value="${escapeHtml(TimesheetSelfServicePage._timeInputValue(line.start_time))}" oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
                <td><input type="time" name="end_time" value="${escapeHtml(TimesheetSelfServicePage._timeInputValue(line.end_time))}" oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
                <td><input type="number" name="break_minutes" min="0" step="1" value="${escapeHtml(String(line.break_minutes ?? 0))}" oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
                <td><input type="text" name="calculated_hours" value="${escapeHtml(TimesheetSelfServicePage._lineHoursDisplay(line))}" readonly tabindex="-1"></td>
                <td><input type="text" name="notes" value="${escapeHtml(line.notes || '')}" placeholder="Optional"></td>
                <td><button type="button" class="btn btn-sm btn-danger" onclick="TimesheetSelfServicePage.removeLineRow(this)">Remove</button></td>
            </tr>
        `).join('');
    },

    refreshLineCalculation(row) {
        if (!row) return;
        const mode = String(row.querySelector('select[name="entry_mode"]')?.value || 'start_end').toLowerCase();
        let calculated = '';
        if (mode === 'duration') {
            const duration = Number(row.querySelector('input[name="duration_hours"]')?.value || '');
            calculated = Number.isFinite(duration) && duration > 0 ? duration.toFixed(2) : '';
        } else {
            const start = TimesheetSelfServicePage._minutesFromTime(row.querySelector('input[name="start_time"]')?.value);
            const end = TimesheetSelfServicePage._minutesFromTime(row.querySelector('input[name="end_time"]')?.value);
            const breakMinutes = Number(row.querySelector('input[name="break_minutes"]')?.value || 0);
            if (start != null && end != null && end > start && Number.isFinite(breakMinutes) && breakMinutes >= 0) {
                const workedMinutes = end - start - breakMinutes;
                calculated = workedMinutes > 0 ? (workedMinutes / 60).toFixed(2) : '';
            }
        }
        const field = row.querySelector('input[name="calculated_hours"]');
        if (field) field.value = calculated;
    },

    _readLines(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return [];
        return Array.from(table.querySelectorAll('tbody tr')).map((row) => {
            const workDate = row.querySelector('input[name="work_date"]')?.value;
            const durationHours = row.querySelector('input[name="duration_hours"]')?.value;
            const entryMode = String(row.querySelector('select[name="entry_mode"]')?.value || 'start_end').toLowerCase() === 'duration'
                ? 'duration'
                : 'start_end';
            const notes = row.querySelector('input[name="notes"]')?.value;
            const startTime = row.querySelector('input[name="start_time"]')?.value;
            const endTime = row.querySelector('input[name="end_time"]')?.value;
            const breakMinutes = row.querySelector('input[name="break_minutes"]')?.value;
            return {
                work_date: workDate,
                entry_mode: entryMode,
                notes: notes || null,
                ...(entryMode === 'duration'
                    ? { duration_hours: durationHours }
                    : {
                        start_time: startTime || null,
                        end_time: endTime || null,
                        break_minutes: Number(breakMinutes || 0),
                    }),
            };
        }).filter((line) => line.work_date && (
            line.entry_mode === 'duration'
                ? Number(line.duration_hours) > 0
                : line.start_time && line.end_time
        ));
    },

    addLineRow(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="date" name="work_date" required oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
            <td>
                <select name="entry_mode" onchange="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))">
                    <option value="start_end" selected>Start / End</option>
                    <option value="duration">Duration</option>
                </select>
            </td>
            <td><input type="number" name="duration_hours" min="0.01" max="24" step="0.01" oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
            <td><input type="time" name="start_time" oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
            <td><input type="time" name="end_time" oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
            <td><input type="number" name="break_minutes" min="0" step="1" value="0" oninput="TimesheetSelfServicePage.refreshLineCalculation(this.closest('tr'))"></td>
            <td><input type="text" name="calculated_hours" readonly tabindex="-1"></td>
            <td><input type="text" name="notes" placeholder="Optional"></td>
            <td><button type="button" class="btn btn-sm btn-danger" onclick="TimesheetSelfServicePage.removeLineRow(this)">Remove</button></td>
        `;
        tbody.appendChild(row);
        TimesheetSelfServicePage.refreshLineCalculation(row);
    },

    removeLineRow(button) {
        const table = button?.closest?.('table');
        const row = button?.closest?.('tr');
        if (!table || !row) return;
        const rowCount = table.querySelectorAll('tbody tr').length;
        if (rowCount <= 1) {
            toast('At least one line is required', 'error');
            return;
        }
        row.remove();
    },

    lineRowsReadonly(lines = []) {
        if (!lines.length) return '<tr><td colspan="7" style="font-size:11px; color:var(--text-muted);">No lines</td></tr>';
        return lines.map((line) => `
            <tr>
                <td>${escapeHtml(formatDate(line.work_date))}</td>
                <td>${escapeHtml(line.entry_mode || 'duration')}</td>
                <td>${escapeHtml(TimesheetSelfServicePage._lineHoursDisplay(line) || String(line.duration_hours ?? '0.00'))}</td>
                <td>${escapeHtml(TimesheetSelfServicePage._timeInputValue(line.start_time))}</td>
                <td>${escapeHtml(TimesheetSelfServicePage._timeInputValue(line.end_time))}</td>
                <td>${escapeHtml(String(line.break_minutes ?? ''))}</td>
                <td>${escapeHtml(line.notes || '')}</td>
            </tr>
        `).join('');
    },

    listRows(timesheets = []) {
        if (!timesheets.length) {
            return '<tr><td colspan="7" style="font-size:11px; color:var(--text-muted);">No timesheets yet.</td></tr>';
        }
        return timesheets.map((timesheet) => {
            const canSubmit = ['draft', 'rejected'].includes(String(timesheet.status || '').toLowerCase());
            return `
                <tr>
                    <td><strong>#${timesheet.id}</strong></td>
                    <td>${escapeHtml(formatDate(timesheet.period_start))}</td>
                    <td>${escapeHtml(formatDate(timesheet.period_end))}</td>
                    <td>${escapeHtml(String(timesheet.total_hours ?? '0.00'))}</td>
                    <td><span style="font-weight:700; color:${TimesheetSelfServicePage._statusTone(timesheet.status)};">${escapeHtml(timesheet.status)}</span></td>
                    <td>${timesheet.submitted_at ? escapeHtml(formatDate(timesheet.submitted_at)) : '—'}</td>
                    <td class="actions">
                        <button class="btn btn-sm btn-secondary" onclick="App.navigate('#/my-timesheets?id=${timesheet.id}')">Open</button>
                        ${canSubmit ? `<button class="btn btn-sm btn-primary" onclick="TimesheetSelfServicePage.submitTimesheet(${timesheet.id})">Submit</button>` : ''}
                        <button class="btn btn-sm btn-secondary" onclick="TimesheetSelfServicePage.downloadTimesheetCsv(${timesheet.id})">CSV</button>
                    </td>
                </tr>
            `;
        }).join('');
    },

    async renderTimesheets() {
        const selectedId = TimesheetSelfServicePage._selectedTimesheetId();
        const timesheets = await API.get('/timesheets/self');
        let detail = null;
        if (selectedId) {
            try {
                detail = await API.get(`/timesheets/self/${selectedId}`);
            } catch (err) {
                toast(err.message, 'error');
            }
        }

        const isEditable = detail && ['draft', 'rejected'].includes(String(detail.status || '').toLowerCase());
        return `
            <div class="page-header">
                <h2>My Timesheets</h2>
                ${selectedId ? '<button class="btn btn-secondary" onclick="App.navigate(\'#/my-timesheets\')">New Timesheet</button>' : ''}
            </div>
            <div class="table-container">
                <table>
                    <thead><tr><th>ID</th><th>Period Start</th><th>Period End</th><th>Total Hours</th><th>Status</th><th>Submitted</th><th>Actions</th></tr></thead>
                    <tbody>${TimesheetSelfServicePage.listRows(timesheets)}</tbody>
                </table>
            </div>

            ${detail ? `
                <div class="settings-section">
                    <h3>Timesheet #${detail.id}</h3>
                    <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">
                        Period ${escapeHtml(formatDate(detail.period_start))} to ${escapeHtml(formatDate(detail.period_end))} · Status <strong style="color:${TimesheetSelfServicePage._statusTone(detail.status)};">${escapeHtml(detail.status)}</strong>
                    </div>
                    ${isEditable ? `
                        <form onsubmit="TimesheetSelfServicePage.updateTimesheet(event, ${detail.id})">
                            <table id="self-timesheet-edit-lines" class="compact-table">
                                <thead><tr><th>Work Date</th><th>Mode</th><th>Duration</th><th>Start</th><th>End</th><th>Break</th><th>Calculated Hours</th><th>Notes</th><th></th></tr></thead>
                                <tbody>${TimesheetSelfServicePage._lineRows(detail.lines || [])}</tbody>
                            </table>
                            <div class="form-actions" style="margin-top:10px;">
                                <button type="button" class="btn btn-secondary" onclick="TimesheetSelfServicePage.addLineRow('self-timesheet-edit-lines')">Add Line</button>
                                <button type="button" class="btn btn-secondary" onclick="TimesheetSelfServicePage.downloadTimesheetCsv(${detail.id})">Download CSV</button>
                                <button type="button" class="btn btn-primary" onclick="TimesheetSelfServicePage.submitTimesheet(${detail.id})">Submit</button>
                                <button type="submit" class="btn btn-primary">Save Draft</button>
                            </div>
                        </form>
                    ` : `
                        <div class="table-container">
                            <table>
                                <thead><tr><th>Work Date</th><th>Mode</th><th>Hours</th><th>Start</th><th>End</th><th>Break</th><th>Notes</th></tr></thead>
                                <tbody>${TimesheetSelfServicePage.lineRowsReadonly(detail.lines || [])}</tbody>
                            </table>
                        </div>
                        <div class="form-actions" style="margin-top:10px;">
                            <button type="button" class="btn btn-secondary" onclick="TimesheetSelfServicePage.downloadTimesheetCsv(${detail.id})">Download CSV</button>
                        </div>
                    `}
                </div>
            ` : `
                <div class="settings-section">
                    <h3>Create Timesheet</h3>
                    <p style="font-size:11px; color:var(--text-muted); margin-top:-4px; margin-bottom:10px;">Enter start/end times with break minutes to calculate daily hours automatically, or switch a row to duration mode if needed.</p>
                    <form onsubmit="TimesheetSelfServicePage.createTimesheet(event)">
                        <div class="form-grid">
                            <div class="form-group">
                                <label>Period Start</label>
                                <input type="date" name="period_start" required>
                            </div>
                            <div class="form-group">
                                <label>Period End</label>
                                <input type="date" name="period_end" required>
                            </div>
                        </div>
                        <table id="self-timesheet-create-lines" class="compact-table">
                            <thead><tr><th>Work Date</th><th>Mode</th><th>Duration</th><th>Start</th><th>End</th><th>Break</th><th>Calculated Hours</th><th>Notes</th><th></th></tr></thead>
                            <tbody>${TimesheetSelfServicePage._lineRows()}</tbody>
                        </table>
                        <div class="form-actions" style="margin-top:10px;">
                            <button type="button" class="btn btn-secondary" onclick="TimesheetSelfServicePage.addLineRow('self-timesheet-create-lines')">Add Line</button>
                            <button type="submit" class="btn btn-primary">Create Draft</button>
                        </div>
                    </form>
                </div>
            `}
        `;
    },

    async createTimesheet(e) {
        e.preventDefault();
        const form = e.target;
        const payload = {
            period_start: form.period_start.value,
            period_end: form.period_end.value,
            lines: TimesheetSelfServicePage._readLines('self-timesheet-create-lines'),
        };
        if (!payload.lines.length) {
            toast('Add at least one line', 'error');
            return;
        }
        try {
            const created = await API.post('/timesheets/self', payload);
            toast('Timesheet created');
            App.navigate(`#/my-timesheets?id=${created.id}`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async updateTimesheet(e, id) {
        e.preventDefault();
        const payload = { lines: TimesheetSelfServicePage._readLines('self-timesheet-edit-lines') };
        if (!payload.lines.length) {
            toast('Add at least one line', 'error');
            return;
        }
        try {
            await API.put(`/timesheets/self/${id}`, payload);
            toast('Timesheet updated');
            App.navigate(`#/my-timesheets?id=${id}`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async submitTimesheet(id) {
        const confirmed = typeof App?.confirmAction === 'function'
            ? await App.confirmAction({
                title: 'Submit Timesheet',
                message: 'Submit this timesheet for payroll review?',
                confirmLabel: 'Submit',
                cancelLabel: 'Cancel',
            })
            : (typeof confirm === 'function' ? confirm('Submit this timesheet for payroll review?') : true);
        if (!confirmed) return;
        try {
            await API.post(`/timesheets/self/${id}/submit`, {});
            toast('Timesheet submitted');
            App.navigate(`#/my-timesheets?id=${id}`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async downloadTimesheetCsv(id) {
        try {
            await API.download(`/timesheets/self/${id}/csv`, `Timesheet_${id}.csv`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async renderPayslips() {
        const payslips = await API.get('/payroll/self/payslips');
        return `
            <div class="page-header">
                <h2>My Payslips</h2>
            </div>
            <div class="table-container">
                <table>
                    <thead><tr><th>Pay Run</th><th>Pay Date</th><th>Period</th><th>Hours</th><th>Gross Pay</th><th>Net Pay</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${payslips.length ? payslips.map((row) => `
                            <tr>
                                <td>#${row.pay_run_id}</td>
                                <td>${escapeHtml(formatDate(row.pay_date))}</td>
                                <td>${escapeHtml(formatDate(row.period_start))} → ${escapeHtml(formatDate(row.period_end))}</td>
                                <td>${escapeHtml(String(row.hours ?? '0.00'))}</td>
                                <td>${escapeHtml(formatCurrency(row.gross_pay || 0, App.settings))}</td>
                                <td>${escapeHtml(formatCurrency(row.net_pay || 0, App.settings))}</td>
                                <td class="actions">
                                    <button class="btn btn-sm btn-secondary" onclick="TimesheetSelfServicePage.openPayslipPdf(${row.pay_run_id})">Open PDF</button>
                                </td>
                            </tr>
                        `).join('') : '<tr><td colspan="7" style="font-size:11px; color:var(--text-muted);">No processed payslips available yet.</td></tr>'}
                    </tbody>
                </table>
            </div>
        `;
    },

    async openPayslipPdf(runId) {
        try {
            await API.open(`/payroll/self/payslips/${runId}/pdf`, `PaySlip_${runId}.pdf`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },
};
