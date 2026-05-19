import { useConfig } from '@/hooks/useConfig'
import SetupWizard from '@/features/config/SetupWizard'

export default function DashboardPage() {
  const { data, isPending, isError } = useConfig()

  if (isPending) {
    return <div className="p-6 text-sm text-muted-foreground">Loading…</div>
  }

  if (isError) {
    return <div className="p-6 text-sm text-red-600">Failed to load configuration.</div>
  }

  if (data.setup_required) {
    return <SetupWizard />
  }

  return <h1 className="text-2xl font-bold">Dashboard</h1>
}
