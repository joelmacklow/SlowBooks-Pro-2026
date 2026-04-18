const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/api.js', 'utf8')}\nthis.API = API;`;
const createdObjects = [];
const opened = [];
const clicked = [];

class FakeFile {
    constructor(parts, name, options = {}) {
        this.parts = parts;
        this.name = name;
        this.type = options.type || '';
    }
}

const context = {
    console,
    File: FakeFile,
    fetch: async () => ({
        ok: true,
        headers: {
            get: (name) => name === 'Content-Disposition' ? 'inline; filename="TrialBalance_2026-04-18.pdf"' : null,
        },
        blob: async () => ({ type: 'application/pdf' }),
    }),
    localStorage: { getItem: () => null },
    URL: {
        createObjectURL: (value) => {
            createdObjects.push(value);
            return 'blob:named';
        },
        revokeObjectURL() {},
    },
    window: {
        open: (url, target) => {
            opened.push({ url, target });
            return { closed: false };
        },
    },
    document: {
        createElement: () => ({
            click() { clicked.push(true); },
        }),
    },
    setTimeout: (fn) => { fn(); return 1; },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.API.open('/reports/trial-balance/pdf', 'fallback.pdf');
    assert.strictEqual(createdObjects.length, 1);
    assert.strictEqual(createdObjects[0].name, 'TrialBalance_2026-04-18.pdf');
    assert.deepStrictEqual(opened, [{ url: 'blob:named', target: '_blank' }]);
    assert.deepStrictEqual(clicked, []);
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
