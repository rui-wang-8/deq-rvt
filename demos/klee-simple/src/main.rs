use verification_annotations::prelude::*;

/// A tiny example that exercises the RVT -> KLEE pipeline:
/// make some values symbolic and check a property that must hold
/// for all possible inputs.
fn main() {
    // Symbolic 32-bit value.
    let x: u32 = VerifierNonDet::verifier_nondet(0);

    // Exercise the allocator and (implicitly) std's init code.
    let mut v = vec![x, x.wrapping_add(1)];
    v.push(x.wrapping_mul(3));

    // Property: x + x is always even.
    verifier::assert!(x.wrapping_add(x) % 2 == 0, "x + x is always even");

    // Keep the vector alive so the compiler can't optimize it away.
    verifier::assert!(v.len() == 3);
}
