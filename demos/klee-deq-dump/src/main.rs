//! deq SMT2-dump smoke test: the Rust twin of deq's C smoke computation.
//!
//! Under KLEE (with KLEE_DUMP_DIR set) the mapped output variable is
//! dumped as a self-contained SMT-LIB expression per explored path, so
//! it can be checked for equivalence against a C (or another Rust)
//! implementation of the same computation.

use verification_annotations::prelude::*;

fn combine(x: u32, y: u32) -> u64 {
    let mut r: u64 = ((x as u64) << 32) | y as u64;
    r ^= r >> 11;
    r = r.wrapping_mul(0x9e3779b97f4a7c15u64);
    r
}

fn main() {
    // deq convention: inputs of equivalent implementations share the
    // same KLEE names, so the dumps of both sides declare identical
    // input arrays and the equivalence query equates the inputs.
    let mut x: u32 = 0;
    let mut y: u32 = 0;
    verifier::make_symbolic_named(&mut x, "stdin");
    verifier::make_symbolic_named(&mut y, "stdin");

    let r = combine(x, y);

    // deq hook: dump the symbolic expression of the output variable.
    verifier::dump_expr("result_combine", r);
}
