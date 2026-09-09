# Copyright 2021 The Rust verification tools Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# default target backend: override on command line
TGT = klee

# this rule comes first to make sure that it is the default target
default: rvt-$(TGT).bc

# LLVM version to use for compiling/linking bitcode.
# LLVM 18 matches both KLEE 3.x (built against LLVM 18) and
# rustc 1.81 (which bundles LLVM 18).
LLVM_VERSION ?= 18

CC = clang-${LLVM_VERSION}
CFLAGS = -emit-llvm
CFLAGS += -O1

LINK = llvm-link-${LLVM_VERSION}

C_SRCS := $(wildcard src/*.c)
OBJS := $(patsubst src/%.c, build_$(TGT)/%.o, $(C_SRCS))

build_$(TGT)/%.o: src/%.c
	mkdir -p build_$(TGT)
	$(CC) $(CFLAGS) $^ -c -o $@

rvt-$(TGT).bc: $(OBJS)
	$(LINK) $(OBJS) -o $@

clean::
	$(RM) $(OBJS)
	$(RM) rvt-$(TGT).bc

# End of Makefile
