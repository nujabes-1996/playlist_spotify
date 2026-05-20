import { Outlet } from 'react-router-dom'
import NavBar from './NavBar'

export default function AppShell() {
  return (
    <div className="min-h-screen flex flex-col bg-[var(--background)]">
      <NavBar />
      <main className="flex-1 container mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
