const assert = require('assert');
const fs = require('fs');

const indexHtml = fs.readFileSync('index.html', 'utf8');
const appJs = fs.readFileSync('app/static/js/app.js', 'utf8');
const styleCss = fs.readFileSync('app/static/css/style.css', 'utf8');
const darkCss = fs.readFileSync('app/static/css/dark.css', 'utf8');

assert.ok(indexHtml.includes('id="workspace-shell"'));
assert.ok(!indexHtml.includes('topbar-brand'));
assert.ok(indexHtml.includes('nav-section-toggle'));
assert.ok(indexHtml.includes('nav-group-links'));
assert.ok(appJs.includes('toggleNavSection('));
assert.ok(appJs.includes('syncNavAccordion('));
assert.ok(styleCss.includes('#workspace-shell'));
assert.ok(styleCss.includes('.nav-section-toggle'));
assert.ok(styleCss.includes('.nav-group:not(.is-open) .nav-group-links'));
assert.ok(darkCss.includes('.nav-section-toggle'));
