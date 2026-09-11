; Portable (non-intrinsic) implementations of LLVM SIMD intrinsics that
; cannot be expressed in C with the exact IR signature.
;
; On x86-64, the C ABI passes 256-bit (and larger) vectors indirectly
; (via a `byval` pointer), so the C implementations in simd_emulation.c
; get IR signatures that differ from the intrinsics they emulate. This
; file provides the same operations with the exact `<N x iN>` signatures
; that rvt-patch-llvm can substitute directly.
;
; See simd_emulation.c for the naming convention ('.' -> '_').

target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

; Bitmask reductions (used e.g. by memchr's masked search).

define i1 @llvm_vector_reduce_and_v16i1(<16 x i1> %a) {
entry:
  %e0 = extractelement <16 x i1> %a, i32 0
  %e1 = extractelement <16 x i1> %a, i32 1
  %e2 = extractelement <16 x i1> %a, i32 2
  %e3 = extractelement <16 x i1> %a, i32 3
  %e4 = extractelement <16 x i1> %a, i32 4
  %e5 = extractelement <16 x i1> %a, i32 5
  %e6 = extractelement <16 x i1> %a, i32 6
  %e7 = extractelement <16 x i1> %a, i32 7
  %e8 = extractelement <16 x i1> %a, i32 8
  %e9 = extractelement <16 x i1> %a, i32 9
  %e10 = extractelement <16 x i1> %a, i32 10
  %e11 = extractelement <16 x i1> %a, i32 11
  %e12 = extractelement <16 x i1> %a, i32 12
  %e13 = extractelement <16 x i1> %a, i32 13
  %e14 = extractelement <16 x i1> %a, i32 14
  %e15 = extractelement <16 x i1> %a, i32 15
  %s0 = and i1 %e0, %e1
  %s1 = and i1 %e2, %e3
  %s2 = and i1 %e4, %e5
  %s3 = and i1 %e6, %e7
  %s4 = and i1 %e8, %e9
  %s5 = and i1 %e10, %e11
  %s6 = and i1 %e12, %e13
  %s7 = and i1 %e14, %e15
  %t0 = and i1 %s0, %s1
  %t1 = and i1 %s2, %s3
  %t2 = and i1 %s4, %s5
  %t3 = and i1 %s6, %s7
  %u0 = and i1 %t0, %t1
  %u1 = and i1 %t2, %t3
  %s = and i1 %u0, %u1
  ret i1 %s
}

define i1 @llvm_vector_reduce_or_v16i1(<16 x i1> %a) {
entry:
  %e0 = extractelement <16 x i1> %a, i32 0
  %e1 = extractelement <16 x i1> %a, i32 1
  %e2 = extractelement <16 x i1> %a, i32 2
  %e3 = extractelement <16 x i1> %a, i32 3
  %e4 = extractelement <16 x i1> %a, i32 4
  %e5 = extractelement <16 x i1> %a, i32 5
  %e6 = extractelement <16 x i1> %a, i32 6
  %e7 = extractelement <16 x i1> %a, i32 7
  %e8 = extractelement <16 x i1> %a, i32 8
  %e9 = extractelement <16 x i1> %a, i32 9
  %e10 = extractelement <16 x i1> %a, i32 10
  %e11 = extractelement <16 x i1> %a, i32 11
  %e12 = extractelement <16 x i1> %a, i32 12
  %e13 = extractelement <16 x i1> %a, i32 13
  %e14 = extractelement <16 x i1> %a, i32 14
  %e15 = extractelement <16 x i1> %a, i32 15
  %s0 = or i1 %e0, %e1
  %s1 = or i1 %e2, %e3
  %s2 = or i1 %e4, %e5
  %s3 = or i1 %e6, %e7
  %s4 = or i1 %e8, %e9
  %s5 = or i1 %e10, %e11
  %s6 = or i1 %e12, %e13
  %s7 = or i1 %e14, %e15
  %t0 = or i1 %s0, %s1
  %t1 = or i1 %s2, %s3
  %t2 = or i1 %s4, %s5
  %t3 = or i1 %s6, %s7
  %u0 = or i1 %t0, %t1
  %u1 = or i1 %t2, %t3
  %s = or i1 %u0, %u1
  ret i1 %s
}

define i32 @llvm_vector_reduce_add_v2i32(<2 x i32> %a) {
entry:
  %e0 = extractelement <2 x i32> %a, i32 0
  %e1 = extractelement <2 x i32> %a, i32 1
  %s = add i32 %e0, %e1
  ret i32 %s
}

define i32 @llvm_vector_reduce_add_v4i32(<4 x i32> %a) {
entry:
  %e0 = extractelement <4 x i32> %a, i32 0
  %e1 = extractelement <4 x i32> %a, i32 1
  %e2 = extractelement <4 x i32> %a, i32 2
  %e3 = extractelement <4 x i32> %a, i32 3
  %s01 = add i32 %e0, %e1
  %s23 = add i32 %e2, %e3
  %s = add i32 %s01, %s23
  ret i32 %s
}

define i16 @llvm_vector_reduce_add_v8i16(<8 x i16> %a) {
entry:
  %e0 = extractelement <8 x i16> %a, i32 0
  %e1 = extractelement <8 x i16> %a, i32 1
  %e2 = extractelement <8 x i16> %a, i32 2
  %e3 = extractelement <8 x i16> %a, i32 3
  %e4 = extractelement <8 x i16> %a, i32 4
  %e5 = extractelement <8 x i16> %a, i32 5
  %e6 = extractelement <8 x i16> %a, i32 6
  %e7 = extractelement <8 x i16> %a, i32 7
  %s0 = add i16 %e0, %e1
  %s1 = add i16 %e2, %e3
  %s2 = add i16 %e4, %e5
  %s3 = add i16 %e6, %e7
  %t0 = add i16 %s0, %s1
  %t1 = add i16 %s2, %s3
  %s = add i16 %t0, %t1
  ret i16 %s
}

define i8 @llvm_vector_reduce_add_v16i8(<16 x i8> %a) {
entry:
  %e0 = extractelement <16 x i8> %a, i32 0
  %e1 = extractelement <16 x i8> %a, i32 1
  %e2 = extractelement <16 x i8> %a, i32 2
  %e3 = extractelement <16 x i8> %a, i32 3
  %e4 = extractelement <16 x i8> %a, i32 4
  %e5 = extractelement <16 x i8> %a, i32 5
  %e6 = extractelement <16 x i8> %a, i32 6
  %e7 = extractelement <16 x i8> %a, i32 7
  %e8 = extractelement <16 x i8> %a, i32 8
  %e9 = extractelement <16 x i8> %a, i32 9
  %e10 = extractelement <16 x i8> %a, i32 10
  %e11 = extractelement <16 x i8> %a, i32 11
  %e12 = extractelement <16 x i8> %a, i32 12
  %e13 = extractelement <16 x i8> %a, i32 13
  %e14 = extractelement <16 x i8> %a, i32 14
  %e15 = extractelement <16 x i8> %a, i32 15
  %s0 = add i8 %e0, %e1
  %s1 = add i8 %e2, %e3
  %s2 = add i8 %e4, %e5
  %s3 = add i8 %e6, %e7
  %s4 = add i8 %e8, %e9
  %s5 = add i8 %e10, %e11
  %s6 = add i8 %e12, %e13
  %s7 = add i8 %e14, %e15
  %t0 = add i8 %s0, %s1
  %t1 = add i8 %s2, %s3
  %t2 = add i8 %s4, %s5
  %t3 = add i8 %s6, %s7
  %u0 = add i8 %t0, %t1
  %u1 = add i8 %t2, %t3
  %s = add i8 %u0, %u1
  ret i8 %s
}

define i64 @llvm_vector_reduce_add_v4i64(<4 x i64> %a) {
entry:
  %e0 = extractelement <4 x i64> %a, i32 0
  %e1 = extractelement <4 x i64> %a, i32 1
  %e2 = extractelement <4 x i64> %a, i32 2
  %e3 = extractelement <4 x i64> %a, i32 3
  %s01 = add i64 %e0, %e1
  %s23 = add i64 %e2, %e3
  %s = add i64 %s01, %s23
  ret i64 %s
}

define i32 @llvm_vector_reduce_add_v8i32(<8 x i32> %a) {
entry:
  %e0 = extractelement <8 x i32> %a, i32 0
  %e1 = extractelement <8 x i32> %a, i32 1
  %e2 = extractelement <8 x i32> %a, i32 2
  %e3 = extractelement <8 x i32> %a, i32 3
  %e4 = extractelement <8 x i32> %a, i32 4
  %e5 = extractelement <8 x i32> %a, i32 5
  %e6 = extractelement <8 x i32> %a, i32 6
  %e7 = extractelement <8 x i32> %a, i32 7
  %s0 = add i32 %e0, %e1
  %s1 = add i32 %e2, %e3
  %s2 = add i32 %e4, %e5
  %s3 = add i32 %e6, %e7
  %t0 = add i32 %s0, %s1
  %t1 = add i32 %s2, %s3
  %s = add i32 %t0, %t1
  ret i32 %s
}

define i16 @llvm_vector_reduce_add_v16i16(<16 x i16> %a) {
entry:
  %r = alloca <16 x i16>, align 32
  store <16 x i16> %a, ptr %r, align 32
  %p = load <16 x i16>, ptr %r, align 32
  %e0 = extractelement <16 x i16> %p, i32 0
  %e1 = extractelement <16 x i16> %p, i32 1
  %e2 = extractelement <16 x i16> %p, i32 2
  %e3 = extractelement <16 x i16> %p, i32 3
  %e4 = extractelement <16 x i16> %p, i32 4
  %e5 = extractelement <16 x i16> %p, i32 5
  %e6 = extractelement <16 x i16> %p, i32 6
  %e7 = extractelement <16 x i16> %p, i32 7
  %e8 = extractelement <16 x i16> %p, i32 8
  %e9 = extractelement <16 x i16> %p, i32 9
  %e10 = extractelement <16 x i16> %p, i32 10
  %e11 = extractelement <16 x i16> %p, i32 11
  %e12 = extractelement <16 x i16> %p, i32 12
  %e13 = extractelement <16 x i16> %p, i32 13
  %e14 = extractelement <16 x i16> %p, i32 14
  %e15 = extractelement <16 x i16> %p, i32 15
  %s0 = add i16 %e0, %e1
  %s1 = add i16 %e2, %e3
  %s2 = add i16 %e4, %e5
  %s3 = add i16 %e6, %e7
  %s4 = add i16 %e8, %e9
  %s5 = add i16 %e10, %e11
  %s6 = add i16 %e12, %e13
  %s7 = add i16 %e14, %e15
  %t0 = add i16 %s0, %s1
  %t1 = add i16 %s2, %s3
  %t2 = add i16 %s4, %s5
  %t3 = add i16 %s6, %s7
  %u0 = add i16 %t0, %t1
  %u1 = add i16 %t2, %t3
  %s = add i16 %u0, %u1
  ret i16 %s
}

define i8 @llvm_vector_reduce_add_v32i8(<32 x i8> %a) {
entry:
  %e0 = extractelement <32 x i8> %a, i32 0
  %e1 = extractelement <32 x i8> %a, i32 1
  %e2 = extractelement <32 x i8> %a, i32 2
  %e3 = extractelement <32 x i8> %a, i32 3
  %e4 = extractelement <32 x i8> %a, i32 4
  %e5 = extractelement <32 x i8> %a, i32 5
  %e6 = extractelement <32 x i8> %a, i32 6
  %e7 = extractelement <32 x i8> %a, i32 7
  %e8 = extractelement <32 x i8> %a, i32 8
  %e9 = extractelement <32 x i8> %a, i32 9
  %e10 = extractelement <32 x i8> %a, i32 10
  %e11 = extractelement <32 x i8> %a, i32 11
  %e12 = extractelement <32 x i8> %a, i32 12
  %e13 = extractelement <32 x i8> %a, i32 13
  %e14 = extractelement <32 x i8> %a, i32 14
  %e15 = extractelement <32 x i8> %a, i32 15
  %e16 = extractelement <32 x i8> %a, i32 16
  %e17 = extractelement <32 x i8> %a, i32 17
  %e18 = extractelement <32 x i8> %a, i32 18
  %e19 = extractelement <32 x i8> %a, i32 19
  %e20 = extractelement <32 x i8> %a, i32 20
  %e21 = extractelement <32 x i8> %a, i32 21
  %e22 = extractelement <32 x i8> %a, i32 22
  %e23 = extractelement <32 x i8> %a, i32 23
  %e24 = extractelement <32 x i8> %a, i32 24
  %e25 = extractelement <32 x i8> %a, i32 25
  %e26 = extractelement <32 x i8> %a, i32 26
  %e27 = extractelement <32 x i8> %a, i32 27
  %e28 = extractelement <32 x i8> %a, i32 28
  %e29 = extractelement <32 x i8> %a, i32 29
  %e30 = extractelement <32 x i8> %a, i32 30
  %e31 = extractelement <32 x i8> %a, i32 31
  %s0 = add i8 %e0, %e1
  %s1 = add i8 %e2, %e3
  %s2 = add i8 %e4, %e5
  %s3 = add i8 %e6, %e7
  %s4 = add i8 %e8, %e9
  %s5 = add i8 %e10, %e11
  %s6 = add i8 %e12, %e13
  %s7 = add i8 %e14, %e15
  %s8 = add i8 %e16, %e17
  %s9 = add i8 %e18, %e19
  %s10 = add i8 %e20, %e21
  %s11 = add i8 %e22, %e23
  %s12 = add i8 %e24, %e25
  %s13 = add i8 %e26, %e27
  %s14 = add i8 %e28, %e29
  %s15 = add i8 %e30, %e31
  %t0 = add i8 %s0, %s1
  %t1 = add i8 %s2, %s3
  %t2 = add i8 %s4, %s5
  %t3 = add i8 %s6, %s7
  %t4 = add i8 %s8, %s9
  %t5 = add i8 %s10, %s11
  %t6 = add i8 %s12, %s13
  %t7 = add i8 %s14, %s15
  %u0 = add i8 %t0, %t1
  %u1 = add i8 %t2, %t3
  %u2 = add i8 %t4, %t5
  %u3 = add i8 %t6, %t7
  %v0 = add i8 %u0, %u1
  %v1 = add i8 %u2, %u3
  %s = add i8 %v0, %v1
  ret i8 %s
}

; Add-with-carry / subtract-with-borrow intrinsics used by big-integer limb
; arithmetic (e.g. num-bigint on 64-bit limbs). rustc emits the two-result
; form:
;
;   %r = call { i8, i64 } @llvm.x86.addcarry.64(i8 %carry, i64 %a, i64 %b)
;   %r = call { i8, i64 } @llvm.x86.subborrow.64(i8 %borrow, i64 %a, i64 %b)
;
; KLEE does not implement these natively and reports "external call with
; symbolic argument". rvt-patch-llvm --intrinsics rewrites the calls to the
; same-named functions below.

define { i8, i64 } @llvm_x86_addcarry_64(i8 %c, i64 %a, i64 %b) {
  %z = zext i8 %c to i128
  %za = zext i64 %a to i128
  %zb = zext i64 %b to i128
  %s1 = add i128 %za, %zb
  %s2 = add i128 %s1, %z
  %lo = trunc i128 %s2 to i64
  %hi = lshr i128 %s2, 64
  %c8 = trunc i128 %hi to i8
  %r0 = insertvalue { i8, i64 } undef, i8 %c8, 0
  %r1 = insertvalue { i8, i64 } %r0, i64 %lo, 1
  ret { i8, i64 } %r1
}

define { i8, i64 } @llvm_x86_subborrow_64(i8 %c, i64 %a, i64 %b) {
  %z = zext i8 %c to i128
  %za = zext i64 %a to i128
  %zb = zext i64 %b to i128
  %s1 = sub i128 %za, %zb
  %d2 = sub i128 %s1, %z
  %lo = trunc i128 %d2 to i64
  ; borrow iff the true difference is negative, i.e. the wrapped result
  ; exceeds a (a < 2^64 <= wrapped values).
  %neg = icmp ugt i128 %d2, %za
  %c8 = zext i1 %neg to i8
  %r0 = insertvalue { i8, i64 } undef, i8 %c8, 0
  %r1 = insertvalue { i8, i64 } %r0, i64 %lo, 1
  ret { i8, i64 } %r1
}
