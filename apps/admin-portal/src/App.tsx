import { useState } from "react";
import { AuthProvider, useAuth, LoginForm } from "@takaflow/ui";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { Dashboard } from "./Dashboard";
import { Staff } from "./Staff";
import { Inventory } from "./Inventory";
import { History } from "./History";
import { Reports } from "./Reports";
import { BuyerOrders } from "./BuyerOrders";
import { Partners } from "./Partners";

export type Page = "dashboard" | "staff" | "inventory" | "history" | "reports" | "buyer-orders" | "partners";

const PAGE_TITLE: Record<Page, string> = {
  dashboard: "Dashboard",
  staff: "Staff",
  inventory: "Inventory",
  history: "History",
  reports: "Reports",
  "buyer-orders": "Buyer Orders",
  partners: "Partners",
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

  // Staff creation and partner management are admin-only; a staff account
  // that opens admin-portal (not blocked — it's a valid, if unusual, way to
  // check on one's own branch) just never sees those nav items or pages.
  const isAdmin = user.role === "admin";
  const activePage = (page === "staff" || page === "partners") && !isAdmin ? "dashboard" : page;

  return (
    <div className="flex h-screen overflow-hidden bg-mist/10 print:h-auto print:overflow-visible">
      <Sidebar page={activePage} onNavigate={setPage} open={sidebarOpen} onClose={() => setSidebarOpen(false)} isAdmin={isAdmin} />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col print:h-auto">
        <TopBar user={user} onMenuClick={() => setSidebarOpen(true)} onSignOut={logout} />
        <main className="min-h-0 flex-1 overflow-y-auto p-5 sm:p-8 print:h-auto print:overflow-visible print:p-0">
          <h1 className="mb-5 text-2xl font-extrabold text-ink">{PAGE_TITLE[activePage]}</h1>
          {activePage === "dashboard" && <Dashboard user={user} onNavigate={setPage} />}
          {activePage === "staff" && isAdmin && <Staff />}
          {activePage === "inventory" && <Inventory />}
          {activePage === "history" && <History />}
          {activePage === "reports" && <Reports />}
          {activePage === "buyer-orders" && <BuyerOrders user={user} />}
          {activePage === "partners" && isAdmin && <Partners />}
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
