"""Bootstrap -> Tailwind primitive codemod (run per bucket, verify each batch)."""
import re, sys, io

# component name -> (module, imported-symbol)  [None module => handled specially]
MAP = {
    'Button': ('@/components/ui/button', 'Button'),
    'Badge': ('@/components/ui/badge', 'Badge'),
    'Alert': ('@/components/ui/alert', 'Alert'),
    'Spinner': ('@/components/ui/spinner', 'Spinner'),
    'ProgressBar': ('@/components/ui/progress', 'Progress'),
    'Container': ('@/components/ui/grid', 'Container'),
    'Row': ('@/components/ui/grid', 'Row'),
    'Col': ('@/components/ui/grid', 'Col'),
    'Card': ('@/components/ui/card', 'Card'),  # subcomponents handled specially
    'Table': ('@/components/ui/table', 'Table'),
}

def inject_class(attrs, classes):
    """Add `classes` to a tag's className="..." (static string) or create one."""
    m = re.search(r'className="([^"]*)"', attrs)
    if m:
        return attrs[:m.start(1)] + classes + ' ' + m.group(1) + attrs[m.end(1):]
    return ' className="' + classes + '"' + attrs

def transform_tag_attrs(src, tag, fn):
    """Apply fn to the attribute-string of every <tag ...> opening tag.
    `tag` is a literal element name (may contain '.')."""
    out = []
    i = 0
    pat = re.compile(r'<' + re.escape(tag) + r'(?=[\s/>])')
    while True:
        m = pat.search(src, i)
        if not m:
            out.append(src[i:]); break
        start = m.start()
        out.append(src[i:start])
        # find matching '>' accounting for nested {} and quotes
        j = m.end()
        depth = 0; q = None
        k = j
        while k < len(src):
            c = src[k]
            if q:
                if c == q: q = None
            elif c in '"\'': q = c
            elif c == '{': depth += 1
            elif c == '}': depth -= 1
            elif c == '>' and depth == 0:
                break
            k += 1
        attrs = src[j:k]
        out.append('<' + tag + fn(attrs))
        i = k
    return ''.join(out)

# regex-tag callers now pass literal names

def process(path):
    s = io.open(path, encoding='utf-8').read()
    m = re.search(r"import\s*\{([^}]*)\}\s*from 'react-bootstrap';\n", s)
    if not m:
        print("  no rb import:", path); return
    names = [n.strip() for n in m.group(1).split(',') if n.strip()]
    unknown = [n for n in names if n not in MAP]
    if unknown:
        print("  SKIP (unmapped:", unknown, ")", path); return

    # ProgressBar -> Progress (tag rename)
    if 'ProgressBar' in names:
        s = re.sub(r'<ProgressBar\b', '<Progress', s)
        s = re.sub(r'</ProgressBar>', '</Progress>', s)

    # Spinner: drop animation="..." and variant="..."
    if 'Spinner' in names:
        s = transform_tag_attrs(s, 'Spinner',
            lambda a: re.sub(r'\s+(animation|variant)="[^"]*"', '', a))

    # Badge: bg= -> variant=, drop text=
    if 'Badge' in names:
        def badge_fix(a):
            a = re.sub(r'\bbg=', 'variant=', a)
            a = re.sub(r'\s+text=\{[^{}]*\}', '', a)
            a = re.sub(r'\s+text="[^"]*"', '', a)
            return a
        s = transform_tag_attrs(s, 'Badge', badge_fix)

    card_syms = set()
    if 'Card' in names:
        # Card.Body -> CardBody (Bootstrap-faithful p-4)
        if 'Card.Body' in s:
            s = s.replace('<Card.Body', '<CardBody').replace('</Card.Body>', '</CardBody>')
            card_syms.add('CardBody')
        # Card.Header -> CardHeader (block header w/ bottom border)
        if 'Card.Header' in s:
            s = transform_tag_attrs(s, 'Card.Header',
                lambda a: inject_class(a, 'block space-y-0 border-b border-border px-4 py-2'))
            s = s.replace('<Card.Header', '<CardHeader').replace('</Card.Header>', '</CardHeader>')
            card_syms.add('CardHeader')
        if 'Card.Footer' in s:
            s = transform_tag_attrs(s, 'Card.Footer',
                lambda a: inject_class(a, 'block border-t border-border px-4 py-2'))
            s = s.replace('<Card.Footer', '<CardFooter').replace('</Card.Footer>', '</CardFooter>')
            card_syms.add('CardFooter')
        if 'Card.Title' in s:
            s = s.replace('<Card.Title', '<CardTitle').replace('</Card.Title>', '</CardTitle>')
            card_syms.add('CardTitle')
        # Card.Text -> <p>, Card.Subtitle -> <p>
        s = s.replace('<Card.Text', '<p').replace('</Card.Text>', '</p>')
        s = s.replace('<Card.Subtitle', '<p').replace('</Card.Subtitle>', '</p>')
        # Card.Img -> <img> with rounded top
        if 'Card.Img' in s:
            s = transform_tag_attrs(s, 'Card.Img', lambda a: inject_class(a, 'rounded-t-xl'))
            s = s.replace('<Card.Img', '<img')

    # Build grouped imports
    by_mod = {}
    for n in names:
        if n == 'Card':
            # only import the root <Card> symbol if it's actually used
            if re.search(r'<Card[\s/>]', s):
                by_mod.setdefault('@/components/ui/card', set()).add('Card')
            continue
        mod, sym = MAP[n]
        by_mod.setdefault(mod, set()).add(sym)
    for sym in card_syms:
        by_mod.setdefault('@/components/ui/card', set()).add(sym)
    lines = []
    for mod in sorted(by_mod):
        syms = ', '.join(sorted(by_mod[mod]))
        lines.append(f"import {{ {syms} }} from '{mod}';")
    s = s[:m.start()] + '\n'.join(lines) + '\n' + s[m.end():]

    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print("  migrated:", path)

if __name__ == '__main__':
    for p in sys.argv[1:]:
        process(p)
