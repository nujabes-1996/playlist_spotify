import { useConfig } from '@/hooks/useConfig'
import { useAuthStatus } from '@/hooks/useAuthStatus'
import SetupWizard from '@/features/config/SetupWizard'
import SpotifyConnect from '@/features/auth/SpotifyConnect'

export default function DashboardPage() {
  const config = useConfig()
  const authStatus = useAuthStatus()

  if (config.isPending || authStatus.isPending) {
    return <div className="p-6 text-sm text-muted-foreground">Loading…</div>
  }

  if (config.isError || authStatus.isError) {
    return <div className="p-6 text-sm text-red-600">Failed to load configuration.</div>
  }

  if (config.data.setup_required) {
    return <SetupWizard />
  }

  if (!authStatus.data.authenticated) {
    return <SpotifyConnect />
  }

  return <h1 className="text-2xl font-bold">Dashboard</h1>
}
