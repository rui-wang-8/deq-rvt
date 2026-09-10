#!/usr/bin/env python3
"""Compare two sets of KLEE klee_dump_expr dumps for total equivalence.

Both sides explore the same computation; each explored path writes
<dir>/<tag>.<id>.smt2 (value) and <dir>/<tag>.<id>.pc.smt2 (path
condition).  The two implementations may partition the input domain
differently, so the dumps are compared as a CROSS PRODUCT with a path
compatibility gate (the deq INCOMPATIBLE_PATHS rule):

  for every path a of side A and path b of side B:
    if   pc_a AND pc_b           is UNSAT  -> skip (incompatible paths)
    if   pc_a AND pc_b AND va!=vb is UNSAT -> ok (agree on the overlap)
    else                                      -> genuine disequivalence

Usage: compare-klee-dump-sets.py A_DIR B_DIR --tag TAG [--z3 z3]
       [--timeout 120] [--max-pairs N] [--max-side-paths N]

Prints a summary line:
    DUMPSET_OK pairs=N unsat=N sat=0 timeout=0 incompatible=N all_ok=true
Exit codes: 0 = equivalent, 1 = disequivalence/timeout.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def sexp_tokens(text):
    return re.findall(r'\(|\)|[^\s()]+', text)


def parse_sexp(tokens, i=0):
    assert tokens[i] == '('
    i += 1
    out = []
    while tokens[i] != ')':
        if tokens[i] == '(':
            node, i = parse_sexp(tokens, i)
            out.append(node)
        else:
            out.append(tokens[i])
            i += 1
    return out, i + 1


def find_assert_expr(node):
    if not isinstance(node, list):
        return None
    if node and node[0] == 'assert':
        return node[1]
    for child in node:
        r = find_assert_expr(child)
        if r is not None:
            return r
    return None


def is_zero_bv(node):
    if isinstance(node, list):
        return len(node) == 3 and node[0] == '_' and node[1] == 'bv0'
    return node.startswith('(_ bv0 ')


def strip_outer_zero_eq(node):
    """Strip ONLY the dump's outer `(= (_ bv0 W) EXPR)` wrapper.

    KLEE normalizes `x != 0` into `(= false (= (_ bv0 W) x))`, so inner
    `(= (_ bv0 W) ...)` occurrences are real program semantics and must
    be preserved."""
    if (isinstance(node, list) and len(node) == 3 and node[0] == '='
            and is_zero_bv(node[1])):
        return node[2]
    return node


def replace_eq_zero(node):
    if not isinstance(node, list):
        return node
    if len(node) == 3 and node[0] == '=' and is_zero_bv(node[1]):
        return replace_eq_zero(node[2])
    return [replace_eq_zero(x) for x in node]


def expr_to_str(node):
    if isinstance(node, list):
        return '(' + ' '.join(expr_to_str(x) for x in node) + ')'
    return node


def parse_dump(path):
    text = Path(path).read_text()
    tokens = sexp_tokens(text)
    forms = []
    i = 0
    while i < len(tokens):
        if tokens[i] == '(':
            node, i = parse_sexp(tokens, i)
            forms.append(node)
        else:
            i += 1
    assert_node = None
    for root in forms:
        assert_node = find_assert_expr(root)
        if assert_node is not None:
            break
    if assert_node is None:
        raise ValueError(f'{path}: no assert found')
    expr = strip_outer_zero_eq(assert_node)
    m = re.search(r'\(_ bv0 (\d+)', text)
    width = int(m.group(1)) if m else 64
    decls = [l for l in text.splitlines()
             if l.strip().startswith('(declare-fun')]
    return decls, width, expr_to_str(expr)


def parse_pc(path):
    """Return (declarations, path-condition expression) from a pc dump."""
    text = Path(path).read_text()
    tokens = sexp_tokens(text)
    forms = []
    i = 0
    while i < len(tokens):
        if tokens[i] == '(':
            node, i = parse_sexp(tokens, i)
            forms.append(node)
        else:
            i += 1
    expr = None
    for root in forms:
        e = find_assert_expr(root)
        if e is not None:
            expr = expr_to_str(e)
            break
    decls = [l for l in text.splitlines()
             if l.strip().startswith('(declare-fun')]
    return (decls, expr)


def path_ids(d, tag):
    ids = []
    for p in Path(d).glob(f'{tag}.*.smt2'):
        stem = p.stem  # e.g. "out_hex.3" or "out_hex.3.pc"
        if stem.endswith('.pc'):
            continue
        ids.append(int(stem.split('.')[-1]))
    return sorted(ids)


def run_z3(query, z3, timeout):
    with tempfile.NamedTemporaryFile('w', suffix='.smt2', delete=False) as f:
        f.write(query)
        qpath = f.name
    try:
        r = subprocess.run([z3, f'-T:{timeout}', qpath],
                           capture_output=True, text=True,
                           timeout=timeout + 30)
    except subprocess.TimeoutExpired:
        return 'timeout'
    finally:
        Path(qpath).unlink(missing_ok=True)
    out = (r.stdout + r.stderr).strip()
    if 'unsat' in out:
        return 'unsat'
    if 'sat' in out:
        return 'sat'
    return 'z3_error'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a_dir')
    ap.add_argument('b_dir')
    ap.add_argument('--tag', required=True,
                    help='dump tag of side A (and B unless --tag-b)')
    ap.add_argument('--tag-b', default=None,
                    help='dump tag of side B')
    ap.add_argument('--mode', choices=['by-id', 'cross'], default='by-id',
                    help='by-id: pair paths with equal state ids (same '
                         'KLEE run / identical partitioning); '
                         'cross: full cross-product with the path-'
                         'compatibility gate (differently partitioned '
                         'path sets)')
    ap.add_argument('--z3', default='z3')
    ap.add_argument('--timeout', type=int, default=120)
    ap.add_argument('--max-pairs', type=int, default=0)
    ap.add_argument('--max-side-paths', type=int, default=0)
    args = ap.parse_args()

    tag_a = args.tag
    tag_b = args.tag_b or args.tag
    ids_a = path_ids(args.a_dir, tag_a)
    ids_b = path_ids(args.b_dir, tag_b)
    if args.max_side_paths:
        ids_a = ids_a[:args.max_side_paths]
        ids_b = ids_b[:args.max_side_paths]

    sides = []
    for ids, d, tag in ((ids_a, args.a_dir, tag_a),
                         (ids_b, args.b_dir, tag_b)):
        entries = []
        for pid in ids:
            va = Path(d) / f'{tag}.{pid}.smt2'
            pca = Path(d) / f'{tag}.{pid}.pc.smt2'
            decls, width, expr = parse_dump(va)
            if pca.exists():
                pc_decls, pc = parse_pc(pca)
                # The pc dump declares the input arrays itself; merge its
                # declarations (constant value dumps reference no arrays).
                decls = decls + [d for d in pc_decls if d not in decls]
            else:
                pc = 'true'
            entries.append((pid, decls, width, expr, pc))
        sides.append(entries)

    entries_a, entries_b = sides
    if not entries_a or not entries_b:
        print('DUMPSET_OK pairs=0 unsat=0 sat=0 timeout=0 incompatible=0 '
              'all_ok=false')
        return 1

    # Deduplicate the declaration sets up front (shared input arrays).
    all_decls = []
    seen = set()
    for _, decls, _, _, _ in entries_a + entries_b:
        for d in decls:
            if d not in seen:
                seen.add(d)
                all_decls.append(d)
    decl_block = '\n'.join(all_decls)

    if args.mode == 'by-id':
        pairs = []
        for a in entries_a:
            for b in entries_b:
                if a[0] == b[0]:
                    pairs.append((a, b))
                    break
    else:
        pairs = [(a, b) for a in entries_a for b in entries_b]

    n_unsat = n_sat = n_timeout = n_incompatible = n_other = 0
    for (ida, decls_a, wa, ea, pca), (idb, decls_b, wb, eb, pcb) in pairs:
        if wa != wb:
            n_other += 1
            continue
        query = ('(set-logic QF_AUFBV)\n(set-option :produce-models true)\n'
                 + decl_block + '\n'
                 + f'(define-fun va () (_ BitVec {wa}) {ea})\n'
                 + f'(define-fun vb () (_ BitVec {wb}) {eb})\n'
                 + f'(assert {pca})\n(assert {pcb})\n'
                 + '(assert (not (= va vb)))\n(check-sat)\n')
        v = run_z3(query, args.z3, args.timeout)
        if v == 'unsat':
            n_unsat += 1
        elif v == 'timeout':
            n_timeout += 1
        elif v == 'sat':
            # INCOMPATIBLE_PATHS gate: a SAT result is only a genuine
            # disequivalence when the two path conditions can hold at
            # the same time.
            compat = ('(set-logic QF_AUFBV)\n(set-option :produce-models true)\n'
                      + decl_block + '\n'
                      + f'(assert {pca})\n(assert {pcb})\n(check-sat)\n')
            cv = run_z3(compat, args.z3, args.timeout)
            if cv == 'unsat':
                n_incompatible += 1
            else:
                n_sat += 1
                print(f'DISEQUIVALENCE: path {ida} vs {idb}', file=sys.stderr)
        else:
            n_other += 1
        if n_sat:
            break

    ok = n_sat == 0 and n_timeout == 0 and n_other == 0
    print(f'DUMPSET_OK pairs={len(pairs)} '
          f'unsat={n_unsat} sat={n_sat} timeout={n_timeout} '
          f'incompatible={n_incompatible} other={n_other} '
          f'all_ok={str(ok).lower()}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
