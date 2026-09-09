# Copyright 2021 The Rust verification tools Authors.
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# This rule comes first to make sure that it is the default target
default: simd_emulation.bc

# LLVM version to use for compiling/linking bitcode.
# LLVM 18 matches both KLEE 3.x (built against LLVM 18) and
# rustc 1.81 (which bundles LLVM 18).
LLVM_VERSION ?= 18

CC = clang-${LLVM_VERSION}
# NOTE: -O0 is deliberate: the optimizer would recognize the bitreverse
# implementations below and re-emit the very intrinsics we are emulating.
CFLAGS = -O0 -emit-llvm
AS = llvm-as-${LLVM_VERSION}
LINK = llvm-link-${LLVM_VERSION}

C_SRCS := $(wildcard *.c)
LL_SRCS := $(wildcard *.ll)
OBJS := $(patsubst %.c, build/%.o, $(C_SRCS))
OBJS += $(patsubst %.ll, build/%.bc, $(LL_SRCS))

build/%.o: %.c
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $< -c -o $@

build/%.bc: %.ll
	mkdir -p $(dir $@)
	$(AS) $< -o $@

simd_emulation.bc: $(OBJS)
	$(LINK) $(OBJS) -o $@

clean::
	$(RM) -r build
	$(RM) simd_emulation.bc

# End of Makefile
