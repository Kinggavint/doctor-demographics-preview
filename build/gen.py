#!/usr/bin/env python3
"""Doctor Demographics preview generator.
Renders every page from build/data (live text captured Oct 29, 2026) into <path>/index.html.
Run from the repo root: python3 build/gen.py
"""
import html, json, os, re, csv, shutil
from bs4 import BeautifulSoup, NavigableString, Comment
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icons import ICONS  # Lucide, ISC License (build/LICENSE-lucide.txt)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Production build (launch-doctordemographics): DD_PROD=1 python3 build/gen.py -> dist/ (served by CloudFront at cutover).
PROD = os.environ.get('DD_PROD') == '1'
DATA = os.path.join(ROOT, 'build', 'data')
# Published output lives in docs/ (GitHub Pages source). build/ and the review docs stay at the repo root, unpublished.
SITE = os.path.join(ROOT, 'dist' if PROD else 'docs')
LIVE = 'https://doctordemographics.com'
# TODO cutover: switch ORDER_BASE to https://order.doctordemographics.com once the GHL subdomain exists.
ORDER_FUTURE = 'https://order.doctordemographics.com'
ORDER_BASE = ORDER_FUTURE if PROD else 'https://doctordemographics.com'
PREVIEW_BASE = 'https://kinggavint.github.io/doctor-demographics-preview/'
GHL_PATHS = ['/getsocial', '/accessdso', '/apexchat', '/ppschedule', '/best-sites-report-form', '/comp-report-form',
             '/quick-view-report-form', '/site-viabilty-report-form', '/best-sites-report-order', '/comp-report-order',
             '/marketing-report-order', '/quick-view-report-order', '/site-viability-order', '/telephone-consultation-order',
             '/order-complete', '/order-complete-telephone']
# Hidden on live (decided): unlinked, noindex, left out of the sitemap in production.
PROD_NOINDEX = {'/partner', '/book', '/mike', '/quick-view-report', '/quick-view-report-sample', '/dental-demographics'}
PHONE, PHONE_TEL = '(844) 704-0499', 'tel:+18447040499'
EMAIL = 'support@doctordemographics.com'
APPLE = 'https://podcasts.apple.com/us/podcast/doctor-demographics-podcast/id800840123'
APPLE_HOME = 'https://podcasts.apple.com/us/podcast/doctordemographics-podcast/id800840123'
SPOTIFY = 'https://open.spotify.com/show/5y2MWJfrbhhp8z3fC0AnVT'
AMAZON_BOOK = 'https://www.amazon.com/dp/B0F89QHSWP'
# Podcast playlist on the YouTube channel (newest episode first). The embed always opens on the newest item, no API key.
POD_PLAYLIST = 'PLxxIgza2sWVsRp5kidLl5D3J9jr6uBsEr'
YT_FOOTER = 'https://www.youtube.com/@doctordemographicslive2702'
SOCIALS = [('Facebook', 'https://www.facebook.com/doctordemograhics'),
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
    if PROD:
        return ''
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

def img(name, alt, cls='', lazy=True, w=None, wh=None):
    c = f' class="{cls}"' if cls else ''
    lz = ' loading="lazy"' if lazy else ''
    d = f' width="{wh[0]}" height="{wh[1]}"' if wh else ''
    return f'<img{c} src="{u("assets/img/" + name)}" alt="{a_(alt)}"{d}{lz}>'

def p(s):
    return f'<p>{t(s)}</p>'

def ul(items, cls='check'):
    return f'<ul class="{cls}">' + ''.join(f'<li>{x if x.startswith("<") else t(x)}</li>' for x in items) + '</ul>'

def lite(vid, alt):
    return (f'<a class="lite" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">'
            f'<img src="https://img.youtube.com/vi/{vid}/hqdefault.jpg" alt="{a_(alt)}" loading="lazy"></a>')

def latest_episode():
    """Newest podcast episode, picked client side by YouTube: the playlist embed opens on the first (newest) item."""
    return (f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/videoseries?list={POD_PLAYLIST}" '
            f'title="Latest podcast episode" allow="accelerometer; encrypted-media; picture-in-picture; fullscreen" '
            f'allowfullscreen loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe></div>')

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
            + ('' if PROD else f'<p class="embed-note">This is the live GoHighLevel form ({fid}). Preview reviewers: please do not submit it.</p>') + '</div>')

def ghl_booking(cid):
    return (f'<div class="form-embed"><iframe src="https://api.leadconnectorhq.com/widget/booking/{cid}" '
            f'id="{cid}_booking" title="Booking calendar" scrolling="no" style="min-height:900px;overflow:hidden"></iframe>'
            f'<script src="https://link.msgsndr.com/js/form_embed.js"></script>'
            + ('' if PROD else f'<p class="embed-note">This is the live GoHighLevel booking calendar ({cid}). Preview reviewers: please do not book a slot.</p>') + '</div>')

# ---------------------------------------------------------------- icons
# One Lucide icon per report, used everywhere a report is named (Gavin, Oct 30).
REPORT_ICON = {'telephone-consultation': 'phone', 'marketing-report': 'trending-up', 'best-sites-report': 'map-pin',
               'site-viability-report': 'clipboard-check', 'comp-report': 'trophy', 'quick-view-report': 'eye'}
SAMPLE_OF = {'best-sites-report-sample': 'best-sites-report', 'site-viability-report-sample': 'site-viability-report',
             'marketing-report-sample': 'marketing-report', 'competition-report-sample': 'comp-report',
             'quick-view-report-sample': 'quick-view-report'}

def icon(name, cls='ico'):
    """Decorative inline SVG (aria-hidden). Lucide, ISC License."""
    return (f'<span class="{cls}" aria-hidden="true"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" focusable="false">{ICONS[name]}</svg></span>')

def ricon(slug, cls='ico'):
    return icon(REPORT_ICON[slug.strip('/')], cls)

# ---------------------------------------------------------------- layout
NAV_REPORTS = [('Best Sites Report', '/best-sites-report'), ('Site Viability Report', '/site-viability-report'),
               ('Marketing Report', '/marketing-report'), ('Competition Report', '/comp-report'),
               ('Telephone Consultation', '/telephone-consultation')]

def begin(path):
    path = path.strip('/')
    CUR['path'] = '/' + path if path else '/'
    CUR['depth'] = len(path.split('/')) if path else 0

PREVIEW_BAR = '<div class="preview-bar">Preview build for review only. Not the live site. Forms and order buttons connect to the live GoHighLevel system, so please do not submit them. <a href="{notes}">Review notes and open items</a></div>\n'

def header():
    cur = CUR['path']
    def nl(label, href):
        ac = ' aria-current="page"' if href == cur else ''
        return f'<a href="{u(href)}"{ac}>{label}</a>'
    dd = ''.join(f'<a href="{u(h)}">{ricon(h, "ico sm")}{l}</a>' for l, h in NAV_REPORTS)
    return f'''<a class="skip" href="#main">Skip to content</a>
{'' if PROD else PREVIEW_BAR.format(notes=u('/preview-notes'))}<div class="topbar"><div class="wrap"><a href="{PHONE_TEL}">{PHONE}</a><a href="mailto:{EMAIL}">{EMAIL}</a></div></div>
<header class="site-header"><div class="wrap">
<a class="logo" href="{u('/')}"><img src="{u('assets/img/logo.svg')}" alt="Doctor Demographics" width="226" height="55"></a>
<button class="menu-toggle" aria-expanded="false" aria-controls="nav" onclick="var n=document.getElementById('nav');n.classList.toggle('open');this.setAttribute('aria-expanded',n.classList.contains('open'))">Menu</button>
<nav class="nav" id="nav" aria-label="Main">
{nl('Home', '/')}{nl('About', '/about')}
<div class="dd"><a href="{u('/reports')}">Demographic Reports</a><div class="dd-menu">{dd}</div></div>
{nl('Sample Reports', '/sample-reports')}{nl('Podcast', '/podcast')}{nl('Blog', '/blog')}
<a class="ext" href="{O('/getsocial')}" target="_blank" rel="noopener">Training</a>
{nl('Contact', '/contact')}
<a class="apex" href="{u('/apex-ai-labs')}"{' aria-current="page"' if cur == '/apex-ai-labs' else ''}><img src="{u('assets/img/apexai-logo-nav.svg')}" alt="Apex AI Labs" width="70" height="33"></a>
</nav></div></header>'''

def _q(x):
    return x.strip().strip('"').strip()

def leadership_short():
    """Home only: short blurbs trimmed from the existing client text, plus a link to About."""
    scott = _q(ln('home', 'Demographics is more than')).split(' Markets change')[0]
    mike = _q(ln('home', 'Mike Green is a seasoned')).split(' He empowers')[0]
    def blk(im, alt, name, role, txt):
        return (f'<div class="card leader-s">{img(im, alt)}<div><h3>{name}</h3><p class="role">{role}</p>'
                f'<p>{t(txt)}</p><a class="more" href="{u("/about")}">More info<span class="sr-only"> about {name}</span></a></div></div>')
    return f'''<section class="section alt leaders" aria-labelledby="lead-h"><div class="wrap">
<h2 id="lead-h" class="center">Our Leadership</h2>
<div class="grid g2">
{blk('631c160e05c40c6f83ebc915.jpg', 'Scott McDonald', 'Scott McDonald', 'Founder, Doctor Demographics (now retired)', scott)}
{blk('mike_profile_26.jpg', 'Mike Green', 'Mike Green', 'Owner &amp; Lead Demographer, Doctor Demographics', mike)}
</div></div></section>'''

def leadership_full():
    """About page: full width rows, Mike on top, Scott below."""
    scott = _q(ln('home', 'Demographics is more than'))
    mike = _q(ln('home', 'Mike Green is a seasoned'))
    def row(im, alt, name, role, txt, quote):
        body_ = f'<blockquote><p>"{t(txt)}"</p></blockquote>' if quote else p(txt)
        return (f'<article class="card leader-l">{img(im, alt)}<div><h3>{name}</h3><p class="role">{role}</p>{body_}</div></article>')
    return f'''<section class="section alt leaders" aria-labelledby="lead-h"><div class="wrap">
<h2 id="lead-h">Our Leadership</h2>
<div class="leader-stack">
{row('mike_profile_26.jpg', 'Mike Green', 'Mike Green', 'Owner &amp; Lead Demographer, Doctor Demographics', mike, False)}
{row('631c160e05c40c6f83ebc915.jpg', 'Scott McDonald', 'Scott McDonald', 'Founder, Doctor Demographics (now retired)', scott, True)}
</div></div></section>'''

def footer():
    ql = [('Reports', '/reports'), ('Site Viability', '/site-viability-report'), ('Best Sites Report', '/best-sites-report'), ('Competition Report', '/comp-report'),
          ('Telephone Consultation', '/telephone-consultation'), ('Marketing Report', '/marketing-report'), ('Contact Us', '/contact')]
    soc = ''.join(f'<li><a href="{h}" target="_blank" rel="noopener">{n}</a></li>' for n, h in SOCIALS)
    return f'''<footer class="site-footer"><div class="wrap"><div class="cols">
<div><img class="logo" src="{u('assets/img/logo-white.svg')}" alt="Doctor Demographics" loading="lazy" style="height:54px;width:auto;margin-bottom:1rem">
<p>{t('For over 40 years, the Doctor Demographics team have helped thousands of doctors and practice owners select the perfect place to set up their practice.')}</p></div>
<div><h4>Quick Links</h4><ul>{''.join(f'<li><a href="{u(h)}">{ricon(h, "ico sm") if h.strip("/") in REPORT_ICON else ""}{l}</a></li>' for l, h in ql)}</ul></div>
<div><h4>Contact Us</h4><ul><li><a href="{PHONE_TEL}"><strong>{PHONE}</strong></a></li><li><a href="mailto:{EMAIL}"><strong>{EMAIL.replace('@', '<wbr>@')}</strong></a></li></ul></div>
<div><h4>Follow Us</h4><ul>{soc}</ul>
</div>
</div>
<div class="legal"><span>&copy; Copyright 2026. Doctor Demographics, LLC. | All Rights Reserved |</span>
<span><a href="{u('/privacy-policy')}">Privacy Policy</a> | <a href="{u('/eula')}">Terms and Conditions</a></span></div>
</div></footer>'''

FOOTER_TODOS_DONE = False

def finish(title, desc, main, flag=None, lead=False, extra_head='', canonical=None, chrome=True):
    path = CUR['path']
    canon = canonical or (LIVE + ('' if path == '/' else path))
    if path == '/':
        canon = LIVE + '/'
    fl = f'<div class="flag"><div class="wrap">{flag}</div></div>' if flag and not PROD else ''
    robots = 'noindex, nofollow' if (not PROD or path in PROD_NOINDEX) else 'index, follow'
    head = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{a_(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canon}">
<link rel="icon" href="{u('assets/img/68a3b42d10041847e0bead17.png')}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&amp;display=swap">
<link rel="stylesheet" href="{u('css/style.css')}">{extra_head}{head_tags(path, title, desc, main, canon)}
</head><body>'''
    if chrome:
        doc = head + header() + fl + f'<main id="main">{main}</main>' + (leadership_short() if lead and path == '/' else '') + footer() + '</body></html>\n'
    else:
        doc = head + f'<main id="main">{main}</main></body></html>\n'
    if PROD:
        doc = prod_links(doc)
    rel = path.strip('/')
    out = os.path.join(SITE, rel, 'index.html') if rel else os.path.join(SITE, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(doc)
    PAGES.append(path)

# Extra <head> tags (analytics, JSON-LD). Each hook is f(path, title, desc, main, canon) -> str; empty string means nothing added.
HEAD_HOOKS = []

def head_tags(path, title, desc, main, canon):
    return ''.join(h(path, title, desc, main, canon) for h in HEAD_HOOKS)

def prod_links(doc):
    """Production: links to GHL pages go straight to the order subdomain (skips the 301 hop)."""
    alt = '|'.join(re.escape(p) for p in sorted(GHL_PATHS, key=len, reverse=True))
    doc = re.sub(r'https://(?:www\.)?doctordemographics\.com(' + alt + r')(?=["/?#])', lambda m_: ORDER_FUTURE + m_.group(1), doc)
    # Pages are served as /<path>/ (CloudFront 301s /<path> to /<path>/), so absolute site links and canonicals use the slash form.
    return re.sub(r'(https://doctordemographics\.com/[A-Za-z0-9_/-]*[A-Za-z0-9_-])(?=["?#])', r'\1/', doc)

def title_of(slug, fallback):
    tt = META.get(slug, {}).get('title') or fallback
    return fx(tt)

def desc_of(slug, fallback=''):
    d = META.get(slug, {}).get('description') or fallback
    return fx(d)

HIDDEN = 'Hidden page on the live site: no navigation link points here. Kept in the preview unlinked and noindexed. Decision pending (keep, update, or retire).'
def flag_hidden(extra=''):
    if extra.startswith('Mike'):
        TODOS.append((CUR['path'], 'hidden page (decided)', extra))
        return f'<strong>Review flag.</strong> Hidden page: no navigation link points here. Kept unlinked and noindexed. {html.escape(extra)}'
    TODOS.append((CUR['path'], 'hidden page', 'Hidden on live, kept unlinked. Keep, update, or retire? ' + extra))
    return f'<strong>Review flag.</strong> {HIDDEN} {html.escape(extra)}'

def hero(h1, sub='', kicker='', small=True, actions='', ico=''):
    k = f'<p class="kicker">{kicker}</p>' if kicker else ''
    if ico:
        h1 = f'{ico}<span>{h1}</span>'
    s = f'<p>{sub}</p>' if sub else ''
    return f'<section class="hero{" small" if small else ""}"><div class="wrap">{k}<h1{' class="with-ico"' if ico else ''}>{h1}</h1>{s}{actions}</div></section>'
# Stock photo credits (list-page headers only; Gavin request Oct 30 2026). Cropped square, resized to 680x680 (2x the 340px slot), WebP q80.
#  podcast-microphone-unsplash-mikey-rogers.webp: Photo by Mikey Rogers (@mikeyrogerstv) on Unsplash,
#    https://unsplash.com/photos/a-close-up-of-a-microphone-in-a-dark-room-DEqW7Kn_OUs  (Unsplash License, https://unsplash.com/license)
#  blog-stethoscope-notes-pexels-thirdman.webp: Photo by Thirdman on Pexels,
#    https://www.pexels.com/photo/a-medical-person-using-a-laptop-for-research-5327916/  (Pexels License, https://www.pexels.com/license/)
POD_HERO_IMG = ('podcast-microphone-unsplash-mikey-rogers.webp',
                'Close-up of a silver studio condenser microphone lit in deep blue, ready for a podcast recording')
BLOG_HERO_IMG = ('blog-stethoscope-notes-pexels-thirdman.webp',
                 'Overhead view of a desk with a stethoscope and a tablet where a hand takes handwritten notes with a stylus')

def dx_hero(h1, aside='', pre='', after='', cls=''):
    """Navy hero with glow + dot pattern (Reports, Sample Reports, Contact, Podcast, Blog; Gavin redesign Oct 30). Scoped .dx-*.
    pre/after: existing page content shown above/below the h1 (breadcrumb, badges, post meta). cls: extra hero class."""
    a = f'<div class="dx-hero-aside">{aside}</div>' if aside else ''
    c = (" has-aside" if aside else "") + (" " + cls if cls else "")
    return (f'<section class="hero dx-hero{c}"><div class="wrap dx-hero-grid">'
            f'<div class="dx-hero-txt">{pre}<span class="dx-rule" aria-hidden="true"></span><h1>{h1}</h1>{after}</div>{a}</div></section>')

# ---------------------------------------------------------------- pages
# Home "Key Benefits" (Gavin redesign, Oct 30): navy editorial split. Benefit bodies are the live copy verbatim (home.txt 24-27);
# the short headlines only restate each line. No new claims or numbers. Scoped classes: .kb-*.
BENEFITS = (('pen-line', 'Hand-written by specialist demographers'), ('messages-square', 'Live one-on-one follow-up consultation'),
            ('map', 'Thousands of reports, nearly every street'), ('scale', 'Straight answers, good news or bad'))
def benefits_home(s):
    rows = ''.join(
        f'<li class="kb-row"><span class="kb-num" aria-hidden="true">{i:02d}</span>{icon(ic, "ico kb-ico")}'
        f'<div class="kb-txt"><h3>{html.escape(hd, quote=False)}</h3><p>{t(x).replace('/', '/<wbr>')}</p></div></li>'
        for i, ((ic, hd), x) in enumerate(zip(BENEFITS, L(s, 24, 27)), 1))
    return (f'<section class="section kb" aria-labelledby="kb-title"><div class="wrap kb-grid">'
            f'<div class="kb-intro">'
            f'<h2 id="kb-title">{t(L(s,23))}</h2>'
            f'<figure class="kb-fig">{img("a3f4f699-56ba-4b33-ba83-e0f60b7e19f8.jpeg", "Team reviewing findings together around a table")}'
            f'<figcaption class="kb-chip">{icon("messages-square", "ico kb-chip-ico")}<span>Every report includes a live one-on-one follow-up</span></figcaption></figure></div>'
            f'<ol class="kb-list">{rows}</ol></div></section>')

# Home polish (Gavin request Oct 30 2026): navy dx hero with stock photo, raised content cards, navy closing band on the
# existing "Most Popular Demographic Reports" section. Wording, headings, links and meta unchanged. Scoped classes: .home-*.
#  home-doctors-tablet-unsplash-vitaly-gariev.webp: Photo "Two doctors looking at a tablet together" by Vitaly Gariev (@silverkblack) on Unsplash,
#    https://unsplash.com/photos/two-doctors-looking-at-a-tablet-together-2kopEHjST-g  (Unsplash License, https://unsplash.com/license)
#    Cropped 4:3 around both doctors, mild cool colour grade (saturation 0.92) for the navy style, 720x540 WebP q78 (under 60KB).
HOME_HERO_LAZY = False  # hero photo is above the fold (LCP candidate on desktop): load eagerly
HOME_HERO_IMG = ('home-doctors-tablet-unsplash-vitaly-gariev.webp',
                 'Two doctors in white coats reviewing information together on a tablet in a clinic office')

def page_home():
    begin('/')
    s = 'home'
    sub = t(L(s, 17).replace('VETERINARIANS, and optometrists', 'veterinarians, optometrists, and audiologists'))
    CHANGES.append(('/', 'client OEDIT d9e575d', 'VETERINARIANS, and optometrists', 'veterinarians, optometrists, and audiologists'))
    m = dx_hero('Helping doctors find the perfect place to practice',
                img(*HOME_HERO_IMG, 'dx-hero-img home-hero-img', lazy=HOME_HERO_LAZY, wh=(720, 540)),
                after=f'<p>{sub}</p><div class="btn-row">{btn("Order a Demographic Report", "/reports", "gold")}</div>', cls='home-hero')
    m += f'''<section class="section dx-light dx-pull home-s"><div class="wrap"><div class="home-card split"><div class="prose">
<h2>{t(L(s,19))}</h2>{p(L(s,20))}{p(L(s,21))}<div class="btn-row">{btn("Order a Demographic Report", "/reports")}</div></div>
<div>{img('62748d21ea2ab126f720248c.png', 'Doctors and team members smiling')}</div></div></div></section>
{benefits_home(s)}
<section class="section dx-light home-s"><div class="wrap"><div class="home-card split"><div>{img('d584a9f2-537d-4611-ae13-77848e700c56.png', 'Practice owners reviewing plans together')}</div>
<div class="prose"><h2>{t(L(s,28))}</h2>{p(L(s,29))}<div class="btn-row">{btn("Order a Demographic Report", "/reports")}</div></div></div></div></section>
<section class="section home-pod-wrap"><div class="wrap"><div class="home-pod dx-navy split"><div class="prose"><h2>{t(L(s,31))}</h2>{p(L(s,32))}
<div class="btn-row">{btn("Subscribe Here", APPLE_HOME, "gold")}</div><p class="note">Weekly Episode in Your Inbox</p></div>
<div><h3>Here's Our Most Recent Episode:</h3>{latest_episode()}</div></div></div></section>
<section class="section dx-navy home-band"><div class="wrap"><h2 class="center">{t(L(s,36))}</h2><div class="grid g4">'''
    cards = [(39, 40, '/best-sites-report', '64adb6bd1aa4669e1a404704.jpg'), (43, 44, '/site-viability-report', '65258de43fd52c3674559fc6.jpg'),
             (47, 48, '/marketing-report', '68e832bde22f982ba43459c3.jpg'), (51, 52, '/telephone-consultation', '68e833334d2dffc79b33fde1.jpg')]
    for h, d, href, im in cards:
        m += f'<div class="card report-card home-rcard">{ricon(href, "ico xl")}<h3>{t(L(s,h))}</h3>{p(L(s,d))}<div class="actions">{btn("More Infomation", href)}</div></div>'
    m += '</div></div></section>'
    CHANGES.append(('/', 'Gavin design (Oct 30)', 'video thumbnails on report cards', 'report icons'))
    CHANGES.append(('/', 'Gavin design (Oct 30)', 'Key Benefits: 4 small icon cards', 'navy editorial split: photo + numbered benefit rows with short headlines (copy unchanged)'))
    finish(title_of(s, 'Doctor Demographics'), desc_of(s), m, lead=True)

def page_about():
    begin('/about')
    m = hero('About Doctor Demographics', t('For over 40 years, the Doctor Demographics team have helped thousands of doctors and practice owners select the perfect place to set up their practice.'))
    m += leadership_full()
    finish('About Doctor Demographics', 'Meet the leadership team at Doctor Demographics.', m)

PRODUCTS = {
    'best-sites-report': dict(order='/best-sites-report-form', sample='/best-sites-report-sample'),
    'site-viability-report': dict(order='/site-viabilty-report-form', sample='/site-viability-report-sample'),
    'marketing-report': dict(order='#order', sample='/marketing-report-sample'),
    'comp-report': dict(order='/comp-report-form', sample='/competition-report-sample'),
    'telephone-consultation': dict(order='#order', sample=None),
    'quick-view-report': dict(order='/quick-view-report-form', sample='/quick-view-report-sample'),
}
def ohref(slug):
    o = PRODUCTS[slug]['order']
    return o if o.startswith('#') else O(o)

def reports_page():
    begin('/reports')
    s = 'reports'
    m = dx_hero('Demographic Reports', img('635195d6b495690eab7a6fa0.jpg', 'Analyst reviewing a report at a desk', 'dx-hero-img', lazy=False))
    items = [('telephone-consultation', 16, 17), ('site-viability-report', 19, 20), ('marketing-report', 22, 24),
             ('best-sites-report', 26, 28), ('comp-report', 30, 31)]
    m += '<section class="section dx-light"><div class="wrap"><div class="dx-cards dx-5">'
    for slug, h0, d in items:
        title = ' '.join(x.strip() for x in L(s, h0, d - 1))
        acts = btn('More Info', '/' + slug, 'ghost')
        o = PRODUCTS[slug]['order']
        acts += btn('Order a report', ('/' + slug + o) if o.startswith('#') else O(o))
        m += (f'<article class="card report-card dx-card"><div class="dx-card-top">{ricon(slug, "ico xl dx-ico")}</div>'
              f'<div class="dx-card-body"><h3>{t(title)}</h3>{p(L(s,d))}<div class="actions">{acts}</div></div></article>')
    m += f'''</div></div></section>
<section class="section dx-cta-wrap"><div class="wrap"><div class="dx-cta dx-contact-band">
<div class="dx-contact-item">{icon('phone', 'ico dx-gold-ico')}<div><h3>Contact Us by Phone</h3><p><a href="{PHONE_TEL}"><strong>{PHONE}</strong></a></p></div></div>
<div class="dx-contact-item">{icon('mail', 'ico dx-gold-ico')}<div><h3>Contact Us by Email</h3><p><a href="mailto:{EMAIL}"><strong>{EMAIL.replace('@', '<wbr>@')}</strong></a></p></div></div></div></div></section>'''
    CHANGES.append(('/reports', 'client OEDIT d92ae0d', 'card buttons', 'added "Order a report" next to More Info'))
    CHANGES.append(('/reports', 'Gavin design (Oct 30)', 'sample report buttons on each block and the Order a Sample Report button', 'removed; report icons added to all 5 blocks'))
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
    m = hero(t(h1), ico=ricon(slug, 'ico hero-ico'))
    m += f'''<section class="section"><div class="wrap split"><div>{media}{top_extra}</div>
<div class="features"><h2 style="font-size:var(--text-lg)">{t(feat_head)}</h2><div class="price">{price_html}</div>{feats}{feat_extra}
<div class="btn-row">{order_btn}</div>{sample}</div></div></section>
<section class="section alt"><div class="wrap split"><div class="prose"><h2>{t(desc_head)}</h2>{desc_html}
{('<div class="btn-row">' + btn(order_label, ohref(slug)) + '</div>') if order_label and pr['order'].startswith('/') else ''}</div>
<div>{need_html}</div></div></section>{after}'''
    finish(title_of(slug, h1), desc_of(slug), m, flag=flag)

# Written from the Marketing Report video on /marketing-report (GCS 68e83148fd24b5fd49c5f4fb.mp4), per Mike.
MKT_FEATURES = ['Built around your street address or cross streets, so the plan fits your exact site.',
                'Profiles of your local competition and of the population you are most likely to draw from.',
                'Drive time and traffic past your site.',
                'A review of your current website, advertising, and what has been used before.',
                'Fits a practice transition: buying a practice, losing a partner, or taking on a new partner.',
                'Built for your goals, from maintaining your practice to growing dramatically or changing your patient base.',
                'Your patient counts by zip code (no names or addresses) set the real geographic radius around your practice.']

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
            ul(MKT_FEATURES + [L(s, 22)]), L(s, 23), L(s, 24), L(s, 25), ''.join(p(x) for x in L(s, 26, 27)),
            f'<div class="need"><h3>{t(L(s,28))}</h3>{need_list(L(s,29,33))}<p class="note">{t(L(s,34))}</p></div>',
            after=f'<section class="section" id="order"><div class="wrap prose"><h2>{t(L(s,35))}</h2>{p(L(s,36))}{ghl_form("RnzOfCKPUBs3omXWcT7J", "Marketing Report form")}</div></section>',
            feat_extra=todo('Marketing Report features written from the Marketing Report video on this page, as Mike asked. The 20 minute call line is kept from the live page. Please check the wording.', 'Mike decision'))
    CHANGES.append(('/marketing-report', 'Mike decision (features from the page video)', 'Site Viability features list (live)', ' / '.join(MKT_FEATURES)))
    s = 'comp-report'
    begin('/comp-report')
    product(s, L(s, 15), video(FS + '69b8614e9379cf3f4dc0cf65.mp4', 'e12832a2aa8ca86a.jpg', 'Competition Report video'), L(s, 17),
            t(L(s, 18)) + ' ' + todo('Competition price $350 per site (confirmed by Mike), matches the checkout.', 'Mike decision'),
            ul(L(s, 19, 23)), L(s, 24), L(s, 25), L(s, 26), ''.join(p(x) for x in L(s, 27, 29)),
            f'<div class="need"><h3>{t(L(s,31))}</h3>{need_list(L(s,32,35))}<p class="note">{t(L(s,36))}</p></div>',
            feat_extra=todo('One live Order button went to the Site Viability form. Both now go to /comp-report-form.', 'ceo'))
    CHANGES.append(('/comp-report', 'wrong button target fixed (CEO call)', '/site-viabilty-report-form', '/comp-report-form'))
    s = 'telephone-consultation'
    begin('/telephone-consultation')
    price = 'Price: $149'
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
            flag=flag_hidden('Mike: partners only, not for retail. Stays unlisted.'))

def sample_hub():
    begin('/sample-reports')
    s = 'sample-reports'
    intro = L(s, 16).replace('developed three exclusive', 'developed four exclusive')
    CHANGES.append(('/sample-reports', 'Mike decision', 'three exclusive sample reports', 'four exclusive sample reports'))
    h2, rest = intro.split('ReportsAt ', 1)
    h2 += 'Reports'; rest = 'At ' + rest
    covers = (img('67adf42190796256c5f5834a.jpg', 'Best Sites Report cover', 'dx-cover c1', lazy=False)
              + img('67adf5a6dd8c5c69890b2d05.jpg', 'Practice Site Viability Report cover', 'dx-cover c2', lazy=False))
    m = dx_hero(t(L(s, 15)), f'<div class="dx-covers">{covers}</div>')
    targets = ['/site-viability-report-sample', '/marketing-report-sample', '/best-sites-report-sample', '/competition-report-sample']
    rslug = ['site-viability-report', 'marketing-report', 'best-sites-report', 'comp-report']
    # Order links first (Gavin, Oct 30), descriptions below, same icons on both.
    m += '<section class="section dx-light dx-pull"><div class="wrap"><div class="dx-cards dx-4 order-row">'
    labels = []
    for a, tg, rs in zip((25, 27, 29, 31), targets, rslug):
        labels.append((t(L(s, a + 1)), tg))
        m += (f'<article class="card report-card dx-card"><div class="dx-card-top">{ricon(rs, "ico xl dx-ico")}</div>'
              f'<div class="dx-card-body"><h3>{t(L(s,a))}</h3><div class="actions">{btn(labels[-1][0], tg, raw=True)}</div></div></article>')
    m += '</div></div></section>'
    blocks = ''.join(f'<li class="dx-glass">{ricon(rs, "ico dx-gold-ico")}<div><h3>{t(L(s,a).rstrip(":"))}</h3>{p(L(s,a+1))}</div></li>'
                     for a, rs in zip((17, 19, 21, 23), rslug))
    m += f'''<section class="section dx-navy"><div class="wrap"><div class="dx-intro"><h2>{t(h2)}</h2>{p(rest)}</div>
<ol class="dx-glass-grid">{blocks}</ol></div></section>'''
    CHANGES.append(('/sample-reports', 'Gavin design (Oct 30)', 'descriptions above the order links', 'order links at the top, descriptions below, report icons on both'))
    why = re.split(r'(?<=[.!])(?=[A-Z][A-Za-z ]+:)', L(s, 34))
    items = []
    for w, ic in zip(why, ('database', 'sliders-horizontal', 'shield-check')):
        k, v = w.split(':', 1)
        items.append(f'<li class="card dx-why">{icon(ic, "ico xl dx-ico")}<p><strong>{t(k)}:</strong> {t(v)}</p></li>')
    again = ''.join(btn(lb, tg, 'gold', raw=True) for lb, tg in labels)
    m += f'''<section class="section dx-light"><div class="wrap"><h2 class="center">{t(L(s,33))}</h2><ul class="dx-why-grid">{''.join(items)}</ul></div></section>
<section class="section dx-cta-wrap"><div class="wrap"><div class="dx-cta"><div class="dx-cta-txt"><h2>{t(L(s,35))}</h2>{p(L(s,36))}</div>
<div class="dx-cta-btns">{again}</div></div></div></section>'''
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
            fl = flag_hidden('Only linked from the Quick View page (partners only, per Mike).')
        elif note:
            extra = todo(note)
        m = hero(t(h), ico=ricon(SAMPLE_OF[slug], 'ico hero-ico')) + f'<section class="section"><div class="wrap prose">{extra}{ghl_form(fid, h + " form")}</div></section>'
        finish(title_of(slug, h), desc_of(slug, h), m, flag=fl)

def page_dental():
    CHANGES.append(('/dental-demographics', 'Mike decision (update counts)', 'over 250 episodes', 'over 290 episodes'))
    begin('/dental-demographics')
    s = 'dental-demographics'
    fl = flag_hidden('Mike asked for the link: ' + PREVIEW_BASE + 'dental-demographics/ (live: ' + LIVE + '/dental-demographics).')
    m = hero(t(L(s, 15)), t(L(s, 16)))
    m += f'''<section class="section"><div class="wrap split"><div class="prose">{p(L(s,17))}{p(L(s,18))}
<h2>{t(L(s,19))}</h2>{p(L(s,20))}</div><div>{img('67adf6c345496e764b44a6b3.jpg', 'Smiling dentist in a dental office')}</div></div></section>
<section class="section alt"><div class="wrap"><h2 class="center">{t(L(s,21))}</h2><div class="grid g2">
<div class="card">{img('67adf42190796256c5f5834a.jpg', 'Best Sites Report', 'thumb')}<h3 class="with-ico">{ricon('best-sites-report')}<span>{t(L(s,22))}</span></h3>{p(L(s,23))}<div class="actions">{btn(L(s,24), '/best-sites-report')}</div></div>
<div class="card">{img('67adf5a6dd8c5c69890b2d05.jpg', 'Practice Site Viability Report', 'thumb')}<h3 class="with-ico">{ricon('site-viability-report')}<span>{t(L(s,25))}</span></h3>{p(L(s,26))}<div class="actions">{btn(L(s,27), '/site-viability-report')}</div></div>
</div></div></section>
<section class="section"><div class="wrap prose"><h2>{t(L(s,28))}</h2><p>{t(L(s,29).replace('over 250 episodes', 'over 290 episodes').replace('well over 100K downloads', '100K+ downloads'))} {todo('Episode count updated to over 290 (the podcast page numbers episodes up to 292). Download count shown as 100K+ per decision on Oct 30.', 'done')}</p>{p(L(s,30))}
<div class="badges"><a href="{SPOTIFY}" target="_blank" rel="noopener">{img('67adf9f516725e5ab4fc8ddf.png', 'Listen on Spotify')}</a>
<a href="{APPLE}" target="_blank" rel="noopener">{img('67adffc74478e192700f4248.png', 'Apple Podcasts')}</a>
<a class="btn ghost ext" href="{YT_FOOTER}" target="_blank" rel="noopener">YouTube</a></div></div></section>'''
    finish(title_of(s, 'Dental Demographics'), desc_of(s), m, flag=fl)

POD_VIDEOS = {292: 'DLRUQ0ugVMA', 291: '0pK3TDC90V0', 290: 'UBmlxksls5Q', 289: 'yDTjof2sIII', 288: 'CTvdj7PVWN4', 287: 'axQAnZh-mDg',
  286: 'iJBQwi3FZtA', 285: 'vAhCjC1FjzM', 284: '7ULHhxkbkiw', 283: 'zq0joirpLTI', 282: 'vjwg3XhGbzM', 281: 'viiWr4cWQp0',
  280: 'nlNjbWqcYLI', 279: 'TDBOGw668-8', 278: '-2zQNXdhd70', 277: 'CYyRiZRHZNA', 276: 'nqmaNhJOiXc', 275: 'NiB5TKiOHbo',
  274: '-bZQ7BynbIY', 273: 'FhkavTfclCA', 272: '_bGqGG8tm08', 271: '16DU0Jx_ecs', 270: 'McF2OJSkCjE', 269: 'QecVd90QOtA',
  267: 'wsF8FJCLh_c', 266: 'Ss6_O-VOw_w', 265: 'XMz4_FLpz24', 264: 'qQPcW9m-LBo', 263: 'Ajlet_7dyGw', 262: 'SOe8DMw4LyQ',
  261: 'DvF14ZfnMiw', 260: 'pW22JzGUgCI', 259: 'VpVAP_W7sdw', 258: 'U0CoXJR5r64', 257: 'fGMEBqRBmtA', 256: 'eA-TMrL2k5k',
  255: 'N-hRgnoCTaw', 254: 'Fb7rAIPV-Sk', 253: 'dQ5GwwFDlj4', 252: 'RlPfnmyHmLs', 251: 'IZ12MUzc5Sg', 250: '3C4HgTNXL_g',
  249: 'xSOmNkxfv-4', 248: 'I6izLXOwo0w', 247: 'r3OThTZjXXQ', 246: 'BmYjJb1Vgn8', 245: 'oFVZ4Hq597k', 244: 'cQzjwIWogX4',
  243: '-5IWzS1YPL8', 242: 'XU3aCGGqd0Q', 241: 'nWK35tnBi_0', 240: 'KZ_RXp6GKKU', 239: 'pc-P1Fhfvkc', 238: 'e-7VHUjtcCs',
  237: '7OVQE2H9pZI', 236: 'ybneRcOrQU0', 235: 'TIItjpf3z1c', 234: 'Bp7-fbmG_BI', 233: 'jC1rbHxh2XI', 232: 'uPmHTgDKQAk',
  231: 'skgTEmW1YKw', 230: 'DsEiipV3GfU'}
WRONG = {}
# Matched by title on YouTube (Mike): 291 'The Top Southern States to Open a Practice in 2027', 259 'Timing Your Growth: When to Expand To A Second Location',
# 246 'Pros and Cons of Opening a Professional Practice in Southern California'.
# Episode 258 description: the YouTube description of 'Site Selection for Specialists' (U0CoXJR5r64), copied word for word.
DESC_FIX = {258: ['There are some very important factors to consider when selecting a site if you are a specialist. In this video, Mike Green from Doctor Demographics reviews 5 tips you will want to consider when selecting your practice site.']}

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
    badges = f'<div class="badges"><a href="{APPLE}" target="_blank" rel="noopener">{img("67adffc74478e192700f4248.png", "Apple Podcasts", lazy=False)}</a><a href="{SPOTIFY}" target="_blank" rel="noopener">{img("67adf9f516725e5ab4fc8ddf.png", "Listen on Spotify", lazy=False)}</a></div>'
    ptitle = 'The Perfect Place to Put a Practice Podcast'
    m = dx_hero(ptitle, img(*POD_HERO_IMG, 'dx-hero-img dx-portrait', lazy=False, wh=(680, 680)), after=badges)
    m += f'''<section class="section dx-light dx-pull"><div class="wrap"><div class="card dx-feature"><div class="dx-feature-txt">{icon('mic', 'ico xl dx-ico')}<h2>Our Most Recent Episode</h2></div>
<div>{latest_episode()}</div></div></div></section>
<section class="section dx-light dx-eps"><div class="wrap"><h2>Previous Podcast Episodes</h2><div class="dx-ep-list">'''
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
        if n in DESC_FIX:
            CHANGES.append(('/podcast', 'Mike decision (match by title on YouTube)', 'Episode %d description (same as 257 on live)' % n, DESC_FIX[n][0][:90]))
            desc = DESC_FIX[n]
        m += f'<article class="episode card dx-ep"><div class="dx-ep-media">{media}</div><div><h3>{t("Episode %d: %s" % (n, title))}</h3>{"".join(p(d) for d in desc)}{extra}</div></article>'
    TODOS.append(('/podcast', 'CEO call, pending Gavin', 'CEO call, pending Gavin: the Episode 278 title is kept as published (decided). verify.sh copy check flags it once, by design.'))
    if 268 not in nums:
        TODOS.append(('/podcast', 'done', 'Episode 268: numbering gap, left out (decided Oct 30).'))
    m += '</div></div></section>'
    # Closing band (Gavin redesign Oct 30): repeats the page title and the same Apple/Spotify badges, no new copy.
    m += (f'<section class="section dx-cta-wrap"><div class="wrap"><div class="dx-cta"><div class="dx-cta-txt">{icon("mic", "ico dx-gold-ico")}'
          f'<p class="dx-cta-title">{ptitle}</p></div><div class="dx-cta-btns">{badges.replace("<img ", "<img loading=\"lazy\" ")}</div></div></div></section>')
    finish(title_of('podcast', 'Podcast'), 'The Perfect Place to Put a Practice podcast from Doctor Demographics with Scott McDonald and Mike Green.', m)
    return eps

BLOGS = [('relocate-or-revamp', 'banner-mike-68b5e065419f89ab7b17b8f3.jpg'), ('big-city-exodus', 'banner-mike-68ae36a93ba6188b15e093ae.jpg'),
         ('places-with-promise-2026', 'banner-mike-68a862537dc6b074cb6ee577.jpg'), ('kiss-of-death-locations-for-2026', 'banner-mike-689bba15b52dae7d965071d5.jpg'),
         ('launch-smart-5-demographic-factors-for-your-new-practice', 'banner-mike-6892773400987beaf980e0fc.jpg'), ('demographic-marketing', 'banner-mike-67b50b86aea6db7f0ba29683.jpg')]

def blog_index():
    begin('/blog')
    s = 'blog'
    lines = [x.strip() for x in body(s)]
    m = dx_hero(t(lines[0]), img(*BLOG_HERO_IMG, 'dx-hero-img dx-portrait', lazy=False, wh=(680, 680)))
    m += '<section class="section dx-light dx-pull"><div class="wrap"><div class="dx-cards dx-3">'
    i = 1
    for slug, im in BLOGS:
        title, exc = lines[i], lines[i + 1]
        j = i + 3; cats = []
        while not re.match(r'[A-Z][a-z]+ \d\d, \d{4}', lines[j]):
            cats.append(lines[j].rstrip(' ,')); j += 1
        date, rt = lines[j], lines[j + 2]
        i = j + 3
        m += (f'<article class="card dx-card dx-post-card"><div class="dx-post-thumb">{img(im, title, "thumb")}</div><div class="dx-card-body"><p class="meta">{t(", ".join(cats))} | {t(date)} | {t(rt)}</p>'
              f'<h3>{t(title)}</h3>{p(exc)}<div class="actions"><a class="dx-more" href="{u("/blog/b/" + slug)}">...more{icon("arrow-right", "ico")}</a></div></div></article>')
        BLOGMETA[slug] = (title, cats, date, rt)
    m += '</div></div></section>'
    # Closing band (Gavin redesign Oct 30): the podcast title and the same Apple/Spotify badges used on /podcast, no new copy.
    m += (f'<section class="section dx-cta-wrap"><div class="wrap"><div class="dx-cta"><div class="dx-cta-txt">{icon("mic", "ico dx-gold-ico")}'
          f'<p class="dx-cta-title"><a href="{u("/podcast")}">The Perfect Place to Put a Practice Podcast</a></p></div><div class="dx-cta-btns"><div class="badges">'
          f'<a href="{APPLE}" target="_blank" rel="noopener">{img("67adffc74478e192700f4248.png", "Apple Podcasts")}</a><a href="{SPOTIFY}" target="_blank" rel="noopener">{img("67adf9f516725e5ab4fc8ddf.png", "Listen on Spotify")}</a></div></div></div></div></section>')
    CHANGES.append(('/blog', 'Mike decision', 'blog not in the menu', 'Blog added to the main menu'))
    finish(title_of(s, 'Blog'), desc_of(s), m)
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

URL_TXT = re.compile(r'(?:https?://|www\.)[^\s<>"]+|[\w.+-]+@[\w-]+(?:\.[\w-]+)+')

def wbr_urls(html):
    """QA Oct 30: add <wbr> break points to web addresses/emails shown as text in post bodies
    (after 'www.', before '@' and '/'), so narrow screens break there, not mid-word.
    Text nodes only; tags and attributes (href etc.) are untouched; visible text is unchanged."""
    def fix(m):
        x = m.group(0)
        x = x.replace('/', '<wbr>/').replace('@', '<wbr>@')
        return re.sub(r'(?i)\bwww\.', lambda w: w.group(0) + '<wbr>', x)
    parts = re.split(r'(<[^>]*>)', html)
    skip = 0
    for i, part in enumerate(parts):
        if part.startswith('<'):
            tag = re.match(r'</?\s*([a-zA-Z0-9]+)', part)
            if tag and tag.group(1).lower() in ('script', 'style', 'textarea'):
                skip = 0 if part.startswith('</') else 1
            continue
        if not skip:
            parts[i] = URL_TXT.sub(fix, part)
    return ''.join(parts)

def blog_posts():
    for slug, im in BLOGS:
        begin('/blog/b/' + slug)
        title, cats, date, rt = BLOGMETA[slug]
        key = 'blog__b__' + slug
        content = wbr_urls(clean_post(slug))
        try:
            bio = ln(key, 'Coming from a marketing background')
        except KeyError:
            bio = ''
        crumb = f'<p class="dx-crumb"><a href="{u("/blog")}">{icon("arrow-left", "ico")}Articles and Podcasts</a></p>'
        meta = f'<p class="meta">{t(", ".join(cats))} | {t(date)} | {t(rt)}</p>'
        m = dx_hero(t(title), img(im, title, 'dx-hero-img', lazy=False), pre=crumb, after=meta, cls='dx-post-hero')
        m += f'''<section class="section dx-light dx-pull"><div class="wrap"><article class="card dx-article prose post">
{content}
{('<p>' + todo('CEO call, pending Gavin: one sentence reworded so it no longer refers to the removed on-location report. It now reads: The idea came to me years ago while consulting with a struggling practice in Washington.', 'CEO call, pending Gavin') + '</p>') if slug == 'demographic-marketing' else ''}
</article></div></section>
<section class="section dx-cta-wrap"><div class="wrap"><div class="dx-cta dx-author">{img('mike_profile_26.jpg', 'Mike Green', 'dx-avatar')}<div class="dx-author-txt"><h3>Mike Green</h3>{p(bio) if bio else ''}</div>
<p class="dx-cta-btns"><a class="btn gold" href="{u('/blog')}">Back to Blog</a></p></div></div></section>'''
        TODOS.append((CUR['path'], 'note', 'Live canonical points to a placeholder domain (GHL blog setting). Preview canonical uses doctordemographics.com.'))
        finish(title_of(key, title), desc_of(key), m)

def page_contact():
    begin('/contact')
    m = dx_hero('Contact Us')
    m += f'''<section class="section dx-light dx-pull"><div class="wrap split contact dx-contact"><div class="grid">
<a class="card contact-card" href="{PHONE_TEL}">{icon('phone', 'ico xl')}<span><span class="lbl">Contact Us by Phone</span><strong>{PHONE}</strong></span></a>
<a class="card contact-card" href="mailto:{EMAIL}">{icon('mail', 'ico xl')}<span><span class="lbl">Contact Us by Email</span><strong>{EMAIL.replace('@', '<wbr>@')}</strong></span></a></div>
<div class="dx-photo">{img('67b8a4a9f4c6849f1db0854b.jpg', 'Doctor Demographics: our team is ready to help', 'contact-img')}</div></div></section>
<section class="section dx-cta-wrap"><div class="wrap"><div class="dx-cta dx-links-panel"><h2 class="center">Demographic Reports</h2><div class="grid g5 report-links dx-links">
{''.join(f'<a class="card report-link" href="{u(h)}">{ricon(h, "ico lg")}<span>{l}</span></a>' for l, h in NAV_REPORTS)}</div></div></div></section>'''
    CHANGES.append(('/contact', 'Gavin design (Oct 30)', 'two plain text cards', 'phone and email icon cards plus report icon links'))
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

def page_partner():
    begin('/partner')
    s = 'partner'
    fl = flag_hidden('Mike: hide this page for now.')
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
    fl = flag_hidden('Not in the menu. The prelaunch form and the December 2024 date are replaced by the Amazon link Mike sent.')
    m = hero('Dental Marketing Mastery', actions=f'<div class="btn-row">{btn("Buy on Amazon", AMAZON_BOOK, "gold")}</div>')
    m += f'''<section class="section"><div class="wrap split"><div>{img('67095a97de5f5d41d9cfa18d.jpg', 'Dental Marketing Mastery book cover')}</div>
<div class="prose"><h2>Dental Marketing Mastery is available on Amazon.</h2>
<div class="btn-row">{btn("Buy on Amazon", AMAZON_BOOK)}</div></div></div></section>'''
    CHANGES.append(('/book', 'Mike decision', 'prelaunch reserve form (expected December 2024)', 'Buy on Amazon: ' + AMAZON_BOOK))
    finish('Dental Marketing Mastery | Doctor Demographics', desc_of(s), m, flag=fl)

def page_apex_draft():
    """Mike asked for an Apex landing page. DRAFT only: noindex, not in the menu, no claims without a source."""
    begin('/apex-seo-draft')
    fl = ('<strong>DRAFT for review.</strong> Apex landing page requested by Mike. Not in the menu, noindexed. '
          'Every statement needs Apex and Mike sign off before launch. Mike\'s line "Apex is the only SEO company in the world that has that level of demographic detail" '
          'is left out until there is a source for it.')
    TODOS.append(('/apex-seo-draft', 'CEO', 'Apex landing page is a DRAFT: Apex to supply its SEO process, results, pricing and contact path. The "only SEO company in the world" claim stays out until sourced.'))
    m = hero('SEO Zeroed In with Doctor Demographics Data', 'Apex AI Labs uses Doctor Demographics data to focus SEO for its clients on the places and people that matter most to each practice.',
             kicker='Apex AI Labs and Doctor Demographics',
             actions=f'<div class="btn-row">{btn("Visit Apex AI Labs", "https://apexailabs.ai/", "gold")}{btn("See the Demographic Reports", "/reports", "ghost")}</div>')
    m += f'''<section class="section"><div class="wrap split"><div class="prose"><h2>Why demographics matter for SEO</h2>
<p>Search works best when it speaks to the patients who actually live and drive near a practice. Doctor Demographics has studied practice locations since 1983. Apex brings that same local detail to search.</p>
{todo('Apex: describe how the data shapes keywords, location pages and Google Business Profile work. Placeholder copy.', 'CEO')}</div>
<div class="card"><h3>What Doctor Demographics data covers</h3>{ul(['The population around a practice and the patients it is most likely to draw from.',
 'Local competition.', 'Drive time and traffic around a street address.', 'Patient counts by zip code that show the real geographic radius of a practice.'])}
<p class="note">From the Doctor Demographics report pages.</p></div></div></section>
<section class="section alt"><div class="wrap prose"><h2>How it works</h2>{ul(['A Doctor Demographics report defines the area and the patients that matter for the practice.',
 'Apex builds the SEO plan around that area.', 'Results are reviewed against the same local data.'], 'plain')}
{todo('Apex to confirm these steps, and add results or case studies only with a source.', 'CEO')}
<div class="btn-row">{btn("Talk to Apex AI Labs", "https://apexailabs.ai/", "gold")}</div></div></section>'''
    finish('DRAFT: Apex AI Labs SEO with Doctor Demographics Data', 'Draft landing page: Apex AI Labs and Doctor Demographics data for local SEO.', m, flag=fl, lead=False, canonical=PREVIEW_BASE + 'apex-seo-draft/')

# Apex AI Labs page (Gavin request Oct 30 2026). Navy .dx-* style, scoped extras .apx-*. Linked from the menu logo.
#  apex-hero-laptop-stethoscope-unsplash-nci.webp: Photo "Stethoscope and Laptop Computer" by National Cancer Institute (@nci)
#    on Unsplash (photographer Daniel Sone), https://unsplash.com/photos/person-sitting-while-using-laptop-computer-and-green-stethoscope-near-NFvdKIhxYlU
#    (Unsplash License, https://unsplash.com/license). Cropped 4:3, mild cool grade, 720x540 WebP q76 (16KB).
#  Menu logo: build/assets/apexai-logo-full.svg is the original (kept out of docs/, unused on the site) from https://apexailabs.ai/images/apexai-logo-full.svg (280x64).
#    apexai-logo-nav.svg is a compact copy: same dark badge, bolt and wordmark, subline dropped, wordmark stacked on two lines (135x64), text as paths (Inter Bold).
# Gavin's line "the only company in the world with that level of detail" is softened until there is a source (see TODO).
APEX_URL = 'https://apexailabs.ai'
APEX_HERO_IMG = ('apex-hero-laptop-stethoscope-unsplash-nci.webp',
                 'Hands typing on a laptop beside a stethoscope on a desk')

def page_apex_ai_labs():
    begin('/apex-ai-labs')
    TODOS.append(('/apex-ai-labs', 'CEO', 'Gavin\'s line "Apex AI Labs is the only company in the world with that level of detail on its clients, their patients and potential patients" is softened on the page until there is a source for it. Apex and Mike to sign off on the copy.'))
    newtab = '<span class="sr-only"> (opens in a new tab)</span>'
    visit = btn('Visit Apex AI Labs' + newtab, APEX_URL, 'gold', raw=True)
    sub = ('<p>Apex AI Labs harnesses the power of Doctor Demographics. It uses demographic, deep demographic and psychographic '
           'research to direct its SEO and AEO (AI answer) work for healthcare practices.</p>'
           '<p>That means Apex AI Labs starts with an unusual level of detail about each client, their patients and their potential patients.</p>')
    m = dx_hero('Apex AI Labs: marketing guided by Doctor Demographics research',
                img(*APEX_HERO_IMG, 'dx-hero-img', lazy=False, wh=(720, 540)),
                after=f'{sub}<div class="btn-row">{visit}</div>', cls='apx-hero')
    layers = [('database', 'Demographic research', 'Who lives around a practice: the population, ages, incomes and households, and how the area is changing.'),
              ('map-pin', 'Deep demographic research', 'A closer look at the neighborhoods a practice draws from, the competition nearby and how far patients travel.'),
              ('users', 'Psychographic research', 'What local patients value, how they choose a provider and what they look for when they need care.')]
    m += '<section class="section dx-light apx-s"><div class="wrap"><h2 class="center">Three layers of research</h2><div class="dx-cards dx-3 apx-cards">'
    for ic, h, d in layers:
        m += f'<article class="card dx-card"><div class="dx-card-top">{icon(ic, "ico xl dx-ico")}</div><div class="dx-card-body"><h3>{h}</h3><p>{d}</p></div></article>'
    m += '</div></div></section>'
    work = [('monitor-smartphone', 'AI-powered websites', 'Websites built around the patients a practice wants to reach, with pages, wording and services shaped by who lives and searches nearby.'),
            ('search', 'SEO', 'Keywords, location pages and local listings chosen from the research, so search work focuses on the people and places most likely to become patients.'),
            ('sparkles', 'AI answer visibility (AEO)', 'Clear, well organized answers to the questions local patients ask, so AI assistants and answer engines can find, understand and mention the practice.')]
    items = ''.join(f'<li class="card dx-why apx-why">{icon(ic, "ico xl dx-ico")}<h3>{h}</h3><p>{d}</p></li>' for ic, h, d in work)
    m += f'''<section class="section dx-light apx-s"><div class="wrap"><h2 class="center">How the research guides the work</h2>
<p class="center apx-lede">Apex AI Labs builds online visibility for healthcare practices. The research decides where that effort goes.</p><ul class="dx-why-grid">{items}</ul></div></section>'''
    steps = [('clipboard-check', 'Start with the research', 'A Doctor Demographics report maps the area around the practice: who lives there, how it is changing and where the opportunity is.'),
             ('sliders-horizontal', 'Turn it into a plan', 'Apex AI Labs uses the demographic, deep demographic and psychographic findings to choose which patients, services and areas to focus on.'),
             ('trending-up', 'Build and refine', 'Apex AI Labs builds the website, SEO and AI answer work around that plan, then checks it against the same research as the practice grows.')]
    blocks = ''.join(f'<li class="dx-glass">{icon(ic, "ico dx-gold-ico")}<div><h3>{h}</h3><p>{d}</p></div></li>' for ic, h, d in steps)
    m += f'''<section class="section dx-navy"><div class="wrap"><div class="dx-intro"><h2>How it pairs with Doctor Demographics reports</h2>
<p>The reports and the marketing work from the same research, in three short steps.</p></div>
<ol class="dx-glass-grid apx-steps">{blocks}</ol></div></section>
<section class="section dx-cta-wrap"><div class="wrap"><div class="dx-cta apx-cta"><div class="dx-cta-txt"><h2>See what the research can do for your practice</h2>
<p>Learn more about Apex AI Labs, or contact the Doctor Demographics team with your questions.</p></div>
<div class="dx-cta-btns">{visit}{btn('Contact Us', '/contact', 'apx-light')}</div></div></div></section>'''
    finish('Apex AI Labs | Doctor Demographics',
           'Apex AI Labs uses Doctor Demographics research to guide AI-powered websites, SEO and AI answer visibility for healthcare practices.', m)

def page_mike():
    begin('/mike')
    m = hero(t(L('mike', 15))) + f'<section class="section"><div class="wrap">{ghl_booking("D2uIZQR7ouj2vEbarqac")}</div></section>'
    finish("Mike Green's Calendar | Doctor Demographics", "Book a time with Mike Green from Doctor Demographics.", m, flag=flag_hidden('Mike: keep, but stay hidden.'), lead=False)

# ---------------------------------------------------------------- stubs
REDIRECTS = [('/home-9727', '/', 'duplicate home page'),
             ('/best-sites-report-general-form', O('/best-sites-report-form'), 'duplicate form page'),
             ('/site-viabilty-report-general-form', O('/site-viabilty-report-form'), 'duplicate form page'),
             ('/getsocial-102622', O('/getsocial'), 'duplicate training page'),
             ('/on-site-report', '/reports', 'removed product (Gavin decision); target approved by APEX CEO Oct 30'),
             # Old blog posts no longer on the site; still cited by Perplexity (baseline Oct 30). Approved by APEX CEO Oct 30.
             ('/blog/b/places-with-promise-2023', '/blog/b/places-with-promise-2026', 'old blog post; newer edition of same article'),
             ('/blog/b/site-selection-process-for-doctors', '/blog/b/launch-smart-5-demographic-factors-for-your-new-practice', 'old blog post; closest current article on choosing a practice location'),
             ('/blog/b/patient-attitudes-7413', '/blog', 'old blog post; no matching current article')]

def redirect_stub(src, dst, why):
    begin(src)
    target = u(dst)
    m = f'''<section class="section"><div class="wrap prose"><h1>This page has moved</h1>
<p>Stand in for a planned 301 redirect from {('this old URL' if src == '/on-site-report' else '<code>' + src + '</code>')} to <a href="{a_(target)}">{html.escape(dst)}</a> ({html.escape(why)}).</p>
<p>The real 301 is set at go live on the host. This preview uses a meta refresh.</p></div></section>'''
    finish('Redirecting | Doctor Demographics', 'Redirect stand in.', m, lead=False,
           extra_head=f'<meta http-equiv="refresh" content="0; url={a_(target)}">', canonical=LIVE + (dst if dst.startswith('/') and dst != '/' else '/') if not dst.startswith('http') else dst)

def ghl_rows():
    rows = list(csv.DictReader(open('/workspace/apex_hq/doctor-demographics/redo-2026-10/urls.csv')))
    return [r for r in rows if r['plan'] == 'ghl' and r['path'].startswith('/') and r['path'] not in RETIRED and not r['path'].startswith('/webinar-')]

# Retired per Mike (Oct 2026): variants, State Briefing, the 2598 order page, webinars. No stub pages; they fall to the 404.
RETIRED = {'/best-sites-report-medical-form', '/best-sites-report-veterinary-form', '/site-viabilty-report-medical-form',
           '/site-viabilty-report-veterinary-form', '/best-sites-report-medical-order', '/best-sites-report-veterinarian',
           '/best-sites-specialist-order', '/site-viability-report-medical-order', '/site-viability-report-medical-order-form-9361-8813',
           '/site-viability-report-veterinary-order', '/state-briefing-order', '/order-complete-state-briefing',
           '/marketing-report-order-2598', '/state-briefings', '/webinars'}

WHY_R = 'retired per Mike (Oct 2026); target approved by APEX CEO Oct 30'
for _p in sorted(RETIRED) + ['/webinar-austin', '/webinar-broadcast-austin', '/webinar-broadcast-cincinnati', '/webinar-cincinnati',
                             '/webinar-confirmation-austin', '/webinar-confirmation-cincinnati', '/webinar-registration-austin', '/webinar-registration-cincinnati']:
    _d = '/best-sites-report' if _p.startswith('/best-sites') else '/site-viability-report' if _p.startswith('/site-viab') else '/reports'
    REDIRECTS.append((_p, _d, WHY_R))


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
    'Set up order.doctordemographics.com as the funnel domain (Mike approved the name and offered account access).',
    'Telephone Consultation checkout: change $90 to $149 and remove the $75 video upgrade (Mike).',
    'The /comp-report-form form sends people on to /site-viability-order instead of /comp-report-order (Mike: you fix it).',
    'The Competition sample form sends people to the Best Sites sample PDF (Mike: you fix it).',
    'Retire the medical, veterinary and specialist forms, order pages and products (Mike: one price per product).',
    'Delete /marketing-report-order-2598 (Mike: eliminate).',
    'Retire the State Briefing order page, the State Briefing thank you page and the State Briefings product (Mike).',
    'Retire the webinar funnels (/webinar-*) (Mike: remove).',
    'Form footers: point Privacy Policy to https://doctordemographics.com/privacy-policy and Terms to https://doctordemographics.com/eula (Mike).',
    'Blog post canonicals point to a placeholder domain (GHL blog setting).',
    'Unknown paths on doctordemographics.com redirect to prodemographics.com. Mike wants a normal page not found page at cutover.',
    'The Site Viability form says "Comparision".',
    'Podcast page on live still plays the wrong video on Episodes 291, 259 and 246 (fixed in the preview).',
    'The form for the removed on-location report (HVWSBqGPEBYVxwgBzyRG) shows a raw label "common.other_option". Only matters while the live page stays up.',
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
<h2>Decided by Mike</h2><ul>
<li>Competition Report: $350 per site (matches the checkout).</li>
<li>Telephone Consultation: $149. QA saw the GHL checkout showing a single $149 item on Oct 30.</li>
<li>Medical, veterinary and specialist versions, State Briefings, the /marketing-report-order-2598 page and the webinars are retired. Their preview pages are gone.</li>
<li>Quick View Report: partners only, stays unlisted. /mike stays hidden. /partner is hidden for now. The newsletter pop up stays hidden.</li>
<li>Marketing Report features: written from the video on that page.</li>
<li>Sample Reports says four. Site copy drops that word (Mike). About page title: About Doctor Demographics. Since 1983 for the company, no separate count for Mike.</li>
<li>Blog banners now use Mike's usual photo. Logo recreated as SVG from the existing design. Phone and email only, no street address.</li>
<li>Home and podcast pages show the latest episode automatically (the YouTube Podcast playlist, newest first). Episodes 291, 259 and 246 matched by title on YouTube. Episode 258 description from YouTube.</li>
<li>Book: Buy on Amazon. Blog is in the menu. Facebook: {html.escape(SOCIALS[0][1])} (the page name has the typo). Typo fixes kept.</li>
<li>Unknown addresses show a normal page not found page.</li>
<li>Dental Demographics link: <a href="{u('/dental-demographics')}">{PREVIEW_BASE}dental-demographics/</a> (live: {LIVE}/dental-demographics).</li></ul>
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
    base = (LIVE + '/') if PROD else PREVIEW_BASE
    home = open(os.path.join(SITE, 'index.html')).read()
    begin('/')
    links = [('Home', ''), ('Demographic Reports', 'reports/'), ('Sample Reports', 'sample-reports/'), ('Podcast', 'podcast/'), ('Blog', 'blog/'), ('Contact Us', 'contact/')]
    m = hero('Page not found', 'Sorry, we could not find that page. It may have moved or the address may be mistyped.',
             actions=f'<div class="btn-row"><a class="btn gold" href="{base}">Go to the home page</a><a class="btn ghost" href="{base}contact/">Contact us</a></div>')
    m += ('<section class="section"><div class="wrap prose"><h2>Popular pages</h2><ul class="check">'
          + ''.join(f'<li><a href="{base}{h}">{l}</a></li>' for l, h in links)
          + f'</ul><p>Questions? Call <a href="{PHONE_TEL}">{PHONE}</a> or email <a href="mailto:{EMAIL}">{EMAIL}</a>.</p></div></section>')
    CUR['depth'] = 0
    finish('Page not found | Doctor Demographics', 'Page not found.', m, lead=False)
    PAGES.pop()
    src = open(os.path.join(SITE, 'index.html')).read()
    open(os.path.join(SITE, 'index.html'), 'w').write(home)
    s404 = src.replace('<head><meta charset="utf-8">', f'<head><meta charset="utf-8">\n<base href="{base}">', 1)
    if PROD:
        s404 = s404.replace('<meta name="robots" content="index, follow">', '<meta name="robots" content="noindex, follow">', 1)
        s404 = re.sub(r'<link rel="canonical" href="[^"]*">\n?', '', s404, count=1)
    s404 = re.sub(r'\n<script type="application/ld\+json">.*?</script>', '', s404)
    open(os.path.join(SITE, '404.html'), 'w').write(s404)

def docs(eps):
    seen = dedupe_todos()
    with open(os.path.join(ROOT, 'TODO.md'), 'w') as f:
        f.write('# Doctor Demographics preview: open items\n\n## Decided by Gavin (Oct 29, 2026)\n\n'
                '- On-Site Demographic Marketing Report removed from the preview: no page, link, or listing.\n'
                '- "Since 1983" replaces every year count (company founded 1983). Scott McDonald shown as founder, now retired.\n'
                f'- YouTube: {YT_FOOTER} everywhere.\n\n'
                '## Decided by Mike (Oct 29, 2026)\n\n'
                '- Competition Report $350 per site (matches checkout).\n'
                '- Telephone Consultation $149, not $90. GHL checkout product change is on Mike\'s side.\n\n'
                '## Decided by Mike (Doc answers, Oct 30, 2026)\n\n'
                '- Remove the $75 video upgrade, the medical/vet/specialist versions, /marketing-report-order-2598, State Briefings and webinars.\n'
                '- Quick View: partners only, unlisted. /mike stays hidden, /partner hidden, newsletter pop up hidden.\n'
                '- Marketing Report features from the page video. Four sample reports. No "free". About title. Since 1983.\n'
                '- Mike photo in blog banners, SVG logo, phone and email only, latest episode on home, Amazon book link, Blog in menu.\n'
                '- Facebook: https://www.facebook.com/doctordemograhics. Normal 404 page. Apex landing page drafted at /apex-seo-draft (DRAFT, noindex, unlinked).\n\n')
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

def prod_files():
    """Production robots.txt and sitemap.xml (public pages only; hidden pages and redirects left out)."""
    import datetime
    today = datetime.date.today().isoformat()
    # Static assets are committed in docs/ (shared with the preview); copy them into the production folder.
    for d in ('assets', 'css'):
        shutil.copytree(os.path.join(ROOT, 'docs', d), os.path.join(SITE, d), dirs_exist_ok=True)
    urls = [p for p in PAGES if p not in PROD_NOINDEX]
    with open(os.path.join(SITE, 'robots.txt'), 'w') as f:
        f.write(f'User-agent: *\nAllow: /\n\nSitemap: {LIVE}/sitemap.xml\n')
    with open(os.path.join(SITE, 'sitemap.xml'), 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for p in sorted(urls, key=lambda x: (x != '/', x)):
            loc = LIVE + '/' if p == '/' else LIVE + p + '/'
            f.write(f'  <url><loc>{loc}</loc><lastmod>{today}</lastmod></url>\n')
        f.write('</urlset>\n')

# ---------------------------------------------------------------- analytics, Organization JSON-LD, llms.txt
# GA4 web stream "Doctor Demographics site - GA4" (property 312406016, stream 3467154372). Verified from the GA4 Admin API
# data stream list and the gtag config on the old live GHL pages. Production only, so preview visits never reach the property.
GA4_MEASUREMENT_ID = 'G-R78SE578C3'
ORG_ID = LIVE + '/#organization'

def ld(obj):
    """One JSON-LD block. '</' is escaped so text can never close the script tag."""
    return '\n<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + '</script>'

def ga4_tag(path, title, desc, main, canon):
    if not PROD or not GA4_MEASUREMENT_ID:
        return ''
    g = GA4_MEASUREMENT_ID
    return (f'\n<script async src="https://www.googletagmanager.com/gtag/js?id={g}"></script>'
            f"\n<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{g}');</script>")

def organization():
    """Facts shown on the site: footer (legal name, phone, email, socials, Since 1983), About (founder)."""
    return {'@type': 'Organization', '@id': ORG_ID, 'name': 'Doctor Demographics', 'legalName': 'Doctor Demographics, LLC',
            'url': LIVE + '/', 'logo': LIVE + '/assets/img/logo.svg',
            'description': t('Since 1983, the Doctor Demographics team has helped thousands of doctors and practice owners select the perfect place to set up their practice.'),
            'foundingDate': '1983', 'founder': {'@type': 'Person', 'name': 'Scott McDonald'},
            'telephone': PHONE_TEL.replace('tel:', ''), 'email': EMAIL,
            'contactPoint': {'@type': 'ContactPoint', 'telephone': PHONE_TEL.replace('tel:', ''), 'email': EMAIL, 'contactType': 'customer service'},
            'sameAs': [h for _, h in SOCIALS]}

def org_ld(path, title, desc, main, canon):
    if path != '/':
        return ''
    site = {'@type': 'WebSite', '@id': LIVE + '/#website', 'name': 'Doctor Demographics', 'url': LIVE + '/', 'publisher': {'@id': ORG_ID}}
    return ld({'@context': 'https://schema.org', '@graph': [organization(), site]})

HEAD_HOOKS += [ga4_tag, org_ld]

def llms_txt():
    """/llms.txt: plain summary for AI crawlers, facts and prices as shown on the site."""
    def lk(name, path):
        return f'[{name}]({LIVE}{path}/)'
    reports = [('Best Sites Report', '/best-sites-report', 'Report and consultation. Finds the 5 best sites in an area you define (up to 5 counties in the same state), with a 20 minute consultation. Price: $795.'),
               ('Site Viability Report', '/site-viability-report', 'Checks the viability of one practice location before you sign, using 14 contiguous zip codes and drive time radii, with a 20 minute consultation. Price: $495 (discount for multiple sites).'),
               ('Marketing Report', '/marketing-report', 'Research based analysis of a practice brand, marketing tools, competition and clinical offerings. Price: $695.'),
               ('Competition Report', '/comp-report', 'Analysis of the local competition for a professional practice. Price: $350 per site.'),
               ('Telephone Consultation', '/telephone-consultation', 'Live telephone consultation on practice placement, marketing and other challenges. Price: $149.')]
    out = ['# Doctor Demographics', '',
           '> Since 1983, Doctor Demographics has provided demographic and psychographic data and custom reports that help doctors and practice owners (dental, medical, optometry, veterinary) choose the perfect place to put a practice.', '',
           f'Doctor Demographics, LLC. Founder: Scott McDonald (now retired). Owner and Lead Demographer: Mike Green. Phone: {PHONE}. Email: {EMAIL}.', '',
           '## Reports and services', '', f'* {lk("All demographic reports", "/reports")}: overview of every report.']
    out += [f'* {lk(n, p_)}: {d}' for n, p_, d in reports]
    out += ['', '## Learn', '',
            f'* {lk("Sample Reports", "/sample-reports")}: sample pages from each report.',
            f'* {lk("The Perfect Place to Put a Practice Podcast", "/podcast")}: podcast with Scott McDonald and Mike Green. Also on [Apple Podcasts]({APPLE}), [Spotify]({SPOTIFY}) and [YouTube]({YT_FOOTER}).',
            f'* {lk("Blog", "/blog")}: articles on practice locations and demographics by Mike Green.',
            '', '## Company', '',
            f'* {lk("About", "/about")}: leadership team.',
            f'* {lk("Contact", "/contact")}: phone and email.', '']
    txt = '\n'.join(out)
    assert not re.search('[\u2013\u2014]| - |free', txt, re.I), 'llms.txt copy rule'
    open(os.path.join(SITE, 'llms.txt'), 'w').write(txt)


# ---------------------------------------------------------------- main
KEEP_PATHS = {'/', '/about', '/reports', '/best-sites-report', '/site-viability-report', '/marketing-report', '/comp-report',
              '/telephone-consultation', '/quick-view-report', '/sample-reports',
              '/best-sites-report-sample', '/site-viability-report-sample', '/marketing-report-sample', '/quick-view-report-sample',
              '/competition-report-sample', '/dental-demographics', '/podcast', '/blog', '/contact', '/privacy-policy', '/eula',
              '/partner', '/book', '/mike', '/apex-seo-draft', '/apex-ai-labs'} | {'/blog/b/' + b for b, _ in BLOGS}

if __name__ == '__main__':
    page_home(); page_about(); reports_page(); products(); sample_hub(); samples(); page_dental()
    eps = page_podcast(); blog_index(); blog_posts(); page_contact()
    legal('privacy-policy', 'Privacy Policy'); legal('eula', 'Terms and Conditions')
    page_partner(); page_book(); page_mike()
    if not PROD:
        page_apex_draft()  # DRAFT: not shipped to production
    page_apex_ai_labs(); llms_txt()
    if PROD:
        page_404(); prod_files()
    else:
        for s_, d_, w_ in REDIRECTS:
            redirect_stub(s_, d_, w_)
        for r in ghl_rows():
            ghl_stub(r)
        notes_page(); page_404(); docs(eps)
    print('pages', len(PAGES), 'todos', len(TODOS), 'unique', len(dedupe_todos()), 'changes', len(CHANGES), 'episodes', len(eps))
