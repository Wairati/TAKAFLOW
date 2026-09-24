import { useState } from "react";
import { ChevronDownIcon, MenuIcon } from "./icons";
import type { UserOut } from "@takaflow/types";

const ROLE_LABEL: Record<UserOut["role"], string> = {
  admin: "Admin",
  collection_point_staff: "Collection Point Staff",
};

export function TopBar({
  user,
  onMenuClick,
  onSignOut,
}: {
  user: UserOut;
  onMenuClick: () => void;
  onSignOut: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="flex items-center justify-between border-b border-black/5 bg-white px-5 py-3.5">
      <button onClick={onMenuClick} className="rounded-lg p-2 text-ink/60 hover:bg-black/5 lg:hidden">
        <MenuIcon className="h-6 w-6" />
      </button>
      <span className="hidden lg:block" />

      <div className="relative">
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="flex items-center gap-2.5 rounded-full py-1 pl-1 pr-2 hover:bg-black/5"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-mint text-sm font-bold text-forest">
            {user.full_name
              .split(" ")
              .map((p) => p[0])
              .slice(0, 2)
              .join("")
              .toUpperCase()}
          </span>
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-bold leading-tight text-ink">{user.full_name}</span>
            <span className="block text-xs leading-tight text-ink/50">{ROLE_LABEL[user.role]}</span>
          </span>
          <ChevronDownIcon className="h-4 w-4 text-ink/40" />
        </button>

        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 z-20 mt-2 w-40 overflow-hidden rounded-xl border border-black/5 bg-white shadow-lg">
              <button
                onClick={onSignOut}
                className="block w-full px-4 py-2.5 text-left text-sm font-semibold text-ink hover:bg-black/5"
              >
                Sign out
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
