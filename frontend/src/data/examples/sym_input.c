// title: Symbolic stdin
// Its preset enables one symbolic stdin byte. Run to make KLEE fork on its value.
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
