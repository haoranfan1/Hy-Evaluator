import { useQuery } from "@tanstack/react-query";

type ComponentHealth = {
  status: "ready" | "not_configured";
  detail: string;
};

type HealthResponse = {
  status: "ready" | "degraded";
  version: string;
  components: Record<string, ComponentHealth>;
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
      <p className="eyebrow">Hy3 process evaluation workbench</p>
      <h1>Evidence before verdict.</h1>
      <p className="lede">
        The application foundation is ready for the first ATIF-to-evidence-debugger slice.
      </p>

      <section className="status-card" aria-labelledby="foundation-status">
        <div>
          <p className="label">Foundation status</p>
          <h2 id="foundation-status">
            {health.isPending && "Checking local API…"}
            {health.isError && "API is not reachable"}
            {health.data && (health.data.status === "ready" ? "Ready" : "Configuration needed")}
          </h2>
        </div>
        {health.data && <span className={`badge badge-${health.data.status}`}>v{health.data.version}</span>}
      </section>

      {health.data && (
        <div className="component-grid">
          {Object.entries(health.data.components).map(([name, component]) => (
            <article className="component-card" key={name}>
              <div className="component-heading">
                <h3>{name}</h3>
                <span className={`dot dot-${component.status}`} aria-hidden="true" />
              </div>
              <p>{component.detail}</p>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
