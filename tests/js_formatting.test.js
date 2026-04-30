const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = fs.readFileSync('app/static/js/utils.js', 'utf8');
function loadUtils(extraContext = {}) {
    const context = {
        document: {
            querySelector: () => null,
            querySelectorAll: () => [],
            createElement: () => ({ className: '', textContent: '', remove() {} }),
        },
        setTimeout,
        Intl,
        Date,
        Number,
        ...extraContext,
    };
    vm.createContext(context);
    vm.runInContext(code, context);
    return context;
}

const context = {
    App: {
        settings: { locale: 'en-NZ', currency: 'NZD' },
    },
};
const cachedSettingsContext = loadUtils(context);

assert.strictEqual(cachedSettingsContext.formatCurrency(1234.5), '$1,234.50');
assert.strictEqual(cachedSettingsContext.formatDate('2026-04-13'), '13 Apr 2026');
assert.strictEqual(
    cachedSettingsContext.formatCurrency(1234.5, { locale: 'en-NZ', currency: 'NZD' }),
    '$1,234.50',
);
assert.strictEqual(
    cachedSettingsContext.formatDate('2026-04-13', { locale: 'en-NZ' }),
    '13 Apr 2026',
);
assert.strictEqual(
    cachedSettingsContext.formatCurrency(1234.5, { locale: 'en_NZ', currency: 'NZD' }),
    'NZ$1,234.50',
);
assert.strictEqual(
    cachedSettingsContext.formatDate('2026-04-13', { locale: 'en_NZ' }),
    'Apr 13, 2026',
);

const noCacheContext = loadUtils();

assert.strictEqual(noCacheContext.formatCurrency(1234.5), '$1,234.50');
assert.strictEqual(noCacheContext.formatDate('2026-04-13'), 'Apr 13, 2026');

assert.strictEqual(noCacheContext.escapeHtml(2027), '2027');
assert.strictEqual(noCacheContext.escapeHtml(null), '');
assert.strictEqual(noCacheContext.escapeHtml(false), 'false');

assert.strictEqual(noCacheContext.escapeHtml(`O'Reilly & <tag>`), 'O&#39;Reilly &amp; &lt;tag&gt;');

const RealDate = Date;
class FixedDate extends RealDate {
    constructor(...args) {
        if (args.length === 0) {
            super('2026-04-14T00:00:00Z');
        } else {
            super(...args);
        }
    }

    toISOString() {
        return '2026-04-13T12:00:00.000Z';
    }
}
const localDateContext = loadUtils({ Date: FixedDate });
assert.strictEqual(localDateContext.todayISO(), '2026-04-14');

const indexHtml = fs.readFileSync('index.html', 'utf8');
assert.ok(indexHtml.includes(`onkeydown="if(event.key==='Escape'){this.value='';App.globalSearch('');}"`));
