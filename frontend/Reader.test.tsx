import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, afterEach, it, expect, vi } from "vitest";
import Reader from "./Reader";
import type { Attachment } from "./types";
const { renderPage, fullscreen } = vi.hoisted(() => ({
  renderPage: vi.fn(() => ({ promise: Promise.resolve(), cancel: vi.fn() })),
  fullscreen: vi.fn(async () => true),
}));
vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: {},
  getDocument: () => ({
    promise: Promise.resolve({
      numPages: 3,
      getOutline: async () => [],
      getPage: async (page: number) => ({
        getViewport: ({ scale }: { scale: number }) => ({
          width: 600 * scale,
          height: 800 * scale,
        }),
        render: renderPage,
        getTextContent: async () => ({
          items: [{ str: `Page ${page} catalyst evidence catalyst` }],
        }),
      }),
    }),
    destroy: vi.fn(),
  }),
  TextLayer: class {
    constructor(public options: { container: HTMLElement }) {}
    async render() {
      this.options.container.textContent = "catalyst evidence";
    }
    cancel() {}
  },
}));
vi.mock("./api", () => ({
  config: async () => ({ base: "http://localhost", token: "test" }),
  api: async (path: string) =>
    path.startsWith("/works/")
      ? {
          title: "Test paper",
          authors: ["Alice"],
          notes: "",
          tags: [],
          files: [],
          sources: [],
          oa_locations: [],
        }
      : [],
}));
const file: Attachment = {
  id: 1,
  work_id: 1,
  name: "paper.pdf",
  pages: 3,
  sha256: "test",
};
beforeEach(() => {
  localStorage.clear();
  renderPage.mockClear();
  fullscreen.mockClear();
  window.desktop = { fullscreen } as never;
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
});
afterEach(() => {
  delete window.desktop;
  vi.unstubAllGlobals();
});
it("preserves the page and avoids PDF rerender when panels toggle", async () => {
  render(<Reader file={file} initialPage={2} onSaved={() => {}} />);
  await waitFor(() =>
    expect(screen.getByTestId("pdf-page")).toHaveAttribute(
      "data-ready",
      "true",
    ),
  );
  const calls = renderPage.mock.calls.length;
  fireEvent.click(screen.getByRole("button", { name: "Left panel" }));
  fireEvent.change(screen.getByLabelText("Left panel width"), {
    target: { value: "350" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Right panel" }));
  expect(screen.getByTestId("pdf-page")).toHaveAttribute("data-page", "2");
  expect(renderPage.mock.calls.length).toBe(calls);
  expect(
    JSON.parse(localStorage.getItem("researchos.reader.layout")!),
  ).toMatchObject({ left: true, right: false, leftWidth: 350 });
});
it("Focus hides panels and Escape restores the previous layout; Zen calls native fullscreen", async () => {
  render(<Reader file={file} onSaved={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "Focus" }));
  expect(document.body).toHaveClass("reader-focus");
  expect(screen.queryByLabelText("Right panel width")).not.toBeInTheDocument();
  fireEvent.keyDown(window, { key: "Escape" });
  expect(screen.getByLabelText("Right panel width")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Zen" }));
  await waitFor(() => expect(fullscreen).toHaveBeenCalledWith(true));
  await screen.findByRole("button", { name: "Exit Zen (Esc)" });
  fireEvent.keyDown(window, { key: "Escape" });
  await waitFor(() => expect(fullscreen).toHaveBeenCalledWith(false));
});
it("finds text throughout the PDF and navigates next/previous results", async () => {
  render(<Reader file={file} onSaved={() => {}} />);
  await waitFor(() =>
    expect(screen.getByTestId("pdf-page")).toHaveAttribute(
      "data-ready",
      "true",
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Find" }));
  fireEvent.change(screen.getByLabelText("Find in PDF"), {
    target: { value: "catalyst" },
  });
  expect(await screen.findByText("1 / 6 matches")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Next match" }));
  fireEvent.click(screen.getByRole("button", { name: "Next match" }));
  expect(screen.getByTestId("pdf-page")).toHaveAttribute("data-page", "2");
  fireEvent.click(screen.getByRole("button", { name: "Previous match" }));
  expect(screen.getByTestId("pdf-page")).toHaveAttribute("data-page", "1");
});
