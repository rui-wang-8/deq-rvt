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

Value dumps can contain array-initializer asserts (for the concrete
constant arrays the expression reads) in addition to the final value
assert; all of those asserts are constraints and are included.  The two
sides name their arrays independently (KLEE numbers const arrays per
run), so all arrays except the shared inputs (names starting with
"stdin") are renamed with a per-side prefix before the queries are
built.

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


def expr_to_str(node):
    """Render an S-expression iteratively.

    CPython 3.12 enforces a *C* recursion limit that `sys.setrecursionlimit`
    does not raise, and a generator expression per level (the obvious
    `' '.join(expr_to_str(x) for x in node)`) trips it on KLEE's deeply nested
    memory-model dumps well before the Python limit.  An explicit stack keeps
    this O(1) in C-stack depth.
    """
    out = []
    stack = [node]
    while stack:
        item = stack.pop()
        if item is None:
            out.append(')')
        elif isinstance(item, list):
            out.append('(')
            stack.append(None)
            for k in range(len(item) - 1, -1, -1):
                stack.append(item[k])
                if k:
                    stack.append(' ')
        else:
            out.append(str(item))
    return ''.join(out)


def _parse_forms(path):
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
    decls = [l for l in text.splitlines()
             if l.strip().startswith('(declare-fun')]
    return forms, decls


def parse_dump(path):
    """Return (declarations, width, value-expr, extra-asserts).

    The value assert is the LAST assert of the dump; any earlier asserts
    (constant-array initializers) are constraints and are returned as
    extra-asserts strings."""
    forms, decls = _parse_forms(path)
    asserts = [expr_to_str(find_assert_expr(root)) for root in forms
               if find_assert_expr(root) is not None]
    if not asserts:
        raise ValueError(f'{path}: no assert found')
    value_assert = asserts[-1]
    extras = asserts[:-1]
    assert_node = None
    for root in forms:
        a = find_assert_expr(root)
        if a is not None:
            assert_node = a
    expr = strip_outer_zero_eq(assert_node)
    # The width comes from the OUTER wrapper, not from any inner
    # `(_ bv0 W)` constants that may appear inside let-bindings.
    width = 64
    node = unwrap_lets(assert_node)
    if (isinstance(node, list) and len(node) == 3 and node[0] == '='
            and is_zero_bv(node[1])):
        width = int(node[1][2]) if len(node[1]) == 3 else width
    return decls, width, expr_to_str(expr), extras


def parse_pc(path):
    """Return (declarations, path-condition expression) from a pc dump.

    All asserts in the file are part of the path condition."""
    forms, decls = _parse_forms(path)
    asserts = [expr_to_str(find_assert_expr(root)) for root in forms
               if find_assert_expr(root) is not None]
    if not asserts:
        return (decls, None)
    if len(asserts) == 1:
        return (decls, asserts[0])
    return (decls, '(and ' + ' '.join(asserts) + ')')


def widen_to(expr, width, target):
    """Zero-extend a value expression to `target` bits.

    KLEE's SMT printer simplifies `(= (_ bv0 64) (zext X))` into
    `(= (_ bv0 32) X)` (equivalent, since zext is injective and the compared
    value is zero), so a dumped 64-bit value whose upper bits are known zero
    can come back as a 32-bit expression while the other side still prints the
    full 64-bit one.  Both harnesses cast the same 4-byte field to u64 /
    uint64_t, so comparing on a common width by zero-extending the narrower
    side recovers exactly the intended comparison.
    """
    if width == target:
        return expr
    return f'((_ zero_extend {target - width}) {expr})'


def make_renamer(names, prefix):
    """Rename every declared array (except shared 'stdin*' inputs) with a
    per-side prefix so the two sides' identically-named constant arrays
    stay independent."""
    names = sorted({n for n in names if not n.startswith('stdin')},
                   key=len, reverse=True)
    if not names:
        return lambda t: t
    pat = re.compile(r'\b(' + '|'.join(re.escape(n) for n in names) + r')\b')
    return lambda t: pat.sub(lambda m: prefix + m.group(1), t)


def make_byte_input_normalizer(array_name, domain_width=32):
    """Rewrite `(select ARRAY (_ bvK W))` into the byte variable `stdinK`.

    KLEE models a symbolic input as an array (`stdin`), while SymCC (via deq's
    SMT2 hook) models it as the bytes `stdin0..stdinN`. Normalizing both sides
    to the same byte variables lets the dumps of the two engines be compared.
    """
    sel = re.compile(
        r'\(select\s+' + re.escape(array_name) + r'\s+\(_\s*bv(\d+)\s+' +
        str(domain_width) + r'\)\s*\)')
    return lambda t: sel.sub(lambda m: f'stdin{m.group(1)}', t)


def drop_array_decl(decls, array_name):
    """Drop the declaration of ARRAY and declare the byte variables instead."""
    pat = re.compile(r'\(declare-fun\s+' + re.escape(array_name) + r'\s')
    kept = [d for d in decls if not pat.match(d)]
    if len(kept) == len(decls):
        return decls
    return kept


def add_byte_decls(decls, text):
    """Add (declare-fun stdinK () (_ BitVec 8)) for every stdinK in text."""
    have = set()
    for d in decls:
        m = re.match(r'\(declare-fun\s+(stdin\d+)\s', d)
        if m:
            have.add(m.group(1))
    out = list(decls)
    for name in sorted(set(re.findall(r'\bstdin(\d+)\b', text)) -
                       {h[len('stdin'):] for h in have}, key=int):
        out.append(f'(declare-fun stdin{name} () (_ BitVec 8))')
    return out


def declared_names(decls):
    names = set()
    for d in decls:
        m = re.match(r'\(declare-fun\s+(\S+)', d)
        if m:
            names.add(m.group(1))
    return names


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
    # A malformed query (e.g. a reference to an undeclared array) makes Z3 print
    # (error ...) and then still answer for whatever part it did parse, which
    # would let a broken comparison masquerade as a proof.  Any Z3 error is
    # therefore a failure of the comparison, not an answer.
    if '(error' in out or 'error:' in out:
        return 'z3_error'
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
    ap.add_argument('--byte-inputs', default=None, metavar='ARRAY',
                    help='normalize (select ARRAY (_ bvK 32)) reads into the '
                         'byte variables stdinK on both sides, so KLEE array '
                         'inputs can be compared with SymCC byte inputs')
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
            decls, width, expr, extras = parse_dump(va)
            if pca.exists():
                pc_decls, pc = parse_pc(pca)
                # The pc dump declares the input arrays itself; merge its
                # declarations.
                decls = decls + [dd for dd in pc_decls if dd not in decls]
            else:
                pc = 'true'
            if args.byte_inputs:
                norm = make_byte_input_normalizer(args.byte_inputs)
                expr, pc = norm(expr), norm(pc)
                extras = [norm(x) for x in extras]
                decls = add_byte_decls(drop_array_decl(decls, args.byte_inputs),
                                       expr + pc + ' '.join(extras))
            entries.append((pid, decls, width, expr, pc, extras))
        sides.append(entries)

    entries_a, entries_b = sides
    if not entries_a or not entries_b:
        print('DUMPSET_OK pairs=0 unsat=0 sat=0 timeout=0 incompatible=0 '
              'all_ok=false')
        return 1

    # Rename each side's constant arrays independently; shared 'stdin*'
    # inputs keep their names so the two sides are compared on the same
    # input variables.
    rename_a = make_renamer(declared_names(
        [d for _, decls, *_ in entries_a for d in decls]), 'a_')
    rename_b = make_renamer(declared_names(
        [d for _, decls, *_ in entries_b for d in decls]), 'b_')

    decl_block_parts = []
    seen = set()
    for decls, rn in (([d for _, ds, *_ in entries_a for d in ds], rename_a),
                       ([d for _, ds, *_ in entries_b for d in ds], rename_b)):
        for d in decls:
            rd = rn(d)
            if rd not in seen:
                seen.add(rd)
                decl_block_parts.append(rd)
    decl_block = '\n'.join(decl_block_parts)

    if args.mode == 'by-id':
        pairs = []
        for a in entries_a:
            for b in entries_b:
                if a[0] == b[0]:
                    pairs.append((a, b))
                    break
    else:
        pairs = [(a, b) for a in entries_a for b in entries_b]
    if args.max_pairs:
        pairs = pairs[:args.max_pairs]

    n_unsat = n_sat = n_timeout = n_incompatible = n_other = 0
    n_widened = 0
    for a, b in pairs:
        ida, decls_a, wa, ea, pca, extras_a = a
        idb, decls_b, wb, eb, pcb, extras_b = b
        width = max(wa, wb)
        if wa != wb:
            n_widened += 1
        ea2, pca2 = rename_a(ea), rename_a(pca)
        eb2, pcb2 = rename_b(eb), rename_b(pcb)
        ea2, eb2 = widen_to(ea2, wa, width), widen_to(eb2, wb, width)
        extra_block = ''.join(f'(assert {rename_a(x)})\n'
                              for x in extras_a) \
            + ''.join(f'(assert {rename_b(x)})\n' for x in extras_b)
        query = ('(set-logic QF_AUFBV)\n(set-option :produce-models true)\n'
                 + decl_block + '\n'
                 + extra_block
                 + f'(define-fun va () (_ BitVec {width}) {ea2})\n'
                 + f'(define-fun vb () (_ BitVec {width}) {eb2})\n'
                 + f'(assert {pca2})\n(assert {pcb2})\n'
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
                      + extra_block
                      + f'(assert {pca2})\n(assert {pcb2})\n(check-sat)\n')
            cv = run_z3(compat, args.z3, args.timeout)
            if cv == 'unsat':
                n_incompatible += 1
            elif cv == 'sat':
                n_sat += 1
                print(f'DISEQUIVALENCE: path {ida} vs {idb}', file=sys.stderr)
            elif cv == 'timeout':
                # The disequality query answered SAT but the compatibility of
                # the two path conditions could not be decided: that is not
                # evidence of a divergence.
                n_timeout += 1
            else:
                n_other += 1
        elif v == 'z3_error':
            n_other += 1
        else:
            n_other += 1
        if n_sat:
            break

    ok = n_sat == 0 and n_timeout == 0 and n_other == 0
    print(f'DUMPSET_OK pairs={len(pairs)} '
          f'unsat={n_unsat} sat={n_sat} timeout={n_timeout} '
          f'incompatible={n_incompatible} other={n_other} '
          f'widened={n_widened} '
          f'all_ok={str(ok).lower()}')
    return 0 if ok else 1


def _run_with_big_stack():
    """Run main() on a thread with a large stack and a raised recursion limit.

    KLEE dumps of memory-heavy paths nest tens of thousands of `store` /
    `concat` nodes, and every stage of this script (parsing, printing, the
    renamer walk) is a recursive descent over them.
    """
    import threading
    box = {}

    def work():
        sys.setrecursionlimit(400000)
        try:
            box['rc'] = main()
        except BaseException as exc:
            box['exc'] = exc

    threading.stack_size(1024 * 1024 * 1024)
    t = threading.Thread(target=work)
    t.start()
    t.join()
    if 'exc' in box:
        raise box['exc']
    return box.get('rc', 1)


if __name__ == '__main__':
    sys.exit(_run_with_big_stack())
