#include <stdio.h>

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