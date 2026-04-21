const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/settings.js', 'utf8')}\nthis.SettingsPage = SettingsPage;`;

const context = {
  API: {
    get: async (path) => {
      if (path === '/settings') return {
        company_name: 'SlowBooks NZ',
        payment_terms_config: 'Net 30|net:30',
        default_tax_rate: '15',
        default_terms: 'Net 30',
      };
      return [];
    },
  },
  escapeHtml: value => String(value || ''),
  setTimeout() {},
  formatDate: value => String(value || ''),
  App: {},
  $: () => null,
  toast() {},
  console,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
  const html = await context.SettingsPage.render();
  assert.ok(html.includes('accept="image/png,image/jpeg,image/gif"'));
  assert.ok(html.includes('PNG, JPG/JPEG, or GIF'));
  assert.ok(!html.includes('SVG'));
})().catch(err => {
  console.error(err);
  process.exit(1);
});
