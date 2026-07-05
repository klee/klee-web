// title: Symbolic stdin
// Turn on "Symbolic input > stdin" in the top bar, then Run: KLEE forks on the symbolic byte.
#include <stdio.h>
#include <unistd.h>

int main(int argc, char** argv)
{
	char in;
	read(0, &in, sizeof(char));
	if (in == 'a') {
		printf("Hello World!");
	} else {
		printf("Goodbye World!");
	}
	return 0;
}
