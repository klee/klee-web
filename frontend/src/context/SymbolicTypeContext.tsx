import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { defaultType, type SymbolicType } from "../lib/decodeSymbolic";

type SymbolicTypeValue = {
  // The type chosen for a variable, or the size-based default if none chosen yet.
  typeFor: (name: string, byteWidth: number) => SymbolicType;
  setType: (name: string, type: SymbolicType) => void;
};

const SymbolicTypeContext = createContext<SymbolicTypeValue | null>(null);

// Holds the per-variable-name type choice. Lives above the results panel so a
// choice applies to that variable in every test case and survives reruns in the
// session (the provider does not unmount between runs).
export function SymbolicTypeProvider({ children }: { children: ReactNode }) {
  const [chosen, setChosen] = useState<Record<string, SymbolicType>>({});

  const setType = useCallback((name: string, type: SymbolicType) => {
    setChosen((prev) => ({ ...prev, [name]: type }));
  }, []);

  const typeFor = useCallback(
    (name: string, byteWidth: number): SymbolicType => chosen[name] ?? defaultType(byteWidth),
    [chosen],
  );

  const value = useMemo(() => ({ typeFor, setType }), [typeFor, setType]);
  return <SymbolicTypeContext.Provider value={value}>{children}</SymbolicTypeContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSymbolicTypes() {
  const ctx = useContext(SymbolicTypeContext);
  if (ctx === null) throw new Error("useSymbolicTypes must be used within SymbolicTypeProvider");
  return ctx;
}
