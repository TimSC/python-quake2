// Reference for common/shared/rand.py: Yamagi's KISS PRNG, seeded, then values printed.
#include <stdio.h>
#include <stdint.h>
int randk(void); float frandk(void); float crandk(void); void randk_seed(void);
int main(void) { int i; randk_seed(); for (i = 0; i < 2000; i++) printf("%d\n", randk()); for (i = 0; i < 20; i++) { float a = frandk(); float b = crandk(); printf("%.6f %.6f\n", a, b); } randk_seed(); printf("%d\n", randk()); return 0; }
