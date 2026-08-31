import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, Route, Routes } from "react-router";

import { RunDetailPage } from "./pages/RunDetailPage";
import { RunsPage } from "./pages/RunsPage";

type HealthResponse = {
  status: "ready" | "degraded";
  version: string;
};

async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`Health request failed with status ${response.status}.`);
  }
  return response.json() as Promise<HealthResponse>;
}

export function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth, retry: false });

  return (
    <main className="shell">
      <header className="app-head">
        <div>
          <p className="eyebrow">Hy3 process evaluation workbench</p>
          <h1 className="app-title">
            <Link to="/runs">Evidence debugger</Link>
          </h1>
        </div>
        <span
          className={`chip chip-${health.data ? health.data.status : "pending"}`}
          title="Local API status"
        >
          {health.isPending && "checking API…"}
          {health.isError && "API unreachable"}
          {health.data && `API ${health.data.status} · v${health.data.version}`}
        </span>
      </header>

      <Routes>
        <Route path="/" element={<Navigate to="/runs" replace />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </main>
  );
}
