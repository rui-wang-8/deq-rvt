//! deq byte-region dump smoke test: hex_decode, the Rust twin of
//! tests/klee/c_hex_decode.c. The output buffer is dumped as a
//! little-endian bit-vector expression per explored path.

use verification_annotations::prelude::*;

fn hexval(c: u8) -> i32 {
    match c {
        b'0'..=b'9' => (c - b'0') as i32,
        b'a'..=b'f' => (c - b'a' + 10) as i32,
        b'A'..=b'F' => (c - b'A' + 10) as i32,
        _ => -1,
    }
}

/// Decode hex pairs; stops at the first invalid character.
fn hex_decode(out: &mut [u8], s: &[u8]) -> usize {
    let mut n = 0;
    let mut i = 0;
    while i + 1 < s.len() && n < out.len() {
        let hi = hexval(s[i]);
        let lo = hexval(s[i + 1]);
        if hi < 0 || lo < 0 {
            break;
        }
        out[n] = ((hi as u8) << 4) | lo as u8;
        n += 1;
        i += 2;
    }
    n
}

fn main() {
    // 2 hex characters -> 1 output byte.
    let mut input = [0u8; 2];
    verifier::make_symbolic_named(&mut input, "stdin");

    let mut out = [0u8; 1];
    let _n = hex_decode(&mut out, &input);

    // deq hook: dump the symbolic expression of the output buffer.
    verifier::dump_expr_bytes("out_hex", &out[..1]);
}
