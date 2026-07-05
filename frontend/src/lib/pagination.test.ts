import { describe, expect, test } from "vitest"
import { clampPage } from "./pagination"

describe("clampPage", () => {
  test("returns an in-range page unchanged", () => {
    expect(clampPage("3", 1, 12)).toBe(3)
  })

  test("clamps above the last page to pageCount", () => {
    expect(clampPage("99", 1, 12)).toBe(12)
  })

  test("clamps below the first page to 1", () => {
    expect(clampPage("0", 5, 12)).toBe(1)
    expect(clampPage("-4", 5, 12)).toBe(1)
  })

  test("falls back to the current page on non-numeric input", () => {
    expect(clampPage("abc", 5, 12)).toBe(5)
  })

  test("falls back to the current page on empty input", () => {
    expect(clampPage("", 5, 12)).toBe(5)
  })

  test("parses the leading integer of trailing junk", () => {
    expect(clampPage("3abc", 1, 12)).toBe(3)
  })
})
