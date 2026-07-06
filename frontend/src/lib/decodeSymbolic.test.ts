import { describe, expect, test } from "vitest";
import { availableTypes, decode, defaultType } from "./decodeSymbolic";

describe("decode", () => {
  test("little-endian signed ints by width", () => {
    expect(decode("ff", "int")).toBe("-1");
    expect(decode("ffff", "int")).toBe("-1");
    expect(decode("00000080", "int")).toBe("-2147483648"); // 0x80000000 LE
    expect(decode("01010101", "int")).toBe("16843009");
    expect(decode("ffffffffffffffff", "int")).toBe("-1"); // int64 via BigInt
  });

  test("little-endian unsigned ints by width", () => {
    expect(decode("ff", "uint")).toBe("255");
    expect(decode("ffff", "uint")).toBe("65535");
    expect(decode("00000080", "uint")).toBe("2147483648");
    expect(decode("ffffffffffffffff", "uint")).toBe("18446744073709551615");
  });

  test("float and double", () => {
    expect(decode("0000803f", "float")).toBe("1"); // 1.0f LE
    expect(decode("00000080", "float")).toBe("-0"); // -0.0f
    expect(decode("000000000000f03f", "double")).toBe("1"); // 1.0 LE
  });

  test("hex prefixes the raw bytes", () => {
    expect(decode("deadbeef", "hex")).toBe("0xdeadbeef");
    expect(decode("00", "hex")).toBe("0x00");
  });

  test("ascii keeps printable chars, dots the rest", () => {
    expect(decode("4869", "ascii")).toBe("Hi");
    expect(decode("48690a00", "ascii")).toBe("Hi.."); // \n and \0 are non-printable
  });

  test("falls back to hex when the width can't hold the type", () => {
    expect(decode("aabbcc", "int")).toBe("0xaabbcc"); // 3 bytes, no int width
    expect(decode("aabbcc", "float")).toBe("0xaabbcc"); // float needs 4 bytes
  });
});

describe("availableTypes filters by byte width", () => {
  test("4 bytes", () => {
    expect(availableTypes(4)).toEqual(["int", "uint", "float", "hex", "ascii"]);
  });
  test("8 bytes", () => {
    expect(availableTypes(8)).toEqual(["int", "uint", "double", "hex", "ascii"]);
  });
  test("1 byte", () => {
    expect(availableTypes(1)).toEqual(["int", "uint", "hex", "ascii"]);
  });
  test("odd width offers only hex and ascii", () => {
    expect(availableTypes(3)).toEqual(["hex", "ascii"]);
  });
});

describe("defaultType matches the backend heuristic", () => {
  test("int for 1/2/4/8, hex otherwise", () => {
    expect(defaultType(4)).toBe("int");
    expect(defaultType(8)).toBe("int");
    expect(defaultType(1)).toBe("int");
    expect(defaultType(3)).toBe("hex");
  });
});
