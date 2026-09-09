// Copyright 2026 The Rust verification tools Authors
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

// std::thread::available_parallelism falls back to sched_getaffinity
// when /sys cannot be read. KLEE leaves sched_getaffinity unresolved,
// so the returned CPU mask (and hence the CPU count used e.g. by the
// regex crate to size its search pool) becomes symbolic, and loops
// bounded by it produce pathological solver queries. Report exactly
// one CPU instead.

#include <sched.h>
#include <string.h>

int sched_getaffinity(pid_t pid, size_t cpusetsize, cpu_set_t *mask) {
    (void)pid;
    memset(mask, 0, cpusetsize);
    if (cpusetsize > 0) {
        // Mark CPU 0 as available.
        ((unsigned char *)mask)[0] = 1;
    }
    // Number of bytes written (the kernel returns the size of the
    // cpumask in bytes, clamped to cpusetsize).
    return (int)(cpusetsize < sizeof(cpu_set_t) ? cpusetsize
                                                : sizeof(cpu_set_t));
}
