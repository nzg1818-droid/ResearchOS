import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, it, expect, beforeEach } from "vitest";
import App from "./App";
import { api } from "./api";
vi.mock("./Reader", () => ({
  default: ({
    initialPage,
    focusId,
  }: {
    initialPage: number;
    focusId: number;
  }) => (
    <div>
      PDF reader page {initialPage} highlight {focusId}
    </div>
  ),
}));
vi.mock("./api", () => ({ api: vi.fn(), openLink: vi.fn() }));
beforeEach(() => {
  vi.mocked(api).mockImplementation(async (path: string) => {
    if (path === "/health") return { data_dir: "test-data" } as never;
    if (path === "/search") return { job_id: 1 } as never;
    return [] as never;
  });
});
it("renders the search shell and sends the actual filters", async () => {
  render(<App />);
  expect(screen.getByText("Start with a question.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith(
      "/search",
      "POST",
      expect.objectContaining({
        query: "NiFe LDH alkaline water electrolysis",
        mode: "keyword",
        start: "2020-01-01",
      }),
    ),
  );
});
it("opens material bank and shows its empty state", async () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /04Knowledge/ }));
  expect(
    await screen.findByText("Evidence you can return to."),
  ).toBeInTheDocument();
});
it("opens a saved material at its original file, page and highlight", async () => {
  vi.mocked(api).mockImplementation(async (path: string) => {
    if (path === "/health") return { data_dir: "test-data" } as never;
    if (path === "/materials")
      return [
        {
          id: 1,
          kind: "evidence",
          provenance: {
            title: "Original paper",
            doi: "10.1234/test",
            authors: ["Alice"],
            year: 2024,
            filename: "paper.pdf",
          },
          annotation: {
            id: 9,
            work_id: 3,
            file_id: 4,
            page: 2,
            text: "Saved sentence",
            note: "Important",
            tags: [],
          },
        },
      ] as never;
    if (path === "/works/3")
      return { files: [{ id: 4, name: "paper.pdf", pages: 3 }] } as never;
    return [] as never;
  });
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /04Knowledge/ }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Open source · page 2" }),
  );
  expect(
    await screen.findByText("PDF reader page 2 highlight 9"),
  ).toBeInTheDocument();
  expect(api).toHaveBeenCalledWith("/works/3");
});
