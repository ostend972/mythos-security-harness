/* Stack buffer overflow demonstration.
 * EXPECTED: ASan reports stack-buffer-overflow.
 * MYTHOS BUG CLASS: oob-rw (stack variant)
 */
#include <stdio.h>
#include <string.h>

void vulnerable(const char *input) {
    char buf[16];
    /* Bug: no length check */
    strcpy(buf, input);
    printf("%s\n", buf);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        vulnerable("default-short");
    } else {
        vulnerable(argv[1]);
    }
    return 0;
}
