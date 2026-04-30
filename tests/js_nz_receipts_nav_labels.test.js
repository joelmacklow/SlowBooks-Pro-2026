const assert = require('assert');
const fs = require('fs');

const indexHtml = fs.readFileSync('index.html', 'utf8');
const appJs = fs.readFileSync('app/static/js/app.js', 'utf8');
const paymentsJs = fs.readFileSync('app/static/js/payments.js', 'utf8');
const depositsJs = fs.readFileSync('app/static/js/deposits.js', 'utf8');

assert.ok(indexHtml.includes('Customer Receipts'));
assert.ok(indexHtml.includes('Bulk Receipt Allocation'));
assert.ok(indexHtml.includes('Cash Deposits'));
assert.ok(indexHtml.includes('Bank Register'));
assert.ok(indexHtml.includes('Record Receipt'));

assert.ok(appJs.includes("label: 'Customer Receipts'"));
assert.ok(appJs.includes("label: 'Bulk Receipt Allocation'"));
assert.ok(appJs.includes("label: 'Cash Deposits'"));
assert.ok(appJs.includes("label: 'Bank Register'"));
assert.ok(appJs.includes("label: 'Receipts'"));

assert.ok(paymentsJs.includes('<h2>Customer Receipts</h2>'));
assert.ok(paymentsJs.includes('+ Record Receipt'));
assert.ok(paymentsJs.includes('Record Receipt'));
assert.ok(depositsJs.includes('<h2>Cash Deposits</h2>'));
