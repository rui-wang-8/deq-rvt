# The RVT → KLEE flow (modernized)

This document describes how Rust code is compiled to LLVM bitcode and
symbolically executed with KLEE using the tools in this repository, how to
build everything from source, and how to run the test suite.

## 1. Toolchain matrix

Everything is pinned to **LLVM 18** so that the bitcode produced by `rustc`
can be read by both `rvt-patch-llvm` and KLEE:

| Component            | Version                          | Notes                                        |
|----------------------|----------------------------------|----------------------------------------------|
| KLEE                 | fork of upstream `master` (3.3-pre), branch `rvt-for-rust` | one Rust-specific fix (see §5) |
| LLVM                 | 18.x                             | `llvm-18-dev`, `clang-18`, `llvm-link-18`    |
| rustc                | 1.81.x                           | bundles LLVM 18; pinned per-crate via `rust-toolchain.toml` |
| Z3                   | 4.8+                             | `libz3-dev`                                   |

## 2. Directory layout

```
tools/klee-src/      KLEE fork (its own git repository; branch rvt-for-rust)
tools/klee/          installed KLEE (bin/klee, lib/libkleeRuntest.so, ...)
tools/klee-build/    KLEE CMake build directory
tools/bin/           cargo-verify, rvt-patch-llvm
klee/patches/        the Rust-specific KLEE patch (applied in the fork)
runtime/             C stubs compiled to runtime/rvt-klee.bc
simd_emulation/      portable SIMD-intrinsic emulations (simd_emulation.bc)
demos/               crates verified under KLEE
tests/               lit-based test suite
```

`tools/` is git-ignored by this repository: KLEE is tracked in its own git
repository at `tools/klee-src`, built with `scripts/build-klee.sh`.

## 3. The pipeline

`cargo-verify --backend=klee` performs these steps (see
`cargo-verify/src/` for details):

1. **Compile to bitcode.** `cargo build` runs with
   `RUSTFLAGS="-Clto -Cembed-bitcode=yes --emit=llvm-bc --cfg=verify ..."`,
   which makes rustc emit one fat-LTO bitcode file for the whole crate
   (including `std`). Debug info is disabled
   (`CARGO_PROFILE_DEV_DEBUG=0` - KLEE's instrumentation of the module
   fails otherwise) and panics abort (`CARGO_PROFILE_DEV_PANIC=abort`).

2. **Link.** `llvm-link-18` merges the crate bitcode with the RVT runtime
   (`runtime/rvt-klee.bc`: deterministic stubs for `getrandom`, `statx`,
   `open*`, `sched_getaffinity`, `pthread`, ... that modern `std` needs
   under KLEE) and the SIMD emulations (`simd_emulation/simd_emulation.bc`).

3. **Patch.** `rvt-patch-llvm` (built against LLVM 18 via inkwell)
   - strips debug info,
   - calls `.init_array` initializers from `main` (so `std::env::args`
     works),
   - stubs runtime CPU-feature detection,
   - rewrites SIMD/bit-manipulation intrinsics KLEE does not implement
     (`llvm.x86.*`, `llvm.vector.*`, `llvm.bitreverse.*`) to the portable
     emulation functions.

4. **Run KLEE.** `klee --exit-on-error --entry-point=main --libc=klee`
   executes the patched bitcode; every path is explored and every
   `verifier::assert!` is checked.

`cargo-verify` reports `VERIFICATION_RESULT: VERIFIED` when all paths
complete without violations, and maps KLEE errors to specific statuses
(`ASSERT_FAILED`, `OVERFLOW`, `PANIC`, ...).

## 4. Building everything

Prerequisites (Ubuntu 24.04): `cmake build-essential clang-18 llvm-18
llvm-18-dev libz3-dev python3` and `lit` (`pip3 install lit`).

```bash
cd rust-verification-tools

# 1. KLEE (fork, branch rvt-for-rust) -> tools/klee
scripts/build-klee.sh

# 2. RVT runtime bitcode and SIMD emulations
make -C runtime TGT=klee
make -C simd_emulation

# 3. The RVT tools -> tools/bin
export CARGO_HOME="$PWD/.cargo-home"          # keep cargo caches in-tree
LLVM_SYS_181_PREFIX=/usr/lib/llvm-18 \
    cargo build --manifest-path rvt-patch-llvm/Cargo.toml
cargo build --manifest-path cargo-verify/Cargo.toml
cp rvt-patch-llvm/target/debug/rvt-patch-llvm \
   cargo-verify/target/debug/cargo-verify tools/bin/
```

## 5. The KLEE fork

Upstream KLEE needs one change for bitcode emitted by rustc: rustc
generates `switch` instructions whose condition can be wider than 64 bits
(i96, from niche-optimized enum discriminants) or negative, and upstream's
`ConstantExpr::getZExtValue()` asserts on those. The fork uses the
full-precision `APInt` instead (`lib/Core/Executor.cpp`).

The fork lives at `tools/klee-src` (its own git repository):

- `master` tracks upstream unchanged;
- `rvt-for-rust` carries the fix (patch kept in `klee/patches/`).

Updating from upstream:

```bash
cd tools/klee-src
git fetch origin
git checkout rvt-for-rust && git rebase origin/master
scripts/build-klee.sh   # in the RVT repo root
```

Note: the KLEE **v3.2 release tag** ships `assert(0)` stubs for the LLVM
≥ 17 module instrumentation and is unusable - build from the `master`-based
`rvt-for-rust` branch instead.

## 6. Writing a verification harness

A harness is a crate (bin, or `#[test]` functions with `--tests`) that
depends on `verification-annotations` with the `verifier-klee` feature:

```rust
use verification_annotations::prelude::*;

fn main() {
    let x: u32 = VerifierNonDet::verifier_nondet(0);   // symbolic value
    verifier::assert!(x.wrapping_add(x) % 2 == 0);     // checked on every path
}
```

Pin the toolchain: `rust-toolchain.toml` with `channel = "1.81.0"` (the
crate's rustc must bundle LLVM 18). Run:

```bash
source scripts/rvt-klee-env.sh
cargo-verify --backend=klee --manifest-path demos/klee-simple/Cargo.toml
```

Examples: `demos/klee-simple` (pipeline smoke test), `demos/klee-regex`
(regex 1.x over symbolic haystacks), `demos/klee-serde-json` (serde_json
1.0.x parser/serializer round-trips).

## 7. Running the test suite

The test suite uses LLVM's **lit** framework (`tests/`, one `.test` file
per check; `RUN:` lines execute commands and `CHECK:` lines are matched
with FileCheck):

```bash
source scripts/rvt-klee-env.sh
scripts/run-tests.sh                # run everything
scripts/run-tests.sh -v             # verbose
scripts/run-tests.sh tests/klee/klee-simple.test
```

The suite verifies KLEE and the tools are installed, then runs the full
pipeline on the three demos and checks for
`VERIFICATION_RESULT: VERIFIED`. It takes a few minutes (dominated by the
serde_json and regex symbolic explorations).

## 8. Known limitations

- **SMT array theory**: symbolic regex *patterns* (regex-syntax then
  builds byte-class tables from symbolic data) and haystacks longer than a
  few bytes make the search index those tables at symbolic positions;
  both can produce Z3 queries that do not terminate. The demos use sizes
  that verify cleanly.
- `--tests` mode unwinds panics (cargo ignores `panic` settings for the
  test profile); panics are still reported as failures.
- KLEE ≥ 3.0 reports `klee_assume(0)` as an error, so
  `verification-annotations` passes assumptions via a branch-free cast.
- The seahorn/smack/proptest backends are unchanged from the original
  project and untested by this suite.
