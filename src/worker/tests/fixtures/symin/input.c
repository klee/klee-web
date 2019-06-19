#include <stdio.h>
int main(int argc, char* argv[])
{
  char a;
  read(0, &a, sizeof(char));
  if (a == 'a') {
    printf("hello!\n");
  } else {
    printf("goodbye!\n");
  }
  return 0;
}