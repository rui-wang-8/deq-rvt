#!/usr/bin/env bash
# Run the RVT-for-KLEE test suite (lit-based). See tests/README.md.

set -e

SCRIPTDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RVT_DIR="$(dirname "${SCRIPTDIR}")"

export RVT_DIR
export KLEE_DIR="${RVT_DIR}/tools/klee"
export CARGO_HOME="${RVT_DIR}/.cargo-home"
export LLVM_VERSION=18
export PATH="${KLEE_DIR}/bin:${RVT_DIR}/tools/bin:${PATH}"
# pip --user installs console scripts into ~/.local/bin.
if [ -d "${HOME}/.local/bin" ]; then
    export PATH="${HOME}/.local/bin:${PATH}"
fi

# Pick a lit runner: prefer the Python package driven through
# scripts/lit_runner.py, which executes -j1 in-process (works without
# POSIX semaphores / /dev/shm); it falls back to lit's own
# multiprocessing pool for -jN>1.
if python3 -c "import lit" 2>/dev/null; then
    LIT=(python3 "${SCRIPTDIR}/lit_runner.py")
elif command -v lit >/dev/null 2>&1; then
    LIT=(lit)
elif command -v llvm-lit >/dev/null 2>&1; then
    LIT=(llvm-lit)
else
    echo "ERROR: lit not found (install it with: pip3 install --user lit)" >&2
    exit 1
fi

# Single worker by default: the tests run KLEE, which is single-threaded
# per process, and lit's multi-process pool needs POSIX semaphores (not
# available in every environment). Pass e.g. -j4 to override.
#
# lit >= 18 requires at least one test path and rejects paths mixed with
# an explicit suite dir, so: when the caller passes test paths, hand them
# to lit directly (the suite is discovered from the path); otherwise run
# the whole suite directory.
has_path=0
for arg in "$@"; do
    case "$arg" in
        -*) ;;
        *) has_path=1 ;;
    esac
done

if [ "$has_path" -eq 1 ]; then
    exec "${LIT[@]}" -j1 --timeout=1200 "$@"
else
    exec "${LIT[@]}" "${RVT_DIR}/tests" -j1 --timeout=1200 "$@"
fi
