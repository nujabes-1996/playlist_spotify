import { NavLink } from 'react-router-dom'

export default function NavBar() {
  return (
    <nav className="border-b px-6 py-4 flex gap-6">
      <NavLink to="/" end>Dashboard</NavLink>
      <NavLink to="/config">Config</NavLink>
      <NavLink to="/logs">Logs</NavLink>
    </nav>
  )
}
