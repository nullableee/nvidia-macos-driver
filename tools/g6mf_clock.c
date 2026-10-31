#include <stdio.h>
#include <time.h>
int main(void) {
    // A shared uptime clock; Python 3.9's macOS monotonic epoch is process-local.
    printf("%llu\n", (unsigned long long)clock_gettime_nsec_np(CLOCK_UPTIME_RAW));
    return 0;
}
