/* C twin of demos/klee-deq-dump-bytes/src/main.rs (hex_decode). */
#include <stdint.h>
#include <klee/klee.h>

static int hexval(unsigned char c) {
    if (c >= '0' && c <= '9') return (int)(c - '0');
    if (c >= 'a' && c <= 'f') return (int)(c - 'a' + 10);
    if (c >= 'A' && c <= 'F') return (int)(c - 'A' + 10);
    return -1;
}

static size_t hex_decode(uint8_t *out, const uint8_t *s, size_t slen,
                         size_t outlen) {
    size_t n = 0, i = 0;
    while (i + 1 < slen && n < outlen) {
        int hi = hexval(s[i]);
        int lo = hexval(s[i + 1]);
        if (hi < 0 || lo < 0) break;
        out[n] = (uint8_t)((hi << 4) | lo);
        n++;
        i += 2;
    }
    return n;
}

int main(void) {
    uint8_t input[2];
    klee_make_symbolic(input, sizeof(input), "stdin");
    uint8_t out[1] = {0};
    (void)hex_decode(out, input, sizeof(input), sizeof(out));
    klee_dump_expr_mem("out_hex", out, sizeof(out));
    return 0;
}
