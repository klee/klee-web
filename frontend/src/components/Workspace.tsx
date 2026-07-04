import { type ReactNode, useCallback, useEffect, useRef } from "react"
import { useSettings } from "../context/SettingsContext"

type WorkspaceProps = {
  topBar: ReactNode
  sidebar?: ReactNode
  main: ReactNode
  results: ReactNode
  statusBar: ReactNode
}

const MIN_RATIO = 15
const MAX_RATIO = 85

export function Workspace({ topBar, sidebar, main, results, statusBar }: WorkspaceProps) {
  const { resultsPosition, splitRight, splitBelow, setSplitRight, setSplitBelow } = useSettings()
  const isHorizontal = resultsPosition === "right"

  const splitRatio = isHorizontal ? splitRight : splitBelow
  const setSplitRatio = isHorizontal ? setSplitRight : setSplitBelow

  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const handleMouseDown = useCallback(() => {
    dragging.current = true
    document.body.style.cursor = isHorizontal ? "col-resize" : "row-resize"
    document.body.style.userSelect = "none"
  }, [isHorizontal])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      let ratio: number
      if (isHorizontal) {
        ratio = ((e.clientX - rect.left) / rect.width) * 100
      } else {
        ratio = ((e.clientY - rect.top) / rect.height) * 100
      }
      ratio = Math.max(MIN_RATIO, Math.min(MAX_RATIO, ratio))
      setSplitRatio(Math.round(ratio))
    }

    const handleMouseUp = () => {
      dragging.current = false
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
    }

    window.addEventListener("mousemove", handleMouseMove)
    window.addEventListener("mouseup", handleMouseUp)
    return () => {
      window.removeEventListener("mousemove", handleMouseMove)
      window.removeEventListener("mouseup", handleMouseUp)
    }
  }, [isHorizontal, setSplitRatio])

  const mainResultsDirection = isHorizontal ? "flex-row" : "flex-col"

  return (
    <div className="h-screen flex flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="shrink-0">{topBar}</div>
      <div className="flex-1 min-h-0 flex flex-row">
        {sidebar && <div className="shrink-0">{sidebar}</div>}
        <div
          ref={containerRef}
          className={`flex-1 min-h-0 min-w-0 flex ${mainResultsDirection}`}
        >
          <div
            className="min-h-0 min-w-0 overflow-auto"
            style={isHorizontal ? { width: `${splitRatio}%` } : { height: `${splitRatio}%` }}
          >
            {main}
          </div>
          <div
            className={`shrink-0 ${
              isHorizontal
                ? "w-1.5 cursor-col-resize"
                : "h-1.5 cursor-row-resize"
            } bg-slate-200 dark:bg-slate-800 hover:bg-blue-500 dark:hover:bg-blue-500 transition-colors`}
            onMouseDown={handleMouseDown}
          />
          <div className="flex-1 min-h-0 min-w-0 overflow-auto">{results}</div>
        </div>
      </div>
      <div className="shrink-0">{statusBar}</div>
    </div>
  )
}
