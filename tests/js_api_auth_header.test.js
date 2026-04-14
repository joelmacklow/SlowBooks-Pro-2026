const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/api.js', 'utf8')}\nthis.API = API;`;
const fetchCalls = [];
const context = {
    fetch: async (url, opts) => {
        fetchCalls.push({ url, opts });
        return { ok: true, json: async () => ({ ok: true }) };
    },
    localStorage: {
        getItem(key) { return key === 'slowbooks-auth-token' ? 'abc123' : null; },
    },
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    await context.API.get('/auth/me');
    assert.strictEqual(fetchCalls[0].url, '/api/auth/me');
    assert.strictEqual(fetchCalls[0].opts.headers.Authorization, 'Bearer abc123');
})().catch(err => {
    console.error(err);
    process.exit(1);
});
