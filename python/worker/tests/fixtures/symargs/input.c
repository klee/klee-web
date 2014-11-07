#include <stdio.h>
int main(int argc, char* argv[])
{
  if(*argv[1] == 'a') {
    printf("hello!\n");
  } else {
    printf("goodbye!\n");
  }
  return 0;
}