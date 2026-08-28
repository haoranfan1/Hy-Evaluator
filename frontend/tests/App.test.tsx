import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "../src/App";

afterEach(() => {
  vi.restoreAllMocks();
});

test("shows configuration state from the local health endpoint", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "degraded",
        version: "0.1.0",
        components: {
          api: { status: "ready", detail: "API process is responsive." },
          hy3: { status: "not_configured", detail: "Configure Hy3 locally." },
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );

  render(
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>,
  );

  expect(await screen.findByText("Configuration needed")).toBeInTheDocument();
  expect(screen.getByText("Configure Hy3 locally.")).toBeInTheDocument();
});
