import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, it, expect, vi } from "vitest";
import Zotero from "./Zotero";
import { api } from "./api";
vi.mock("./api", () => ({ api: vi.fn(), openLink: vi.fn() }));
beforeEach(() => {
  localStorage.clear();
  vi.mocked(api).mockImplementation(async (path, method) =>
    path === "/zotero/connections" && method === "POST"
      ? ({ id: 1 } as never)
      : ([] as never),
  );
});
it("sends a key to backend settings, clears the input and never stores it in localStorage", async () => {
  render(<Zotero />);
  await waitFor(() => expect(api).toHaveBeenCalledWith("/zotero/connections"));
  fireEvent.change(screen.getByLabelText("Library ID"), {
    target: { value: "123" },
  });
  fireEvent.change(screen.getByLabelText("Web API key"), {
    target: { value: "SECRET-CANARY" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Save connection securely" }),
  );
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith(
      "/zotero/connections",
      "POST",
      expect.objectContaining({ key: "SECRET-CANARY" }),
    ),
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Web API key")).toHaveValue(""),
  );
  expect(JSON.stringify(localStorage)).not.toContain("SECRET-CANARY");
});
