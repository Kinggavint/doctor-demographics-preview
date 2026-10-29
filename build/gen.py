#!/usr/bin/env python3
"""Doctor Demographics preview generator.
Renders every page from build/data (live text captured Oct 29, 2026) into <path>/index.html.
Run from the repo root: python3 build/gen.py
"""
import html, json, os, re, csv, shutil
from bs4 import BeautifulSoup, NavigableString, Comment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'build', 'data')
# Published output lives in docs/ (GitHub Pages source). build/ and the review docs stay at the repo root, unpublished.
SITE = os.path.join(ROOT, 'docs')
LIVE = 'https://doctordemographics.com'
# TODO cutover: switch ORDER_BASE to https://order.doctordemographics.com once the GHL subdomain exists.
ORDER_BASE = 'https://doctordemographics.com'
ORDER_FUTURE = 'https://order.doctordemographics.com'
PREVIEW_BASE = 'https://kinggavint.github.io/doctor-demographics-preview/'
PHONE, PHONE_TEL = '(844) 704-0499', 'tel:+18447040499'
EMAIL = 'support@doctordemographics.com'
APPLE = 'https://podcasts.apple.com/us/podcast/doctor-demographics-podcast/id800840123'
APPLE_HOME = 'https://podcasts.apple.com/us/podcast/doctordemographics-podcast/id800840123'
SPOTIFY = 'https://open.spotify.com/show/5y2MWJfrbhhp8z3fC0AnVT'
YT_FOOTER = 'https://www.youtube.com/@doctordemographicslive2702'
SOCIALS = [('Facebook', 'https://www.facebook.com/doctordemographics'),
           ('Instagram', 'https://www.instagram.com/doctordemographics/'),
           ('X', 'https://x.com/Dr_Demographics'),
           ('LinkedIn', 'https://www.linkedin.com/company/doctor-demographics'),
           ('YouTube', YT_FOOTER),
           ('TikTok', 'https://www.tiktok.com/@doctordemographics')]
GCS = 'https://storage.googleapis.com/msgsndr/r2zxbinSYE1Bmb07a0FY/media/'
FS = 'https://assets.cdn.filesafe.space/r2zxbinSYE1Bmb07a0FY/media/'

META = json.load(open(os.path.join(DATA, 'meta.json')))
CHANGES = []   # (page, kind, before, after)
TODOS = []     # (page, kind, text)
PAGES = []     # generated paths
CUR = {'path': '', 'depth': 0}

# ---------------------------------------------------------------- text
def body(slug):
    lines = open(os.path.join(DATA, 'text', slug + '.txt')).read().split('\n')[14:]
    out = []
    for l in lines:
        if l.strip() in ('Our Leadership',) or l.startswith('For over 40 years, the Doctor'):
            break
        out.append(l)
    return out

_cache = {}
def L(slug, a, b=None):
    """file line numbers (1-based) a..b inclusive"""
    if slug not in _cache:
        _cache[slug] = open(os.path.join(DATA, 'text', slug + '.txt')).read().split('\n')
    ls = _cache[slug]
    if b is None:
        return ls[a - 1]
    return ls[a - 1:b]

def ln(slug, prefix):
    if slug not in _cache:
        L(slug, 1)
    for l in _cache[slug]:
        if l.startswith(prefix):
            return l
    raise KeyError((slug, prefix))

TYPOS = [('Micheal', 'Michael'), ('Infomation', 'Information'), ('Viabililty', 'Viability'),
         ('Comparision', 'Comparison'), ('Governemnts', 'Governments'), ('over the. years', 'over the years'),
         ('nessecity', 'necessity'), ("doctor's of all kinds", 'doctors of all kinds'),
         ("give doctor's a little", 'give doctors a little'), ('in the follow situations', 'in the following situations'),
         ('numbers will comes', 'numbers will come'), ('to make a decisions', 'to make decisions'),
         ('Site Viability  Report', 'Site Viability Report'), ('Report Price:  $', 'Report Price: $'),
         ('shall by governed', 'shall be governed'), ('Order A DEMOGRAPHIC REPORt', 'Order a Demographic Report'),
         ('doctor demographics has helped', 'Doctor Demographics has helped')]
YEARS = [('For over 40 years, the Doctor Demographics team have helped', 'Since 1983, the Doctor Demographics team has helped'),
         ('For over 40 years, the team at Doctor Demographics has', 'Since 1983, the team at Doctor Demographics has'),
         ('For more than 30 years, doctor demographics has helped', 'Since 1983, Doctor Demographics has helped'),
         ('For over 30 Years, Doctor Demographics has', 'Since 1983, Doctor Demographics has'),
         ('with over 30 years of experience specializing', 'specializing'),
         ('with 40+ years of experience', 'with expertise built since 1983'),
         ('a company with over 30 years of experience in assisting doctors with these very questions', 'a company that has been assisting doctors with these very questions since 1983'),
         ('As a marketer with 30 years of experience\u201415 of those as a demographic marketer with Scott McDonald at Doctor Demographics\u2014', 'As a marketer, and as a demographic marketer with Scott McDonald at Doctor Demographics, '),
         ('for doctors nearly 40 years ago', 'for doctors back in 1983'),
         ('Our founder, Scott McDonald pioneered', 'Our founder, Scott McDonald (now retired), pioneered')]
FREE = [('Live (Free) Trainings', 'Live Trainings'), ('Order a Free Sample Report', 'Order a Sample Report'),
        ('Our Free Sample Reports', 'Our Sample Reports'), ('Order Free Sample ', 'Order a Sample '),
        ('Get Your Free Sample Reports', 'Get Your Sample Reports'), ('your free sample reports', 'your sample reports'),
        ('Free Sample Reports', 'Sample Reports'), ('Free sample reports', 'Sample reports'),
        ('Weekly Free Webinar', 'Weekly Webinar'), ('Free Weekly Webinar', 'Weekly Webinar'),
        ('Weekly Free', 'Weekly'), ('These FREE webinars', 'These webinars'), ('Register for Free Webinar', 'Register for Webinar'),
        ('Join our free weekly', 'Join our weekly'), ('Reserve Your Free Copy', 'Reserve Your Copy'),
        ('get your free copy', 'get your copy'), ('for a free consultation', 'for a consultation')]
EMOJI = re.compile('[\U0001F300-\U0001FAFF\u2600-\u27BF\U0001F000-\U0001F2FF\uFE0F]')

def dashfix(s):
    s2 = re.sub(r'(\d)\s*[\u2013\u2014]\s*(\d)', r'\1 to \2', s)
    s2 = re.sub(r'\s*[\u2014\u2013]\s*', ', ', s2)
    s2 = re.sub(r'(?<=\S)\s-\s(?=\S)', ', ', s2)
    s2 = re.sub(r',\s*,', ',', s2)
    s2 = re.sub(r',\s+([.!?:;)])', r'\1', s2)
    s2 = re.sub(r'^\s*,\s*', '', s2) if not s.lstrip().startswith((',', '\u2014', '\u2013')) else s2
    return s2

def fx(s):
    """Apply logged copy fixes: typos and no-cost wording (CEO calls), dashes (builder rule)."""
    orig = s
    for a, b in YEARS:
        if a in s:
            s = s.replace(a, b); CHANGES.append((CUR['path'], 'Gavin decision (since 1983, Scott now retired)', a, b))
    for a, b in TYPOS:
        if a in s:
            s = s.replace(a, b); CHANGES.append((CUR['path'], 'typo (CEO call)', a, b))
    for a, b in FREE:
        if a in s:
            s = s.replace(a, b); CHANGES.append((CUR['path'], 'no-cost wording (CEO call)', a, b))
    e = EMOJI.sub('', s)
    if e != s:
        CHANGES.append((CUR['path'], 'emoji removed (builder copy rule)', s[:90], e[:90])); s = re.sub(r'  +', ' ', e)
    d = dashfix(s)
    if d != s:
        CHANGES.append((CUR['path'], 'dash removed (builder copy rule)', s[:90], d[:90]))
        s = d
    s = s.replace('\u00a0', ' ')
    return s

def t(s):
    return html.escape(fx(s.strip()), quote=False)

def a_(s):
    return html.escape(s, quote=True)

def todo(text, kind=''):
    TODOS.append((CUR['path'] or '/', kind or 'todo', text))
    cls = 'todo' + ((' ' + ('ceo' if kind.startswith('CEO') else kind)) if kind else '')
    return f'<span class="{cls}">{html.escape(text, quote=False)}</span>'

# ---------------------------------------------------------------- links
def u(p):
    pre = '../' * CUR['depth']
    if p.startswith(('http:', 'https:', 'mailto:', 'tel:', '#')):
        return p
    frag = ''
    if '#' in p:
        p, frag = p.split('#', 1); frag = '#' + frag
    p = p.strip('/')
    if p == '':
        return (pre or './') + frag
    last = p.split('/')[-1]
    if p.startswith(('assets/', 'css/', 'js/')) or '.' in last:
        return pre + p + frag
    return pre + p + '/' + frag

def O(path):
    return ORDER_BASE + path

def btn(text, href, cls='', ext=None, raw=False):
    if ext is None:
        ext = href.startswith('http')
    extra = ' target="_blank" rel="noopener"' if ext else ''
    label = text if raw else t(text)
    c = 'btn' + (' ' + cls if cls else '') + (' ext' if ext else '')
    return f'<a class="{c}" href="{a_(u(href))}"{extra}>{label}</a>'

def img(name, alt, cls='', lazy=True, w=None):
    c = f' class="{cls}"' if cls else ''
    lz = ' loading="lazy"' if lazy else ''
    return f'<img{c} src="{u("assets/img/" + name)}" alt="{a_(alt)}"{lz}>'

def p(s):
    return f'<p>{t(s)}</p>'

def ul(items, cls='check'):
    return f'<ul class="{cls}">' + ''.join(f'<li>{x if x.startswith("<") else t(x)}</li>' for x in items) + '</ul>'

def lite(vid, alt):
    return (f'<a class="lite" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">'
            f'<img src="https://img.youtube.com/vi/{vid}/hqdefault.jpg" alt="{a_(alt)}" loading="lazy"></a>')

def video(src, poster=None, title='Product video'):
    if 'vimeo' in src:
        return f'<div class="video"><iframe src="{src}" title="{a_(title)}" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen loading="lazy"></iframe></div>'
    pa = f' poster="{u("assets/img/" + poster)}"' if poster else ''
    return f'<div class="video"><video controls preload="metadata" playsinline{pa} src="{src}" title="{a_(title)}"></video></div>'

def ghl_form(fid, name, height=700):
    return (f'<div class="form-embed"><iframe src="https://api.leadconnectorhq.com/widget/form/{fid}" '
            f'id="inline-{fid}" data-layout="{{\'id\':\'INLINE\'}}" data-trigger-type="alwaysShow" data-trigger-value="" '
            f'data-activation-type="alwaysActivated" data-activation-value="" data-deactivation-type="neverDeactivate" '
            f'data-deactivation-value="" data-form-name="{a_(name)}" data-height="{height}" data-layout-iframe-id="inline-{fid}" '
            f'data-form-id="{fid}" title="{a_(name)}" style="min-height:{height}px"></iframe>'
            f'<script src="https://link.msgsndr.com/js/form_embed.js"></script>'
            f'<p class="embed-note">This is the live GoHighLevel form ({fid}). Preview reviewers: please do not submit it.</p></div>')

def ghl_booking(cid):
    return (f'<div class="form-embed"><iframe src="https://api.leadconnectorhq.com/widget/booking/{cid}" '
            f'id="{cid}_booking" title="Booking calendar" scrolling="no" style="min-height:900px;overflow:hidden"></iframe>'
            f'<script src="https://link.msgsndr.com/js/form_embed.js"></script>'
            f'<p class="embed-note">This is the live GoHighLevel booking calendar ({cid}). Preview reviewers: please do not book a slot.</p></div>')

# ---------------------------------------------------------------- layout
NAV_REPORTS = [('Best Sites Report', '/best-sites-report'), ('Site Viability Report', '/site-viability-report'),
               ('Marketing Report', '/marketing-report'), ('Competition Report', '/comp-report'),
               ('Telephone Consultation', '/telephone-consultation')]

def begin(path):
    path = path.strip('/')
    CUR['path'] = '/' + path if path else '/'
    CUR['depth'] = len(path.split('/')) if path else 0

def header():
    cur = CUR['path']
    def nl(label, href):
        ac = ' aria-current="page"' if href == cur else ''
        return f'<a href="{u(href)}"{ac}>{label}</a>'
    dd = ''.join(f'<a href="{u(h)}">{l}</a>' for l, h in NAV_REPORTS)
    return f'''<a class="skip" href="#main">Skip to content</a>
<div class="preview-bar">Preview build for review only. Not the live site. Forms and order buttons connect to the live GoHighLevel system, so please do not submit them. <a href="{u('/preview-notes')}">Review notes and open items</a></div>
<div class="topbar"><div class="wrap"><a href="{PHONE_TEL}">{PHONE}</a><a href="mailto:{EMAIL}">{EMAIL}</a></div></div>
<header class="site-header"><div class="wrap">
<a class="logo" href="{u('/')}"><img src="{u('assets/img/68a3b42d10041847e0bead17.png')}" alt="Doctor Demographics"></a>
<button class="menu-toggle" aria-expanded="false" aria-controls="nav" onclick="var n=document.getElementById('nav');n.classList.toggle('open');this.setAttribute('aria-expanded',n.classList.contains('open'))">Menu</button>
<nav class="nav" id="nav" aria-label="Main">
{nl('Home', '/')}{nl('About', '/about')}
<div class="dd"><a href="{u('/reports')}">Demographic Reports</a><div class="dd-menu">{dd}</div></div>
{nl('Sample Reports', '/sample-reports')}{nl('Podcast', '/podcast')}
<a class="ext" href="{O('/getsocial')}" target="_blank" rel="noopener">Training</a>
{nl('Contact', '/contact')}
<a class="apex" href="https://apexailabs.ai/" target="_blank" rel="noopener" aria-label="Powered by ApexAI Labs">ApexAI</a>
</nav></div></header>'''

def leadership(h1=False):
    tag = 'h1' if h1 else 'h2'
    scott = ln('home', 'Demographics is more than')
    mike = ln('home', 'Mike Green is a seasoned')
    return f'''<section class="section alt leaders" aria-labelledby="lead-h"><div class="wrap">
<{tag} id="lead-h" class="center">Our Leadership</{tag}>
<div class="grid g2">
<div class="card person"><div class="person">{img('631c160e05c40c6f83ebc915.jpg', 'Scott McDonald')}
<div><blockquote>"{t(scott)}"</blockquote><h3>Scott McDonald</h3><p class="role">Founder, Doctor Demographics (now retired)</p></div></div></div>
<div class="card person"><div class="person">{img('mike_profile_26.jpg', 'Mike Green')}
<div><blockquote>"{t(mike)}"</blockquote><h3>Mike Green</h3><p class="role">Owner &amp; Lead Demographer, Doctor Demographics</p>
{todo("Mike's own year count was removed under the since 1983 rule. Add a figure for Mike back?")}</div></div></div>
</div></div></section>'''

def footer():
    ql = [('Reports', '/reports'), ('Site Viability', '/site-viability-report'), ('Best Sites Report', '/best-sites-report'),
          ('Telephone Consultation', '/telephone-consultation'), ('Marketing Report', '/marketing-report'), ('Contact Us', '/contact')]
    soc = ''.join(f'<li><a href="{h}" target="_blank" rel="noopener">{n}</a></li>' for n, h in SOCIALS)
    return f'''<footer class="site-footer"><div class="wrap"><div class="cols">
<div><img class="logo" src="{u('assets/img/DD_WHITE.png')}" alt="Doctor Demographics" loading="lazy" style="height:54px;width:auto;margin-bottom:1rem">
<p>{t('For over 40 years, the Doctor Demographics team have helped thousands of doctors and practice owners select the perfect place to set up their practice.')}</p></div>
<div><h4>Quick Links</h4><ul>{''.join(f'<li><a href="{u(h)}">{l}</a></li>' for l, h in ql)}</ul></div>
<div><h4>Contact Us</h4><ul><li><a href="{PHONE_TEL}"><strong>{PHONE}</strong></a></li><li><a href="mailto:{EMAIL}"><strong>{EMAIL}</strong></a></li></ul></div>
<div><h4>Follow Us</h4><ul>{soc}</ul>
{todo('Facebook link corrected from doctordemograhics to doctordemographics; could_not_verify which page is the real one.', 'ceo')}
{todo('ApexAI link kept in the main menu; confirm it stays.', 'ceo')}</div>
</div>
<div class="legal"><span>&copy; Copyright 2026. Doctor Demographics, LLC. | All Rights Reserved |</span>
<span><a href="{u('/privacy-policy')}">Privacy Policy</a> | <a href="{u('/eula')}">Terms and Conditions</a></span></div>
</div></footer>'''

FOOTER_TODOS_DONE = False

def finish(title, desc, main, flag=None, lead=True, extra_head='', canonical=None, chrome=True):
    path = CUR['path']
    canon = canonical or (LIVE + ('' if path == '/' else path))
    if path == '/':
        canon = LIVE + '/'
    fl = f'<div class="flag"><div class="wrap">{flag}</div></div>' if flag else ''
    head = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{a_(desc)}">
<meta name="robots" content="noindex, nofollow">
<link rel="canonical" href="{canon}">
<link rel="icon" href="{u('assets/img/68a3b42d10041847e0bead17.png')}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&amp;display=swap">
<link rel="stylesheet" href="{u('css/style.css')}">{extra_head}
</head><body>'''
    if chrome:
        doc = head + header() + fl + f'<main id="main">{main}</main>' + (leadership() if lead else '') + footer() + '</body></html>\n'
    else:
        doc = head + f'<main id="main">{main}</main></body></html>\n'
    rel = path.strip('/')
    out = os.path.join(SITE, rel, 'index.html') if rel else os.path.join(SITE, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(doc)
    PAGES.append(path)

def title_of(slug, fallback):
    tt = META.get(slug, {}).get('title') or fallback
    return fx(tt)

def desc_of(slug, fallback=''):
    d = META.get(slug, {}).get('description') or fallback
    return fx(d)

HIDDEN = 'Hidden page on the live site: no navigation link points here. Kept in the preview unlinked and noindexed. Decision pending (keep, update, or retire).'
def flag_hidden(extra=''):
    TODOS.append((CUR['path'], 'hidden page', 'Hidden on live, kept unlinked. Keep, update, or retire? ' + extra))
    return f'<strong>Review flag.</strong> {HIDDEN} {html.escape(extra)}'

def hero(h1, sub='', kicker='', small=True, actions=''):
    k = f'<p class="kicker">{kicker}</p>' if kicker else ''
    s = f'<p>{sub}</p>' if sub else ''
    return f'<section class="hero{" small" if small else ""}"><div class="wrap">{k}<h1>{h1}</h1>{s}{actions}</div></section>'
# ---------------------------------------------------------------- pages
def page_home():
    begin('/')
    s = 'home'
    sub = t(L(s, 17).replace('VETERINARIANS, and optometrists', 'veterinarians, optometrists, and audiologists'))
    CHANGES.append(('/', 'client OEDIT d9e575d', 'VETERINARIANS, and optometrists', 'veterinarians, optometrists, and audiologists'))
    m = hero('Helping doctors find the perfect place to practice', sub, small=False,
             actions=f'<div class="btn-row">{btn("Order a Demographic Report", "/reports", "gold")}</div>')
    m += f'''<section class="section"><div class="wrap split"><div class="prose">
<h2>{t(L(s,19))}</h2>{p(L(s,20))}{p(L(s,21))}<div class="btn-row">{btn("Order a Demographic Report", "/reports")}</div></div>
<div>{img('62748d21ea2ab126f720248c.png', 'Doctors and team members smiling')}</div></div></section>
<section class="section alt"><div class="wrap"><h2 class="center">{t(L(s,23))}</h2><div class="grid g4">
{''.join(f'<div class="card benefit"><p>{t(x)}</p></div>' for x in L(s,24,27))}</div></div></section>
<section class="section"><div class="wrap split"><div>{img('d584a9f2-537d-4611-ae13-77848e700c56.png', 'Practice owners reviewing plans together')}</div>
<div class="prose"><h2>{t(L(s,28))}</h2>{p(L(s,29))}<div class="btn-row">{btn("Order a Demographic Report", "/reports")}</div></div></div></section>
<section class="section dark"><div class="wrap split"><div class="prose"><h2>{t(L(s,31))}</h2>{p(L(s,32))}
<div class="btn-row">{btn("Subscribe Here", APPLE_HOME, "gold")}</div><p class="note">Weekly Episode in Your Inbox</p></div>
<div><h3>Here's Our Most Recent Episode:</h3>{lite('RlPfnmyHmLs', 'Play the most recent episode video')}
{todo('Live home shows the Episode 252 video. The podcast page lists a newer most recent episode (10/14/2026, video 0QxDdSgI0VY). Which should show here?')}</div></div></section>
<section class="section"><div class="wrap"><h2 class="center">{t(L(s,36))}</h2><div class="grid g4">'''
    cards = [(39, 40, '/best-sites-report', '64adb6bd1aa4669e1a404704.jpg'), (43, 44, '/site-viability-report', '65258de43fd52c3674559fc6.jpg'),
             (47, 48, '/marketing-report', '68e832bde22f982ba43459c3.jpg'), (51, 52, '/telephone-consultation', '68e833334d2dffc79b33fde1.jpg')]
    for h, d, href, im in cards:
        m += f'<div class="card">{img(im, fx(L(s,h)).strip(), "thumb")}<h3>{t(L(s,h))}</h3>{p(L(s,d))}<div class="actions">{btn("More Infomation", href)}</div></div>'
    m += '</div></div></section>'
    TODOS.append(('/', 'note', 'Live home also has a hidden popup ("Weekly Practice Placement, Promotion, and Profit Tips", Book prelaunch form s7hud67kdZaPKZmuYwDE, "Join 2,000+ Doctors"). Hidden on live, left out of the preview. Add it?'))
    finish(title_of(s, 'Doctor Demographics'), desc_of(s), m)

def page_about():
    begin('/about')
    m = hero('About Doctor Demographics', t('For over 40 years, the Doctor Demographics team have helped thousands of doctors and practice owners select the perfect place to set up their practice.'))
    m += f'<div class="wrap" style="padding-top:1rem">{todo("Live /about shows only the leadership block and has no page title. Title and heading here are placeholders.", "open")}</div>'
    m += leadership(h1=False)
    finish('About | Doctor Demographics', 'Meet the leadership team at Doctor Demographics.', m, lead=False)

PRODUCTS = {
    'best-sites-report': dict(order='/best-sites-report-form', sample='/best-sites-report-sample'),
    'site-viability-report': dict(order='/site-viabilty-report-form', sample='/site-viability-report-sample'),
    'marketing-report': dict(order='#order', sample='/marketing-report-sample'),
    'comp-report': dict(order='/comp-report-form', sample='/competition-report-sample'),
    'telephone-consultation': dict(order='#order', sample=None),
    'quick-view-report': dict(order='/quick-view-report-form', sample='/quick-view-report-sample'),
    'state-briefings': dict(order='/state-briefing-order', sample='/site-viability-report-sample'),
}
def ohref(slug):
    o = PRODUCTS[slug]['order']
    return o if o.startswith('#') else O(o)

def reports_page():
    begin('/reports')
    s = 'reports'
    m = hero('Demographic Reports')
    items = [('telephone-consultation', 16, 17), ('site-viability-report', 19, 20), ('marketing-report', 22, 24),
             ('best-sites-report', 26, 28), ('comp-report', 30, 31)]
    m += '<section class="section"><div class="wrap"><div class="grid g3">'
    for slug, h0, d in items:
        title = ' '.join(x.strip() for x in L(s, h0, d - 1))
        acts = btn('More Info', '/' + slug, 'ghost')
        o = PRODUCTS[slug]['order']
        acts += btn('Order a report', ('/' + slug + o) if o.startswith('#') else O(o))
        if PRODUCTS[slug]['sample']:
            acts += btn('See sample report', PRODUCTS[slug]['sample'], 'ghost')
        m += f'<div class="card"><h3>{t(title)}</h3>{p(L(s,d))}<div class="actions">{acts}</div></div>'
    m += f'''</div><p style="margin-top:1.5rem">{todo('Quick View Report and State Briefings are not listed here on live (hidden pages). Add them to this hub?', 'open')}</p>
<div class="btn-row">{btn('Order a Free Sample Report', '/sample-reports', 'gold')}</div></div></section>
<section class="section alt"><div class="wrap grid g2"><div><h3>Contact Us by Phone</h3><p><a href="{PHONE_TEL}"><strong>{PHONE}</strong></a></p></div>
<div><h3>Contact Us by Email</h3><p><a href="mailto:{EMAIL}"><strong>{EMAIL}</strong></a></p></div></div></section>'''
    CHANGES.append(('/reports', 'client OEDIT d92ae0d', 'card buttons', 'added "Order a report" and "See sample report" next to More Info (no sample for Telephone, per OEDIT f66af04)'))
    finish(title_of(s, 'Demographic Reports'), desc_of(s), m)

def need_list(items, sub_after=None, sub=None):
    out = []
    for x in items:
        x = x.strip()
        if sub_after and x == sub_after:
            out.append(f'{t(x)} <span class="note">{t(sub)}</span>')
        else:
            out.append(t(x))
    return '<ul class="check">' + ''.join(f'<li>{x}</li>' for x in out) + '</ul>'

def product(slug, h1, media, feat_head, price_html, feats, order_label, sample_label, desc_head, desc_html,
            need_html='', after='', flag=None, feat_extra='', top_extra=''):
    begin('/' + slug)
    pr = PRODUCTS[slug]
    sample = f'<p><a href="{u(pr["sample"])}">{t(sample_label)}</a></p>' if sample_label else ''
    order_btn = btn(order_label, ohref(slug), 'gold') if order_label else ''
    m = hero(t(h1))
    m += f'''<section class="section"><div class="wrap split"><div>{media}{top_extra}</div>
<div class="features"><h2 style="font-size:var(--text-lg)">{t(feat_head)}</h2><div class="price">{price_html}</div>{feats}{feat_extra}
<div class="btn-row">{order_btn}</div>{sample}</div></div></section>
<section class="section alt"><div class="wrap split"><div class="prose"><h2>{t(desc_head)}</h2>{desc_html}
{('<div class="btn-row">' + btn(order_label, ohref(slug)) + '</div>') if order_label and pr['order'].startswith('/') else ''}</div>
<div>{need_html}</div></div></section>{after}'''
    finish(title_of(slug, h1), desc_of(slug), m, flag=flag)

def products():
    s = 'best-sites-report'
    begin('/best-sites-report')
    product(s, L(s, 15), video(GCS + '68e831483c4de916636bc770.mp4', title='Best Sites Report video'), L(s, 17), t(L(s, 18)),
            ul(L(s, 19, 23)), 'Order Best Sites Report', L(s, 25), L(s, 26), ''.join(p(x) for x in L(s, 27, 31)),
            f'<div class="need"><h3>{t(L(s,33))}</h3>{need_list(L(s,34,37), "Circumstances", L(s,38))}<p class="note">{t(L(s,39))}</p></div>')
    s = 'site-viability-report'
    begin('/site-viability-report')
    product(s, L(s, 15), video(GCS + '68e831484d2dff121b33a36c.mp4', title='Site Viability Report video'), L(s, 17), t(L(s, 18)),
            ul(L(s, 19, 22)), L(s, 23), L(s, 24), L(s, 25), ''.join(p(x) for x in L(s, 26, 27)),
            f'<div class="need"><h3>{t(L(s,29))}</h3>{need_list(L(s,30,33), "Circumstances", L(s,34))}<p class="note">{t(L(s,35))}</p></div>')
    s = 'marketing-report'
    begin('/marketing-report')
    product(s, L(s, 15), video(GCS + '68e83148fd24b5fd49c5f4fb.mp4', title='Marketing Report video'), L(s, 17), t(L(s, 18)),
            ul(L(s, 19, 22)), L(s, 23), L(s, 24), L(s, 25), ''.join(p(x) for x in L(s, 26, 27)),
            f'<div class="need"><h3>{t(L(s,28))}</h3>{need_list(L(s,29,33))}<p class="note">{t(L(s,34))}</p></div>',
            after=f'<section class="section" id="order"><div class="wrap prose"><h2>{t(L(s,35))}</h2>{p(L(s,36))}{ghl_form("RnzOfCKPUBs3omXWcT7J", "Marketing Report form")}</div></section>',
            feat_extra=todo('On live, this features list is identical to the Site Viability list. Confirm the Marketing Report features.', 'open'))
    s = 'comp-report'
    begin('/comp-report')
    product(s, L(s, 15), video(FS + '69b8614e9379cf3f4dc0cf65.mp4', 'e12832a2aa8ca86a.jpg', 'Competition Report video'), L(s, 17),
            t(L(s, 18)) + ' ' + todo('Competition price $350 per site, matches the checkout.', 'ceo'),
            ul(L(s, 19, 23)), L(s, 24), L(s, 25), L(s, 26), ''.join(p(x) for x in L(s, 27, 29)),
            f'<div class="need"><h3>{t(L(s,31))}</h3>{need_list(L(s,32,35))}<p class="note">{t(L(s,36))}</p></div>',
            feat_extra=todo('One live Order button went to the Site Viability form. Both now go to /comp-report-form.', 'ceo'))
    CHANGES.append(('/comp-report', 'wrong button target fixed (CEO call)', '/site-viabilty-report-form', '/comp-report-form'))
    s = 'telephone-consultation'
    begin('/telephone-consultation')
    price = f'Price: <s>$225</s> $90 (60% off) {todo("Telephone price $90, matches the checkout.", "ceo")}'
    desc = (f'<h3>{t(L(s,28))}</h3>{p(L(s,29))}{ul([x.lstrip("- ") for x in L(s,30,32)], "plain")}'
            + ''.join(p(x) for x in L(s, 33, 35)) + f'<h3>{t(L(s,36))}</h3>{ul(L(s,37,40), "plain")}')
    product(s, L(s, 15), video(FS + '68e831484d2dff19aa33a36b.mp4', title='Telephone Consultation video'), L(s, 17), price,
            ul(L(s, 22, 25)), L(s, 26), None, L(s, 27), desc, '',
            after=f'<section class="section" id="order"><div class="wrap prose"><h2>{t(L(s,41))}</h2>{ghl_form("edICwOvB663uJ8lbtCRO", "Telephone Consultation form")}</div></section>')
    s = 'quick-view-report'
    begin('/quick-view-report')
    product(s, L(s, 15), img('635195d6b495690eab7a6fa0.jpg', 'Analyst reviewing a report at a desk'), L(s, 16), t(L(s, 17)),
            ul(L(s, 18, 22)), L(s, 23), L(s, 24), L(s, 25), p(L(s, 26)),
            f'<div class="need"><h3>{t(L(s,28))}</h3>{need_list(L(s,29,31))}<p class="note">{t(L(s,32))}</p></div>',
            flag=flag_hidden())
    s = 'state-briefings'
    begin('/state-briefings')
    states = [x.strip() for x in L(s, 34, 58)]
    i = states.index('New York'); states[i:i + 2] = ['New York (City)']
    feats = ul(L(s, 19, 23))
    desc = (''.join(p(x) for x in L(s, 27, 29)) + f'<h3>{t(L(s,30))}</h3>{ul([L(s,31)])}<div class="btn-row">{btn(L(s,32), ohref(s), "gold")}</div>'
            + f'<h3>{t(L(s,33))}</h3><ul class="states">' + ''.join(f'<li>{t(x)}</li>' for x in states) + '</ul>'
            + todo('Texas is listed as both available and coming soon.', 'open') + f'<p class="note">{t(L(s,59))}</p>')
    product(s, L(s, 15), todo('CEO call, pending Gavin: the dead State Briefing Vimeo video (792399334, dead on live too) is removed from the preview. For Mike\'s team: supply a working video if one should show here.', 'CEO call, pending Gavin'), L(s, 17), t(L(s, 18)),
            feats, L(s, 24), L(s, 25), L(s, 26), desc, '',
            top_extra=f'<p style="margin-top:1rem"><strong>{t(L(s,16))}</strong> {todo("Dated: says Updated for 2023.", "open")}</p>',
            feat_extra=todo('The sample link goes to the Site Viability sample (as on live). No State Briefing sample exists.'),
            flag=flag_hidden('Also dated (Updated for 2023).'))

def sample_hub():
    begin('/sample-reports')
    s = 'sample-reports'
    intro = L(s, 16)
    h2, rest = intro.split('ReportsAt ', 1)
    h2 += 'Reports'; rest = 'At ' + rest
    m = hero(t(L(s, 15)))
    blocks = ''.join(f'<div class="card"><h3>{t(L(s,a).rstrip(":"))}</h3>{p(L(s,a+1))}</div>' for a in (17, 19, 21, 23))
    m += f'''<section class="section"><div class="wrap"><div class="prose"><h2>{t(h2)}</h2>{p(rest)}
{todo('The intro says three exclusive sample reports, but four are listed.', 'open')}</div>
<div class="grid g2" style="margin-top:1.5rem">{blocks}</div></div></section>'''
    targets = ['/site-viability-report-sample', '/marketing-report-sample', '/best-sites-report-sample', '/competition-report-sample']
    m += '<section class="section alt"><div class="wrap"><div class="grid g4">'
    for a, tg in zip((25, 27, 29, 31), targets):
        m += f'<div class="card"><h3>{t(L(s,a))}</h3><div class="actions">{btn(L(s,a+1), tg)}</div></div>'
    m += '</div></div></section>'
    why = re.split(r'(?<=[.!])(?=[A-Z][A-Za-z ]+:)', L(s, 34))
    items = []
    for w in why:
        k, v = w.split(':', 1)
        items.append(f'<strong>{t(k)}:</strong> {t(v)}')
    m += f'''<section class="section"><div class="wrap prose"><h2>{t(L(s,33))}</h2><ul class="check">{''.join(f'<li>{x}</li>' for x in items)}</ul>
<h2>{t(L(s,35))}</h2>{p(L(s,36))}</div></section>'''
    finish(title_of(s, 'Sample Reports'), desc_of(s), m)

SAMPLES = [('best-sites-report-sample', 'sZobEUyu2FoPFeWiim6r', None),
           ('site-viability-report-sample', '3Kazn9X8UQxcuFR636rY', None),
           ('marketing-report-sample', 'IpZ30XZ7nD68ltQf6s4z', None),
           ('quick-view-report-sample', 'GPjnEHRH42zStlqVylhe', 'hidden'),
           ('competition-report-sample', 'KSVqxwblXOTO880qRZyj', 'GHL side: after submit, this form sends people to the Best Sites sample PDF, not the Competition sample. Fix in GHL.')]
def samples():
    for slug, fid, note in SAMPLES:
        begin('/' + slug)
        h = L(slug, 15)
        fl = None
        extra = ''
        if note == 'hidden':
            fl = flag_hidden('Only linked from the hidden Quick View page.')
        elif note:
            extra = todo(note)
        m = hero(t(h)) + f'<section class="section"><div class="wrap prose">{extra}{ghl_form(fid, h + " form")}</div></section>'
        finish(title_of(slug, h), desc_of(slug, h), m, flag=fl)

def page_dental():
    begin('/dental-demographics')
    s = 'dental-demographics'
    fl = flag_hidden()
    m = hero(t(L(s, 15)), t(L(s, 16)))
    m += f'''<section class="section"><div class="wrap split"><div class="prose">{p(L(s,17))}{p(L(s,18))}
<h2>{t(L(s,19))}</h2>{p(L(s,20))}</div><div>{img('67adf6c345496e764b44a6b3.jpg', 'Smiling dentist in a dental office')}</div></div></section>
<section class="section alt"><div class="wrap"><h2 class="center">{t(L(s,21))}</h2><div class="grid g2">
<div class="card">{img('67adf42190796256c5f5834a.jpg', 'Best Sites Report', 'thumb')}<h3>{t(L(s,22))}</h3>{p(L(s,23))}<div class="actions">{btn(L(s,24), '/best-sites-report')}</div></div>
<div class="card">{img('67adf5a6dd8c5c69890b2d05.jpg', 'Practice Site Viability Report', 'thumb')}<h3>{t(L(s,25))}</h3>{p(L(s,26))}<div class="actions">{btn(L(s,27), '/site-viability-report')}</div></div>
</div></div></section>
<section class="section"><div class="wrap prose"><h2>{t(L(s,28))}</h2><p>{t(L(s,29))} {todo('Download and episode counts are live claims and look dated. Confirm or remove.', 'open')}</p>{p(L(s,30))}
<div class="badges"><a href="{SPOTIFY}" target="_blank" rel="noopener">{img('67adf9f516725e5ab4fc8ddf.png', 'Listen on Spotify')}</a>
<a href="{APPLE}" target="_blank" rel="noopener">{img('67adffc74478e192700f4248.png', 'Apple Podcasts')}</a>
<a class="btn ghost ext" href="{YT_FOOTER}" target="_blank" rel="noopener">YouTube</a></div></div></section>'''
    finish(title_of(s, 'Dental Demographics'), desc_of(s), m, flag=fl)

POD_VIDEOS = {292: 'DLRUQ0ugVMA', 291: None, 290: 'UBmlxksls5Q', 289: 'yDTjof2sIII', 288: 'CTvdj7PVWN4', 287: 'axQAnZh-mDg',
  286: 'iJBQwi3FZtA', 285: 'vAhCjC1FjzM', 284: '7ULHhxkbkiw', 283: 'zq0joirpLTI', 282: 'vjwg3XhGbzM', 281: 'viiWr4cWQp0',
  280: 'nlNjbWqcYLI', 279: 'TDBOGw668-8', 278: '-2zQNXdhd70', 277: 'CYyRiZRHZNA', 276: 'nqmaNhJOiXc', 275: 'NiB5TKiOHbo',
  274: '-bZQ7BynbIY', 273: 'FhkavTfclCA', 272: '_bGqGG8tm08', 271: '16DU0Jx_ecs', 270: 'McF2OJSkCjE', 269: 'QecVd90QOtA',
  267: 'wsF8FJCLh_c', 266: 'Ss6_O-VOw_w', 265: 'XMz4_FLpz24', 264: 'qQPcW9m-LBo', 263: 'Ajlet_7dyGw', 262: 'SOe8DMw4LyQ',
  261: 'DvF14ZfnMiw', 260: 'pW22JzGUgCI', 259: None, 258: 'U0CoXJR5r64', 257: 'fGMEBqRBmtA', 256: 'eA-TMrL2k5k',
  255: 'N-hRgnoCTaw', 254: 'Fb7rAIPV-Sk', 253: 'dQ5GwwFDlj4', 252: 'RlPfnmyHmLs', 251: 'IZ12MUzc5Sg', 250: '3C4HgTNXL_g',
  249: 'xSOmNkxfv-4', 248: 'I6izLXOwo0w', 247: 'r3OThTZjXXQ', 246: None, 245: 'oFVZ4Hq597k', 244: 'cQzjwIWogX4',
  243: '-5IWzS1YPL8', 242: 'XU3aCGGqd0Q', 241: 'nWK35tnBi_0', 240: 'KZ_RXp6GKKU', 239: 'pc-P1Fhfvkc', 238: 'e-7VHUjtcCs',
  237: '7OVQE2H9pZI', 236: 'ybneRcOrQU0', 235: 'TIItjpf3z1c', 234: 'Bp7-fbmG_BI', 233: 'jC1rbHxh2XI', 232: 'uPmHTgDKQAk',
  231: 'skgTEmW1YKw', 230: 'DsEiipV3GfU'}
WRONG = {291: 'the Episode 290 video', 259: 'the Episode 258 video', 246: 'the Episode 247 video'}

def episodes():
    eps, cur = [], None
    for l in body('podcast'):
        mm = re.match(r'Episode (\d+): (.*)', l.strip())
        if mm:
            cur = [int(mm.group(1)), mm.group(2), []]; eps.append(cur)
        elif cur and l.strip():
            cur[2].append(l.strip())
    return eps

def page_podcast():
    begin('/podcast')
    eps = episodes()
    m = hero('The Perfect Place to Put a Practice Podcast', '',
             actions=f'<div class="badges"><a href="{APPLE}" target="_blank" rel="noopener">{img("67adffc74478e192700f4248.png", "Apple Podcasts")}</a><a href="{SPOTIFY}" target="_blank" rel="noopener">{img("67adf9f516725e5ab4fc8ddf.png", "Listen on Spotify")}</a></div>')
    m += f'''<section class="section"><div class="wrap split"><div><h2>Our Most Recent Episode</h2><p class="meta">(10/14/2026)</p></div>
<div>{lite('0QxDdSgI0VY', 'Play the most recent episode')}</div></div></section>
<section class="section alt"><div class="wrap"><h2>Previous Podcast Episodes</h2>'''
    nums = [e[0] for e in eps]
    for n, title, desc in eps:
        vid = POD_VIDEOS.get(n)
        if n in WRONG:
            media = todo(f'Correct video needed: on live this episode plays {WRONG[n]}.')
        elif vid:
            media = lite(vid, f'Play Episode {n} video')
        else:
            media = todo('Video could_not_verify.')
        extra = ''
        if n in (257, 258):
            extra = todo('Episodes 257 and 258 share the same description on live.', 'open')
        m += f'<article class="episode"><div>{media}</div><div><h3>{t("Episode %d: %s" % (n, title))}</h3>{"".join(p(d) for d in desc)}{extra}</div></article>'
    TODOS.append(('/podcast', 'CEO call, pending Gavin', 'CEO call, pending Gavin: the Episode 278 title is kept as published (decided). verify.sh copy check flags it once, by design.'))
    if 268 not in nums:
        m += f'<p style="margin-top:1rem">{todo("Episode 268 is missing from the live list.", "open")}</p>'
    m += '</div></section>'
    finish(title_of('podcast', 'Podcast'), 'The Perfect Place to Put a Practice podcast from Doctor Demographics with Scott McDonald and Mike Green.', m)
    return eps

BLOGS = [('relocate-or-revamp', '68b5e065419f89ab7b17b8f3.jpg'), ('big-city-exodus', '68ae36a93ba6188b15e093ae.jpg'),
         ('places-with-promise-2026', '68a862537dc6b074cb6ee577.jpg'), ('kiss-of-death-locations-for-2026', '689bba15b52dae7d965071d5.jpg'),
         ('launch-smart-5-demographic-factors-for-your-new-practice', '6892773400987beaf980e0fc.jpg'), ('demographic-marketing', '67b50b86aea6db7f0ba29683.jpg')]

def blog_index():
    begin('/blog')
    s = 'blog'
    lines = [x.strip() for x in body(s)]
    m = hero(t(lines[0]))
    m += '<section class="section"><div class="wrap"><div class="grid g3">'
    i = 1
    for slug, im in BLOGS:
        title, exc = lines[i], lines[i + 1]
        j = i + 3; cats = []
        while not re.match(r'[A-Z][a-z]+ \d\d, \d{4}', lines[j]):
            cats.append(lines[j].rstrip(' ,')); j += 1
        date, rt = lines[j], lines[j + 2]
        i = j + 3
        m += (f'<div class="card">{img(im, title, "thumb")}<p class="meta">{t(", ".join(cats))} | {t(date)} | {t(rt)}</p>'
              f'<h3>{t(title)}</h3>{p(exc)}<div class="actions"><a href="{u("/blog/b/" + slug)}">...more</a></div></div>')
        BLOGMETA[slug] = (title, cats, date, rt)
    m += '</div></div></section>'
    finish(title_of(s, 'Blog'), desc_of(s), m, flag=flag_hidden('The blog is not linked from the live menu.'))
BLOGMETA = {}

ALLOWED = {'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'li', 'strong', 'b', 'em', 'i', 'a', 'blockquote', 'br', 'img', 'table', 'thead', 'tbody', 'tr', 'td', 'th'}
def clean_post(slug):
    so = BeautifulSoup(open(os.path.join(DATA, 'blog', slug + '.html')).read(), 'lxml')
    root = so.find(id='blogPostContent')
    for c in root.find_all(string=lambda x: isinstance(x, Comment)):
        c.extract()
    for c in root.find_all(attrs={'data-code-embed-container': True}):
        src = re.search(r'src="([^"]+)"', c.get('data-content', ''))
        new = ''
        if src:
            sv = src.group(1)
            yt = re.search(r'youtube\.com/embed/([\w-]+)', sv)
            if yt:
                new = lite(yt.group(1), 'Play the episode video')
            elif 'libsyn.com' in sv:
                new = f'<iframe class="audio" src="{sv}" title="Podcast audio player" loading="lazy" scrolling="no"></iframe>'
        c.replace_with(BeautifulSoup(new, 'html.parser') if new else '')
    for sp in list(root.find_all(attrs={'data-cfemail': True})):
        enc = sp['data-cfemail']; k = int(enc[:2], 16)
        sp.replace_with(NavigableString(''.join(chr(int(enc[i:i + 2], 16) ^ k) for i in range(2, len(enc), 2))))
    first_h1 = True
    for tag in list(root.find_all(True)):
        if getattr(tag, 'decomposed', False) or tag.parent is None:
            continue
        if tag.name == 'h1':
            if first_h1:
                tag.decompose(); first_h1 = False; continue
            tag.name = 'h2'
        if tag.name in ('a',) and tag.get('class') and 'lite' in tag.get('class'):
            continue
        if tag.parent and tag.parent.name == 'a' and 'lite' in (tag.parent.get('class') or []):
            continue
        if tag.name == 'iframe' and 'audio' in (tag.get('class') or []):
            continue
        if tag.name not in ALLOWED:
            tag.unwrap(); continue
        keep = {}
        if tag.name == 'a' and tag.get('href'):
            h = tag['href']
            if '/cdn-cgi/l/email-protection#' in h:
                enc = h.split('#', 1)[1]; k = int(enc[:2], 16)
                h = 'mailto:' + ''.join(chr(int(enc[i:i + 2], 16) ^ k) for i in range(2, len(enc), 2))
            if h.lower().rstrip('/') == 'http://kff.org':
                CHANGES.append((CUR['path'], 'link fix', h, 'https://www.kff.org'))
                h = 'https://www.kff.org'
            if 'example.com' in h:
                CHANGES.append((CUR['path'], 'placeholder domain link removed (CEO call)', h, '(text kept, link removed)'))
                tag.unwrap(); continue
            mm = re.match(r'https?://(www\.)?doctordemographics\.com(/[^?#]*)?', h)
            if mm:
                pth = (mm.group(2) or '/').rstrip('/') or '/'
                h = u(pth) if pth in KEEP_PATHS else O(pth)
            keep['href'] = h
            if h.startswith('http'):
                keep['target'] = '_blank'; keep['rel'] = 'noopener'
        if tag.name == 'img':
            keep = {'src': tag.get('src', ''), 'alt': fx(tag.get('alt', '')), 'loading': 'lazy'}
        tag.attrs = keep
    for sn in list(root.find_all(string=True)):
        if isinstance(sn, NavigableString) and sn.strip():
            v = fx(str(sn))
            if 'during an on-site consultation with a struggling practice' in v:
                CHANGES.append((CUR['path'], 'CEO call, pending Gavin', 'during an on-site consultation with a struggling practice', 'while consulting with a struggling practice'))
                v = v.replace('during an on-site consultation with a struggling practice', 'while consulting with a struggling practice')
            if v.strip() == 'KFF.org':
                v = v.replace('KFF.org', 'www.kff.org')
            sn.replace_with(v)
    for tag in root.find_all(['p', 'h2', 'h3', 'li']):
        if not tag.get_text(strip=True) and not tag.find(['img', 'iframe', 'a']):
            tag.decompose()
    return root.decode_contents()

def blog_posts():
    for slug, im in BLOGS:
        begin('/blog/b/' + slug)
        title, cats, date, rt = BLOGMETA[slug]
        key = 'blog__b__' + slug
        content = clean_post(slug)
        try:
            bio = ln(key, 'Coming from a marketing background')
        except KeyError:
            bio = ''
        m = f'''<section class="section"><div class="wrap prose post"><p><a href="{u('/blog')}">Articles and Podcasts</a></p>
{img(im, title)}<h1>{t(title)}</h1><p class="meta">{t(", ".join(cats))} | {t(date)} | {t(rt)}</p>
{content}
{('<p>' + todo('CEO call, pending Gavin: one sentence reworded so it no longer refers to the removed on-location report. It now reads: The idea came to me years ago while consulting with a struggling practice in Washington.', 'CEO call, pending Gavin') + '</p>') if slug == 'demographic-marketing' else ''}
<div class="card" style="margin-top:2rem"><h3>Mike Green</h3>{p(bio) if bio else ''}
{todo('The header banners on blog posts show a different man labeled Micheal Green than the Mike Green photo used elsewhere. could_not_verify who is pictured.', 'open')}</div>
<p style="margin-top:1.5rem"><a href="{u('/blog')}">Back to Blog</a></p></div></section>'''
        TODOS.append((CUR['path'], 'note', 'Live canonical points to a placeholder domain (GHL blog setting). Preview canonical uses doctordemographics.com.'))
        finish(title_of(key, title), desc_of(key), m, flag=flag_hidden('The blog is not linked from the live menu.'))

def page_contact():
    begin('/contact')
    m = hero('Contact Us')
    m += f'''<section class="section"><div class="wrap split"><div class="grid">
<div class="card"><h2 style="font-size:var(--text-lg)">Contact Us by Phone</h2><p><a href="{PHONE_TEL}"><strong>{PHONE}</strong></a></p></div>
<div class="card"><h2 style="font-size:var(--text-lg)">Contact Us by Email</h2><p><a href="mailto:{EMAIL}"><strong>{EMAIL}</strong></a></p></div></div>
<div>{img('67b8a4a9f4c6849f1db0854b.jpg', 'Doctor Demographics: our team is ready to help')}</div></div></section>'''
    finish(title_of('contact', 'Contact Us'), desc_of('contact'), m)

def legal(slug, h1):
    begin('/' + slug)
    lines = [x.strip() for x in body(slug)[2:] if x.strip()]
    paras, buf = [], ''
    for x in lines:
        buf = (buf + ' ' + x).strip() if buf else x
        if re.search(r'[.:?!\u201d")]$', x):
            paras.append(buf); buf = ''
    if buf:
        paras.append(buf)
    out = ''
    for x in paras:
        mm = re.match(r'^([A-Z][A-Za-z/ ]{2,40}):\s(.*)', x)
        if mm:
            out += f'<p><strong>{t(mm.group(1))}:</strong> {t(mm.group(2))}</p>'
        else:
            out += p(x)
    sub = body(slug)[1].strip()
    m = hero(t(h1)) + f'<section class="section"><div class="wrap prose"><h2>{t(sub)}</h2>{out}</div></section>'
    finish(title_of(slug, h1), desc_of(slug), m, lead=False)

def page_webinars():
    begin('/webinars')
    s = 'webinars'
    fl = flag_hidden('Also dated: the listed webinars were Sep 24 and Oct 1, 2025.')
    m = hero(t(L(s, 15) + ' ' + L(s, 16)), t(L(s, 17)))
    cards = [(20, 21, '/webinar-cincinnati', '9ba39d25-b30f-46b7-a6d9-5e1bde1c3641.jpg', 'Cincinnati riverfront bridge'),
             (23, 24, '/webinar-austin', '75cc39c2-9d4f-4271-8ea7-35d58df5df5f.jpg', 'Painted bull sculpture in Austin')]
    m += f'<section class="section"><div class="wrap"><h2>{t(L(s,18))}</h2><h3>{t(L(s,19))}</h3><div class="grid g2">'
    for h, d, tg, im, alt in cards:
        m += f'<div class="card">{img(im, alt, "thumb")}<h3>{t(L(s,h))}</h3>{p(L(s,d))}<div class="actions">{btn(L(s,22), O(tg))}</div></div>'
    m += f'</div><p style="margin-top:1rem">{todo("Both webinar dates have passed (2025). Update or retire.", "open")}</p></div></section>'
    finish(title_of(s, 'Weekly Webinar Series'), desc_of(s), m, flag=fl)

def page_partner():
    begin('/partner')
    s = 'partner'
    fl = flag_hidden()
    m = hero(t(L(s, 15) + ' ' + L(s, 16)), t(L(s, 17)), actions=f'<div class="btn-row">{btn(L(s,18), "#apply", "gold")}</div>')
    m += f'''<section class="section"><div class="wrap split"><div class="prose"><h2>{t(L(s,19))}</h2><h3>{t(L(s,20))}</h3><h3>{t(L(s,21))}</h3>{ul(L(s,22,26))}
{todo('Live shows a client quote image here (signed, about referring to Doctor Demographics for over 25 years). Left out under the no testimonials rule. Keep it?', 'open')}</div>
<div>{img('29969d22-aa40-4db8-86dd-0ada7c5bd70a.jpg', 'Business partners joining hands')}</div></div></section>
<section class="section alt" id="apply"><div class="wrap prose"><h2>{t(L(s,27))}</h2>{ghl_form('mUncEfheN1LfzFqe03QM', 'Partner Program Application', 760)}
{todo('GHL side: the form footer Privacy Policy and Terms links point to a placeholder domain. Fix in GHL.')}</div></section>'''
    finish(title_of(s, 'Partners'), desc_of(s), m, flag=fl)

def page_book():
    begin('/book')
    s = 'book'
    fl = flag_hidden('Also dated: says the book is expected December 2024.')
    m = hero(t(L(s, 15)))
    m += f'''<section class="section"><div class="wrap split"><div>{img('67095a97de5f5d41d9cfa18d.jpg', 'Dental Marketing Mastery book cover')}</div>
<div class="prose"><h2>{t(L(s,16))}</h2><p>{t(L(s,17))} {todo('Dated: publication was expected December 2024. The blog says the book is on Amazon now. Update or retire.', 'open')}</p>
{ghl_form('s7hud67kdZaPKZmuYwDE', 'Join Book Prelaunch', 420)}</div></div></section>'''
    finish(title_of(s, 'Book'), desc_of(s), m, flag=fl)

def page_mike():
    begin('/mike')
    m = hero(t(L('mike', 15))) + f'<section class="section"><div class="wrap">{ghl_booking("D2uIZQR7ouj2vEbarqac")}</div></section>'
    finish("Mike Green's Calendar | Doctor Demographics", "Book a time with Mike Green from Doctor Demographics.", m, flag=flag_hidden(), lead=False)

# ---------------------------------------------------------------- stubs
REDIRECTS = [('/home-9727', '/', 'duplicate home page'),
             ('/best-sites-report-general-form', O('/best-sites-report-form'), 'duplicate form page'),
             ('/site-viabilty-report-general-form', O('/site-viabilty-report-form'), 'duplicate form page'),
             ('/marketing-report-order-2598', O('/marketing-report-order'), 'duplicate order page with no products (left out per CEO call)'),
             ('/getsocial-102622', O('/getsocial'), 'duplicate training page'),
             ('/on-site-report', '/reports', 'removed product (Gavin decision). Target /reports is a CEO call, pending Gavin')]

def redirect_stub(src, dst, why):
    begin(src)
    target = u(dst)
    m = f'''<section class="section"><div class="wrap prose"><h1>This page has moved</h1>
<p>Stand in for a planned 301 redirect from {('this old URL' if src == '/on-site-report' else '<code>' + src + '</code>')} to <a href="{a_(target)}">{html.escape(dst)}</a> ({html.escape(why)}).</p>
<p>The real 301 is set at go live on the host. This preview uses a meta refresh.</p>{('<p>' + todo('CEO call, pending Gavin: this old URL redirects to ' + dst + '.', 'CEO call, pending Gavin') + '</p>') if src == '/on-site-report' else ''}</div></section>'''
    finish('Redirecting | Doctor Demographics', 'Redirect stand in.', m, lead=False,
           extra_head=f'<meta http-equiv="refresh" content="0; url={a_(target)}">', canonical=LIVE + (dst if dst.startswith('/') and dst != '/' else '/') if not dst.startswith('http') else dst)

def ghl_rows():
    rows = list(csv.DictReader(open('/workspace/apex_hq/doctor-demographics/redo-2026-10/urls.csv')))
    return [r for r in rows if r['plan'] == 'ghl' and r['path'].startswith('/')]

def ghl_stub(r):
    path = r['path']
    begin(path)
    title = r['title'] if r['title'] not in ('(empty)', '') else path.strip('/')
    m = f'''<section class="section"><div class="wrap prose"><h1>{t(title)}</h1>
<p>This page stays in GoHighLevel. It is not rebuilt in the new site. Site buttons link straight to it.</p>
<ul class="plain"><li>Live today: <a class="ext" href="{LIVE + path}" target="_blank" rel="noopener">{LIVE + path}</a></li>
<li>Planned after cutover: {ORDER_FUTURE + path} {todo('Needs the order.doctordemographics.com subdomain set up in GHL at cutover. No DNS change made.', 'open')}</li></ul>
<p class="note">{t(r['type'])}. Please do not submit anything on the live page.</p></div></section>'''
    finish(fx(title) + ' | GHL page', 'GoHighLevel page link out.', m, lead=False, canonical=LIVE + path)

# ---------------------------------------------------------------- notes and docs
GHL_BUGS = [
    'The /comp-report-form form sends people on to /site-viability-order instead of /comp-report-order.',
    'The Competition sample form sends people to the Best Sites sample PDF.',
    '/marketing-report-order-2598 shows no products (duplicate order page).',
    'The State Briefing thank you page (/order-complete-state-briefing) shows a blank sender name.',
    'GHL form footers link Privacy Policy and Terms to a placeholder domain.',
    'Blog post canonicals point to a placeholder domain (GHL blog setting).',
    'Unknown paths on doctordemographics.com redirect to prodemographics.com.',
    'Podcast page plays the wrong video on Episodes 291, 259 and 246.',
    'The home page "most recent episode" is stale (Episode 252).',
    'The Site Viability form says "Comparision".',
    'The form for the removed on-location report (HVWSBqGPEBYVxwgBzyRG) shows a raw label "common.other_option". The product is removed from the new site (Gavin decision), so this only matters while the live page stays up.',
]

def dedupe_todos():
    seen = {}
    for pg, kind, text in TODOS:
        key = (kind, text)
        seen.setdefault(key, []).append(pg)
    return seen

def notes_page():
    begin('/preview-notes')
    seen = dedupe_todos()
    def rows(filter_fn):
        r = ''
        for (kind, text), pages in seen.items():
            if not filter_fn(kind):
                continue
            pg = 'every page' if len(set(pages)) > 15 else ', '.join(sorted(set(pages)))
            r += f'<tr><td>{html.escape(kind)}</td><td>{html.escape(text.replace("CEO call, pending Gavin: ", ""))}</td><td>{html.escape(pg)}</td></tr>'
        return r
    ch = {}
    for pg, kind, b, a in CHANGES:
        ch.setdefault((kind, b, a), set()).add(pg)
    chrows = ''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(b)}</td><td>{html.escape(a)}</td><td>{html.escape(", ".join(sorted(p)) if len(p) < 15 else "many pages")}</td></tr>'
                     for (k, b, a), p in ch.items() if not k.startswith(('dash', 'no-cost', 'emoji', 'Gavin', 'placeholder', 'CEO call')))
    ndash = sum(1 for c in CHANGES if c[1].startswith(('dash', 'emoji')))
    nph = len({c[2] for c in CHANGES if c[1].startswith('placeholder')})
    ngav = len({(c[2], c[3]) for c in CHANGES if c[1].startswith('Gavin')})
    nfree = len({(c[2], c[3]) for c in CHANGES if c[1].startswith('no-cost')})
    m = hero('Preview notes')
    m += f'''<section class="section"><div class="wrap prose">
<p>Preview of doctordemographics.com, rebuilt from the live copy for review. Every page is noindexed and the robots file blocks crawling. Canonicals point to the live URLs.
Forms and calendars are the live GoHighLevel embeds and order buttons go to the live GoHighLevel pages, so please do not submit anything.</p>
<h2>Decided by Gavin</h2><ul>
<li>The removed on-location report: removed from the preview (no page, link, or listing).</li>
<li>Experience: "since 1983" replaces every year count. Scott McDonald is shown as founder, now retired.</li>
<li>YouTube: {html.escape(YT_FOOTER)} everywhere.</li></ul>
<h2>Decisions made by the APEX CEO</h2><p>Each one is a CEO call, pending Gavin/Mike review.</p>
<div class="tbl-wrap"><table class="tbl"><tr><th>Kind</th><th>Item</th><th>Pages</th></tr>{rows(lambda k: k == 'ceo')}</table></div>
<h2>CEO calls (Oct 29), pending Gavin</h2><div class="tbl-wrap"><table class="tbl"><tr><th>Kind</th><th>Item</th><th>Pages</th></tr>{rows(lambda k: k == 'CEO call, pending Gavin')}</table></div>
<h2>Open questions</h2><div class="tbl-wrap"><table class="tbl"><tr><th>Kind</th><th>Item</th><th>Pages</th></tr>{rows(lambda k: k == 'open')}</table></div>
<h2>Other TODOs</h2><div class="tbl-wrap"><table class="tbl"><tr><th>Kind</th><th>Item</th><th>Pages</th></tr>{rows(lambda k: k not in ('ceo', 'open', 'CEO call, pending Gavin'))}</table></div>
<h2>GoHighLevel side bugs (not changed, report only)</h2><ul>{''.join(f'<li>{html.escape(b)}</li>' for b in GHL_BUGS)}</ul>
<h2>Redirect plan (stand in pages)</h2><div class="tbl-wrap"><table class="tbl"><tr><th>From</th><th>To</th><th>Why</th></tr>
{''.join(f'<tr><td><a href="{u(s)}">{s}</a></td><td>{html.escape(d)}</td><td>{html.escape(w)}</td></tr>' for s, d, w in REDIRECTS)}</table></div>
<h2>Copy changes</h2><p>{ndash} dash and emoji fixes (builder copy rule) and {nfree} no cost wording changes (CEO call, pending Gavin/Mike review) and {ngav} experience wording changes (Gavin decision) are listed in CHANGES.md (in the repo, not published). {nph} links to a placeholder domain were removed from blog posts (CEO call).</p>
<div class="tbl-wrap"><table class="tbl"><tr><th>Kind</th><th>Before</th><th>After</th><th>Pages</th></tr>{chrows}</table></div>
<h2>Copy exception</h2><p>The Episode 278 podcast title keeps its published wording (decided, CEO call, pending Gavin), so the copy lint flags it once by design.</p>
</div></section>'''
    finish('Preview notes | Doctor Demographics', 'Review notes.', m, lead=False, canonical=LIVE + '/')

def page_404():
    home = open(os.path.join(SITE, 'index.html')).read()
    begin('/')
    m = hero('Page not found', 'That page does not exist in this preview.', actions=f'<div class="btn-row"><a class="btn gold" href="{PREVIEW_BASE}">Go to the home page</a></div>')
    CUR['depth'] = 0
    finish('Page not found | Doctor Demographics', 'Page not found.', m, lead=False)
    PAGES.pop()
    src = open(os.path.join(SITE, 'index.html')).read()
    open(os.path.join(SITE, 'index.html'), 'w').write(home)
    s404 = src.replace('<head><meta charset="utf-8">', f'<head><meta charset="utf-8">\n<base href="{PREVIEW_BASE}">', 1)
    open(os.path.join(SITE, '404.html'), 'w').write(s404)

def docs(eps):
    seen = dedupe_todos()
    with open(os.path.join(ROOT, 'TODO.md'), 'w') as f:
        f.write('# Doctor Demographics preview: open items\n\n## Decided by Gavin (Oct 29, 2026)\n\n'
                '- On-Site Demographic Marketing Report removed from the preview: no page, link, or listing.\n'
                '- "Since 1983" replaces every year count (company founded 1983). Scott McDonald shown as founder, now retired.\n'
                f'- YouTube: {YT_FOOTER} everywhere.\n\n')
        for label, fn in (('CEO calls, pending Gavin/Mike review', lambda k: k == 'ceo'),
                          ('CEO calls (Oct 29), pending Gavin', lambda k: k == 'CEO call, pending Gavin'),
                          ('Open questions', lambda k: k == 'open'),
                          ('Other TODOs', lambda k: k not in ('ceo', 'open', 'CEO call, pending Gavin'))):
            f.write(f'## {label}\n\n')
            for (kind, text), pages in seen.items():
                if fn(kind):
                    pg = 'every page' if len(set(pages)) > 15 else ', '.join(sorted(set(pages)))
                    f.write(f'- [{kind}] {text.replace("CEO call, pending Gavin: ", "")} ({pg})\n')
            f.write('\n')
        f.write('## GoHighLevel side bugs (report only, nothing changed)\n\n' + ''.join(f'- {b}\n' for b in GHL_BUGS))
    with open(os.path.join(ROOT, 'CHANGES.md'), 'w') as f:
        f.write('# Copy changes versus live\n\n| Page | Kind | Before | After |\n|---|---|---|---|\n')
        for pg, kind, b, a in CHANGES:
            f.write(f'| {pg} | {kind} | {b.replace("|", "/")} | {a.replace("|", "/")} |\n')
    with open(os.path.join(ROOT, 'REDIRECTS.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['from', 'to', 'type', 'reason'])
        for s, d, why in REDIRECTS:
            w.writerow([s, (LIVE + d) if d.startswith('/') else d, '301', why])
    with open(os.path.join(SITE, 'robots.txt'), 'w') as f:
        f.write('User-agent: *\nDisallow: /\n')
    open(os.path.join(SITE, '.nojekyll'), 'w').close()
    with open(os.path.join(ROOT, 'README.md'), 'w') as f:
        f.write(f'''# doctordemographics.com preview

Static preview of the Doctor Demographics site, built from the live copy for review.
Preview: {PREVIEW_BASE}

- Branch `preview` only. Not for go live.
- Every page has noindex, nofollow, and robots.txt blocks crawling. Canonicals point to doctordemographics.com.
- Forms and calendars embed the live GoHighLevel widgets by ID. Order and training buttons link to the live GHL pages.
  ORDER_BASE in build/gen.py switches to {ORDER_FUTURE} at cutover.
- Build: `python3 build/gen.py` then `build/verify.sh docs`
- Published folder: `docs/` (Pages source: branch `preview`, path `/docs`). build/, TODO.md, CHANGES.md, REDIRECTS.csv and this README are not published.
- Open items: TODO.md. Copy changes: CHANGES.md. Redirect plan: REDIRECTS.csv.
- Pages: {len(PAGES)} generated. Podcast episodes listed: {len(eps)}.
''')

# ---------------------------------------------------------------- main
KEEP_PATHS = {'/', '/about', '/reports', '/best-sites-report', '/site-viability-report', '/marketing-report', '/comp-report',
              '/telephone-consultation', '/quick-view-report', '/state-briefings', '/sample-reports',
              '/best-sites-report-sample', '/site-viability-report-sample', '/marketing-report-sample', '/quick-view-report-sample',
              '/competition-report-sample', '/dental-demographics', '/podcast', '/blog', '/contact', '/privacy-policy', '/eula',
              '/webinars', '/partner', '/book', '/mike'} | {'/blog/b/' + b for b, _ in BLOGS}

if __name__ == '__main__':
    page_home(); page_about(); reports_page(); products(); sample_hub(); samples(); page_dental()
    eps = page_podcast(); blog_index(); blog_posts(); page_contact()
    legal('privacy-policy', 'Privacy Policy'); legal('eula', 'Terms and Conditions')
    page_webinars(); page_partner(); page_book(); page_mike()
    for s_, d_, w_ in REDIRECTS:
        redirect_stub(s_, d_, w_)
    for r in ghl_rows():
        ghl_stub(r)
    notes_page(); page_404(); docs(eps)
    print('pages', len(PAGES), 'todos', len(TODOS), 'unique', len(dedupe_todos()), 'changes', len(CHANGES), 'episodes', len(eps))
