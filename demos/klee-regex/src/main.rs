//! Verification of the `regex` crate under KLEE.
//!
//! We symbolically generate small patterns and haystacks and check
//! consistency properties between the different `regex` APIs.

use regex::Regex;
use verification_annotations::prelude::*;

fn main() {
    // A symbolic 3-character pattern and a 4-character haystack.
    let pat: String = verifier::verifier_nondet_ascii_string(2);
    let text: String = verifier::verifier_nondet_ascii_string(3);

    match Regex::new(&pat) {
        Ok(re) => {
            let m = re.find(&text);

            // is_match and find must agree.
            verifier::assert!(
                m.is_some() == re.is_match(&text),
                "find and is_match agree"
            );

            if let Some(m) = m {
                // The match must be a valid, in-bounds span of the haystack
                // and its contents must really match the pattern.
                verifier::assert!(m.start() <= m.end());
                verifier::assert!(m.end() <= text.len());
                verifier::assert!(
                    re.is_match(m.as_str()),
                    "the matched slice matches the pattern"
                );
                verifier::assert!(text.contains(m.as_str()));
            }

            // Empty regex matches everything, including the empty string.
            if pat.is_empty() {
                verifier::assert!(re.is_match(""));
            }
        }
        // Invalid pattern: rejected.
        Err(_) => {}
    }
}
