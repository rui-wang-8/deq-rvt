// Copyright 2026 The Rust verification tools Authors
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

// The Rust standard library references statx through an `extern_weak`
// declaration (sys::pal::unix::fs). KLEE's libc does not provide statx,
// so the weak symbol resolves to a null pointer and the call fails with
// "invalid function pointer" (e.g. when std::thread::available_parallelism
// probes the file system). Report ENOSYS so that std falls back to its
// default behaviour.

#include <errno.h>
#include <stddef.h>

struct statx_stub;

int statx(int dirfd, const char *pathname, int flags, unsigned int mask,
          struct statx_stub *statxbuf) {
    (void)dirfd;
    (void)pathname;
    (void)flags;
    (void)mask;
    (void)statxbuf;
    errno = ENOSYS;
    return -1;
}
