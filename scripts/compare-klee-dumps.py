#!/usr/bin/env python3
"""Check two KLEE klee_dump_expr dumps (a, b) for equivalence with Z3.

Each side provides a value dump (<tag>.<id>.smt2) and optionally a path
condition dump (<tag>.<id>.pc.smt2).  The combined query asserts

    path_a AND path_b AND a_result != b_result

and the pair is equivalent iff Z3 answers UNSAT.

Usage: compare-klee-dumps.py a.smt2 b.smt2 [--pc-a a.pc.smt2]
        [--pc-b b.pc.smt2] [--z3 /path/to/z3] [--timeout 120]

Exit codes: 0 = EQUIV (unsat), 1 = NOT_EQUIV (sat), 2 = error.
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
    be preserved.  The dump printer emits (possibly nested) let-bindings
    around the wrapper; every let level is kept so the result stays
    self-contained."""
    if (isinstance(node, list) and len(node) == 3 and node[0] == '='
            and is_zero_bv(node[1])):
        return node[2]
    if (isinstance(node, list) and len(node) >= 3 and node[0] == 'let'):
        inner = strip_outer_zero_eq(node[2])
        return ['let', node[1], inner]
    return node


def unwrap_lets(node):
    while (isinstance(node, list) and len(node) >= 3 and node[0] == 'let'):
        node = node[2]
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


def load_value_dump(path, name):
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
    # The width comes from the OUTER wrapper, not from any inner
    # `(_ bv0 W)` constants that may appear inside let-bindings.
    width = 64
    node = unwrap_lets(assert_node)
    if (isinstance(node, list) and len(node) == 3 and node[0] == '='
            and is_zero_bv(node[1])):
        width = int(node[1][2]) if len(node[1]) == 3 else width

    decls = [l for l in text.splitlines()
             if l.strip().startswith('(declare-fun')]
    return decls, width, expr_to_str(expr)


def load_pc_dump(path):
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
    exprs = [e for root in forms
             for e in [find_assert_expr(root)] if e is not None]
    if not exprs:
        return None
    return expr_to_str(exprs[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--pc-a')
    ap.add_argument('--pc-b')
    ap.add_argument('--z3', default='z3')
    ap.add_argument('--timeout', type=int, default=120)
    args = ap.parse_args()

    decls_a, width_a, expr_a = load_value_dump(args.a, 'va')
    decls_b, width_b, expr_b = load_value_dump(args.b, 'vb')
    if width_a != width_b:
        print(f'ERROR: width mismatch {width_a} vs {width_b}', file=sys.stderr)
        return 2

    pc_a = load_pc_dump(args.pc_a) if args.pc_a else None
    pc_b = load_pc_dump(args.pc_b) if args.pc_b else None

    lines = ['(set-logic QF_AUFBV)', '(set-option :produce-models true)']
    # Deduplicate identical declarations: equivalent implementations
    # follow the deq convention of using the same input array names
    # (e.g. "stdin"), so both dumps declare the same arrays.
    seen = set()
    for d in decls_a + decls_b:
        if d not in seen:
            seen.add(d)
            lines.append(d)
    lines.append(f'(define-fun va () (_ BitVec {width_a}) {expr_a})')
    lines.append(f'(define-fun vb () (_ BitVec {width_b}) {expr_b})')
    if pc_a:
        lines.append(f'(assert {pc_a})')
    if pc_b:
        lines.append(f'(assert {pc_b})')
    lines.append(f'(assert (not (= va vb)))')
    lines.append('(check-sat)')
    query = '\n'.join(lines) + '\n'

    with tempfile.NamedTemporaryFile('w', suffix='.smt2', delete=False) as f:
        f.write(query)
        qpath = f.name
    try:
        r = subprocess.run([args.z3, f'-T:{args.timeout}', qpath],
                           capture_output=True, text=True, timeout=args.timeout + 30)
    except subprocess.TimeoutExpired:
        print('ERROR: z3 timed out', file=sys.stderr)
        return 2
    finally:
        Path(qpath).unlink(missing_ok=True)

    out = (r.stdout + r.stderr).strip()
    print(out)
    if 'unsat' in out:
        print('EQUIV')
        return 0
    if 'sat' in out:
        print('NOT_EQUIV')
        return 1
    print(f'ERROR: unexpected z3 output (rc={r.returncode})', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
