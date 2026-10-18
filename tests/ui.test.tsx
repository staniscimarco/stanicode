import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => ({ port: 12345, token: "test-only-token" })),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: vi.fn(async () => "/test/workspace"),
}));
import { App } from "../apps/desktop/src/main";

describe("Desktop controls (native bridge and HTTP mocked)", () => {
  let ready: boolean;
  let tasks: unknown[];
  let calls: { path: string; body: any }[];
  beforeEach(() => {
    localStorage.clear();
    ready = true;
    tasks = [];
    calls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, options: any) => {
        const path = new URL(url).pathname;
        const body = options?.body ? JSON.parse(options.body) : undefined;
        calls.push({ path, body });
        let data: unknown = { ok: true };
        if (path === "/health")
          data = {
            backend: true,
            inference: { ready, detail: ready ? "ready" : "missing model" },
          };
        if (path === "/tasks" && !body) data = tasks;
        if (path === "/tasks" && body) data = { id: "task1" };
        if (path === "/memory") data = [];
        return { ok: true, json: async () => data };
      }),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  it("selects a workspace and sends the actual request", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Scegli cartella" }));
    await user.type(screen.getByRole("textbox"), "Create a calculator");
    await waitFor(() =>
      expect(
        screen
          .getByRole("button", { name: /Avvia sviluppo/ })
          .hasAttribute("disabled"),
      ).toBe(false),
    );
    await user.click(screen.getByRole("button", { name: /Avvia sviluppo/ }));
    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.path === "/tasks" &&
            c.body?.prompt === "Create a calculator" &&
            c.body.workspace === "/test/workspace",
        ),
      ).toBe(true),
    );
  });
  it("blocks start when real runtime status is unavailable", async () => {
    ready = false;
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Scegli cartella" }));
    await user.type(screen.getByRole("textbox"), "Create tests");
    expect(
      screen
        .getByRole("button", { name: /Avvia sviluppo/ })
        .hasAttribute("disabled"),
    ).toBe(true);
    expect(screen.getByText("Modello locale non disponibile")).toBeTruthy();
  });
  it("shows proposed content and sends approval only after a click", async () => {
    tasks = [
      {
        id: "task1",
        prompt: "test",
        workspace: "/test/workspace",
        state: "awaiting_approval",
        approval_id: "fixture-approval",
        events: [],
        changes: [],
        pending: [{ path: "example.py", before: null, after: "print(42)" }],
      },
    ];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("example.py");
    expect(screen.getByText("print(42)")).toBeTruthy();
    expect(calls.some((c) => c.body?.action === "approve")).toBe(false);
    await user.click(
      screen.getByRole("button", { name: "Approva modifiche e test" }),
    );
    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.path === "/control" && c.body?.action === "approve",
        ),
      ).toBe(true),
    );
  });
  it("persists locale and switches visible labels", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Language" }),
      "en",
    );
    expect(
      screen.getByRole("heading", { name: "What do you want to build?" }),
    ).toBeTruthy();
    expect(localStorage.getItem("locale")).toBe("en");
  });
});
