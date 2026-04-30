const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = [
  fs.readFileSync('app/static/js/app.js', 'utf8'),
  fs.readFileSync('app/static/js/invoices.js', 'utf8'),
  'this.App = App; this.InvoicesPage = InvoicesPage;'
].join('\n');

const context = {
  API: {
    get: async (path) => {
      if (path === '/customers?active_only=true') return [{ id: 5, name: 'Aroha Ltd', terms: 'Net 30' }];
      if (path === '/items?active_only=true') return [{ id: 2, name: 'Pens', description: 'Pens', rate: 50, cost: 15 }];
      if (path === '/settings') return { default_terms: 'Net 30', default_tax_rate: '15', invoice_notes: 'Default invoice notes' };
      if (path === '/gst-codes') return [{ code: 'GST15', rate: 0.15, name: 'GST 15%' }];
      if (path === '/invoices/9') return {
        id: 9,
        invoice_number: 'INV-PAID',
        customer_id: 5,
        customer_name: 'Aroha Ltd',
        date: '2026-04-16',
        due_date: '2026-04-30',
        terms: 'Net 30',
        po_number: 'PO-55',
        status: 'paid',
        subtotal: 100,
        tax_rate: 0.15,
        tax_amount: 15,
        total: 115,
        amount_paid: 115,
        balance_due: 0,
        notes: 'Invoice notes',
        lines: [{ item_id: 2, description: 'Pens', quantity: 2, rate: 50, amount: 100, gst_code: 'GST15', gst_rate: 0.15 }],
      };
      if (path === '/credit-memos?customer_id=5&status=issued') return [];
      throw new Error(`unexpected path ${path}`);
    },
    post: async () => ({}),
    open() {},
  },
  App: {
    authState: { authenticated: true, bootstrap_required: false, user: { membership: { effective_permissions: ['sales.view', 'sales.manage', 'contacts.manage'] } } },
    hasPermission: () => true,
    navigate() {},
    setStatus() {},
    showDocumentEmailModal() {},
    settings: { locale: 'en-NZ', currency: 'NZD' },
  },
  AuthPage: { render() {}, renderUserManagement() {} },
  CustomersPage: { render() {}, showForm() {} },
  VendorsPage: { render() {} },
  ItemsPage: { render() {} },
  PaymentsPage: { render() {}, showForm() {} },
  BankingPage: { render() {} },
  DepositsPage: { render() {} },
  CheckRegisterPage: { render() {} },
  CCChargesPage: { render() {} },
  JournalPage: { render() {} },
  ReportsPage: { render() {}, renderGstReturnsScreen() {}, renderGstReturnDetailScreen() {} },
  SettingsPage: { render() {} },
  IIFPage: { render() {} },
  XeroImportPage: { render() {} },
  AuditPage: { render() {} },
  PurchaseOrdersPage: { render() {}, renderDetailScreen() {} },
  BillsPage: { render() {} },
  CreditMemosPage: { render() {} },
  RecurringPage: { render() {} },
  BatchPaymentsPage: { render() {} },
  CompaniesPage: { render() {} },
  EmployeesPage: { render() {} },
  PayrollPage: { render() {} },
  document: {
    documentElement: { getAttribute: () => 'light', setAttribute() {} },
    addEventListener() {},
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: () => ({ click() {}, remove() {}, style: {} }),
  },
  window: { addEventListener() {} },
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  location: { hash: '#/' },
  escapeHtml: value => String(value || ''),
  formatDate: value => String(value || ''),
  formatCurrency: value => `$${Number(value || 0).toFixed(2)}`,
  statusBadge: value => String(value || ''),
  todayISO: () => '2026-04-16',
  gstOptionsHtml: selected => `<option value="${selected || 'GST15'}">GST 15%</option>`,
  readGstLinePayload: row => ({
    quantity: parseFloat(row.querySelector('.line-qty')?.value) || 0,
    rate: parseFloat(row.querySelector('.line-rate')?.value) || 0,
    gst_code: row.querySelector('.line-gst')?.value || 'GST15',
    gst_rate: 0.15,
  }),
  calculateGstTotals: lines => {
    const subtotal = lines.reduce((sum, line) => sum + ((line.quantity || 0) * (line.rate || 0)), 0);
    const tax_amount = subtotal * 0.15;
    return { subtotal, tax_amount, total: subtotal + tax_amount };
  },
  openModal() {},
  closeModal() {},
  toast() {},
  confirm: () => true,
  setTimeout,
  setInterval: () => 1,
  console,
  fetch: async () => ({ ok: true, headers: { get: () => null }, blob: async () => ({}) }),
  URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} },
  $: () => null,
  $$: () => [],
  Date,
  Intl,
  Number,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
  await context.InvoicesPage.open(9);
  const html = context.InvoicesPage.renderDetailScreen();
  assert.ok(html.includes('Invoice INV-PAID'));
  assert.ok(html.includes('disabled'));
  assert.ok(!html.includes('Update Invoice'));
  assert.ok(!html.includes('Void Invoice'));
  assert.ok(!html.includes('Send Invoice'));
})();
