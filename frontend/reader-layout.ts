export type ReaderLayout = {
  left: boolean;
  right: boolean;
  leftWidth: number;
  rightWidth: number;
  focus: boolean;
};
export const defaultLayout: ReaderLayout = {
  left: false,
  right: true,
  leftWidth: 260,
  rightWidth: 320,
  focus: false,
};
export function readLayout(): ReaderLayout {
  try {
    const value = JSON.parse(
      localStorage.getItem("researchos.reader.layout") || "{}",
    );
    return {
      left: typeof value.left === "boolean" ? value.left : defaultLayout.left,
      right:
        typeof value.right === "boolean" ? value.right : defaultLayout.right,
      leftWidth: Math.max(220, Math.min(420, Number(value.leftWidth) || 260)),
      rightWidth: Math.max(240, Math.min(440, Number(value.rightWidth) || 320)),
      focus: value.focus === true,
    };
  } catch {
    return defaultLayout;
  }
}
export function selectionContext(
  text: string,
  selected: string,
  offset?: number,
) {
  const index = offset ?? text.indexOf(selected);
  return index < 0
    ? selected
    : text.slice(Math.max(0, index - 240), index + selected.length + 240);
}
export function rotateRect(
  r: { x: number; y: number; width: number; height: number },
  rotation: number,
) {
  switch (((rotation % 360) + 360) % 360) {
    case 90:
      return {
        x: 1 - r.y - r.height,
        y: r.x,
        width: r.height,
        height: r.width,
      };
    case 180:
      return {
        x: 1 - r.x - r.width,
        y: 1 - r.y - r.height,
        width: r.width,
        height: r.height,
      };
    case 270:
      return { x: r.y, y: 1 - r.x - r.width, width: r.height, height: r.width };
    default:
      return r;
  }
}
