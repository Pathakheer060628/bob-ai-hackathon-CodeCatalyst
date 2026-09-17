import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import Header from "./components/ui/Header.jsx";
import Sidebar from "./components/ui/Sidebar.jsx";
import { useRuns } from "./context/RunContext.jsx";

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
  const { datasetInfo, backendStatus, activeStatus, activeResult } = useRuns();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const activeVerified = activeResult ? activeResult.verification?.trusted : null;

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
          activeVerified={activeVerified}
          onMenuClick={() => setSidebarOpen((o) => !o)}
        />

        <main className="content">
          <Routes>
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
