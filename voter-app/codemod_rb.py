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

# Recognised but rendered as native elements (no import) / handled specially.
SPECIAL = {'Form', 'InputGroup'}

def inject_class(attrs, classes):
    """Add `classes` to a tag's className="..." (static string) or create one."""
    m = re.search(r'className="([^"]*)"', attrs)
    if m:
        return attrs[:m.start(1)] + classes + ' ' + m.group(1) + attrs[m.end(1):]
    return ' className="' + classes + '"' + attrs

def table_fix(a):
    """Convert react-bootstrap <Table striped bordered hover size> props to
    Tailwind utility classes on the native <table> (children stay native)."""
    pad = '1' if re.search(r'size="sm"', a) else '2'
    cls = [f'[&_th]:p-{pad}', f'[&_td]:p-{pad}', '[&_th]:text-left',
           '[&_td]:border-t', '[&_th]:border-b', '[&_td]:border-border',
           '[&_th]:border-border', '[&_*]:align-middle']
    if re.search(r'\bbordered\b', a):
        cls += ['[&_th]:border', '[&_td]:border']
    if re.search(r'\bstriped\b', a):
        cls += ['[&_tbody_tr:nth-child(odd)]:bg-muted/40']
    if re.search(r'\bhover\b', a):
        cls += ['[&_tbody_tr:hover]:bg-muted/50']
    a = re.sub(r'\s+(striped|bordered|hover|responsive)\b(=\{[^{}]*\})?', '', a)
    a = re.sub(r'\s+size="[^"]*"', '', a)
    return inject_class(a, ' '.join(cls))

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
    unknown = [n for n in names if n not in MAP and n not in SPECIAL]
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

    if 'Table' in names:
        s = transform_tag_attrs(s, 'Table', table_fix)

    form_syms = set()
    if 'Form' in names:
        # Form.Range / Select / Check / Control → form-controls primitives
        for sub, prim in [('Form.Range', 'Range'), ('Form.Select', 'Select'),
                          ('Form.Check', 'Check'), ('Form.Control', 'Control')]:
            if sub in s:
                s = s.replace('<' + sub, '<' + prim).replace('</' + sub + '>', '</' + prim + '>')
                form_syms.add(prim)
        # Form.Switch → <Check type="switch">
        if 'Form.Switch' in s:
            s = transform_tag_attrs(s, 'Form.Switch',
                lambda a: ' type="switch"' + a)
            s = s.replace('<Form.Switch', '<Check').replace('</Form.Switch>', '</Check>')
            form_syms.add('Check')
        # Form.Label → <label> (drop layout-only props), Form.Text → <small>
        if 'Form.Label' in s:
            s = transform_tag_attrs(s, 'Form.Label', lambda a: inject_class(
                re.sub(r'\s+(column|srOnly|visuallyHidden)\b(=\{[^{}]*\})?', '', a),
                'mb-1 inline-block'))
            s = s.replace('<Form.Label', '<label').replace('</Form.Label>', '</label>')
        if 'Form.Text' in s:
            s = transform_tag_attrs(s, 'Form.Text', lambda a: inject_class(
                re.sub(r'\s+muted\b(=\{[^{}]*\})?', '', a), 'block text-sm text-muted-foreground'))
            s = s.replace('<Form.Text', '<small').replace('</Form.Text>', '</small>')
        # Form.Group → <div> (no controlId in this codebase)
        if 'Form.Group' in s:
            s = s.replace('<Form.Group', '<div').replace('</Form.Group>', '</div>')
        # Form root → <form>
        s = re.sub(r'<Form(?=[\s>])', '<form', s)
        s = s.replace('</Form>', '</form>')

    if 'InputGroup' in names:
        if 'InputGroup.Text' in s:
            s = transform_tag_attrs(s, 'InputGroup.Text', lambda a: inject_class(
                a, 'inline-flex items-center border border-input bg-muted px-3 text-sm'))
            s = s.replace('<InputGroup.Text', '<span').replace('</InputGroup.Text>', '</span>')
        s = transform_tag_attrs(s, 'InputGroup', lambda a: inject_class(
            re.sub(r'\s+size="[^"]*"', '', a), 'flex items-stretch'))
        s = s.replace('<InputGroup', '<div').replace('</InputGroup>', '</div>')

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
        if n in SPECIAL:
            continue  # Form / InputGroup → native elements
        if n == 'Card':
            # only import the root <Card> symbol if it's actually used
            if re.search(r'<Card[\s/>]', s):
                by_mod.setdefault('@/components/ui/card', set()).add('Card')
            continue
        mod, sym = MAP[n]
        by_mod.setdefault(mod, set()).add(sym)
    for sym in card_syms:
        by_mod.setdefault('@/components/ui/card', set()).add(sym)
    for sym in form_syms:
        by_mod.setdefault('@/components/ui/form-controls', set()).add(sym)
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
