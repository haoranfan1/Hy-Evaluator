import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, NavLink, Route, Routes } from "react-router";

import { I18nProvider, useI18n } from "./i18n";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { RegressionsPage } from "./pages/RegressionsPage";
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

function LanguageToggle() {
  const { language, setLanguage } = useI18n();
  return (
    <div className="lang-toggle" role="group" aria-label="Language">
      <button
        type="button"
        className={language === "en" ? "lang-option lang-active" : "lang-option"}
        aria-pressed={language === "en"}
        onClick={() => setLanguage("en")}
      >
        EN
      </button>
      <button
        type="button"
        className={language === "zh" ? "lang-option lang-active" : "lang-option"}
        aria-pressed={language === "zh"}
        onClick={() => setLanguage("zh")}
      >
        中文
      </button>
    </div>
  );
}

function AppShell() {
  const { t } = useI18n();
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth, retry: false });

  return (
    <main className="shell">
      <header className="app-head">
        <div>
          <p className="eyebrow">{t("app.eyebrow")}</p>
          <h1 className="app-title">
            <Link to="/runs">{t("app.title")}</Link>
          </h1>
        </div>
        <div className="head-side">
          <nav className="main-nav" aria-label="Main">
            <NavLink to="/runs">{t("nav.runs")}</NavLink>
            <NavLink to="/analytics">{t("nav.analytics")}</NavLink>
            <NavLink to="/regressions">{t("nav.regressions")}</NavLink>
          </nav>
          <LanguageToggle />
          <span
            className={`chip chip-${health.data ? health.data.status : "pending"}`}
            title="Local API status"
          >
            {health.isPending && t("health.checking")}
            {health.isError && t("health.unreachable")}
            {health.data && `API ${health.data.status} · v${health.data.version}`}
          </span>
        </div>
      </header>

      <Routes>
        <Route path="/" element={<Navigate to="/runs" replace />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/regressions" element={<RegressionsPage />} />
      </Routes>
    </main>
  );
}

export function App() {
  return (
    <I18nProvider>
      <AppShell />
    </I18nProvider>
  );
}
