#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv)
{
	char* x = (char*)malloc(1);
	free(x);
	free(x);
	return 0;
}