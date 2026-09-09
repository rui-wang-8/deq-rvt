//! Verification of `serde_json` under KLEE.
//!
//! We symbolically generate JSON-ish input strings and check properties of
//! the parser/serializer that must hold for all inputs.

use serde_json::Value;
use verification_annotations::prelude::*;

fn main() {
    // A symbolic 4-character ASCII string (no NUL bytes).
    let s: String = verifier::verifier_nondet_ascii_string(3);

    // Parsing must either fail or produce a value.
    match serde_json::from_str::<Value>(&s) {
        Ok(value) => {
            // Round-trip: serialize then parse again; values must be equal.
            let s2 = serde_json::to_string(&value).expect("serialization cannot fail");
            let value2: Value =
                serde_json::from_str(&s2).expect("serialized JSON must parse");
            verifier::assert_eq!(
                value,
                value2,
                "serde_json parse(serialize(x)) == x"
            );
        }
        // Invalid JSON: rejected.
        Err(_) => {}
    }

    // `serde_json::from_str` and `serde_json::from_slice` must agree.
    let v1: Result<Value, _> = serde_json::from_str(&s);
    let v2: Result<Value, _> = serde_json::from_slice(s.as_bytes());
    verifier::assert!(
        v1.is_ok() == v2.is_ok(),
        "from_str and from_slice agree on success/failure"
    );
}
