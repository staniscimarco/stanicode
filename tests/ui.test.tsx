import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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
  let projectTools: unknown;
  let calls: { path: string; body: any }[];
  beforeEach(() => {
    if (!HTMLDialogElement.prototype.showModal)
      HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
    if (!HTMLDialogElement.prototype.close)
      HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
    localStorage.clear();
    ready = true;
    tasks = [];
    projectTools = null;
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
            project_tools: projectTools,
          };
        if (path === "/tasks" && !body) data = tasks;
        if (path === "/tasks" && body) data = { id: "task1" };
        if (path === "/memory") data = [];
        if (path === "/project-tools/node/propose") data = { approval_id: "fixture-sdk-approval", version: "24.19.0", destination: "/test/appdata/tools/node" };
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
  it("does not provision a project SDK when the user declines", async () => {
    projectTools = { supported: true, installed: false, busy: false, version: "24.19.0", phase: "not-installed", error: "" };
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Impostazioni", exact: true }));
    await user.click(await screen.findByRole("button", { name: "Configura Node.js e npm" }));
    const sdkDialog = await screen.findByRole("dialog", { name: "Conferma operazione" });
    await user.click(within(sdkDialog).getByRole("button", { name: "Annulla", exact: true }));
    expect(calls.some((call) => call.path === "/project-tools/node/install")).toBe(false);
  });
  it("sends the exact SDK proposal approval after consent", async () => {
    projectTools = { supported: true, installed: false, busy: false, version: "24.19.0", phase: "not-installed", error: "" };
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Impostazioni", exact: true }));
    await user.click(await screen.findByRole("button", { name: "Configura Node.js e npm" }));
    await user.click(await screen.findByRole("button", { name: "Autorizza", exact: true }));
    await waitFor(() => expect(calls.some((call) => call.path === "/project-tools/node/install" && call.body.approval_id === "fixture-sdk-approval")).toBe(true));
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
  it("requires explicit dialog approval before restoring task files", async () => {
    tasks = [{ id: "completed-task", prompt: "fixture completed task", workspace: "/test/workspace", state: "completed",
      events: [], changes: [{ path: "example.py", before: null, after: "print(42)" }], pending: null, approval_id: null }];
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Ripristina file" }));
    const restoreDialog = await screen.findByRole("dialog", { name: "Conferma operazione" });
    expect(screen.getByTestId("confirmation-message").textContent).toContain("example.py");
    expect(calls.some((call) => call.path === "/rollback")).toBe(false);
    await user.click(within(restoreDialog).getByRole("button", { name: "Annulla", exact: true }));
    expect(calls.some((call) => call.path === "/rollback")).toBe(false);
    await user.click(screen.getByRole("button", { name: "Ripristina file" }));
    await user.click(await screen.findByRole("button", { name: "Autorizza", exact: true }));
    await waitFor(() => expect(calls.some((call) => call.path === "/rollback" && call.body.id === "completed-task")).toBe(true));
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
