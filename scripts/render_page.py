"""Render a kb .svx page to static HTML the way the runbook layout shows it.

The export ships no build setup, so this mirrors runbook.svelte, Callout, RenderStamp,
ProblemSplit (problems.ts) and desk-ref.ts for the one page that needs them.
Usage: python3 scripts/render_page.py src/routes/kb/incidents/4471-split/+page.svx out.html
"""
import datetime as dt, glob, html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'src/lib/data'

def fnv1a(text, seed):
    h = seed & 0xFFFFFFFF
    for ch in text.encode('utf-16-le').decode('utf-16-le'):
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h

def desk_ref(signature):
    t = signature.strip()
    a, b = fnv1a(t, 0x811C9DC5), fnv1a(t, 0x9E3779B9)
    bits = (a << 8) | (b & 0xFF)
    alphabet = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
    out = ''
    for _ in range(8):
        out = alphabet[bits & 31] + out
        bits >>= 5
    return f'DR-{out[:4]}-{out[4:]}'

DAY_FIRST = {'de-DE', 'es-ES', 'en-GB', 'nl-NL', 'cs-CZ', 'it-IT', 'fr-FR', 'pl-PL', 'pt-PT', 'da-DK', 'en-IE'}
HINT = {'booking-v2': 'DD/MM/YYYY', 'booking-v3': 'MM/DD/YYYY'}
WHAT = {
    'parser': 'shared parser reads day-first dates month first',
    'hint': 'booking-v3 form hints MM/DD/YYYY, reads day first',
    'one-day': 'date moves by one day (time zone / DST)',
    'unplaced': 'no tenant on file',
}

def split_ticket(ticket):
    tenants = {t['handle']: t for t in (json.load(open(f)) for f in glob.glob(str(DATA / 'tenants/*.json')))}
    one_day = json.load(open(DATA / 'desk-notes.json'))['oneDayMove']
    reports = list({r['id']: r for r in json.load(open(DATA / 'reports-4471.json'))}.values())
    merged = [r for r in reports if r['mergedInto'] == ticket]
    by = {}
    for r in merged:
        t = tenants.get(r['tenant'])
        if r['id'] in one_day:
            p = 'one-day'
        elif not t or t['locale'] not in DAY_FIRST:
            p = 'unplaced'
        else:
            p = 'hint' if r['channel'] == 'form' and HINT[t['form']].startswith('MM') else 'parser'
        by.setdefault(p, []).append(r)
    rows = []
    for p, rs in by.items():
        days = sorted(r['receivedAt'][:10] for r in rs)
        rows.append(dict(problem=p, reports=len(rs), tenants=len({r['tenant'] for r in rs}), first=days[0], last=days[-1]))
    rows.sort(key=lambda r: -r['reports'])
    return len(merged), rows

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)

def problem_split(ticket, issues):
    merged, rows = split_ticket(ticket)
    body = ''.join(
        f'<tr><td><code>{r["problem"]}</code></td><td>{WHAT[r["problem"]]}</td><td>{r["reports"]}</td>'
        f'<td>{r["tenants"]}</td><td>{r["first"]} → {r["last"]}</td><td>'
        + (f'<a href="{issues[r["problem"]]}">#{issues[r["problem"]].rsplit("/", 1)[1]}</a>' if r['problem'] in issues else 'none yet')
        + '</td></tr>' for r in rows)
    word = 'problem' if len(rows) == 1 else 'problems'
    return (f'<p class="sum"><strong>{merged}</strong> reports merged into #{ticket} · <strong>{len(rows)}</strong> {word}</p>'
            '<table><thead><tr><th>problem</th><th>what it is</th><th>reports</th><th>tenants</th><th>seen</th><th>ticket</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')

def render(src, now):
    text = Path(src).read_text()
    _, fm, rest = text.split('---\n', 2)
    meta = dict(re.findall(r"^(\w+): '?(.*?)'?$", fm, re.M))
    script = re.search(r'<script>(.*?)</script>', rest, re.S).group(1)
    issues = dict(re.findall(r"'?([\w-]+)'?: '(https://[^']+)'", script))
    rest = re.sub(r'<script>.*?</script>', '', rest, flags=re.S)
    out, para, items = [], [], []
    def flush():
        if para: out.append(f'<p>{inline(" ".join(para))}</p>'); para.clear()
        if items: out.append('<ul>' + ''.join(f'<li>{inline(i)}</li>' for i in items) + '</ul>'); items.clear()
    lines = iter(rest.strip().splitlines())
    for line in lines:
        s = line.strip()
        if not s: flush(); continue
        if s.startswith('<Callout'):
            flush(); kind = re.search(r'kind="(\w+)"', s); inner = []
            for l in lines:
                if l.strip().startswith('</Callout>'): break
                inner.append(l.strip())
            out.append(f'<aside class="{kind.group(1) if kind else "note"}">{inline(" ".join(inner))}</aside>')
        elif s.startswith('<ProblemSplit'):
            flush(); out.append(problem_split(int(re.search(r'ticket=\{(\d+)\}', s).group(1)), issues))
        elif s.startswith('<RenderStamp'):
            flush(); sig = meta.get('signature')
            out.append(f'<p class="stamp">desk ref <b>{desk_ref(sig)}</b></p>' if sig else
                       '<p class="stamp missing">no desk ref: this page isn\'t signed (no <code>signature</code> in its frontmatter)</p>')
        elif s.startswith('## '):
            flush(); out.append(f'<h2>{inline(s[3:])}</h2>')
        elif s.startswith('- '):
            if para: flush()
            items.append(s[2:])
        elif items:
            items[-1] += ' ' + s
        else:
            para.append(s)
    flush()
    reviewed = meta['reviewed']
    age = (now - dt.date.fromisoformat(reviewed)).days
    stale = age > 180
    banner = f'<p class="banner">Nobody has re-read this page in {age} days. Check it against the live views before you rely on it.</p>' if stale else ''
    css = Path(__file__).with_name('runbook.css').read_text()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(meta["title"])} · support kb</title><style>{css}</style></head>
<body><div class="kb">
<header><a class="crumb" href="/kb">support desk · kb</a><h1>{html.escape(meta["title"])}</h1>
<p class="meta"><span>owner <b>{html.escape(meta["owner"])}</b></span><span class="status {meta["status"]}">{meta["status"]}</span>
<span class="{"stale" if stale else ""}">reviewed {reviewed} · {age} days ago{" · stale" if stale else ""}</span></p></header>
{banner}<main>
{chr(10).join(out)}
</main>
<footer>Pages are written by people. Tables and charts are built from data at render time.</footer>
</div></body></html>
'''

if __name__ == '__main__':
    Path(sys.argv[2]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[2]).write_text(render(sys.argv[1], dt.date.today()))
