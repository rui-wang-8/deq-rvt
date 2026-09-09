/* C twin of demos/klee-deq-dump/src/main.rs (combine). */
#include <stdint.h>
#include <klee/klee.h>

static uint64_t combine(uint32_t x, uint32_t y) {
    uint64_t r = ((uint64_t)x << 32) | y;
    r ^= r >> 11;
    r *= 0x9e3779b97f4a7c15ULL;
    return r;
}

int main(void) {
    uint32_t x, y;
    klee_make_symbolic(&x, sizeof(x), "stdin");
    klee_make_symbolic(&y, sizeof(y), "stdin");
    uint64_t r = combine(x, y);
    klee_dump_expr("c_combine", r);
    return 0;
}
