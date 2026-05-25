/* Out-of-bounds read demonstration.
 * EXPECTED: ASan reports heap-buffer-overflow READ.
 * MYTHOS BUG CLASS: oob-rw
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char *buf = malloc(8);
    strcpy(buf, "ABCDEFG");
    /* Bug: read 16 bytes from an 8-byte allocation */
    char copy[16];
    memcpy(copy, buf, 16);
    printf("%.16s\n", copy);
    free(buf);
    return 0;
}
