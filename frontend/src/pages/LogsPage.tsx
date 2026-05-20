import SyncLogPanel from '@/features/sync/SyncLogPanel'

export default function LogsPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Sync Logs</h1>
      <SyncLogPanel />
    </div>
  )
}
