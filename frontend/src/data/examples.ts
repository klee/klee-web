import type { KleeFlags } from "../api/jobs";
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
  description: string;
  flags: KleeFlags;
};

function exampleFlags(overrides: Partial<KleeFlags> = {}): KleeFlags {
  return {
    max_time: 10,
    max_memory: 512,
    enable_replay: true,
    query_format: "none",
    extra_flags: "",
    sym_stdin: null,
    sym_files: null,
    sym_args: null,
    ...overrides,
  };
}

export const EXAMPLES: Example[] = [
  {
    id: "get_sign",
    label: "get_sign.c",
    tag: "tutorial",
    code: getSign,
    description: "Makes one integer symbolic and explores its negative, zero, and positive paths.",
    flags: exampleFlags(),
  },
  {
    id: "regexp",
    label: "regexp.c",
    tag: "tutorial",
    code: regexp,
    description:
      'Makes a seven-byte regular expression symbolic and explores matching it against "hello".',
    flags: exampleFlags({
      max_time: 60,
      enable_replay: false,
      extra_flags: "--only-output-states-covering-new",
    }),
  },
  {
    id: "maze",
    label: "maze.c",
    tag: "tutorial",
    code: maze,
    description: "Makes 28 movement commands symbolic and searches for a path through the maze.",
    flags: exampleFlags({
      max_time: 60,
      extra_flags: "--only-output-states-covering-new",
    }),
  },
  {
    id: "hello_world",
    label: "hello_world.c",
    tag: "example",
    code: helloWorld,
    description: 'Runs a concrete one-path program that prints "Hello world".',
    flags: exampleFlags(),
  },
  {
    id: "sym_input",
    label: "sym_input.c",
    tag: "example",
    code: symInput,
    description: 'Reads one symbolic stdin byte and branches on whether it is "a".',
    flags: exampleFlags({ sym_stdin: { size: 1 } }),
  },
  {
    id: "double_free",
    label: "double_free.c",
    tag: "example",
    code: doubleFree,
    description: "Demonstrates KLEE detecting an allocation that is freed twice.",
    flags: exampleFlags(),
  },
];

// get_sign doubles as the first-visit seed, replacing the old inline GET_SIGN_C.
export const DEFAULT_EXAMPLE: Example = EXAMPLES[0];
