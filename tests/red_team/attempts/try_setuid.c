/* Escape attempt #2: try to setuid(0) after compile.
   Expected outcome: setuid(0) fails because cap-drop=ALL removed CAP_SETUID. */
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>

int main(void) {
    int r = setuid(0);
    if (r == 0) {
        /* We got root — sandbox failed */
        printf("SANDBOX_BREACH: setuid(0) succeeded, EUID=%d\n", geteuid());
        return 0;
    }
    printf("setuid_denied: errno=%d (%s)\n", errno, strerror(errno));
    return 1;
}
