import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

export default function ReauthBanner() {
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleReconnect() {
    setIsConnecting(true)
    setError(null)
    try {
      const { auth_url } = await api.post<{ auth_url: string }>('/auth/connect')
      window.location.href = auth_url
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reconnection failed')
      setIsConnecting(false)
    }
  }

  return (
    <div className="rounded border border-yellow-300 bg-yellow-50 p-4 flex items-center justify-between gap-4">
      <div>
        <p className="font-medium text-yellow-900">Spotify disconnected</p>
        <p className="text-sm text-yellow-700">
          {error ?? 'Your Spotify session has expired or been revoked. Reconnect to resume syncing.'}
        </p>
      </div>
      <Button variant="outline" onClick={handleReconnect} disabled={isConnecting}>
        {isConnecting ? 'Redirecting…' : 'Reconnect Spotify'}
      </Button>
    </div>
  )
}
