#!/usr/bin/env bash
# Set up the environment for running the KLEE backend of cargo-verify
# with the modernized RVT toolchain.
#
# Toolchain matrix:
#   - KLEE 3.x built against LLVM 18  (tools/klee)
#   - rustc 1.81.x (bundles LLVM 18)  (see the demos' rust-toolchain.toml)
#   - clang/llvm-link/llvm-nm 18 from the system
#
# Usage: source scripts/rvt-klee-env.sh

SCRIPTDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export RVT_DIR="$(dirname "${SCRIPTDIR}")"
export KLEE_DIR="${RVT_DIR}/tools/klee"
export CARGO_HOME="${RVT_DIR}/.cargo-home"
export PATH="${KLEE_DIR}/bin:${RVT_DIR}/tools/bin:${PATH}"

echo "RVT_DIR=${RVT_DIR}"
echo "KLEE_DIR=${KLEE_DIR}"
echo "klee: $(${KLEE_DIR}/bin/klee --version 2>/dev/null | head -1)"
echo "cargo-verify: ${RVT_DIR}/tools/bin/cargo-verify"
echo "Use: cargo-verify --backend=klee --manifest-path demos/<crate>/Cargo.toml"
echo "Run the lit test suite: scripts/run-tests.sh"
