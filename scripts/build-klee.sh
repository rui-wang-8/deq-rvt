#!/usr/bin/env bash
# Build and install the RVT KLEE fork (tools/klee-src, branch rvt-for-rust)
# into tools/klee.
#
# Prerequisites (Ubuntu 24.04 package names):
#   cmake build-essential clang-18 llvm-18 llvm-18-dev libz3-dev
#
# See docs/klee-flow.md for details.

set -e

SCRIPTDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RVT_DIR="$(dirname "${SCRIPTDIR}")"

KLEE_SRC="${RVT_DIR}/tools/klee-src"
BUILD_DIR="${RVT_DIR}/tools/klee-build"
PREFIX="${RVT_DIR}/tools/klee"
LLVM_DIR="${LLVM_DIR:-/usr/lib/llvm-18/lib/cmake/llvm}"

if [ ! -d "${KLEE_SRC}/.git" ]; then
    echo "ERROR: KLEE fork not found at ${KLEE_SRC}" >&2
    echo "Clone upstream KLEE there and apply klee/patches/*.patch (see docs/klee-flow.md)." >&2
    exit 1
fi
if [ ! -f "${LLVM_DIR}/LLVMConfig.cmake" ]; then
    echo "ERROR: LLVM 18 CMake config not found at ${LLVM_DIR}" >&2
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

cmake -S "${KLEE_SRC}" -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
    -DLLVM_DIR="${LLVM_DIR}" \
    -DLLVMCC=/usr/bin/clang-18 \
    -DLLVMCXX=/usr/bin/clang++-18 \
    -DCMAKE_C_COMPILER=/usr/bin/clang-18 \
    -DCMAKE_CXX_COMPILER=/usr/bin/clang++-18 \
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

echo
echo "Installed:"
"${PREFIX}/bin/klee" --version | head -2
