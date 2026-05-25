/* Double-free demonstration.
 * EXPECTED: ASan reports attempting double-free.
 * MYTHOS BUG CLASS: double-free
 */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *p = malloc(sizeof(int));
    *p = 42;
    printf("value=%d\n", *p);
    free(p);
    /* Bug: free the same pointer again */
    free(p);
    return 0;
}
