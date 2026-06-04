"use client";

import { Bell, Menu, Moon, Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { normalizeWorkspaceId } from "@/lib/workspace";
import { CurrentUser, WorkspaceMembership } from "@/types/auth";

type Props = {
  currentUser: CurrentUser | null;
  currentWorkspace: WorkspaceMembership | null;
  currentWorkspaceId: string | null;
  onOpenMenu: () => void;
  onLogout: () => void;
  onSwitchWorkspace: (workspaceId: string) => void;
};

export function AppTopbar({ currentUser, currentWorkspace, currentWorkspaceId, onOpenMenu, onLogout, onSwitchWorkspace }: Props) {
  const router = useRouter();
  const validMemberships = currentUser?.memberships.filter((membership) => normalizeWorkspaceId(membership.workspace_id)) ?? [];

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-[#F8F7FC]/90 px-3 py-3 backdrop-blur-xl sm:px-4 md:px-6">
      <div className="flex items-center gap-2 sm:gap-3">
        <button className="grid h-11 w-11 place-items-center rounded-2xl border border-slate-200 bg-white shadow-sm lg:hidden" onClick={onOpenMenu} aria-label="Open navigation">
          <Menu className="h-5 w-5" />
        </button>

        <div className="relative hidden flex-1 md:block">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="h-12 w-full rounded-2xl border border-slate-200 bg-white pl-11 pr-4 text-sm shadow-sm outline-none transition focus:border-violet-300 focus:ring-4 focus:ring-violet-100"
            placeholder="Search customers, orders, products…"
          />
        </div>

        <select className="hidden h-12 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm lg:block" aria-label="Dashboard date range">
          <option>Last 30 days</option>
          <option>This month</option>
          <option>Today</option>
        </select>

        <button className="hidden h-12 items-center rounded-2xl border border-slate-200 bg-white px-4 text-sm font-bold shadow-sm transition hover:border-violet-200 hover:text-violet-700 md:inline-flex">
          Create ▾
        </button>
        <button className="hidden h-12 w-12 place-items-center rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:border-violet-200 hover:text-violet-700 sm:grid" aria-label="Notifications">
          <Bell className="h-5 w-5" />
        </button>
        <button className="hidden h-12 w-12 place-items-center rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:border-violet-200 hover:text-violet-700 sm:grid" aria-label="Theme toggle">
          <Moon className="h-5 w-5" />
        </button>
        <button
          className="grid h-11 w-11 place-items-center rounded-2xl bg-[linear-gradient(135deg,#6D28D9_0%,#EC4899_45%,#F97316_75%,#FACC15_100%)] text-white shadow-lg shadow-pink-500/20 sm:h-12 sm:w-12"
          onClick={() => router.push("/orders")}
          aria-label="Create order"
        >
          <Plus className="h-5 w-5" />
        </button>
      </div>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="truncate text-sm font-black text-slate-900">{currentWorkspace?.workspace_name ?? "Workspace"}</p>
          <p className="truncate text-xs text-slate-500">{currentUser?.email}</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {validMemberships.length > 1 ? (
            <select
              className="min-h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm shadow-sm"
              value={currentWorkspaceId ?? ""}
              onChange={(event) => { const workspaceId = normalizeWorkspaceId(event.target.value); if (workspaceId) onSwitchWorkspace(workspaceId); }}
              aria-label="Switch workspace"
            >
              {validMemberships.map((membership) => (
                <option key={membership.workspace_id} value={membership.workspace_id}>
                  {membership.workspace_name} · {membership.role}
                </option>
              ))}
            </select>
          ) : null}
          <button className="min-h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-700 shadow-sm transition hover:border-violet-200 hover:text-violet-700" onClick={onLogout}>
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
