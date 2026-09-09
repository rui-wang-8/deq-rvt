// Copyright 2026 The Rust verification tools Authors
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

// KLEE (with --libc=klee and without --posix-runtime) leaves the file
// system entry points unresolved: calls to open() etc. return fresh
// symbolic values, and code like std::thread::available_parallelism
// (used by the regex crate) then loops forever in read_to_end on the
// symbolic results. Verification runs do not need a file system, so
// provide deterministic implementations that report ENOENT: std falls
// back to its default behaviour.

#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>

int open(const char *pathname, int flags, ...) {
    (void)pathname;
    (void)flags;
    errno = ENOENT;
    return -1;
}

int open64(const char *pathname, int flags, ...) {
    (void)pathname;
    (void)flags;
    errno = ENOENT;
    return -1;
}

int openat(int dirfd, const char *pathname, int flags, ...) {
    (void)dirfd;
    (void)pathname;
    (void)flags;
    errno = ENOENT;
    return -1;
}

int openat64(int dirfd, const char *pathname, int flags, ...) {
    (void)dirfd;
    (void)pathname;
    (void)flags;
    errno = ENOENT;
    return -1;
}
