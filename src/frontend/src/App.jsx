import { useEffect, useState } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import Header from "./components/ui/Header.jsx";
import Sidebar from "./components/ui/Sidebar.jsx";
import { useRuns } from "./context/RunContext.jsx";

const THEME_KEY = "gridsentinel-theme";

function getInitialTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* ignore storage access errors (private mode, etc.) */
  }
  return "dark";
}

import CommandCenter from "./pages/CommandCenter.jsx";
import NewRun from "./pages/NewRun.jsx";
import AnomalyIntelligence from "./pages/AnomalyIntelligence.jsx";
import OptimizationPlan from "./pages/OptimizationPlan.jsx";
import CurtailmentImpact from "./pages/CurtailmentImpact.jsx";
import OperatorBrief from "./pages/OperatorBrief.jsx";
import RunHistory from "./pages/RunHistory.jsx";
import RunDetail from "./pages/RunDetail.jsx";
import NotFound from "./pages/NotFound.jsx";

export default function App() {
  const { datasetInfo, backendStatus, activeStatus } = useRuns();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* ignore storage access errors (private mode, etc.) */
    }
  }, [theme]);

  return (
    <div className="shell">
      <Sidebar
        open={sidebarOpen}
        collapsed={collapsed}
        backendOnline={backendStatus === "online"}
        onNavigate={() => setSidebarOpen(false)}
        onToggleCollapse={() => setCollapsed((c) => !c)}
      />
      {sidebarOpen && <div className="sidebar__backdrop sidebar__backdrop--visible" onClick={() => setSidebarOpen(false)} />}

      <div className={`shell__main ${collapsed ? "shell__main--collapsed" : ""}`}>
        <Header
          datasetInfo={datasetInfo}
          backendStatus={backendStatus}
          activeStatus={activeStatus}
          onMenuClick={() => setSidebarOpen((o) => !o)}
          theme={theme}
          onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
        />

        <main className="content" key={location.pathname}>
          <Routes location={location}>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/new-run" element={<NewRun />} />
            <Route path="/anomalies" element={<AnomalyIntelligence />} />
            <Route path="/optimization" element={<OptimizationPlan />} />
            <Route path="/curtailment" element={<CurtailmentImpact />} />
            <Route path="/brief" element={<OperatorBrief />} />
            <Route path="/history" element={<RunHistory />} />
            <Route path="/runs/:runId" element={<RunDetail />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
