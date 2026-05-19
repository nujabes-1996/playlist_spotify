import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

export default function SpotifyConnect() {
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const urlParams = new URLSearchParams(window.location.search)
  const authError = urlParams.get('auth_error') === '1'

  async function handleConnect() {
    setIsConnecting(true)
    setError(null)
    try {
      const { auth_url } = await api.post<{ auth_url: string }>('/auth/connect')
      window.location.href = auth_url
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Connection failed')
      setIsConnecting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16 space-y-6">
      <h1 className="text-2xl font-bold">Connect Spotify</h1>
      <p className="text-sm text-muted-foreground">
        Credentials saved. Now connect your Spotify account to grant access to your playlists.
      </p>
      <div className="rounded border bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
        <p className="font-medium">Before connecting, add this Redirect URI to your Spotify app:</p>
        <p className="font-mono select-all">http://localhost:8000/api/v1/auth/callback</p>
        <p>Go to <span className="font-mono">developer.spotify.com</span> → Your App → Edit Settings → Redirect URIs.</p>
      </div>
      {(authError || error) && (
        <p className="text-sm text-red-600">
          {error ?? 'Spotify authorization was denied or failed. Please try again.'}
        </p>
      )}
      <Button onClick={handleConnect} disabled={isConnecting}>
        {isConnecting ? 'Redirecting to Spotify…' : 'Connect Spotify'}
      </Button>
    </div>
  )
}
