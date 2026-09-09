# Rust verification tools

This is a collection of tools/libraries to support both static
and dynamic verification of Rust programs.

We see static verification (formal verification) and dynamic verification
(testing) as two parts of the same activity and so these tools can be used for
either form of verification.

- Dynamic verification using the
  [proptest](https://github.com/AltSysrq/proptest)
  fuzzing/property testing library.

- Static verification using the
  [KLEE](http://klee.github.io/)
  symbolic execution engine.

We aim to add other backends in the near future.

In addition, [we document](https://project-oak.github.io/rust-verification-tools/about.html) how the tools we wrote work
in case you are porting a verification tool for use with Rust.
(In particular, we describe how to generate LLVM bitcode files that can
be used with LLVM-based verification tools.)

## Tools and libraries

- `verification-annotations` crate: an FFI layer for creating symbolic values in
  [KLEE](http://klee.github.io/)

- `propverify` crate:
  an implementation of the [proptest](https://github.com/AltSysrq/proptest)
  library for use with static verification tools.

- `cargo-verify`: a tool for compiling a crate and
  either verifying main/tests or for fuzzing main/tests.
  (Use the `--backend` flag to select which.)

- `compatibility-test` test crate:
  test programs that can be verified either using the original `proptest`
  library or using `propverify`.
  Used to check that proptest and propverify are compatible with each other.

## Usage

TL;DR

1. Install
   For installation with Docker, see the Usage section of [our main docs](https://project-oak.github.io/rust-verification-tools/about.html).

2. Fuzz some examples with proptest

   ```
   cd compatibility-test
   cargo test
   cd ..
   ```

   (You can also use
   `cargo-verify --backend=proptest --verbose`.)

   One test should fail – this is correct behaviour.

3. Verify some examples with propverify

   `cd verification-annotations; cargo-verify --tests`

   `cd verification-annotations; cargo-verify --tests`

   No tests should fail.

4. Read [the propverify intro](https://project-oak.github.io/rust-verification-tools/using-propverify/) for an example
   of fuzzing with `proptest` and verifying with `propverify`.

5. Read [the proptest book](https://altsysrq.github.io/proptest-book/intro.html)

6. Read the source code for the [compatibility test suite](compatibility-test/src).

   (Many of these examples are taken from or based on examples in
   [the proptest book](https://altsysrq.github.io/proptest-book/intro.html).)

There is also [some limited documentation](https://project-oak.github.io/rust-verification-tools/about.html) of how this works.

## Verifying Rust code with KLEE (modernized toolchain)

The original project pinned a 2021-era toolchain (LLVM 10, KLEE 2.x, a
2021 nightly compiler). This tree has been updated to run with current
KLEE and current Rust code. The supported (tested) toolchain matrix is:

| Component       | Version                                   | Why                                        |
|-----------------|-------------------------------------------|--------------------------------------------|
| KLEE            | 3.x (built from master; ≥ 3.2 has a known issue on LLVM ≥ 17) | symbolic executor                          |
| LLVM            | 18.x                                      | KLEE is built against it                   |
| rustc           | 1.81.x                                    | bundles LLVM 18, so the emitted bitcode matches KLEE |
| clang/llvm-link | 18.x                                      | compile/link the RVT runtime bitcode       |

Changes from the original flow:

- `cargo-verify` now targets LLVM 18 by default (`--llvm-version 18`),
  drops the nightly-only `-Z` flags, and disables debug info in the
  generated bitcode (cargo enables it by default since 1.70, which
  breaks KLEE's instrumentation of the module).
- `rvt-patch-llvm` is built against upstream inkwell (LLVM 18) and
  handles opaque pointers; it strips debug info and rewrites SIMD
  intrinsics (`llvm.x86.*`, `llvm.vector.*`, `llvm.bitreverse.*`) to
  portable emulations.
- `simd_emulation` is now written in C + a small `.ll` file (no nightly
  `repr(simd)` compiler required).
- The runtime adds stubs for modern `glibc`/`std` (e.g. `getrandom`,
  which `std` resolves via an `extern_weak` symbol).

Building the tools (KLEE, rvt-patch-llvm, cargo-verify):

```
# 1. KLEE (the RVT fork: tools/klee-src, branch rvt-for-rust) -> tools/klee
scripts/build-klee.sh

# 2. RVT runtime bitcode and tools:
make -C runtime TGT=klee
make -C simd_emulation
LLVM_SYS_181_PREFIX=/usr/lib/llvm-18 cargo build --manifest-path rvt-patch-llvm/Cargo.toml
cargo build --manifest-path cargo-verify/Cargo.toml
cp rvt-patch-llvm/target/debug/rvt-patch-llvm cargo-verify/target/debug/cargo-verify tools/bin/
```

Verifying a crate (e.g. the bundled demos):

```
source scripts/rvt-klee-env.sh
cargo-verify --backend=klee --manifest-path demos/klee-simple/Cargo.toml
cargo-verify --backend=klee --manifest-path demos/klee-regex/Cargo.toml
cargo-verify --backend=klee --manifest-path demos/klee-serde-json/Cargo.toml
```

Running the test suite (lit-based):

```
scripts/run-tests.sh
```

The full flow (pipeline stages, fork maintenance, harness writing, test
suite) is documented in [docs/klee-flow.md](docs/klee-flow.md).

The demos pin `rustc 1.81.0` via `rust-toolchain.toml`. The crate under
test must be compiled by a rustc whose bundled LLVM matches the LLVM
version KLEE was built against.

- `demos/klee-simple` makes a value symbolic and checks an arithmetic
  property (smoke test of the pipeline).
- `demos/klee-regex` verifies `regex` 1.x properties (`find`/`is_match`/
  `captures` agreement, span validity) over symbolic haystacks.
- `demos/klee-serde-json` verifies `serde_json` 1.0.x parser/serializer
  round-trips over symbolic JSON-ish input strings.

Two local KLEE patches are applied to the `tools/klee` build (see
`lib/Core/Executor.cpp` in the KLEE tree):

1. `switch` instructions with >64-bit or negative concrete conditions
   (rustc emits i96 switches) use the full-precision APInt instead of
   `getZExtValue()` (which asserts). Upstream KLEE is affected.
2. NOTE: the KLEE v3.2 release tag ships `assert(0)` stubs for the LLVM
   >= 17 module instrumentation - build from the master branch instead.

Known limitations (SMT array theory): symbolic regex *patterns* make
regex-syntax compute byte-class tables from symbolic data, and haystacks
longer than a few bytes make the search index those tables at symbolic
positions; both can produce Z3 queries that do not terminate. The
bundled demo sizes are chosen to verify cleanly.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or
  http://www.apache.org/licenses/LICENSE-2.0)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or
  http://opensource.org/licenses/MIT)

at your option.

## Acknowledgements

The `propverify` crate is heavily based on the design and API of the wonderful
[proptest](https://github.com/AltSysrq/proptest)
property/fuzz-testing library.
The implementation also borrows techniques, tricks and code
from the implementation – you can learn a lot about how to write
an embedded DSL from reading the proptest code.

In turn, `proptest` was influenced by
the [Rust port of QuickCheck](https://github.com/burntsushi/quickcheck)
and
the [Hypothesis](https://hypothesis.works/) fuzzing/property testing library for Python.
(`proptest` also acknowledges `regex_generate` – but we have not yet implemented
regex strategies for this library.)

## Known limitations

This is not an officially supported Google product;
this is an early release of a research project
to enable experiments, feedback and contributions.
It is probably not useful to use on real projects at this stage
and it may change significantly in the future.

Our current goal is to make `propverify` as compatible with
`proptest` as possible but we are not there yet.
The most obvious features that are not even implemented are
support for
using regular expressions for string strategies,
the `Arbitrary` trait,
`proptest-derive`.

We would like the `propverify` library and the `cargo-verify` script
to work with as many Rust verification tools as possible
and we welcome pull requests to add support.
We expect that this will require design/interface changes.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally
submitted for inclusion in the
work by you, as defined in the Apache-2.0 license, shall be dual licensed as
above, without any
additional terms or conditions.

See [the contribution instructions](CONTRIBUTING.md) for further details.
