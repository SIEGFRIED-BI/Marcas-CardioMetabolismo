"""Restaura el grafico de Venta Interna en SNC (chart + meter + totals + pills)
desde el commit 89836ab, dejando intacto el resto del archivo actual.

Idempotente: si SNC ya tiene budChart en el HTML, no hace nada.
"""
import re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

def find_section_close(text, start):
    depth, i = 1, start
    while i < len(text) and depth > 0:
        nxt_open  = text.find('<div', i)
        nxt_close = text.find('</div>', i)
        if nxt_close < 0: return -1
        if nxt_open >= 0 and nxt_open < nxt_close:
            depth += 1; i = nxt_open + 4
        else:
            depth -= 1
            if depth == 0: return nxt_close + len('</div>')
            i = nxt_close + len('</div>')
    return -1

def find_matching_brace(text, start):
    depth, i = 0, start
    in_s, q = False, None
    in_t = False
    in_lc, in_bc = False, False
    while i < len(text):
        c = text[i]
        nxt = text[i+1] if i+1 < len(text) else ''
        if in_lc:
            if c == '\n': in_lc = False
            i += 1; continue
        if in_bc:
            if c == '*' and nxt == '/': in_bc = False; i += 2; continue
            i += 1; continue
        if in_s:
            if c == '\\': i += 2; continue
            if c == q: in_s = False
            i += 1; continue
        if in_t:
            if c == '\\': i += 2; continue
            if c == '`': in_t = False
            i += 1; continue
        if c == '/' and nxt == '/': in_lc = True; i += 2; continue
        if c == '/' and nxt == '*': in_bc = True; i += 2; continue
        if c in ('"', "'"): in_s = True; q = c; i += 1; continue
        if c == '`': in_t = True; i += 1; continue
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: return i
        i += 1
    return -1

def extract_section(text, marker='<div class="sec" id="s-bud">'):
    s = text.find(marker)
    if s < 0: return None, None
    end = find_section_close(text, s + len(marker))
    if end < 0: return None, None
    return s, end

def extract_function(text, name):
    m = re.search(r'function\s+' + re.escape(name) + r'\s*\([^)]*\)\s*\{', text)
    if not m: return None, None
    ob = m.end() - 1
    cb = find_matching_brace(text, ob)
    if cb < 0: return None, None
    return m.start(), cb + 1


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    snc_path = REPO / 'SNC' / 'index.html'
    cur = snc_path.read_text(encoding='utf-8', errors='replace')
    if 'budChart' in cur and 'bud-meter' in cur:
        print('SNC already has budChart + bud-meter — skipping')
        return 0
    # Get the historic version
    old = subprocess.check_output(
        ['git', 'show', '89836ab:SNC/index.html'],
        cwd=str(REPO), text=True, encoding='utf-8'
    )
    # Extract pieces from old SNC
    ohs, ohe = extract_section(old)
    old_html = old[ohs:ohe]
    print(f'old html section len: {len(old_html)}')

    old_rb_s, old_rb_e = extract_function(old, 'renderBudget')
    old_rb = old[old_rb_s:old_rb_e]
    print(f'old renderBudget len: {len(old_rb)}')

    old_rp_s, old_rp_e = extract_function(old, 'renderBudPills')
    old_rp = old[old_rp_s:old_rp_e]
    print(f'old renderBudPills len: {len(old_rp)}')

    old_sbp_s, old_sbp_e = extract_function(old, 'setBP')
    old_sbp = old[old_sbp_s:old_sbp_e]
    print(f'old setBP len: {len(old_sbp)}')

    # Find current locations
    chs, che = extract_section(cur)
    cur_rb_s, cur_rb_e = extract_function(cur, 'renderBudget')
    cur_rp_s, cur_rp_e = extract_function(cur, 'renderBudPills')
    cur_sbp_s, cur_sbp_e = extract_function(cur, 'setBP')

    print(f'current html: {chs}..{che}')
    print(f'current renderBudget: {cur_rb_s}..{cur_rb_e}')
    print(f'current renderBudPills: {cur_rp_s}..{cur_rp_e}')
    print(f'current setBP: {cur_sbp_s}..{cur_sbp_e}')

    # Apply replacements from end to start
    replacements = sorted([
        (chs, che, old_html),
        (cur_rb_s, cur_rb_e, old_rb),
        (cur_rp_s, cur_rp_e, old_rp),
        (cur_sbp_s, cur_sbp_e, old_sbp),
    ], key=lambda r: -r[0])

    new = cur
    for s, e, replacement in replacements:
        new = new[:s] + replacement + new[e:]

    snc_path.write_text(new, encoding='utf-8', newline='')
    print('SNC restored: chart + meter + totals + pills + redistribucion trimestral')
    return 0


if __name__ == '__main__':
    sys.exit(main())
