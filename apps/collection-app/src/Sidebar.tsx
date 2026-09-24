import { CashIcon, ChartIcon, ClockIcon, HomeIcon, PackageIcon, PlusBoxIcon } from "./icons";
import type { Page } from "./App";

const NAV_ITEMS: { page: Page; label: string; icon: typeof HomeIcon }[] = [
  { page: "dashboard", label: "Dashboard", icon: HomeIcon },
  { page: "log-collection", label: "Log Collection", icon: PlusBoxIcon },
  { page: "inventory", label: "Inventory", icon: PackageIcon },
  { page: "collectors", label: "Collectors", icon: CashIcon },
  { page: "history", label: "History", icon: ClockIcon },
  { page: "reports", label: "Reports", icon: ChartIcon },
];

interface SidebarProps {
  page: Page;
  onNavigate: (page: Page) => void;
  branchName: string;
  isOnline: boolean;
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ page, onNavigate, branchName, isOnline, open, onClose }: SidebarProps) {
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onClose} />}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col bg-forest px-5 py-6 text-mist transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-2.5 px-1">
          <img src="/logo-mark.jpg" alt="TAKAFLOW" className="h-10 w-10 rounded-xl object-cover" />
          <div>
            <div className="text-lg font-extrabold tracking-tight text-white">TAKAFLOW</div>
            <div className="text-xs text-mist/70">Turning Waste Into Worth</div>
          </div>
        </div>

        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const active = item.page === page;
            return (
              <button
                key={item.page}
                onClick={() => {
                  onNavigate(item.page);
                  onClose();
                }}
                className={`flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-left text-sm font-semibold transition ${
                  active ? "bg-white/10 text-white" : "text-mist/70 hover:bg-white/5 hover:text-white"
                }`}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="space-y-3 border-t border-white/10 pt-4">
          <div className="rounded-xl bg-white/5 px-3.5 py-2.5">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-mist/50">Branch</div>
            <div className="text-sm font-semibold text-white">{branchName}</div>
          </div>
          <div className="flex items-center gap-2 px-1 text-xs font-medium text-mist/70">
            <span className={`h-2 w-2 rounded-full ${isOnline ? "bg-lime" : "bg-pale-lime/40"}`} />
            {isOnline ? "Online" : "Offline — data will sync when online"}
          </div>
          <p className="px-1 pt-2 text-xs leading-relaxed text-mist/40">Cleaner communities. A greener tomorrow.</p>
        </div>
      </aside>
    </>
  );
}
