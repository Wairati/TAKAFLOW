import { useState } from "react";
import { AuthProvider, useAuth, LoginForm } from "@takaflow/ui";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { Dashboard } from "./Dashboard";
import { CreateStaffForm } from "./CreateStaffForm";
import { Inventory } from "./Inventory";
import { History } from "./History";
import { Reports } from "./Reports";

export type Page = "dashboard" | "staff" | "inventory" | "history" | "reports";

const PAGE_TITLE: Record<Page, string> = {
  dashboard: "Dashboard",
  staff: "Staff",
  inventory: "Inventory",
  history: "History",
  reports: "Reports",
};

function AuthedApp() {
  const { user, loading, logout } = useAuth();
  const [page, setPage] = useState<Page>("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (loading) return null;
  if (!user)
    return (
      <LoginForm
        eyebrow="Admin Console"
        subtitle="Sign in to oversee branches, materials, rates, and every collection across the network."
        footerLabel="TAKAFLOW Admin · v1.0"
        photoCaption="Oversee every branch, every payout, every kilogram — all from one place."
        photoSrc="/images/forest-stream.jpg"
        photoAlt="A clear forest stream"
      />
    );

  // Staff creation is admin-only; a staff account that opens admin-portal
  // (not blocked — it's a valid, if unusual, way to check on one's own
  // branch) just never sees that nav item or page.
  const isAdmin = user.role === "admin";
  const activePage = page === "staff" && !isAdmin ? "dashboard" : page;

  return (
    <div className="flex min-h-screen bg-mist/10">
      <Sidebar page={activePage} onNavigate={setPage} open={sidebarOpen} onClose={() => setSidebarOpen(false)} isAdmin={isAdmin} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar user={user} onMenuClick={() => setSidebarOpen(true)} onSignOut={logout} />
        <main className="flex-1 overflow-y-auto p-5 sm:p-8">
          <h1 className="mb-5 text-2xl font-extrabold text-ink">{PAGE_TITLE[activePage]}</h1>
          {activePage === "dashboard" && <Dashboard user={user} onNavigate={setPage} />}
          {activePage === "staff" && isAdmin && <CreateStaffForm />}
          {activePage === "inventory" && <Inventory />}
          {activePage === "history" && <History />}
          {activePage === "reports" && <Reports />}
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AuthedApp />
    </AuthProvider>
  );
}

export default App;
