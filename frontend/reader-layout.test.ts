import { it, expect, beforeEach } from "vitest";
import { readLayout, rotateRect, selectionContext } from "./reader-layout";
beforeEach(() => localStorage.clear());
it("restores bounded layout preferences without persisting Zen", () => {
  localStorage.setItem(
    "researchos.reader.layout",
    JSON.stringify({
      left: true,
      right: false,
      leftWidth: 900,
      rightWidth: 1,
      focus: true,
      zen: true,
    }),
  );
  expect(readLayout()).toEqual({
    left: true,
    right: false,
    leftWidth: 420,
    rightWidth: 240,
    focus: true,
  });
});
it("survives invalid saved preferences", () => {
  localStorage.setItem("researchos.reader.layout", "broken");
  expect(readLayout().right).toBe(true);
});
it("maps annotation rectangles through rotation and back", () => {
  const r = { x: 0.1, y: 0.2, width: 0.3, height: 0.04 };
  for (const angle of [0, 90, 180, 270]) {
    const result = rotateRect(rotateRect(r, angle), 360 - angle);
    for (const key of ["x", "y", "width", "height"] as const)
      expect(result[key]).toBeCloseTo(r[key]);
  }
});
it("retains bounded local context near a selection late in a long page", () => {
  const result = selectionContext(
    "prefix ".repeat(1000) + "selected sentence" + " suffix".repeat(1000),
    "selected sentence",
  );
  expect(result).toContain("selected sentence");
  expect(result.length).toBe(497);
});
