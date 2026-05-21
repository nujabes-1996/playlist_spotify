// Handoff panel — TSX snippets to drop into the user's actual repo.
// These are the deliverables called out in the spec.

const SNIPPETS = {
  tokens: `/* frontend/src/index.css — drop-in shadcn dark theme override */

@layer base {
  :root, .dark {
    /* --- shadcn HSL bridge (so existing primitives pick this up) --- */
    --background: 0 0% 7%;          /* #121212 */
    --foreground: 0 0% 100%;
    --card: 0 0% 11%;               /* #1c1c1c */
    --card-foreground: 0 0% 100%;
    --popover: 0 0% 14%;
    --popover-foreground: 0 0% 100%;
    --primary: 141 76% 48%;         /* #1DB954 */
    --primary-foreground: 0 0% 0%;
    --secondary: 0 0% 16%;
    --secondary-foreground: 0 0% 100%;
    --muted: 0 0% 14%;
    --muted-foreground: 0 0% 70%;
    --accent: 141 76% 48%;
    --accent-foreground: 0 0% 0%;
    --destructive: 354 76% 54%;     /* #e22134 */
    --destructive-foreground: 0 0% 100%;
    --border: 0 0% 100% / 0.09;
    --input: 0 0% 14%;
    --ring: 141 76% 48%;
    --radius: 0.5rem;

    /* --- app-level tokens used directly via arbitrary properties --- */
    --bg-base: #0d0d0d;
    --bg-app:  #121212;
    --bg-elevated:   #1c1c1c;
    --bg-elevated-2: #232323;
    --bg-hover:      #2a2a2a;
    --bg-row-hover:  #1a1a1a;
    --text-primary:   #ffffff;
    --text-secondary: #b3b3b3;
    --text-muted:     #6a6a6a;
    --accent-color:   #1DB954;
    --accent-hover:   #1ed760;
    --danger:         #e22134;
    --sidebar-w: 248px;
    --header-h: 64px;
  }

  html, body { background: var(--bg-base); color: var(--text-primary); }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif; }
}`,

  card: `// frontend/src/components/PlaylistCard.tsx
import { MoreHorizontal, Play, Check } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export interface Playlist {
  id: string;
  name: string;
  trackCount: number;
  coverUrl: string;
  included: boolean;
  hidden: boolean;
  isTarget?: boolean;
}

interface Props {
  playlist: Playlist;
  dimmed?: boolean;
  onToggleInclude?: (id: string) => void;
  onToggleHide?: (id: string) => void;
}

export function PlaylistCard({ playlist: p, dimmed, onToggleInclude, onToggleHide }: Props) {
  return (
    <div
      className={cn(
        "group relative rounded-lg bg-[var(--bg-elevated)] p-3.5 transition",
        "hover:bg-[var(--bg-hover)]",
        dimmed && "opacity-55 hover:opacity-100",
        p.included && "ring-2 ring-[var(--accent-color)] ring-inset",
      )}
    >
      <div className="relative aspect-square mb-3.5 overflow-hidden rounded-md shadow-[0_8px_24px_rgba(0,0,0,0.5)]">
        <img src={p.coverUrl} alt={p.name} className="h-full w-full object-cover" />
        {p.included && (
          <div className="absolute left-2 top-2 grid h-[22px] w-[22px] place-items-center
                          rounded-full bg-[var(--accent-color)] text-black">
            <Check size={12} strokeWidth={3} />
          </div>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger className="absolute right-2 top-2 grid h-8 w-8 place-items-center
                                          rounded-full bg-black/70 opacity-0 group-hover:opacity-100
                                          transition hover:bg-black/90">
            <MoreHorizontal size={14} />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {!p.isTarget && (
              <DropdownMenuItem onClick={() => onToggleInclude?.(p.id)}>
                {p.included ? "Remove from sync" : "Include in sync"}
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => onToggleHide?.(p.id)}>
              {p.hidden ? "Unhide" : "Hide playlist"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <button
          aria-label="Preview"
          className="absolute bottom-2 right-2 grid h-11 w-11 place-items-center rounded-full
                     bg-[var(--accent-color)] text-black shadow-lg opacity-0 translate-y-2
                     group-hover:opacity-100 group-hover:translate-y-0 transition
                     hover:bg-[var(--accent-hover)] hover:scale-105"
        >
          <Play size={16} fill="currentColor" />
        </button>
      </div>
      <h3 className="line-clamp-2 text-[14.5px] font-bold leading-tight">{p.name}</h3>
      <div className="mt-1 flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
        <span>{p.trackCount.toLocaleString()} tracks</span>
        {p.isTarget && (
          <>
            <span className="text-[var(--text-muted)]">•</span>
            <span className="font-bold text-[var(--accent-color)]">Sync target</span>
          </>
        )}
      </div>
    </div>
  );
}`,

  track: `// frontend/src/components/TrackRow.tsx
import { MoreHorizontal, Play, ExternalLink } from "lucide-react";
import {
  Tooltip, TooltipContent, TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface Track {
  id: string;
  title: string;
  artist: string;
  album: string;
  artUrl: string;
  durationLabel: string;     // "3:42"
  addedAgo: string;          // "3 days ago"
  addedAbs: string;          // "May 18, 2026"
  explicit?: boolean;
  hasVideo?: boolean;
  isNew?: boolean;
}

const cols = "grid grid-cols-[36px_minmax(220px,4fr)_minmax(160px,3fr)_minmax(140px,2fr)_60px_40px] gap-3.5";

export function TrackRow({ track, index }: { track: Track; index: number }) {
  return (
    <div className={\`group \${cols} items-center rounded px-4 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-row-hover)]\`}>
      <div className="grid place-items-center text-[var(--text-muted)]">
        <span className="group-hover:hidden">{index + 1}</span>
        <Play size={12} className="hidden group-hover:grid text-white" fill="currentColor" />
      </div>
      <div className="flex min-w-0 items-center gap-3">
        <img src={track.artUrl} alt="" className="h-10 w-10 flex-shrink-0 rounded-sm object-cover" />
        <div className="min-w-0">
          <div className="truncate text-[14.5px] text-white">
            {track.title}
            {track.isNew && <span className="ml-2 rounded bg-[var(--accent-color)]/15 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--accent-color)]">New</span>}
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-[12.5px] text-[var(--text-muted)]">
            {track.explicit && <span className="rounded-sm bg-[#535353] px-1 py-px text-[8px] font-bold text-[#d4d4d4]">E</span>}
            {track.hasVideo && <ExternalLink size={12} className="opacity-70" />}
            <a className="hover:underline hover:text-white">{track.artist}</a>
          </div>
        </div>
      </div>
      <div className="truncate">{track.album}</div>
      <Tooltip><TooltipTrigger asChild><div className="truncate">{track.addedAgo}</div></TooltipTrigger><TooltipContent>{track.addedAbs}</TooltipContent></Tooltip>
      <div className="text-right tabular-nums">{track.durationLabel}</div>
      <DropdownMenu>
        <DropdownMenuTrigger className="grid h-8 w-8 place-items-center rounded-full opacity-0 group-hover:opacity-100 hover:bg-[var(--bg-hover)]">
          <MoreHorizontal size={14} />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem>Hide from Recent Adds</DropdownMenuItem>
          <DropdownMenuItem>Open in Spotify</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}`,

  shell: `// frontend/src/components/AppShell.tsx
import { ReactNode, useState, useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Clock, Settings as Cog, ScrollText, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/",                  label: "Dashboard",      Icon: LayoutDashboard },
  { to: "/recently-added",    label: "Recently Added", Icon: Clock },
  { to: "/settings",          label: "Settings",       Icon: Cog },
  { to: "/logs",              label: "Logs",           Icon: ScrollText },
] as const;

export function AppShell({ pageTitle, syncStatus, lastSync, onSync }: {
  pageTitle: string;
  syncStatus: "ok" | "err";
  lastSync: string;
  onSync: () => void;
}) {
  const [scrolled, setScrolled] = useState(false);
  return (
    <div className="grid h-screen gap-2 p-2 grid-cols-[var(--sidebar-w)_1fr] bg-[var(--bg-base)]">
      <aside className="flex flex-col rounded-lg bg-[var(--bg-app)] p-3 pt-4">
        <div className="flex items-center gap-2.5 px-2.5 pb-4">
          <div className="grid h-7 w-7 place-items-center rounded-lg bg-[var(--accent-color)] font-extrabold text-black">P</div>
          <div className="text-[15px] font-bold tracking-tight">playlist<span className="text-[var(--accent-color)]">_</span>spotify</div>
        </div>
        <div className="px-3 pb-1.5 pt-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Workspace</div>
        <nav className="flex flex-col gap-0.5">
          {NAV.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} end
              className={({ isActive }) => cn(
                "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-[13.5px] font-semibold text-[var(--text-secondary)] transition",
                "hover:bg-[var(--bg-hover)] hover:text-white",
                isActive && "bg-[var(--bg-elevated-2)] text-white before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] before:rounded before:bg-[var(--accent-color)] [&_svg]:text-[var(--accent-color)]"
              )}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex items-center gap-2.5 border-t border-white/5 pt-3">
          {/* connection footer — see styles.css for .status-dot */}
        </div>
      </aside>
      <main className="relative flex min-w-0 flex-col overflow-hidden rounded-lg bg-[var(--bg-elevated)]">
        <header className={cn("sticky top-0 z-20 flex h-[var(--header-h)] items-center gap-3 px-8 backdrop-blur",
                              scrolled ? "bg-[var(--bg-app)]/95 border-b border-white/5" : "")}>
          <div className="flex-1 text-2xl font-extrabold tracking-tight">{pageTitle}</div>
          <div className="rounded-full border border-white/5 bg-[var(--bg-elevated-2)] px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)]">
            Last sync · {lastSync}
          </div>
          <Button onClick={onSync} className="rounded-full bg-[var(--accent-color)] text-black hover:bg-[var(--accent-hover)]">
            <RotateCw size={14} className="mr-2" />Sync now
          </Button>
        </header>
        <div onScroll={(e) => setScrolled(e.currentTarget.scrollTop > 4)}
             className="flex-1 overflow-y-auto px-8 pb-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}`,

  accordion: `// frontend/src/components/HiddenPlaylistsAccordion.tsx
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { PlaylistCard, Playlist } from "./PlaylistCard";

export function HiddenPlaylistsAccordion({
  hidden, onToggleHide,
}: { hidden: Playlist[]; onToggleHide: (id: string) => void }) {
  if (hidden.length === 0) return null;
  return (
    <Accordion type="single" collapsible className="mt-2 border-t border-white/5 pt-6">
      <AccordionItem value="hidden" className="border-0">
        <AccordionTrigger className="py-1 text-[22px] font-extrabold tracking-tight hover:no-underline">
          Hidden playlists ({hidden.length})
        </AccordionTrigger>
        <AccordionContent>
          <p className="my-3 max-w-[720px] text-sm text-[var(--text-muted)]">
            Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back.
          </p>
          <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(190px,1fr))]">
            {hidden.map(p => (
              <PlaylistCard key={p.id} playlist={p} dimmed onToggleHide={onToggleHide} />
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}`,

  shadcn: `# shadcn components to add

npx shadcn@latest add button input label dropdown-menu accordion table \\
  tooltip dialog separator scroll-area badge skeleton switch \\
  select textarea form sonner

# Then update your tailwind.config.ts so the css vars from index.css
# are reachable as arbitrary-property utilities (already supported in v3.3+).

# Recommended additional npm deps:
#   lucide-react       (icons — already in shadcn ecosystem)
#   class-variance-authority + clsx + tailwind-merge   (shadcn defaults)
#   react-router-dom@6 (for the NavLink wiring in AppShell)
#   @tanstack/react-query v5  (already in stack)

# File layout produced by these snippets:
#   frontend/src/
#     index.css                     ← Tokens block
#     components/
#       AppShell.tsx
#       PlaylistCard.tsx
#       TrackRow.tsx
#       HiddenPlaylistsAccordion.tsx
#     routes/
#       Dashboard.tsx               (uses PlaylistCard + HiddenPlaylistsAccordion)
#       RecentlyAdded.tsx           (uses TrackRow)
#       Settings.tsx
#       Logs.tsx`,
};

function HandoffPanel() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState('tokens');
  const tabs = [
    { id: 'tokens',    label: '1 · Tokens' },
    { id: 'card',      label: '2 · PlaylistCard' },
    { id: 'track',     label: '3 · TrackRow' },
    { id: 'shell',     label: '4 · AppShell' },
    { id: 'accordion', label: '5 · HiddenAccordion' },
    { id: 'shadcn',    label: '6 · shadcn add' },
  ];
  return (
    <>
      <div className="handoff">
        <button className="handoff-btn" onClick={() => setOpen(true)}>
          <I.Code size={14}/> Dev handoff · 6 snippets
        </button>
      </div>
      {open && (
        <div className="handoff-panel">
          <div className="handoff-head">
            <I.Code size={16}/>
            <h3>Developer handoff — drop into <span style={{ fontFamily: 'var(--font-mono)' }}>frontend/src/</span></h3>
            <div style={{ flex: 1 }}/>
            <button className="btn-icon" onClick={() => setOpen(false)}><I.X size={16}/></button>
          </div>
          <div className="handoff-tabs">
            {tabs.map(t => (
              <button key={t.id} className={'handoff-tab' + (tab === t.id ? ' active' : '')} onClick={() => setTab(t.id)}>{t.label}</button>
            ))}
          </div>
          <div className="handoff-body">
            <pre><code>{SNIPPETS[tab]}</code></pre>
          </div>
        </div>
      )}
    </>
  );
}

Object.assign(window, { HandoffPanel });
