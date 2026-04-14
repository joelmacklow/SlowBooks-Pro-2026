const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/iif.js', 'utf8')}\nthis.IIFPage = IIFPage;`;
const context = {
    App: { setStatus() {} },
    API: { get: async () => ({}) },
    escapeHtml: value => String(value || ''),
    toast() {},
    document: {
        createElement: () => ({ click() {}, set href(v) {}, set download(v) {} }),
        getElementById: () => ({ click() {} }),
    },
    URL: { createObjectURL() { return 'blob:test'; }, revokeObjectURL() {} },
    fetch: async () => ({ ok: true, blob: async () => new Blob(), headers: { get: () => null }, json: async () => ({}) }),
    FormData,
    $: () => ({ value: '' }),
    console,
};
vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    const html = await context.IIFPage.render();
    assert.ok(html.includes('QuickBooks Interop'));
    assert.ok(html.includes('QB2003-compatible legacy IIF'));
    assert.ok(html.includes('NZ-ledger data'));
    assert.ok(!html.includes('Sales Tax'));
})();
