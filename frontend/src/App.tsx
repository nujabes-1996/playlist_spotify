import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import DashboardPage from './pages/DashboardPage'
import ConfigPage from './pages/ConfigPage'
import LogsPage from './pages/LogsPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'config', element: <ConfigPage /> },
      { path: 'logs', element: <LogsPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
