export function clampPage(raw: string, current: number, pageCount: number): number {
  const parsed = Number.parseInt(raw, 10)
  if (Number.isNaN(parsed)) return current
  return Math.min(Math.max(parsed, 1), pageCount)
}
