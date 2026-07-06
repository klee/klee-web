import doubleFree from "./examples/double_free.c?raw";
import getSign from "./examples/get_sign.c?raw";
import helloWorld from "./examples/hello_world.c?raw";
import maze from "./examples/maze.c?raw";
import regexp from "./examples/regexp.c?raw";
import symInput from "./examples/sym_input.c?raw";

export type Example = {
  id: string;
  label: string;
  tag: "tutorial" | "example";
  code: string;
};

export const EXAMPLES: Example[] = [
  { id: "get_sign", label: "get_sign.c", tag: "tutorial", code: getSign },
  { id: "regexp", label: "regexp.c", tag: "tutorial", code: regexp },
  { id: "maze", label: "maze.c", tag: "tutorial", code: maze },
  { id: "hello_world", label: "hello_world.c", tag: "example", code: helloWorld },
  { id: "sym_input", label: "sym_input.c", tag: "example", code: symInput },
  { id: "double_free", label: "double_free.c", tag: "example", code: doubleFree },
];

// get_sign doubles as the first-visit seed, replacing the old inline GET_SIGN_C.
export const DEFAULT_EXAMPLE: Example = EXAMPLES[0];
