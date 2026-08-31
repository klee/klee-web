import { useId, useState, type ReactNode } from "react";

type Placement = "below-left" | "below-center" | "below-right" | "sidebar";

type HelpTooltipProps = {
  children: (descriptionId: string) => ReactNode;
  content: ReactNode;
  placement?: Placement;
  wide?: boolean;
  className?: string;
  inline?: boolean;
};

const PLACEMENT_CLASSES: Record<Placement, string> = {
  "below-left": "left-0 top-full mt-2",
  "below-center": "left-1/2 top-full mt-2 -translate-x-1/2",
  "below-right": "right-0 top-full mt-2",
  sidebar: "left-2 right-2 top-full mt-1",
};

export function HelpTooltip({
  children,
  content,
  placement = "below-left",
  wide = false,
  className = "inline-flex",
  inline = false,
}: HelpTooltipProps) {
  const descriptionId = useId();
  const [hoverDismissed, setHoverDismissed] = useState(false);
  const widthClass = placement === "sidebar" ? "w-auto" : wide ? "w-96" : "w-72";
  const hoverClasses = hoverDismissed ? "" : "group-hover:visible group-hover:opacity-100";

  function handlePointerDown() {
    setHoverDismissed(true);
  }

  function handlePointerLeave() {
    setHoverDismissed(false);
  }

  const contents = (
    <>
      {children(descriptionId)}
      <span
        id={descriptionId}
        role="tooltip"
        className={`pointer-events-none invisible absolute z-50 rounded border border-slate-300 bg-white px-2.5 py-2 text-xs leading-relaxed text-slate-700 opacity-0 shadow-lg transition-opacity ${hoverClasses} dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 ${widthClass} max-w-[calc(100vw-1.5rem)] ${PLACEMENT_CLASSES[placement]}`}
      >
        {content}
      </span>
    </>
  );

  if (inline) {
    return (
      <span
        className={`group relative ${className}`}
        onPointerDownCapture={handlePointerDown}
        onPointerLeave={handlePointerLeave}
      >
        {contents}
      </span>
    );
  }

  return (
    <div
      className={`group relative ${className}`}
      onPointerDownCapture={handlePointerDown}
      onPointerLeave={handlePointerLeave}
    >
      {contents}
    </div>
  );
}
