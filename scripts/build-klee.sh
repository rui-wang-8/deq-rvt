#!/usr/bin/env bash
# Build and install the RVT KLEE fork (tools/klee-src, branch rvt-for-rust)
# into tools/klee.
#
# Usage:
#   LLVM_VERSION=22 scripts/build-klee.sh     # -> tools/klee-22
#   scripts/build-klee.sh                     # -> tools/klee-18 (default)
#
# Prerequisites (Ubuntu 24.04 package names; substitute the LLVM major):
#   cmake build-essential clang-N llvm-N llvm-N-dev libz3-dev
#
# The oss-fuzz base image exports CFLAGS/CXXFLAGS aimed at its own sanitizer
# build (-stdlib=libc++); they must not leak into KLEE, so they are cleared
# here unless the caller set KLEE_KEEP_FUZZ_FLAGS=1.
#
# See docs/klee-flow.md for details.

set -e

SCRIPTDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RVT_DIR="$(dirname "${SCRIPTDIR}")"

KLEE_SRC="${RVT_DIR}/tools/klee-src"
# One KLEE build per LLVM major version: KLEE can only read bitcode emitted by
# its own LLVM major, so a rustc upgrade means a new KLEE build.  Everything
# below derives from LLVM_VERSION; nothing is hard-coded to one version.
LLVM_VERSION="${LLVM_VERSION:-18}"
BUILD_DIR="${BUILD_DIR:-${RVT_DIR}/tools/klee-build-${LLVM_VERSION}}"
PREFIX="${PREFIX:-${RVT_DIR}/tools/klee-${LLVM_VERSION}}"
LLVM_DIR="${LLVM_DIR:-/usr/lib/llvm-${LLVM_VERSION}/lib/cmake/llvm}"
CLANG="${CLANG:-/usr/bin/clang-${LLVM_VERSION}}"
CLANGXX="${CLANGXX:-/usr/bin/clang++-${LLVM_VERSION}}"

# `tools/klee-src` is a submodule, so its `.git` is a *file* holding a gitdir
# pointer, not a directory.  Testing `-d` rejected a perfectly good checkout
# and made every documented rebuild fail before cmake ran.
if ! git -C "${KLEE_SRC}" rev-parse --git-dir >/dev/null 2>&1; then
    echo "ERROR: KLEE fork not found at ${KLEE_SRC}" >&2
    echo "Clone upstream KLEE there and apply klee/patches/*.patch (see docs/klee-flow.md)." >&2
    exit 1
fi
if [ ! -f "${LLVM_DIR}/LLVMConfig.cmake" ]; then
    echo "ERROR: LLVM ${LLVM_VERSION} CMake config not found at ${LLVM_DIR}" >&2
    exit 1
fi

# The KLEE branch should be rvt-for-rust (upstream master is missing the
# Rust-specific switch fix; the v3.2 release tag is broken for LLVM >= 17).
BRANCH="$(git -C "${KLEE_SRC}" rev-parse --abbrev-ref HEAD)"
echo "Building KLEE fork at ${KLEE_SRC} (branch ${BRANCH})"

Z3_ARGS=()
if [ -n "${Z3_INCLUDE_DIRS}" ]; then
    Z3_ARGS+=("-DZ3_INCLUDE_DIRS=${Z3_INCLUDE_DIRS}")
fi
if [ -n "${Z3_LIBRARIES}" ]; then
    Z3_ARGS+=("-DZ3_LIBRARIES=${Z3_LIBRARIES}")
fi

# Neutralise the fuzzing image's compiler flags (see header comment).
if [ -z "${KLEE_KEEP_FUZZ_FLAGS:-}" ]; then
    unset CFLAGS CXXFLAGS LDFLAGS
fi

cmake -S "${KLEE_SRC}" -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
    -DLLVM_DIR="${LLVM_DIR}" \
    -DLLVMCC="${CLANG}" \
    -DLLVMCXX="${CLANGXX}" \
    -DCMAKE_C_COMPILER="${CLANG}" \
    -DCMAKE_CXX_COMPILER="${CLANGXX}" \
    -DENABLE_SOLVER_Z3=ON \
    -DENABLE_TCMALLOC=OFF \
    -DENABLE_UNIT_TESTS=OFF \
    -DENABLE_SYSTEM_TESTS=OFF \
    -DKLEE_ENABLE_UNIT_TESTS=OFF \
    -DKLEE_ENABLE_SYSTEM_TESTS=OFF \
    -DENABLE_DOXYGEN=OFF \
    "${Z3_ARGS[@]}"

JOBS="${JOBS:-$(nproc)}"
make -C "${BUILD_DIR}" -j"${JOBS}"
make -C "${BUILD_DIR}" install

# `make install` does not ship the runtest shim that harness crates link
# against (-lkleeRuntest), so copy it in explicitly.
mkdir -p "${PREFIX}/lib"
cp -a "${BUILD_DIR}"/lib/libkleeRuntest.so* "${PREFIX}/lib/" 2>/dev/null || true

echo
echo "Installed:"
"${PREFIX}/bin/klee" --version | head -2
