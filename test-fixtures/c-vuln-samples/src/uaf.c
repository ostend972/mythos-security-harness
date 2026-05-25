/* Use-after-free demonstration.
 * EXPECTED: ASan reports heap-use-after-free.
 * MYTHOS BUG CLASS: uaf
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char *buf = malloc(32);
    strcpy(buf, "first allocation");
    printf("Before free: %s\n", buf);
    free(buf);
    /* Bug: dereference after free */
    printf("After free:  %s\n", buf);
    return 0;
}
