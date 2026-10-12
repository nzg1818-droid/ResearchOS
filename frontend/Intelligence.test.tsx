import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, it, expect, vi } from "vitest";
import Intelligence, { BatchIntelligence } from "./Intelligence";
import AISettings from "./AISettings";
import { api } from "./api";
vi.mock("./api", () => ({ api: vi.fn() }));
const anchor = {
  id: 1,
  work_id: 7,
  file_id: 9,
  page: 2,
  field_path: "performance.0.reported_value",
  quote: "250 mV",
  bboxes: [{ page: 2, rect: [0.1, 0.2, 0.5, 0.3] }],
};
const overview = {
  documents: [
    {
      id: 1,
      parse_status: "Parsed",
      page_count: 3,
      chunks: 8,
      characters: 900,
    },
  ],
  extractions: [
    {
      id: 4,
      run: { extraction_level: "full_text" },
      effective: {
        performance: [
          {
            reported_value: {
              value: 250,
              origin: "source_reported",
              confidence: 0.8,
              evidence: [anchor],
            },
          },
        ],
      },
      field_states: {
        "performance.0.reported_value": {
          status: "Evidence matched",
          issues: [],
        },
      },
      anchors: [anchor],
    },
  ],
  questions: [],
};
beforeEach(() => {
  localStorage.clear();
  vi.mocked(api).mockReset();
  vi.mocked(api).mockImplementation(async (path) => {
    if (path === "/intelligence/providers") return [] as never;
    if (path.startsWith("/intelligence/works/")) return overview as never;
    return {} as never;
  });
});
it("shows provenance, jumps to exact evidence and submits an auditable field decision", async () => {
  const jump = vi.fn();
  render(<Intelligence workId={7} onEvidence={jump} />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Show evidence p. 2" }),
  );
  expect(jump).toHaveBeenCalledWith(anchor);
  expect(screen.getByText("source_reported")).toBeInTheDocument();
  expect(screen.getByText("Evidence matched")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Verify" }));
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith(
      "/intelligence/extractions/4/verify",
      "POST",
      expect.objectContaining({
        field_path: "performance.0.reported_value",
        action: "accept",
      }),
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Edit" }));
  fireEvent.change(screen.getByLabelText("Corrected value"), {
    target: { value: "251" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith(
      "/intelligence/extractions/4/verify",
      "POST",
      expect.objectContaining({ action: "edit", value: 251 }),
    ),
  );
});
it("does not send a cloud batch until size preview and explicit consent", async () => {
  vi.mocked(api).mockImplementation(async (path) =>
    path === "/intelligence/providers"
      ? ([
          {
            id: 2,
            name: "Remote",
            model: "model",
            enabled: true,
            is_default: true,
            cloud: true,
          },
        ] as never)
      : (overview as never),
  );
  render(<BatchIntelligence workIds={[7]} />);
  await screen.findByText("Remote · model · Cloud");
  fireEvent.mouseDown(screen.getByLabelText("Processing action"));
  fireEvent.click(
    await screen.findByRole("option", { name: "Extract full text" }),
  );
  expect(
    screen.getByRole("button", { name: "Start selected processing" }),
  ).toBeDisabled();
  expect(api).not.toHaveBeenCalledWith(
    "/intelligence/batches",
    expect.anything(),
    expect.anything(),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Preview cloud input size" }),
  );
  await screen.findByText(/3 pages, 8 chunks/);
  fireEvent.click(screen.getByLabelText(/I consent to send source text/));
  fireEvent.click(
    screen.getByRole("button", { name: "Start selected processing" }),
  );
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith(
      "/intelligence/batches",
      "POST",
      expect.objectContaining({ cloud_consent: true, work_ids: [7] }),
    ),
  );
});
it("keeps provider credentials out of persistent renderer storage and clears input after saving", async () => {
  render(<AISettings />);
  fireEvent.change(screen.getByLabelText("Provider name"), {
    target: { value: "Cloud" },
  });
  fireEvent.change(screen.getByLabelText("Provider model"), {
    target: { value: "model" },
  });
  fireEvent.change(screen.getByLabelText("Provider API key"), {
    target: { value: "AI-SECRET-CANARY" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Save AI provider securely" }),
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Provider API key")).toHaveValue(""),
  );
  expect(JSON.stringify(localStorage)).not.toContain("AI-SECRET-CANARY");
});
it("asks only the selected paper and exposes citation snippets", async () => {
  vi.mocked(api).mockImplementation(async (path) =>
    path === "/intelligence/providers"
      ? ([] as never)
      : ({
          ...overview,
          questions: [
            {
              id: 1,
              text: "overpotential?",
              answers: [{ id: 1, text: "250 mV", anchors: [anchor] }],
            },
          ],
        } as never),
  );
  const jump = vi.fn();
  render(<Intelligence workId={7} askOnly onEvidence={jump} />);
  await screen.findByText("overpotential?");
  fireEvent.click(screen.getByText("Evidence p. 2"));
  fireEvent.click(screen.getByRole("button", { name: "Show evidence p. 2" }));
  expect(jump).toHaveBeenCalledWith(anchor);
  fireEvent.change(screen.getByLabelText("Question about this paper"), {
    target: { value: "Which electrolyte?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Ask this paper" }));
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith(
      "/intelligence/works/7/ask",
      "POST",
      expect.objectContaining({
        question: "Which electrolyte?",
        cloud_consent: false,
      }),
    ),
  );
});
