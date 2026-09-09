// Copyright 2026 The Rust verification tools Authors
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

// The Rust standard library (since ~1.73) obtains the random keys used
// to seed hash maps by calling getrandom() through an `extern_weak`
// declaration (sys::pal::unix::rand). KLEE's libc does not provide
// getrandom, so the weak symbol resolves to a null pointer and the call
// fails with "invalid function pointer" as soon as any HashMap is
// created. This stub provides a deterministic implementation instead.

#include <stddef.h>
#include <sys/types.h>

ssize_t getrandom(void *buf, size_t buflen, unsigned int flags) {
    (void)flags;
    // Deterministic "entropy": leave the buffer zeroed.
    for (size_t i = 0; i < buflen; i++) {
        ((char *)buf)[i] = 0;
    }
    return (ssize_t)buflen;
}
