; Test suite for the RVT -> KLEE flow (lit-based).
;
; Prerequisites: KLEE installed at tools/klee (scripts/build-klee.sh),
; cargo-verify + rvt-patch-llvm at tools/bin, a rustc 1.81.x toolchain.
;
; Run with:
;
;   source scripts/rvt-klee-env.sh
;   scripts/run-tests.sh            # all tests
;   scripts/run-tests.sh -v         # verbose
;   scripts/run-tests.sh tests/klee/klee-simple.test
;
; See docs/klee-flow.md for the full flow.
