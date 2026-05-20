import { NavLink } from 'react-router-dom'

export default function NavBar() {
  return (
    <nav className="border-b border-[var(--border)] bg-[var(--background)] px-6 py-4 flex items-center gap-8">
      <span className="text-[var(--spotify-green)] font-bold text-lg tracking-tight select-none">
        ● Playlist Sync
      </span>
      <div className="flex gap-6">
        {[
          { to: '/', label: 'Dashboard', end: true },
          { to: '/config', label: 'Config', end: false },
          { to: '/logs', label: 'Logs', end: false },
        ].map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `text-sm font-medium transition-colors ${
                isActive
                  ? 'text-[var(--spotify-green)]'
                  : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
