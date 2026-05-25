/* Format-string demonstration.
 * EXPECTED: leaks stack via %x / %p when ASLR doesn't fully mask.
 * MYTHOS BUG CLASS: format-string
 */
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <format>\n", argv[0]);
        return 1;
    }
    /* Bug: argv[1] is used as the format string */
    printf(argv[1]);
    printf("\n");
    return 0;
}
