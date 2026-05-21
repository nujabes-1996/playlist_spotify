// frontend/src/components/AppShell.tsx
import { ReactNode, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard, Clock, Settings as Cog, ScrollText,
  RotateCw, ChevronLeft, ChevronRight, Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/",                 label: "Dashboard",      Icon: LayoutDashboard },
  { to: "/recently-added",   label: "Recently Added", Icon: Clock },
  { to: "/settings",         label: "Settings",       Icon: Cog },
  { to: "/logs",             label: "Logs",           Icon: ScrollText },
] as const;

interface Props {
  syncStatus: "ok" | "err";
  lastSync: string;
  syncing?: boolean;
  hiddenCount?: number;
  connectedAs?: string;
  showSearch?: boolean;
  onSync: () => void;
}

export function AppShell({
  syncStatus, lastSync, syncing, hiddenCount = 0,
  connectedAs = "you@example.com", showSearch, onSync,
}: Props) {
  const [scrolled, setScrolled] = useState(false);

  return (
    <div className="grid h-screen gap-2 p-2 grid-cols-[var(--sidebar-w)_1fr] bg-[var(--bg-base)]">
      {/* ---------- SIDEBAR ---------- */}
      <aside className="flex min-h-0 flex-col rounded-lg bg-[var(--bg-app)] p-3 pt-4">
        {/* brand */}
        <div className="flex items-center gap-2.5 px-2.5 pb-4">
          <div className="relative grid h-7 w-7 place-items-center overflow-hidden rounded-lg
                          bg-gradient-to-br from-[var(--accent-color)] to-cyan-400 text-black font-extrabold">
            <span className="text-[11px]">P</span>
          </div>
          <div className="text-[15px] font-bold tracking-tight">
            playlist<span className="text-[var(--accent-color)]">_</span>spotify
          </div>
        </div>

        <div className="px-3 pb-1.5 pt-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Workspace
        </div>

        <nav className="flex flex-col gap-0.5">
          {NAV.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "group relative flex items-center gap-3 rounded-md px-3 py-2.5 text-[13.5px] font-semibold",
                  "text-[var(--text-secondary)] transition hover:bg-[var(--bg-hover)] hover:text-white",
                  isActive &&
                    "bg-[var(--bg-elevated-2)] text-white " +
                    "before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] before:rounded before:bg-[var(--accent-color)] " +
                    "[&_svg]:text-[var(--accent-color)]",
                )
              }
            >
              <Icon size={17} />
              <span>{label}</span>
              {to === "/" && hiddenCount > 0 && (
                <span className="ml-auto text-[11px] font-semibold text-[var(--text-muted)]">
                  {hiddenCount} hidden
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* footer */}
        <div className="mt-auto flex items-center gap-2.5 border-t border-white/5 px-2.5 pt-3 text-xs text-[var(--text-secondary)]">
          <div className="grid h-[26px] w-[26px] flex-shrink-0 place-items-center rounded-full
                          bg-gradient-to-br from-violet-500 to-pink-500 text-[11px] font-bold text-white">
            {connectedAs.slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0 leading-tight">
            <div className="text-[12px] font-semibold text-white">Connected as</div>
            <div className="truncate text-[13px] font-bold text-white">{connectedAs}</div>
            <div className="mt-0.5 flex items-center gap-1.5 text-[11px]">
              <span className={cn(
                "inline-block h-1.5 w-1.5 rounded-full shadow-[0_0_0_3px_rgba(29,185,84,0.18)]",
                syncStatus === "ok" ? "bg-[var(--accent-color)]" : "bg-[var(--danger)]",
              )} />
              {syncStatus === "ok" ? "Token healthy" : "Token expired"}
            </div>
          </div>
        </div>
      </aside>

      {/* ---------- MAIN ---------- */}
      <section
        className="relative flex min-w-0 flex-col overflow-hidden rounded-lg
                   bg-gradient-to-b from-[var(--bg-elevated)] via-[var(--bg-elevated)] to-[var(--bg-app)]"
        style={{ backgroundSize: "100% 280px", backgroundRepeat: "no-repeat" }}
      >
        {/* topbar */}
        <header className={cn(
          "sticky top-0 z-20 flex h-[var(--header-h)] items-center gap-3.5 px-8 backdrop-blur-md transition-colors",
          scrolled
            ? "bg-[var(--bg-app)]/95 border-b border-white/5"
            : "bg-gradient-to-b from-black/40 to-transparent",
        )}>
          <button disabled className="grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-muted)]">
            <ChevronLeft size={16} />
          </button>
          <button disabled className="grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-muted)]">
            <ChevronRight size={16} />
          </button>

          {showSearch && (
            <div className="ml-1.5 flex w-80 items-center gap-2 rounded-full border border-transparent
                            bg-[var(--bg-elevated-2)] px-3.5 py-1.5 text-[13px] text-[var(--text-secondary)]
                            focus-within:border-[var(--border-strong)]">
              <Search size={15} />
              <input className="w-full bg-transparent text-white outline-none placeholder:text-[var(--text-faint)]"
                     placeholder="Filter playlists…" />
            </div>
          )}

          <div className="flex-1" />

          <div className="flex items-center gap-3">
            <div className={cn(
              "inline-flex items-center gap-2 rounded-full border border-white/5 bg-[var(--bg-elevated-2)] py-1 pl-2 pr-3 text-xs font-semibold text-[var(--text-secondary)]",
            )}>
              <span className={cn(
                "h-[7px] w-[7px] rounded-full",
                syncStatus === "ok" ? "bg-[var(--accent-color)]" : "bg-[var(--danger)]",
              )} />
              <span>{syncStatus === "ok" ? `Last sync · ${lastSync}` : `Last sync failed · ${lastSync}`}</span>
            </div>
            <Button
              onClick={onSync}
              disabled={syncing}
              className="rounded-full bg-[var(--accent-color)] px-5 font-bold text-black
                         hover:bg-[var(--accent-hover)] hover:scale-[1.03] active:scale-[0.98] transition"
            >
              <RotateCw size={14} className={cn("mr-2", syncing && "animate-spin")} />
              {syncing ? "Syncing…" : "Sync now"}
            </Button>
          </div>
        </header>

        {/* scroll region */}
        <div
          className="flex-1 overflow-y-auto"
          onScroll={(e) => setScrolled(e.currentTarget.scrollTop > 4)}
        >
          <div className="px-8 pb-10 pt-2">
            <Outlet />
          </div>
        </div>
      </section>
    </div>
  );
}
