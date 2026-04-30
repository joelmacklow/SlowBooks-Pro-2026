/**
 * Payroll — NZ draft pay runs with PAYE calculations and posting.
 */
const PayrollPage = {
    _timeInputValue(value) {
        const raw = value == null ? '' : String(value).trim();
        if (!raw) return '';
        const match = raw.match(/\b(\d{2}:\d{2})/);
        if (match) return match[1];
        return raw.length > 5 ? raw.slice(0, 5) : raw;
    },

    _breakHoursDisplay(line = {}) {
        const provided = Number(line.break_hours);
        if (Number.isFinite(provided) && provided > 0) return provided.toFixed(2);
        const minutes = Number(line.break_minutes ?? 0);
        if (!Number.isFinite(minutes) || minutes <= 0) return '';
        return (minutes / 60).toFixed(2);
    },

    _lineHoursDisplay(line = {}) {
        const start = PayrollPage._timeInputValue(line.start_time);
        const end = PayrollPage._timeInputValue(line.end_time);
        const breakMinutes = Number(line.break_minutes ?? 0);
        if (!start || !end || !Number.isFinite(breakMinutes) || breakMinutes < 0) return String(line.duration_hours ?? '');
        const startParts = start.split(':').map(Number);
        const endParts = end.split(':').map(Number);
        if (startParts.some((part) => !Number.isFinite(part)) || endParts.some((part) => !Number.isFinite(part))) {
            return String(line.duration_hours ?? '');
        }
        const workedMinutes = ((endParts[0] * 60) + endParts[1]) - ((startParts[0] * 60) + startParts[1]) - breakMinutes;
        return workedMinutes > 0 ? (workedMinutes / 60).toFixed(2) : '';
    },

    _timesheetPermissions() {
        const hasPermission = typeof App !== 'undefined' && typeof App.hasPermission === 'function'
            ? (permission) => App.hasPermission(permission)
            : () => true;
        return {
            manage: hasPermission('timesheets.manage'),
            approve: hasPermission('timesheets.approve'),
            export: hasPermission('timesheets.export'),
        };
    },

    _canReviewTimesheets() {
        const perms = PayrollPage._timesheetPermissions();
        return perms.manage || perms.approve || perms.export;
    },

    _reviewPeriodValues() {
        return {
            periodStart: $('#timesheet-review-period-start')?.value || todayISO(),
            periodEnd: $('#timesheet-review-period-end')?.value || todayISO(),
        };
    },

    _timesheetLineRows(lines = []) {
        const source = Array.isArray(lines) && lines.length
            ? lines
            : [{ work_date: '', start_time: '', end_time: '', break_hours: '', notes: '' }];
        return source.map((line) => `
            <tr>
                <td class="col-work-date"><input type="date" name="work_date" value="${escapeHtml(line.work_date || '')}" required></td>
                <td class="col-time"><input type="time" name="start_time" value="${escapeHtml(PayrollPage._timeInputValue(line.start_time))}"></td>
                <td class="col-time"><input type="time" name="end_time" value="${escapeHtml(PayrollPage._timeInputValue(line.end_time))}"></td>
                <td class="col-break"><input type="number" name="break_hours" min="0" max="12" step="0.01" value="${escapeHtml(String(PayrollPage._breakHoursDisplay(line) || line.break_hours || ''))}"></td>
                <td class="col-hours"><input type="text" name="calculated_hours" value="${escapeHtml(PayrollPage._lineHoursDisplay(line))}" readonly tabindex="-1"></td>
                <td class="col-notes"><input type="text" name="notes" value="${escapeHtml(line.notes || '')}" placeholder="Optional"></td>
                <td class="col-actions"><button type="button" class="btn btn-sm btn-danger" onclick="PayrollPage.removeTimesheetLineRow(this)">Remove</button></td>
            </tr>
        `).join('');
    },

    _readTimesheetLines(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return [];
        return Array.from(table.querySelectorAll('tbody tr')).map((row) => {
            const workDate = row.querySelector('input[name="work_date"]')?.value;
            const startTime = row.querySelector('input[name="start_time"]')?.value;
            const endTime = row.querySelector('input[name="end_time"]')?.value;
            const breakHours = Number(row.querySelector('input[name="break_hours"]')?.value || 0);
            const notes = row.querySelector('input[name="notes"]')?.value;
            if (!workDate) return null;
            const payload = {
                work_date: workDate,
                entry_mode: 'start_end',
                notes: notes || null,
                start_time: startTime || null,
                end_time: endTime || null,
                break_minutes: Number.isFinite(breakHours) ? Math.round(breakHours * 60) : 0,
            };
            return payload;
        }).filter((line) => line && line.start_time && line.end_time);
    },

    addTimesheetLineRow(tableId, line = {}) {
        const table = document.getElementById(tableId);
        if (!table) return;
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="col-work-date"><input type="date" name="work_date" value="${escapeHtml(line.work_date || '')}" required></td>
            <td class="col-time"><input type="time" name="start_time" value="${escapeHtml(PayrollPage._timeInputValue(line.start_time))}"></td>
            <td class="col-time"><input type="time" name="end_time" value="${escapeHtml(PayrollPage._timeInputValue(line.end_time))}"></td>
            <td class="col-break"><input type="number" name="break_hours" min="0" max="12" step="0.01" value="${escapeHtml(String(PayrollPage._breakHoursDisplay(line) || line.break_hours || ''))}"></td>
            <td class="col-hours"><input type="text" name="calculated_hours" value="${escapeHtml(PayrollPage._lineHoursDisplay(line))}" readonly tabindex="-1"></td>
            <td class="col-notes"><input type="text" name="notes" value="${escapeHtml(line.notes || '')}" placeholder="Optional"></td>
            <td class="col-actions"><button type="button" class="btn btn-sm btn-danger" onclick="PayrollPage.removeTimesheetLineRow(this)">Remove</button></td>
        `;
        tbody.appendChild(row);
    },

    removeTimesheetLineRow(button) {
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

    _timesheetStatusTone(status) {
        const normalized = String(status || '').toLowerCase();
        if (normalized === 'approved' || normalized === 'locked') return '#1f6f43';
        if (normalized === 'submitted') return '#1d4d7a';
        if (normalized === 'rejected') return '#8a2d2d';
        return 'var(--text-primary)';
    },

    _timesheetSummaryRows(rows = [], actionHtml = '') {
        if (!rows.length) {
            return '<tr><td colspan="6" style="font-size:11px; color:var(--text-muted);">None</td></tr>';
        }
        return rows.map((row) => `
            <tr>
                <td><strong>#${row.id}</strong></td>
                <td>${escapeHtml(String(row.employee_id || ''))}</td>
                <td>${escapeHtml(formatDate(row.period_start))} → ${escapeHtml(formatDate(row.period_end))}</td>
                <td><span style="font-weight:700; color:${PayrollPage._timesheetStatusTone(row.status)};">${escapeHtml(row.status)}</span></td>
                <td class="amount">${escapeHtml(String(row.total_hours ?? '0.00'))}</td>
                <td class="actions">
                    <button class="btn btn-sm btn-secondary" onclick="PayrollPage.showTimesheetDetail(${row.id})">View</button>
                    ${actionHtml}
                </td>
            </tr>
        `).join('');
    },

    _renderTimesheetReviewModal(data, title, options = {}) {
        const perms = PayrollPage._timesheetPermissions();
        const canManage = perms.manage;
        const canApprove = perms.approve || perms.manage;
        const canExport = perms.export || perms.manage;
        const bulkApproveIds = (data.submitted || []).map((row) => row.id);
        const actionButtons = [];
        if (canApprove && bulkApproveIds.length) {
            actionButtons.push(`<button class="btn btn-primary" onclick="PayrollPage.bulkApproveTimesheets([${bulkApproveIds.join(',')}])">Bulk Approve Submitted</button>`);
        }
        if (canExport && options.periodStart && options.periodEnd) {
            actionButtons.push(`<button class="btn btn-secondary" onclick="PayrollPage.exportTimesheetPeriodCsv('${options.periodStart}', '${options.periodEnd}')">Export CSV</button>`);
        }
        const header = options.periodStart && options.periodEnd
            ? `Period ${escapeHtml(options.periodStart)} → ${escapeHtml(options.periodEnd)}`
            : options.payRunId
                ? `Pay Run #${escapeHtml(String(options.payRunId))}`
                : '';
        openModal(title, `
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">${header}</div>
            ${actionButtons.length ? `<div class="form-actions" style="margin-bottom:10px;">${actionButtons.join('')}</div>` : ''}
            <div class="table-container">
                <table>
                    <thead><tr><th>ID</th><th>Employee</th><th>Period</th><th>Status</th><th class="amount">Hours</th><th>Actions</th></tr></thead>
                    <tbody>
                        <tr><td colspan="6"><strong>Submitted</strong></td></tr>
                        ${PayrollPage._timesheetSummaryRows(data.submitted || [], canManage ? '' : '')}
                        <tr><td colspan="6"><strong>Approved</strong></td></tr>
                        ${PayrollPage._timesheetSummaryRows(data.approved || [], canManage ? '' : '')}
                        <tr><td colspan="6"><strong>Rejected</strong></td></tr>
                        ${PayrollPage._timesheetSummaryRows(data.rejected || [], canManage ? '' : '')}
                        <tr><td colspan="6"><strong>Draft</strong></td></tr>
                        ${PayrollPage._timesheetSummaryRows(data.draft || [], canManage ? '' : '')}
                        <tr><td colspan="6"><strong>Locked</strong></td></tr>
                        ${PayrollPage._timesheetSummaryRows(data.locked || [], canManage ? '' : '')}
                    </tbody>
                </table>
            </div>
            <div class="form-actions" style="margin-top:10px;">
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>`);
    },

    async _loadTimesheetReviewFromUrl(url, title, options = {}) {
        try {
            const data = await API.get(url);
            PayrollPage._renderTimesheetReviewModal(data, title, options);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async showTimesheetPeriodReview() {
        const { periodStart, periodEnd } = PayrollPage._reviewPeriodValues();
        await PayrollPage._loadTimesheetReviewFromUrl(
            `/timesheets/periods?period_start=${encodeURIComponent(periodStart)}&period_end=${encodeURIComponent(periodEnd)}`,
            'Timesheet Review',
            { periodStart, periodEnd },
        );
    },

    async showTimesheetPayRunReview(runId) {
        await PayrollPage._loadTimesheetReviewFromUrl(
            `/timesheets/pay-runs/${runId}`,
            `Timesheet Review — Pay Run ${runId}`,
            { payRunId: runId },
        );
    },

    async showTimesheetDetail(timesheetId) {
        try {
            const detail = await API.get(`/timesheets/${timesheetId}`);
            const canManage = PayrollPage._timesheetPermissions().manage;
            const canApprove = PayrollPage._timesheetPermissions().approve || canManage;
            const lines = (detail.lines || []).map((line) => `
                <tr>
                    <td>${escapeHtml(formatDate(line.work_date))}</td>
                    <td>${escapeHtml(PayrollPage._lineHoursDisplay(line) || String(line.duration_hours ?? ''))}</td>
                    <td>${escapeHtml(PayrollPage._timeInputValue(line.start_time))}</td>
                    <td>${escapeHtml(PayrollPage._timeInputValue(line.end_time))}</td>
                    <td>${escapeHtml(PayrollPage._breakHoursDisplay(line))}</td>
                    <td>${escapeHtml(line.notes || '')}</td>
                </tr>
            `).join('') || '<tr><td colspan="6" style="font-size:11px; color:var(--text-muted);">No lines</td></tr>';
            const auditRows = (detail.audit_events || []).map((event) => `
                <tr>
                    <td>${escapeHtml(String(event.id || ''))}</td>
                    <td>${escapeHtml(event.action || '')}</td>
                    <td>${escapeHtml(String(event.status_from || ''))}</td>
                    <td>${escapeHtml(String(event.status_to || ''))}</td>
                    <td>${escapeHtml(event.reason || '')}</td>
                </tr>
            `).join('') || '<tr><td colspan="5" style="font-size:11px; color:var(--text-muted);">No audit events</td></tr>';
            openModal(`Timesheet #${timesheetId}`, `
                <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">
                    Period ${escapeHtml(formatDate(detail.period_start))} → ${escapeHtml(formatDate(detail.period_end))}
                    · Status <strong style="color:${PayrollPage._timesheetStatusTone(detail.status)};">${escapeHtml(detail.status)}</strong>
                    · Total Hours <strong>${escapeHtml(String(detail.total_hours ?? '0.00'))}</strong>
                </div>
                <div class="table-container">
                    <table class="compact-table timesheet-lines-table">
                        <thead><tr><th>Work Date</th><th>Hours</th><th>Start</th><th>End</th><th>Break (hrs)</th><th>Notes</th></tr></thead>
                        <tbody>${lines}</tbody>
                    </table>
                </div>
                ${canManage ? `
                    <div class="form-actions" style="margin-top:10px;">
                        <button class="btn btn-primary" onclick="PayrollPage.openTimesheetCorrection(${timesheetId})">Correct</button>
                        ${canApprove ? `<button class="btn btn-secondary" onclick="PayrollPage.approveTimesheet(${timesheetId})">Approve</button>` : ''}
                        ${canApprove ? `<button class="btn btn-secondary" onclick="PayrollPage.rejectTimesheet(${timesheetId})">Reject</button>` : ''}
                        <button class="btn btn-secondary" onclick="PayrollPage.showTimesheetAudit(${timesheetId})">Audit</button>
                    </div>
                ` : ''}
                <div class="table-container" style="margin-top:10px;">
                    <table>
                        <thead><tr><th>ID</th><th>Action</th><th>From</th><th>To</th><th>Reason</th></tr></thead>
                        <tbody>${auditRows}</tbody>
                    </table>
                </div>
                <div class="form-actions" style="margin-top:10px;">
                    <button class="btn btn-secondary" onclick="closeModal()">Close</button>
                </div>`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async showTimesheetAudit(timesheetId) {
        try {
            const events = await API.get(`/timesheets/${timesheetId}/audit`);
            const rows = (events || []).map((event) => `
                <tr>
                    <td>${escapeHtml(String(event.id || ''))}</td>
                    <td>${escapeHtml(event.action || '')}</td>
                    <td>${escapeHtml(String(event.status_from || ''))}</td>
                    <td>${escapeHtml(String(event.status_to || ''))}</td>
                    <td>${escapeHtml(event.reason || '')}</td>
                </tr>
            `).join('') || '<tr><td colspan="5" style="font-size:11px; color:var(--text-muted);">No audit events</td></tr>';
            openModal(`Timesheet Audit #${timesheetId}`, `
                <div class="table-container">
                    <table>
                        <thead><tr><th>ID</th><th>Action</th><th>From</th><th>To</th><th>Reason</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
                <div class="form-actions" style="margin-top:10px;">
                    <button class="btn btn-secondary" onclick="closeModal()">Close</button>
                </div>`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async openTimesheetCorrection(timesheetId) {
        try {
            const detail = await API.get(`/timesheets/${timesheetId}`);
            const rows = (detail.lines || []).length ? detail.lines : [{ work_date: '', start_time: '', end_time: '', break_hours: '', notes: '' }];
            openModal(`Correct Timesheet #${timesheetId}`, `
                <form onsubmit="PayrollPage.submitTimesheetCorrection(event, ${timesheetId})">
                    <div class="form-group">
                        <label>Reason</label>
                        <textarea name="reason" rows="3" required></textarea>
                    </div>
                    <div class="table-container" style="margin-top:8px;">
                        <table id="timesheet-correction-lines-${timesheetId}" class="compact-table timesheet-lines-table">
                            <thead><tr><th>Work Date</th><th>Start</th><th>End</th><th>Break (hrs)</th><th>Calculated Hours</th><th>Notes</th><th></th></tr></thead>
                            <tbody>${PayrollPage._timesheetLineRows(rows)}</tbody>
                        </table>
                    </div>
                    <div class="form-actions" style="margin-top:10px;">
                        <button type="button" class="btn btn-secondary" onclick="PayrollPage.addTimesheetLineRow('timesheet-correction-lines-${timesheetId}')">Add Line</button>
                        <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">Save Correction</button>
                    </div>
                </form>`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async submitTimesheetCorrection(e, timesheetId) {
        e.preventDefault();
        const form = e.target;
        const reason = form.reason.value;
        const lines = PayrollPage._readTimesheetLines(`timesheet-correction-lines-${timesheetId}`);
        if (!lines.length) {
            toast('Add at least one line', 'error');
            return;
        }
        try {
            await API.put(`/timesheets/${timesheetId}`, { reason, lines });
            closeModal();
            toast('Timesheet corrected');
            await PayrollPage.showTimesheetDetail(timesheetId);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async approveTimesheet(timesheetId) {
        const confirmed = typeof App?.confirmAction === 'function'
            ? await App.confirmAction({
                title: 'Approve Timesheet',
                message: 'Approve this timesheet for payroll?',
                confirmLabel: 'Approve',
                cancelLabel: 'Cancel',
            })
            : (typeof confirm === 'function' ? confirm('Approve this timesheet for payroll?') : true);
        if (!confirmed) return;
        try {
            await API.post(`/timesheets/${timesheetId}/approve`, {});
            toast('Timesheet approved');
            await PayrollPage.showTimesheetDetail(timesheetId);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async rejectTimesheet(timesheetId) {
        const reason = typeof prompt === 'function' ? prompt('Enter a rejection reason') : '';
        if (!reason) return;
        try {
            await API.post(`/timesheets/${timesheetId}/reject`, { reason });
            toast('Timesheet rejected');
            await PayrollPage.showTimesheetDetail(timesheetId);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async bulkApproveTimesheets(timesheetIds) {
        const confirmed = typeof App?.confirmAction === 'function'
            ? await App.confirmAction({
                title: 'Bulk Approve Timesheets',
                message: `Approve ${timesheetIds.length} submitted timesheet${timesheetIds.length === 1 ? '' : 's'}?`,
                confirmLabel: 'Approve All',
                cancelLabel: 'Cancel',
            })
            : (typeof confirm === 'function' ? confirm(`Approve ${timesheetIds.length} submitted timesheet${timesheetIds.length === 1 ? '' : 's'}?`) : true);
        if (!confirmed) return;
        try {
            await API.post('/timesheets/bulk-approve', { timesheet_ids: timesheetIds });
            toast('Timesheets approved');
            await PayrollPage.showTimesheetPeriodReview();
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    exportTimesheetPeriodCsv(periodStart, periodEnd) {
        const { periodStart: start, periodEnd: end } = periodStart && periodEnd
            ? { periodStart, periodEnd }
            : PayrollPage._reviewPeriodValues();
        API.open(`/timesheets/export?period_start=${encodeURIComponent(start)}&period_end=${encodeURIComponent(end)}`, `Timesheets_${start}_${end}.csv`);
    },

    async render() {
        const canCreateRun = !App.hasPermission || App.hasPermission('payroll.create');
        const canProcessRun = !App.hasPermission || App.hasPermission('payroll.process');
        const canViewPayslips = !App.hasPermission || App.hasPermission('payroll.payslips.view');
        const canEmailPayslips = !App.hasPermission || App.hasPermission('payroll.payslips.email');
        const canExportFiling = !App.hasPermission || App.hasPermission('payroll.filing.export');
        const canReviewTimesheets = PayrollPage._canReviewTimesheets();
        const canExportTimesheets = PayrollPage._timesheetPermissions().export || PayrollPage._timesheetPermissions().manage;
        const [runs, employees] = await Promise.all([
            API.get('/payroll'),
            API.get('/employees?active_only=true'),
        ]);
        const filingHistoryByRun = new Map();
        await Promise.all(runs.map(async (run) => {
            if (String(run.status || '').toLowerCase() !== 'processed') {
                filingHistoryByRun.set(run.id, []);
                return;
            }
            try {
                filingHistoryByRun.set(run.id, await API.get(`/payroll/${run.id}/filing/history`));
            } catch (_err) {
                filingHistoryByRun.set(run.id, []);
            }
        }));

        let html = `
            <div class="page-header">
                <h2>Payroll</h2>
                ${canCreateRun ? `<button class="btn btn-primary" onclick="PayrollPage.showForm()">New Pay Run</button>` : ''}
            </div>
            <div style="background:#e0f2fe;border:1px solid #7dd3fc;padding:10px 12px;margin-bottom:12px;font-size:12px;color:#0c4a6e;">
                <strong>NZ payroll setup is ready.</strong> PAYE calculations, KiwiSaver deductions, student loan deductions, ESCT, payslips, Employment Information export, starter/leaver filing, and posting now run through the NZ payroll workflow.
            </div>
            ${canReviewTimesheets ? `
                <div class="settings-section">
                    <h3>Timesheet Review</h3>
                    <div class="form-grid">
                        <div class="form-group">
                            <label>Period Start</label>
                            <input id="timesheet-review-period-start" type="date" value="${todayISO()}">
                        </div>
                        <div class="form-group">
                            <label>Period End</label>
                            <input id="timesheet-review-period-end" type="date" value="${todayISO()}">
                        </div>
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-primary" onclick="PayrollPage.showTimesheetPeriodReview()">Review Period</button>
                        ${canExportTimesheets ? `<button class="btn btn-secondary" onclick="PayrollPage.exportTimesheetPeriodCsv()">Export CSV</button>` : ''}
                    </div>
                    <p style="font-size:11px; color:var(--text-muted); margin-top:8px;">Review submitted timesheets, correct hours, approve work, and export scoped CSVs from the payroll screen.</p>
                </div>
            ` : ''}
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:12px;">
                ${employees.length} active employee${employees.length === 1 ? '' : 's'} available for payroll.
            </div>`;

        if (!runs.length) {
            html += `<div class="empty-state"><p>No pay runs yet. Create a draft run to calculate PAYE and review totals before processing.</p></div>`;
            return html;
        }

        html += `<div class="table-container"><table>
            <thead><tr><th>Pay Date</th><th>Tax Year</th><th>Status</th><th class="amount">Gross</th><th class="amount">Net</th><th class="amount">Deductions</th><th>Filing Status</th><th>Actions</th></tr></thead>
            <tbody>`;
        for (const run of runs) {
            const status = String(run.status || '').toLowerCase();
            const latestFiling = (filingHistoryByRun.get(run.id) || [])[0];
            html += `<tr>
                <td>${formatDate(run.pay_date)}</td>
                <td>${escapeHtml(String(run.tax_year || ''))}</td>
                <td>${status === 'processed' ? '<span class="badge badge-paid">Processed</span>' : '<span class="badge badge-draft">Draft</span>'}</td>
                <td class="amount">${formatCurrency(run.total_gross)}</td>
                <td class="amount">${formatCurrency(run.total_net)}</td>
                <td class="amount">${formatCurrency(run.total_taxes)}</td>
                <td style="font-size:10px;">${PayrollPage.filingSummary(latestFiling)}</td>
                <td class="actions">
                    <button class="btn btn-sm btn-secondary" onclick="PayrollPage.viewRun(${run.id})">View</button>
                    ${canReviewTimesheets ? `<button class="btn btn-sm btn-secondary" onclick="PayrollPage.showTimesheetPayRunReview(${run.id})">Timesheets</button>` : ''}
                    ${status === 'draft'
                        ? `${canProcessRun ? `<button class="btn btn-sm btn-primary" onclick="PayrollPage.processRun(${run.id})">Process</button>` : ''}`
                        : `${canViewPayslips ? `<button class="btn btn-sm btn-secondary" onclick="PayrollPage.viewRun(${run.id})">Payslips</button>` : ''}
                           ${canExportFiling ? `<button class="btn btn-sm btn-secondary" onclick="PayrollPage.exportEmploymentInformation(${run.id})">Employment Information</button>` : ''}
                           ${canExportFiling && latestFiling && latestFiling.status === 'generated' ? `<button class="btn btn-sm btn-secondary" onclick="PayrollPage.markFilingStatus(${run.id}, ${latestFiling.id}, 'filed')">Mark Filed</button>` : ''}
                           ${canExportFiling && latestFiling && latestFiling.status === 'filed' && latestFiling.changed_since_source ? `<button class="btn btn-sm btn-secondary" onclick="PayrollPage.markFilingStatus(${run.id}, ${latestFiling.id}, 'amended')">Mark Amended</button>` : ''}`}
                </td>
            </tr>`;
        }
        html += `</tbody></table></div>`;
        return html;
    },

    filingSummary(record) {
        if (!record) return '';
        return `<div>Employment Information ${escapeHtml(record.status)}</div>${record.changed_since_source ? '<div style="color:#9d1f1f;">Changed since filing</div>' : ''}`;
    },

    async showForm() {
        const employees = await API.get('/employees?active_only=true');
        if (!employees.length) {
            toast('Add an active employee before creating a pay run', 'error');
            return;
        }

        const today = todayISO();
        const rows = employees.map(emp => `
            <tr>
                <td>
                    <label style="display:flex; align-items:center; gap:6px;">
                        <input type="checkbox" name="include_${emp.id}" checked>
                        <span>${escapeHtml(emp.first_name)} ${escapeHtml(emp.last_name)}</span>
                    </label>
                </td>
                <td>${escapeHtml(emp.pay_type)}</td>
                <td>${escapeHtml(emp.tax_code || '')}</td>
                <td>${escapeHtml(emp.pay_frequency || '')}</td>
                <td><input name="hours_${emp.id}" type="number" step="0.01" min="0" value="${emp.pay_type === 'hourly' ? '0' : ''}" ${emp.pay_type === 'salary' ? 'disabled' : ''}></td>
            </tr>
        `).join('');

        openModal('New Pay Run', `
            <form onsubmit="PayrollPage.save(event)">
                <div class="form-grid">
                    <div class="form-group"><label>Period Start</label><input name="period_start" type="date" value="${today}" required></div>
                    <div class="form-group"><label>Period End</label><input name="period_end" type="date" value="${today}" required></div>
                    <div class="form-group"><label>Pay Date</label><input name="pay_date" type="date" value="${today}" required></div>
                </div>
                <div class="table-container" style="margin-top:12px;">
                    <table>
                        <thead><tr><th>Employee</th><th>Pay Type</th><th>Tax Code</th><th>Frequency</th><th>Hours</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
                <p style="font-size:11px; color:var(--text-muted); margin-top:10px;">Salary employees use their annual salary and pay frequency. Enter hours for hourly staff.</p>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create Draft Run</button>
                </div>
            </form>`);
    },

    async save(e) {
        e.preventDefault();
        const form = new FormData(e.target);
        const employees = await API.get('/employees?active_only=true');
        const stubs = employees
            .filter(emp => form.get(`include_${emp.id}`))
            .map(emp => ({
                employee_id: emp.id,
                ...(emp.pay_type === 'hourly' ? { hours: parseFloat(form.get(`hours_${emp.id}`) || '0') || 0 } : {}),
            }));
        if (!stubs.length) {
            toast('Select at least one employee', 'error');
            return;
        }

        try {
            await API.post('/payroll', {
                period_start: form.get('period_start'),
                period_end: form.get('period_end'),
                pay_date: form.get('pay_date'),
                stubs,
            });
            closeModal();
            toast('Draft pay run created');
            App.navigate('#/payroll');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async processRun(id) {
        if (!confirm('Process this pay run and post the payroll journal?')) return;
        try {
            await API.post(`/payroll/${id}/process`);
            toast('Pay run processed');
            App.navigate('#/payroll');
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    async viewRun(id) {
        try {
            const canViewPayslips = !App.hasPermission || App.hasPermission('payroll.payslips.view');
            const canEmailPayslips = !App.hasPermission || App.hasPermission('payroll.payslips.email');
            const run = await API.get(`/payroll/${id}`);
            const rows = (run.stubs || []).map(stub => `
                <tr>
                    <td>${escapeHtml(stub.employee_name || '')}</td>
                    <td>${escapeHtml(stub.tax_code || '')}</td>
                    <td class="amount">${formatCurrency(stub.gross_pay)}</td>
                    <td class="amount">${formatCurrency(stub.paye)}</td>
                    <td class="amount">${formatCurrency(stub.acc_earners_levy)}</td>
                    <td class="amount">${formatCurrency(stub.student_loan_deduction)}</td>
                    <td class="amount">${formatCurrency(stub.kiwisaver_employee_deduction)}</td>
                    <td class="amount">${formatCurrency(stub.child_support_deduction)}</td>
                    <td class="amount">${formatCurrency(stub.net_pay)}</td>
                    <td>${String(run.status || '').toLowerCase() === 'processed' ? `${canViewPayslips ? `<button class="btn btn-sm btn-secondary" onclick="PayrollPage.openPayslip(${run.id}, ${stub.employee_id})">Print / PDF</button>` : ''} ${canEmailPayslips ? `<button class="btn btn-sm btn-secondary" onclick="PayrollPage.emailPayslip(${run.id}, ${stub.employee_id})">Email</button>` : ''}` : ''}</td>
                </tr>
            `).join('');
            openModal(`Pay Run ${id}`, `
                <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">
                    Pay Date: <strong>${formatDate(run.pay_date)}</strong>
                    · Tax Year: <strong>${escapeHtml(String(run.tax_year || ''))}</strong>
                    · Status: <strong>${escapeHtml(run.status)}</strong>
                </div>
                <div class="table-container">
                    <table>
                        <thead><tr><th>Employee</th><th>Tax Code</th><th class="amount">Gross</th><th class="amount">PAYE</th><th class="amount">ACC</th><th class="amount">Student Loan</th><th class="amount">KiwiSaver</th><th class="amount">Child Support</th><th class="amount">Net</th><th>Actions</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
                <div style="margin-top:10px; font-size:11px; color:var(--text-muted);">
                    Employer KiwiSaver: <strong>${formatCurrency(run.total_employer_kiwisaver || 0)}</strong>
                    · ESCT: <strong>${formatCurrency(run.total_esct || 0)}</strong>
                </div>
                <div class="form-actions">
                    <button class="btn btn-secondary" onclick="closeModal()">Close</button>
                </div>`);
        } catch (err) {
            toast(err.message, 'error');
        }
    },

    openPayslip(runId, employeeId) {
        API.open(`/payroll/${runId}/payslips/${employeeId}/pdf`, `payslip-${employeeId}.pdf`);
    },

    emailPayslip(runId, employeeId) {
        App.showDocumentEmailModal({
            title: `Email Payslip for Pay Run ${runId}`,
            endpoint: `/payroll/${runId}/payslips/${employeeId}/email`,
            recipient: '',
            defaultSubject: `Payslip for pay run ${runId}`,
            successMessage: 'Payslip emailed',
        });
    },

    exportEmploymentInformation(runId) {
        API.open(`/payroll/${runId}/employment-information/export`, `employment-information-${runId}.csv`);
    },

    async markFilingStatus(runId, auditId, status) {
        try {
            await API.post(`/payroll/${runId}/filing/${auditId}/status`, { status });
            toast(`Filing marked ${status}`);
            App.navigate('#/payroll');
        } catch (err) {
            toast(err.message, 'error');
        }
    },
};
