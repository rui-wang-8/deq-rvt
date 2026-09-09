# KLEE fork for Rust

The RVT → KLEE flow needs one fix to upstream KLEE for bitcode produced
by `rustc`: rustc emits `switch` instructions whose condition can be wider
than 64 bits (e.g. `i96`, from niche-optimized enum discriminants) or
negative, and upstream's `ConstantExpr::getZExtValue()` asserts on those
(observed on `serde_json` under KLEE). The fix uses the full-precision
`APInt` instead.

## The fork repository

The fork is tracked in its own git repository at `tools/klee-src`:

- `master` tracks upstream KLEE unchanged.
- `rvt-for-rust` carries the fix, committed as
  `rvt: handle wide/negative switch conditions emitted by rustc`.

The same change is kept here as a patch for reference / re-application:

- `patches/0001-executor-handle-wide-switch-conditions.patch`

Build and install the fork with `scripts/build-klee.sh`; update it from
upstream as described in `tools/klee-src/README-RVT.md`. Full details of
the pipeline are in [../docs/klee-flow.md](../docs/klee-flow.md).

## Reproducing the fork

```bash
git clone https://github.com/klee/klee.git tools/klee-src
cd tools/klee-src
git checkout -b rvt-for-rust
git apply ../../klee/patches/0001-executor-handle-wide-switch-conditions.patch
git commit -am "rvt: handle wide/negative switch conditions emitted by rustc"
```

Note: the KLEE v3.2 release tag ships `assert(0)` stubs for the LLVM ≥ 17
module instrumentation and is unusable; the fork is based on the
`master` branch.
