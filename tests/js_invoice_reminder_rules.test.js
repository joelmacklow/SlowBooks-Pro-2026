const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const code = `${fs.readFileSync('app/static/js/settings.js', 'utf8')}\nthis.SettingsPage = SettingsPage;`;
const posts = [];
const puts = [];
const toasts = [];
let closed = 0;

const context = {
    API: {
        get: async () => [],
        post: async (path, body) => {
            posts.push({ path, body });
            return { id: 1 };
        },
        put: async (path, body) => {
            puts.push({ path, body });
            return { id: 2 };
        },
        del: async () => ({ status: 'deleted' }),
    },
    toast: (message) => { toasts.push(message); },
    closeModal: () => { closed += 1; },
    openModal() {},
    escapeHtml: (value) => String(value ?? ''),
    setTimeout,
    confirm: () => true,
};

vm.createContext(context);
vm.runInContext(code, context);

(async () => {
    context.SettingsPage.loadInvoiceReminderRules = async () => {};

    await context.SettingsPage.saveReminderRule({
        preventDefault() {},
        target: {
            name: { value: 'Friendly reminder' },
            timing_direction: { value: 'before_due' },
            day_offset: { value: '3' },
            sort_order: { value: '1' },
            is_enabled: { checked: true },
            subject_template: { value: 'Reminder subject' },
            body_template: { value: 'Reminder body' },
        },
    }, null);

    await context.SettingsPage.saveReminderRule({
        preventDefault() {},
        target: {
            name: { value: '' },
            timing_direction: { value: 'after_due' },
            day_offset: { value: '7' },
            sort_order: { value: '2' },
            is_enabled: { checked: false },
            subject_template: { value: '' },
            body_template: { value: '' },
        },
    }, 9);

    assert.strictEqual(posts.length, 1);
    assert.strictEqual(posts[0].path, '/settings/invoice-reminder-rules');
    assert.strictEqual(posts[0].body.timing_direction, 'before_due');
    assert.strictEqual(posts[0].body.day_offset, 3);
    assert.strictEqual(posts[0].body.is_enabled, true);

    assert.strictEqual(puts.length, 1);
    assert.strictEqual(puts[0].path, '/settings/invoice-reminder-rules/9');
    assert.strictEqual(puts[0].body.timing_direction, 'after_due');
    assert.strictEqual(puts[0].body.day_offset, 7);
    assert.strictEqual(puts[0].body.is_enabled, false);

    assert.ok(toasts.includes('Invoice reminder rule created'));
    assert.ok(toasts.includes('Invoice reminder rule updated'));
    assert.strictEqual(closed, 2);
})().catch((err) => {
    console.error(err);
    process.exit(1);
});
