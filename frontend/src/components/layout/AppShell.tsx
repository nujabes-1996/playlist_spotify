import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Clock,
  Settings as Cog,
  ScrollText,
  RotateCw,
  ChevronLeft,
  ChevronRight,
  Search,
  Menu,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import { useSyncStatus } from '@/hooks/useSyncStatus'
import { useSyncStream } from '@/hooks/useSyncStream'
import { formatRelative } from '@/lib/relativeTime'

const NAV = [
  { to: '/', label: 'Dashboard', Icon: LayoutDashboard, end: true },
  { to: '/recently-added', label: 'Recently Added', Icon: Clock, end: false },
  { to: '/settings', label: 'Settings', Icon: Cog, end: false },
  { to: '/logs', label: 'Logs', Icon: ScrollText, end: false },
] as const

function computeInitials(label: string): string {
  const letters = label.match(/[a-z0-9]/gi)?.slice(0, 2).join('') ?? '??'
  return letters.toUpperCase()
}

type SidebarContentsProps = {
  collapsed: boolean
  connectedAs: string
  initials: string
  authResolved: boolean
  authOk: boolean
  onNavigate?: () => void
}

function SidebarContents({
  collapsed,
  connectedAs,
  initials,
  authResolved,
  authOk,
  onNavigate,
}: SidebarContentsProps) {
  return (
    <>
      {/* brand */}
      <div
        className={cn(
          'flex items-center pb-4',
          collapsed ? 'justify-center px-0' : 'gap-2.5 px-2.5',
        )}
      >
        <div
          className="relative grid h-7 w-7 place-items-center overflow-hidden rounded-lg
                     bg-gradient-to-br from-[var(--accent-color)] to-cyan-400 text-black font-extrabold"
        >
          <span className="text-[11px]">P</span>
        </div>
        {!collapsed && (
          <div className="text-[15px] font-bold tracking-tight">
            playlist<span className="text-[var(--accent-color)]">_</span>spotify
          </div>
        )}
      </div>

      {!collapsed && (
        <div className="px-3 pb-1.5 pt-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Workspace
        </div>
      )}

      <nav className={cn('flex flex-col gap-0.5', collapsed && 'items-center')}>
        {NAV.map(({ to, label, Icon, end }) => {
          const link = (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center rounded-md text-[13.5px] font-semibold',
                  'text-[var(--text-secondary)] transition hover:bg-[var(--bg-hover)] hover:text-white',
                  collapsed
                    ? 'h-10 w-10 justify-center'
                    : 'gap-3 px-3 py-2.5',
                  isActive &&
                    'bg-[var(--bg-elevated-2)] text-white ' +
                      'before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] before:rounded before:bg-[var(--accent-color)] ' +
                      '[&_svg]:text-[var(--accent-color)]',
                )
              }
            >
              <Icon size={17} />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          )

          if (collapsed) {
            return (
              <Tooltip key={to}>
                <TooltipTrigger asChild>{link}</TooltipTrigger>
                <TooltipContent side="right">{label}</TooltipContent>
              </Tooltip>
            )
          }
          return link
        })}
      </nav>

      {/* footer */}
      <div
        className={cn(
          'mt-auto border-t border-[var(--border-soft)] pt-3 text-xs text-[var(--text-secondary)]',
          collapsed ? 'flex justify-center px-0' : 'flex items-center gap-2.5 px-2.5',
        )}
      >
        <div
          className="grid h-[26px] w-[26px] flex-shrink-0 place-items-center rounded-full
                     bg-gradient-to-br from-violet-500 to-pink-500 text-[11px] font-bold text-white"
        >
          {initials}
        </div>
        {!collapsed && (
          <div className="min-w-0 leading-tight">
            <div className="text-[12px] font-semibold text-white">Connected as</div>
            <div className="truncate text-[13px] font-bold text-white">{connectedAs}</div>
            <div className="mt-0.5 flex items-center gap-1.5 text-[11px]">
              <span
                className={cn(
                  'inline-block h-1.5 w-1.5 rounded-full',
                  !authResolved
                    ? 'bg-[var(--text-muted)]'
                    : authOk
                      ? 'bg-[var(--accent-color)] shadow-[0_0_0_3px_rgba(29,185,84,0.18)]'
                      : 'bg-[var(--danger)]',
                )}
              />
              {!authResolved ? 'Connecting…' : authOk ? 'Token healthy' : 'Token expired'}
            </div>
          </div>
        )}
      </div>
    </>
  )
}

export default function AppShell() {
  const { pathname } = useLocation()
  const showSearch = pathname === '/'
  const auth = useAuthStatus()
  const sync = useSyncStatus()
  const { startStream, isStreaming } = useSyncStream()
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  const authResolved = !auth.isPending && !auth.isError
  const authOk = auth.data?.authenticated === true
  const connectedAs =
    auth.data?.spotify_user_id ??
    (auth.isPending ? 'Connecting…' : 'Not connected')
  const initials = authResolved && auth.data?.spotify_user_id
    ? computeInitials(auth.data.spotify_user_id)
    : '?'

  const lastSyncRelative = sync.data ? formatRelative(sync.data.timestamp) : null
  const syncFailed = sync.data?.status === 'failure'

  const statusLabel =
    lastSyncRelative == null
      ? 'Never synced'
      : syncFailed
        ? `Last sync failed · ${lastSyncRelative}`
        : `Last sync · ${lastSyncRelative}`

  return (
    <TooltipProvider delayDuration={200}>
      <div className="grid h-screen gap-2 p-2 grid-cols-[1fr] md:grid-cols-[64px_1fr] lg:grid-cols-[var(--sidebar-w)_1fr] bg-[var(--bg-base)]">
        {/* Desktop sidebar (≥ lg) */}
        <aside className="hidden lg:flex min-h-0 flex-col rounded-lg bg-[var(--bg-app)] p-3 pt-4">
          <SidebarContents
            collapsed={false}
            connectedAs={connectedAs}
            initials={initials}
            authResolved={authResolved}
            authOk={authOk}
          />
        </aside>
        {/* Tablet icon rail (md..lg) */}
        <aside className="hidden md:flex lg:hidden min-h-0 flex-col rounded-lg bg-[var(--bg-app)] p-2 pt-4">
          <SidebarContents
            collapsed
            connectedAs={connectedAs}
            initials={initials}
            authResolved={authResolved}
            authOk={authOk}
          />
        </aside>

        {/* MAIN */}
        <section
          className="relative flex min-w-0 flex-col overflow-hidden rounded-lg
                     bg-gradient-to-b from-[var(--bg-elevated)] via-[var(--bg-elevated)] to-[var(--bg-app)]"
          style={{ backgroundSize: '100% 280px', backgroundRepeat: 'no-repeat' }}
        >
          {/* topbar */}
          <header
            className={cn(
              'sticky top-0 z-20 flex h-[var(--header-h)] items-center gap-3.5 px-4 md:px-8 backdrop-blur-md transition-colors',
              scrolled
                ? 'bg-[rgba(18,18,18,0.95)] border-b border-[var(--border-soft)]'
                : 'bg-gradient-to-b from-black/40 to-transparent',
            )}
          >
            {/* Mobile hamburger (< md) */}
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <button
                  type="button"
                  aria-label="Open navigation"
                  className="md:hidden grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-secondary)]"
                >
                  <Menu size={18} />
                </button>
              </SheetTrigger>
              <SheetContent
                side="left"
                className="w-[var(--sidebar-w)] max-w-[80vw] bg-[var(--bg-app)] p-3 pt-4 border-0 flex flex-col"
              >
                <SheetTitle className="sr-only">Navigation</SheetTitle>
                <SidebarContents
                  collapsed={false}
                  connectedAs={connectedAs}
                  initials={initials}
                  authResolved={authResolved}
                  authOk={authOk}
                  onNavigate={() => setMobileOpen(false)}
                />
              </SheetContent>
            </Sheet>

            <button
              disabled
              aria-label="Back"
              className="hidden md:grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-muted)]"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              disabled
              aria-label="Forward"
              className="hidden md:grid h-8 w-8 place-items-center rounded-full bg-black/55 text-[var(--text-muted)]"
            >
              <ChevronRight size={16} />
            </button>

            {showSearch && (
              <div
                className="ml-1.5 hidden md:flex w-80 items-center gap-2 rounded-full border border-transparent
                           bg-[var(--bg-elevated-2)] px-3.5 py-1.5 text-[13px] text-[var(--text-secondary)]
                           focus-within:border-[var(--border-strong)]"
              >
                <Search size={15} />
                <input
                  className="w-full bg-transparent text-white outline-none placeholder:text-[var(--text-faint)]"
                  placeholder="Filter playlists…"
                />
              </div>
            )}

            <div className="flex-1" />

            <div className="flex items-center gap-3">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border-soft)] bg-[var(--bg-elevated-2)] py-1 pl-2 pr-2 md:pr-3 text-xs font-semibold text-[var(--text-secondary)]">
                    <span
                      className={cn(
                        'h-[7px] w-[7px] rounded-full',
                        lastSyncRelative == null
                          ? 'bg-[var(--text-muted)]'
                          : syncFailed
                            ? 'bg-[var(--danger)]'
                            : 'bg-[var(--accent-color)]',
                      )}
                    />
                    <span className="hidden md:inline">{statusLabel}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom">{statusLabel}</TooltipContent>
              </Tooltip>

              <Button
                onClick={() => startStream()}
                disabled={isStreaming}
                aria-label={isStreaming ? 'Syncing' : 'Sync now'}
                className="rounded-full bg-[var(--accent-color)] px-2 md:px-5 font-bold text-black
                           hover:bg-[var(--accent-hover)] hover:scale-[1.03] active:scale-[0.98] transition"
              >
                <RotateCw size={14} className={cn('md:mr-2', isStreaming && 'animate-spin')} />
                <span className="hidden md:inline">{isStreaming ? 'Syncing…' : 'Sync now'}</span>
              </Button>
            </div>
          </header>

          {/* scroll region */}
          <div
            className="flex-1 overflow-y-auto overflow-x-hidden"
            onScroll={(e) => setScrolled(e.currentTarget.scrollTop > 4)}
          >
            <div className="px-4 md:px-8 pb-10 pt-2">
              <Outlet />
            </div>
          </div>
        </section>
      </div>
    </TooltipProvider>
  )
}
