const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/api.js', 'utf8')}\nthis.API = API;`;

const fetchCalls = [];
let promptCount = 0;

const context = {
  console,
  localStorage: { getItem: () => null },
  App: {
    promptClosingDatePassword: async (message) => {
      promptCount += 1;
      assert.ok(message.includes('company admin lock date'));
      return 'secret';
    },
    handleUnauthorized() {},
  },
  fetch: async (url, opts) => {
    fetchCalls.push({ url, opts });
    if (fetchCalls.length === 1) {
      return {
        ok: false,
        status: 403,
        json: async () => ({ detail: 'Transaction date 2026-04-20 is on or before the company admin lock date (2026-04-30). Modifications to closed periods are not allowed without the company override password.' }),
      };
    }
    return {
      ok: true,
      json: async () => ({ status: 'ok' }),
    };
  },
  FormData: class {},
  setTimeout,
  URL: { createObjectURL() {}, revokeObjectURL() {} },
  document: { createElement: () => ({ click() {} }) },
  window: { open: () => true },
  File: undefined,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
  const result = await context.API.post('/demo', { hello: 'world' });
  assert.strictEqual(result.status, 'ok');
  assert.strictEqual(promptCount, 1);
  assert.strictEqual(fetchCalls.length, 2);
  assert.strictEqual(fetchCalls[1].opts.headers['X-Closing-Date-Password'], 'secret');

  fetchCalls.length = 0;
  promptCount = 0;
  context.fetch = async (_url, _opts) => ({
    ok: false,
    status: 403,
    json: async () => ({ detail: 'Transaction date 2026-04-20 is on or before the organization lock date (2026-04-30). Company override passwords cannot bypass organization locks.' }),
  });
  await assert.rejects(() => context.API.post('/demo', { hello: 'world' }));
  assert.strictEqual(promptCount, 0);
})();
