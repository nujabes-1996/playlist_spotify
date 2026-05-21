import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import DashboardPage from './pages/DashboardPage'
import RecentlyAddedPage from './pages/RecentlyAddedPage'
import ConfigPage from './pages/ConfigPage'
import LogsPage from './pages/LogsPage'
import { Toaster } from '@/components/ui/sonner'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'recently-added', element: <RecentlyAddedPage /> },
      { path: 'settings', element: <ConfigPage /> },
      { path: 'config', element: <Navigate to="/settings" replace /> },
      { path: 'logs', element: <LogsPage /> },
    ],
  },
])

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster richColors position="bottom-right" />
    </>
  )
}
