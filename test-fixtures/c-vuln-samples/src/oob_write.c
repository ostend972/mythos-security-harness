/* Out-of-bounds write demonstration.
 * EXPECTED: ASan reports heap-buffer-overflow WRITE.
 * MYTHOS BUG CLASS: oob-rw
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    char *buf = malloc(8);
    /* Bug: write 16 bytes into an 8-byte buffer */
    memset(buf, 'X', 16);
    printf("done\n");
    free(buf);
    (void)argc; (void)argv;
    return 0;
}
