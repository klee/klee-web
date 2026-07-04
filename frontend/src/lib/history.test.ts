import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"
import {
  addRun,
  clearHistory,
  MAX_ENTRIES,
  readHistory,
  removeEntry,
  setStatus,
  type HistoryEntry,
} from "./history"

const FLAGS = { max_time: 60, max_memory: 512, query_format: "none" } as const

function entry(jobId: string, code: string, createdAt: number): HistoryEntry {
  return { jobId, code, flags: { ...FLAGS }, createdAt }
}

// Vitest runs in a node environment with no DOM, so localStorage is not defined.
// Stub a minimal in-memory Storage rather than pull in jsdom/happy-dom.
class MemoryStorage {
  private store = new Map<string, string>()
  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value))
  }
  removeItem(key: string): void {
    this.store.delete(key)
  }
  clear(): void {
    this.store.clear()
  }
}

beforeEach(() => {
  vi.stubGlobal("localStorage", new MemoryStorage())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("history store", () => {
  test("readHistory returns [] when empty or corrupt", () => {
    expect(readHistory()).toEqual([])
    localStorage.setItem("klee.history", "not json")
    expect(readHistory()).toEqual([])
    localStorage.setItem("klee.history", JSON.stringify({ not: "an array" }))
    expect(readHistory()).toEqual([])
  })

  test("addRun prepends newest first", () => {
    addRun(entry("a", "code A", 1))
    const after = addRun(entry("b", "code B", 2))
    expect(after.map((e) => e.jobId)).toEqual(["b", "a"])
  })

  test("addRun dedups a repeat of the newest identical code and flags", () => {
    addRun(entry("a", "same", 1))
    const after = addRun(entry("b", "same", 2))
    expect(after).toHaveLength(1)
    expect(after[0].jobId).toBe("b")
    expect(after[0].createdAt).toBe(2)
  })

  test("addRun dedups an identical run even with another run in between", () => {
    addRun(entry("a", "same", 1))
    addRun(entry("b", "other", 2))
    const after = addRun(entry("c", "same", 3))
    expect(after.map((e) => e.jobId)).toEqual(["c", "b"])
  })

  test("addRun keeps distinct code as separate entries", () => {
    addRun(entry("a", "one", 1))
    const after = addRun(entry("b", "two", 2))
    expect(after).toHaveLength(2)
  })

  test("addRun evicts beyond MAX_ENTRIES", () => {
    for (let i = 0; i < MAX_ENTRIES + 5; i++) {
      addRun(entry(`job${i}`, `code ${i}`, i))
    }
    const all = readHistory()
    expect(all).toHaveLength(MAX_ENTRIES)
    expect(all[0].jobId).toBe(`job${MAX_ENTRIES + 4}`)
  })

  test("setStatus updates the matching entry only", () => {
    addRun(entry("a", "one", 1))
    addRun(entry("b", "two", 2))
    const after = setStatus("a", "completed")
    expect(after.find((e) => e.jobId === "a")?.status).toBe("completed")
    expect(after.find((e) => e.jobId === "b")?.status).toBeUndefined()
  })

  test("removeEntry drops one, clearHistory empties", () => {
    addRun(entry("a", "one", 1))
    addRun(entry("b", "two", 2))
    expect(removeEntry("a").map((e) => e.jobId)).toEqual(["b"])
    expect(clearHistory()).toEqual([])
    expect(readHistory()).toEqual([])
  })
})
