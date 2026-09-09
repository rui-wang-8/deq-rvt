//! Verification of the `regex` crate under KLEE.
//!
//! The haystack is fully symbolic; the pattern is concrete.
//!
//! Note on scope: KLEE explores every path through the regex search
//! engine, and the resulting SMT queries (byte-class table lookups at
//! symbolic indexes) are hard for Z3's array theory. A 2-character
//! haystack verifies cleanly; larger haystacks and symbolic *patterns*
//! (which make regex-syntax build byte-class tables from symbolic data)
//! can produce queries that do not terminate in the solver.

use regex::Regex;
use verification_annotations::prelude::*;

fn main() {
    // A symbolic 2-character haystack.
    let text: String = verifier::verifier_nondet_ascii_string(2);

    let re = Regex::new("a*b|c").expect("pattern is valid");
    let m = re.find(&text);

    // is_match and find must agree.
    verifier::assert!(
        m.is_some() == re.is_match(&text),
        "find and is_match agree"
    );

    if let Some(m) = m {
        // The match must be a valid, in-bounds span of the haystack.
        verifier::assert!(m.start() <= m.end());
        verifier::assert!(m.end() <= text.len());
    }

    // Captures agree with find.
    let caps = re.captures(&text);
    verifier::assert!(
        caps.is_some() == m.is_some(),
        "captures and find agree"
    );
}
