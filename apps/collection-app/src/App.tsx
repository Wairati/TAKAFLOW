import { useState } from "react";
import { AuthProvider, useAuth, LoginForm } from "@takaflow/ui";
import { useOnlineStatus } from "./sync";
import { useBranch } from "./useBranch";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { Dashboard } from "./Dashboard";
import { CollectionForm } from "./CollectionForm";
import { Inventory } from "./Inventory";
import { Collectors } from "./Collectors";
import { History } from "./History";
import { BuyerOrders } from "./BuyerOrders";

// Reports (company-wide/branch analytics) is admin-only — see admin-portal
// instead. Staff never had a reason to see it here.
export type Page = "dashboard" | "log-collection" | "inventory" | "collectors" | "history" | "buyer-orders";

const PAGE_TITLE: Record<Page, string> = {
  dashboard: "Dashboard",
  "log-collection": "Log Collection",
  inventory: "Inventory",
  collectors: "Collectors",
  history: "History",
  "buyer-orders": "Buyer Orders",
};

function AuthedApp() {
  const { user, loading, logout } = useAuth();
  const [page, setPage] = useState<Page>("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isOnline = useOnlineStatus();
  const branch = useBranch(user?.collection_point_id ?? null);

  if (loading) return null;
  if (!user)
    return (
      <LoginForm
        eyebrow="Collection Point System"
        subtitle="Sign in with your employee number to manage collections, verify materials, and keep your collection point moving."
        footerLabel="TAKAFLOW POS · v1.0"
        photoCaption="Every collection you log keeps material out of the dump and puts money in someone's hands."
        photoSrc="/images/cleanup-1.jpg"
        photoAlt="Volunteers clearing plastic waste from a drainage channel"
        identifierMode="employeeNumber"
      />
    );

  return (
    <div className="flex h-screen overflow-hidden bg-mist/10">
      <Sidebar
        page={page}
        onNavigate={setPage}
        branchName={branch?.name ?? "Unassigned"}
        isOnline={isOnline}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <TopBar user={user} onMenuClick={() => setSidebarOpen(true)} onSignOut={logout} />
        <main className="min-h-0 flex-1 overflow-y-auto p-5 sm:p-8">
          <h1 className="mb-5 text-2xl font-extrabold text-ink">{PAGE_TITLE[page]}</h1>
          {page === "dashboard" && <Dashboard user={user} branch={branch} onNavigate={setPage} />}
          {page === "log-collection" && <CollectionForm user={user} />}
          {page === "inventory" && <Inventory user={user} />}
          {page === "collectors" && <Collectors user={user} />}
          {page === "history" && <History user={user} />}
          {page === "buyer-orders" && <BuyerOrders user={user} />}
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
