// Re-interprets a symbolic value's raw ktest bytes as a chosen C type, entirely
// client-side. Little-endian throughout, matching the backend heuristic and ktest-tool.

export type SymbolicType = "int" | "uint" | "float" | "double" | "hex" | "ascii";

const INT_WIDTHS = new Set([1, 2, 4, 8]);

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

function formatFloat(v: number): string {
  return Object.is(v, -0) ? "-0" : String(v);
}

// The types offered for a value of a given byte width. Int/uint need a standard
// width; float needs 4 bytes, double 8. Hex and ascii work for any length.
export function availableTypes(byteWidth: number): SymbolicType[] {
  const types: SymbolicType[] = [];
  if (INT_WIDTHS.has(byteWidth)) types.push("int", "uint");
  if (byteWidth === 4) types.push("float");
  if (byteWidth === 8) types.push("double");
  types.push("hex", "ascii");
  return types;
}

// The initial type, matching the backend's size heuristic so the first render
// equals the server-decoded value.
export function defaultType(byteWidth: number): SymbolicType {
  return INT_WIDTHS.has(byteWidth) ? "int" : "hex";
}

export function decode(bytesHex: string, type: SymbolicType): string {
  const bytes = hexToBytes(bytesHex);
  const view = new DataView(bytes.buffer);
  const width = bytes.length;
  const hex = () => "0x" + bytesHex;

  switch (type) {
    case "hex":
      return hex();
    case "ascii":
      return Array.from(bytes, (b) => (b >= 0x20 && b <= 0x7e ? String.fromCharCode(b) : ".")).join(
        "",
      );
    case "int":
      if (width === 1) return String(view.getInt8(0));
      if (width === 2) return String(view.getInt16(0, true));
      if (width === 4) return String(view.getInt32(0, true));
      if (width === 8) return String(view.getBigInt64(0, true));
      return hex();
    case "uint":
      if (width === 1) return String(view.getUint8(0));
      if (width === 2) return String(view.getUint16(0, true));
      if (width === 4) return String(view.getUint32(0, true));
      if (width === 8) return String(view.getBigUint64(0, true));
      return hex();
    case "float":
      return width === 4 ? formatFloat(view.getFloat32(0, true)) : hex();
    case "double":
      return width === 8 ? formatFloat(view.getFloat64(0, true)) : hex();
  }
}
