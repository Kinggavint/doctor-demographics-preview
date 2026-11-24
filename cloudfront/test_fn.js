// Local test of the CloudFront function. usage (repo root): DD_PROD=1 python3 build/gen.py && node cloudfront/test_fn.js [old-function.js]
// Checks: every old-WP row -> one 301 to its CSV target (with/without slash, www, query string, upper case);
// every target is a real page in dist/ that the function serves without another redirect (no chains/loops);
// every page in dist/ passes through untouched (prefix rules never catch a live page);
// GHL paths still go to order.doctordemographics.com; optional: same output as the old function for its whole map.
const fs = require('fs'), path = require('path');
const HERE = __dirname, ROOT = path.dirname(HERE), DIST = path.join(ROOT, 'dist');
function load(f) { return new Function(fs.readFileSync(f, 'utf8') + ';return handler;')(); }
const handler = load(path.join(HERE, 'apex-site-doctor-demographics-redirects.js'));
const run = (h, u, q = {}, fn = handler) => fn({ request: { uri: u, headers: { host: { value: h } }, querystring: q } });
const A = 'https://doctordemographics.com';
let fails = 0, checks = 0;
const ok = (c, msg) => { checks++; if (!c) { fails++; console.log('FAIL', msg); } };
function csvRows(f) {
  const [head, ...lines] = fs.readFileSync(f, 'utf8').trim().split(/\r?\n/);
  const cols = head.split(',');
  return lines.map(l => { const v = []; let cur = '', qd = false;
    for (const ch of l) { if (ch === '"') qd = !qd; else if (ch === ',' && !qd) { v.push(cur); cur = ''; } else cur += ch; }
    v.push(cur); return Object.fromEntries(cols.map((c, i) => [c, v[i]])); });
}
// pages that exist in the production build
const pages = new Set();
(function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name);
  if (e.isDirectory()) walk(p); else pages.add('/' + path.relative(DIST, p).split(path.sep).join('/')); } })(DIST);
ok(pages.size > 50, 'dist/ missing: run DD_PROD=1 python3 build/gen.py first');
function servedOK(t) { // t: absolute https://doctordemographics.com/... target
  if (!t.startsWith(A + '/')) return false;
  const u = t.slice(A.length); const r = run('doctordemographics.com', u);
  return !r.statusCode && pages.has(r.uri);
}
const rows = csvRows(path.join(HERE, 'old-wp-404-redirects.csv'));
ok(rows.length === 423, 'expected 423 rows, got ' + rows.length);
const types = {};
for (const r of rows) {
  types[r.type] = (types[r.type] || 0) + 1;
  ok(['exact', 'closest-article', 'section-fallback'].includes(r.type), 'bad type ' + r.old_url);
  ok(servedOK(r.target), 'target is not a live page served without redirect: ' + r.target);
  const u = r.old_url, alt = u.endsWith('/') ? u.slice(0, -1) : u + '/';
  for (const [h, uu, q, want] of [['doctordemographics.com', u, {}, r.target], ['doctordemographics.com', alt, {}, r.target],
      ['www.doctordemographics.com', u, {}, r.target], ['doctordemographics.com', u.toUpperCase(), {}, r.target],
      ['doctordemographics.com', u, { utm_source: { value: 'x' } }, r.target + '?utm_source=x']]) {
    const res = run(h, uu, q);
    ok(res.statusCode === 301 && res.headers.location.value === want, `${h}${uu} -> ${res.statusCode ? res.statusCode + ' ' + res.headers.location.value : 'PASS ' + res.uri} (want ${want})`);
  }
}
// every live page passes through (and its slash-less form gets only the trailing-slash 301 to itself)
const FILE_301 = { '/index.html': A + '/', '/favicon.ico': A + '/assets/img/68a3b42d10041847e0bead17.png' };
for (const [f, want] of Object.entries(FILE_301)) {
  const r = run('doctordemographics.com', f); ok(r.statusCode === 301 && r.headers.location.value === want, 'file 301 ' + f);
}
ok(pages.has('/assets/img/68a3b42d10041847e0bead17.png'), 'favicon target missing from dist');
{ const r = run('doctordemographics.com', '/'); ok(!r.statusCode && r.uri === '/index.html', 'home / must still serve /index.html'); }
// George Nov 23 item 3: correctly spelled order-form URLs
for (const [u_, want] of [['/site-viability-report-form', 'https://order.doctordemographics.com/site-viabilty-report-form'],
                          ['/site-viability-report-form/', 'https://order.doctordemographics.com/site-viabilty-report-form'],
                          ['/marketing-report-form', 'https://order.doctordemographics.com/marketing-report-order']]) {
  const r = run('doctordemographics.com', u_); ok(r.statusCode === 301 && r.headers.location.value === want, 'order form 301 ' + u_);
}
for (const p of pages) {
  if (FILE_301[p]) continue;
  const r = run('doctordemographics.com', p);
  ok(!r.statusCode && r.uri === p, 'live file redirected: ' + p);
  if (p.endsWith('/index.html') && p !== '/index.html') {
    const dir = p.slice(0, -'index.html'.length);
    const r1 = run('doctordemographics.com', dir); ok(!r1.statusCode && r1.uri === p, 'live page redirected: ' + dir);
    const r2 = run('doctordemographics.com', dir.slice(0, -1));
    ok(r2.statusCode === 301 && r2.headers.location.value === A + dir, 'slashless live page: ' + dir);
  }
}
// GHL order pages unchanged
for (const g of ['/getsocial', '/accessdso', '/apexchat', '/ppschedule', '/best-sites-report-form', '/comp-report-form', '/quick-view-report-form',
  '/site-viabilty-report-form', '/best-sites-report-order', '/comp-report-order', '/marketing-report-order', '/quick-view-report-order',
  '/site-viability-order', '/telephone-consultation-order', '/order-complete', '/order-complete-telephone']) {
  const r = run('doctordemographics.com', g, { email: { value: 'a%40b.com' } });
  ok(r.statusCode === 301 && r.headers.location.value === 'https://order.doctordemographics.com' + g + '?email=a%40b.com', 'GHL ' + g);
}
// unknown paths still fall to the 404 page (no catch-all)
for (const u of ['/no-such-page/', '/blog/b/no-such-post/', '/podcast/no-such/', '/order-complete-x/']) {
  const r = run('doctordemographics.com', u); ok(!r.statusCode, 'unknown path redirected: ' + u);
}
// George Nov 24: remaining GSC 404s and duplicates (main site)
for (const [u_, want] of [['/webinar-nyc', A + '/reports/'], ['/webinar-nyc/', A + '/reports/'],
                          ['/faq', A + '/reports/'], ['/faq/', A + '/reports/'],
                          ['/blog/c/podcast/b/kiss-of-death-locations-for-2026', A + '/blog/b/kiss-of-death-locations-for-2026/'],
                          ['/blog/c/podcast/b/kiss-of-death-locations-for-2026/', A + '/blog/b/kiss-of-death-locations-for-2026/']]) {
  const r = run('doctordemographics.com', u_);
  ok(r.statusCode === 301 && r.headers.location.value === want, 'nov24 301 ' + u_ + ' -> ' + (r.statusCode ? r.headers.location.value : r.uri));
}
// single-hop slash + NitroPack / ?cat= strip; keep utm; do not strip a lone token
{
  const r = run('doctordemographics.com', '/best-sites-report', { ignorenitro: { value: '1' }, nitroWebhook: { value: 'config' }, token: { value: 'test' } });
  ok(r.statusCode === 301 && r.headers.location.value === A + '/best-sites-report/', 'nitro slashless single hop');
  const r2 = run('doctordemographics.com', '/best-sites-report/', { ignorenitro: { value: '1' }, nitroWebhook: { value: 'config' }, token: { value: 'test' } });
  ok(r2.statusCode === 301 && r2.headers.location.value === A + '/best-sites-report/', 'nitro slashed 301 to canonical');
  const r3 = run('doctordemographics.com', '/best-sites-report/', { ignorenitro: { value: '1' }, utm_source: { value: 'x' } });
  ok(r3.statusCode === 301 && r3.headers.location.value === A + '/best-sites-report/?utm_source=x', 'nitro strip keeps utm');
  const r4 = run('doctordemographics.com', '/', { cat: { value: '' } });
  ok(r4.statusCode === 301 && r4.headers.location.value === A + '/', 'empty cat 301 home');
  const r5 = run('doctordemographics.com', '/', { cat: { value: 'podcast' } });
  ok(r5.statusCode === 301 && r5.headers.location.value === A + '/', 'cat=podcast 301 home (same as live canonical)');
  const r6 = run('doctordemographics.com', '/about/', { ignorenitro: { value: '1' }, trk: { value: 'test' } });
  ok(r6.statusCode === 301 && r6.headers.location.value === A + '/about/', 'about nitro+trk');
  const r7 = run('doctordemographics.com', '/best-sites-report/', { token: { value: 'abc' } });
  ok(!r7.statusCode && r7.uri === '/best-sites-report/index.html', 'lone token not stripped');
  const r8 = run('doctordemographics.com', '/best-sites-report/', { utm_source: { value: 'x' } });
  ok(!r8.statusCode && r8.uri === '/best-sites-report/index.html', 'utm alone still served');
  // junk builder paths stay 404 (no 301 to home)
  for (const u of ['/_preview/', '/cdn-cgi/l/email-protection/', '/tmp/workspace/production/common/builder-preview/locales/da.json', '/tmp/workspace/production/common/builder-preview/locales/no.json']) {
    const r = run('doctordemographics.com', u);
    ok(!r.statusCode, 'junk should stay 404 (no redirect): ' + u);
  }
}
// regression vs the old (live) function: identical result for every one of its redirects and the old test cases
const oldf = process.argv[2];
if (oldf) {
  const old = load(oldf); const src = fs.readFileSync(oldf, 'utf8');
  const keys = Object.keys(JSON.parse(src.match(/var M=(\{.*\});/)[1]));
  const cases = keys.flatMap(k => [['doctordemographics.com', k], ['www.doctordemographics.com', k + '/'], ['d1.cloudfront.net', k]])
    .concat([['doctordemographics.com', '/'], ['doctordemographics.com', '/about'], ['doctordemographics.com', '/About'], ['www.doctordemographics.com', '/'],
      ['doctordemographics.com', '/css/style.css'], ['doctordemographics.com', '/sitemap.xml'], ['doctordemographics.com', '/no-such-page/']]);
  let n = 0;
  for (const [h, u] of cases) { n++; const a = JSON.stringify(run(h, u, { x: { value: '1' } }, old)), b = JSON.stringify(run(h, u, { x: { value: '1' } }));
    ok(a === b, `changed vs old function: ${h}${u}\n  old ${a}\n  new ${b}`); }
  console.log('regression cases vs old function:', n);
}
console.log('rows', rows.length, JSON.stringify(types), 'live files', pages.size, 'checks', checks, 'fails', fails);
process.exit(fails ? 1 : 0);
