/*
 * Copyright 2021-2026 The Rust verification tools authors
 *
 * Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
 * http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
 * <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
 * option. This file may not be copied, modified, or distributed
 * except according to those terms.
 */

/*
 * Portable (non-intrinsic) implementations of the LLVM SIMD intrinsics
 * and bit-manipulation intrinsics that KLEE does not implement natively.
 *
 * rvt-patch-llvm (--intrinsics) rewrites calls to LLVM intrinsics such as
 *
 *     call i64 @llvm.vector.reduce.add.v2i64(<2 x i64> %x)
 *
 * into calls to the corresponding functions in this library:
 *
 *     call i64 @llvm_vector_reduce_add_v2i64(<2 x i64> %x)
 *
 * i.e. the '.' characters in the intrinsic name are replaced by '_'.
 *
 * This file is written in C (rather than Rust) so that it can be compiled
 * directly to LLVM-18 bitcode with clang-18: no nightly Rust compiler and
 * no `repr(simd)` support is required.
 */

typedef signed char i8x16 __attribute__((ext_vector_type(16)));
typedef unsigned char u8x16 __attribute__((ext_vector_type(16)));
typedef short i16x8 __attribute__((ext_vector_type(8)));
typedef unsigned short u16x8 __attribute__((ext_vector_type(8)));
typedef int i32x4 __attribute__((ext_vector_type(4)));
typedef unsigned int u32x4 __attribute__((ext_vector_type(4)));
typedef long long i64x2 __attribute__((ext_vector_type(2)));
typedef unsigned long long u64x2 __attribute__((ext_vector_type(2)));
typedef long long i64x4 __attribute__((ext_vector_type(4)));
typedef unsigned long long u64x4 __attribute__((ext_vector_type(4)));
typedef int i32x2 __attribute__((ext_vector_type(2)));
typedef unsigned int u32x2 __attribute__((ext_vector_type(2)));

typedef signed char i8x32 __attribute__((ext_vector_type(32)));
typedef unsigned char u8x32 __attribute__((ext_vector_type(32)));
typedef short i16x16 __attribute__((ext_vector_type(16)));
typedef unsigned short u16x16 __attribute__((ext_vector_type(16)));
typedef int i32x8 __attribute__((ext_vector_type(8)));
typedef unsigned int u32x8 __attribute__((ext_vector_type(8)));
typedef long long i64x8 __attribute__((ext_vector_type(8)));
typedef unsigned long long u64x8 __attribute__((ext_vector_type(8)));

/////////////////////////////////////////////////////////////////
// Bit manipulation intrinsics
//
// NOTE: do not use clang's __builtin_bitreverse* here: they lower
// to `llvm.bitreverse.*`, which rvt-patch-llvm would then rewrite
// (together with all other uses) into a call to this very function,
// creating an infinite recursion. Implement the operation manually.
/////////////////////////////////////////////////////////////////

static unsigned int bitrev32(unsigned int x) {
    x = ((x & 0x55555555u) << 1) | ((x >> 1) & 0x55555555u);
    x = ((x & 0x33333333u) << 2) | ((x >> 2) & 0x33333333u);
    x = ((x & 0x0f0f0f0fu) << 4) | ((x >> 4) & 0x0f0f0f0fu);
    x = (x << 24) | ((x & 0xff00u) << 8) | ((x >> 8) & 0xff00u) | (x >> 24);
    return x;
}

static unsigned long long bitrev64(unsigned long long x) {
    unsigned int lo = bitrev32((unsigned int)(x >> 32));
    unsigned int hi = bitrev32((unsigned int)x);
    return ((unsigned long long)lo) | ((unsigned long long)hi << 32);
}

int llvm_bitreverse_i32(int x) {
    return (int)bitrev32((unsigned int)x);
}

long long llvm_bitreverse_i64(long long x) {
    return (long long)bitrev64((unsigned long long)x);
}

/////////////////////////////////////////////////////////////////
// x86 intrinsics
/////////////////////////////////////////////////////////////////

/* _mm_pause - no-op */
void llvm_x86_sse2_pause(void) {
}

/* _xgetbv - report no extended control register state */
long long llvm_x86_xgetbv(int ecx) {
    (void)ecx;
    return 0;
}

/* _mm_srli_epi8/16/32/64 (SSE2) */
u8x16 llvm_x86_sse2_psrli_b(u8x16 a, int imm8) {
    return a >> imm8;
}

u16x8 llvm_x86_sse2_psrli_w(u16x8 a, int imm8) {
    return a >> imm8;
}

u32x4 llvm_x86_sse2_psrli_d(u32x4 a, int imm8) {
    return a >> imm8;
}

u64x2 llvm_x86_sse2_psrli_q(u64x2 a, int imm8) {
    return a >> imm8;
}

/* _mm256_srli_epi8/16/32/64 (AVX2) */
u8x32 llvm_x86_avx2_psrli_b(u8x32 a, int imm8) {
    return a >> imm8;
}

u16x16 llvm_x86_avx2_psrli_w(u16x16 a, int imm8) {
    return a >> imm8;
}

u32x8 llvm_x86_avx2_psrli_d(u32x8 a, int imm8) {
    return a >> imm8;
}

u64x4 llvm_x86_avx2_psrli_q(u64x4 a, int imm8) {
    return a >> imm8;
}

/* _mm_movemask_epi8 (SSE2) */
int llvm_x86_sse2_pmovmskb_128(u8x16 a) {
    int r = 0;
    for (int i = 0; i < 16; i++) {
        r |= (a[i] >> 7 & 1) << i;
    }
    return r;
}

/* _mm256_movemask_epi8 (AVX2) */
int llvm_x86_avx2_pmovmskb(u8x32 a) {
    int r = 0;
    for (int i = 0; i < 32; i++) {
        r |= (a[i] >> 7 & 1) << i;
    }
    return r;
}

/* _mm_shuffle_epi8 (SSSE3) */
u8x16 llvm_x86_ssse3_pshuf_b_128(u8x16 a, u8x16 b) {
    u8x16 r;
    for (int i = 0; i < 16; i++) {
        r[i] = a[b[i] & 15];
    }
    return r;
}

/* _mm256_shuffle_epi8 (AVX2) */
u8x32 llvm_x86_avx2_pshuf_b(u8x32 a, u8x32 b) {
    u8x32 r;
    for (int i = 0; i < 32; i++) {
        r[i] = a[b[i] & 31];
    }
    return r;
}

/////////////////////////////////////////////////////////////////
// Vector reduction intrinsics
// (llvm.experimental.vector.reduce.* is the pre-LLVM-12 name;
//  llvm.vector.reduce.* is the modern name)
/////////////////////////////////////////////////////////////////

long long llvm_experimental_vector_reduce_add_v2i64(i64x2 a) {
    return a[0] + a[1];
}

long long llvm_experimental_vector_reduce_or_v2i64(i64x2 a) {
    return a[0] | a[1];
}

long long llvm_vector_reduce_add_v2i64(i64x2 a) {
    return a[0] + a[1];
}

/* NOTE: llvm.vector.reduce.add.{v4i64,v8i32,v16i16,v32i8,v2i32} are defined
 * in simd_emulation_ll.ll with exact IR signatures: on x86-64, the C ABI
 * passes 256-bit vectors indirectly (byval pointer) and passes <2 x i32>
 * as a `double`, changing the IR signature. */
