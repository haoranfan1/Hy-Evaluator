import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";

import { App } from "../src/App";

export type RecordedCall = { method: string; url: string; body?: unknown };

export function mockApi(routes: Record<string, unknown>): RecordedCall[] {
  const calls: RecordedCall[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url =
      typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    const call: RecordedCall = { method, url };
    if (typeof init?.body === "string") {
      call.body = JSON.parse(init.body);
    }
    calls.push(call);
    const headers = { "Content-Type": "application/json" };
    if (method === "POST") {
      return new Response(JSON.stringify({}), { status: 201, headers });
    }
    for (const [suffix, data] of Object.entries(routes)) {
      if (url.endsWith(suffix)) {
        return new Response(JSON.stringify(data), { status: 200, headers });
      }
    }
    return new Response(JSON.stringify({ detail: `unmocked URL ${url}` }), { status: 404 });
  });
  return calls;
}

export function renderApp(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export const HEALTH = {
  status: "degraded",
  version: "0.1.0",
  components: {},
};
