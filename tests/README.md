# Test suite for the RVT -> KLEE flow (lit-based).

Prerequisites: KLEE installed at `tools/klee` (`scripts/build-klee.sh`),
`cargo-verify` + `rvt-patch-llvm` at `tools/bin`, a rustc 1.81.x toolchain,
`clang-18`, `FileCheck-18`, `z3`.

Run with:

```
source scripts/rvt-klee-env.sh
scripts/run-tests.sh                             # all tests
scripts/run-tests.sh -v                          # verbose
scripts/run-tests.sh tests/klee/klee-simple.test # single test
```

`klee-deq-dump.test` covers the deq differential-equivalence hook: the C
twin of `demos/klee-deq-dump` is compiled with clang, both sides run under
KLEE with `KLEE_DUMP_DIR` set, and the dumped SMT2 output expressions are
proven equivalent with Z3 (`scripts/compare-klee-dumps.py`).

See `docs/klee-flow.md` for the full flow.
