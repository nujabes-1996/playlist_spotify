import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { ConnectRequest } from '@/types'

type LoginScreenProps = {
  hasPreviousAuth?: boolean
  // The backend's actual Redirect URI (from GET /auth/status). Source of truth so the
  // displayed value always matches what the backend sends to Spotify — never a hardcoded
  // dev string (which is wrong in prod) nor window.location.origin (can differ from the
  // backend's configured SPOTIFY_REDIRECT_URI).
  redirectUri?: string
}

/**
 * Single login screen for unauthenticated visitors (Story 10.2).
 *
 * Merges the old SetupWizard (credential entry) and SpotifyConnect (the "Connect"
 * step) into one form: an anonymous visitor has no session yet, so their Spotify app
 * credentials must accompany the connect call. Posts {client_id, client_secret} to the
 * public /auth/connect, then redirects the browser to the returned Spotify authorize URL.
 */
export default function LoginScreen({ hasPreviousAuth, redirectUri }: LoginScreenProps) {
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const urlParams = new URLSearchParams(window.location.search)
  const authError = urlParams.get('auth_error') === '1'

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setIsConnecting(true)
    setError(null)
    try {
      const { auth_url } = await api.post<{ auth_url: string }>('/auth/connect', {
        client_id: clientId,
        client_secret: clientSecret,
      } satisfies ConnectRequest)
      window.location.href = auth_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed')
      setIsConnecting(false)
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-[var(--bg-base)] px-4">
      <div className="w-full max-w-md space-y-6 rounded-xl bg-[var(--bg-app)] p-8">
        <div className="flex items-center gap-2.5">
          <div className="grid h-8 w-8 place-items-center overflow-hidden rounded-lg bg-gradient-to-br from-[var(--accent-color)] to-cyan-400 font-extrabold text-black">
            <span className="text-[12px]">P</span>
          </div>
          <div className="text-lg font-bold tracking-tight">
            playlist<span className="text-[var(--accent-color)]">_</span>spotify
          </div>
        </div>

        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-white">
            {hasPreviousAuth ? 'Reconnect Spotify' : 'Log in with Spotify'}
          </h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {hasPreviousAuth
              ? 'Your Spotify session expired. Confirm your app credentials to reconnect.'
              : 'Enter your Spotify app credentials, then connect your account. Create an app at developer.spotify.com.'}
          </p>
        </div>

        <div className="space-y-1 rounded border border-[var(--border-soft)] bg-[var(--bg-elevated-2)] p-3 text-xs text-[var(--text-secondary)]">
          <p className="font-medium text-white">Add this Redirect URI to your Spotify app:</p>
          {redirectUri ? (
            <p className="select-all font-mono text-[var(--accent-color)]">{redirectUri}</p>
          ) : (
            <p className="font-mono text-[var(--text-muted)]">Loading…</p>
          )}
          <p>developer.spotify.com → Your App → Edit Settings → Redirect URIs (must match exactly).</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="client-id" className="text-sm font-medium text-white">
              Client ID
            </label>
            <input
              id="client-id"
              type="text"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              required
              autoComplete="off"
              className="w-full rounded border border-[var(--border-soft)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-white outline-none focus:border-[var(--border-strong)]"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="client-secret" className="text-sm font-medium text-white">
              Client Secret
            </label>
            <input
              id="client-secret"
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              required
              autoComplete="off"
              className="w-full rounded border border-[var(--border-soft)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-white outline-none focus:border-[var(--border-strong)]"
            />
          </div>

          {(authError || error) && (
            <p className="text-sm text-[var(--danger)]">
              {error ?? 'Spotify authorization was denied or failed. Please try again.'}
            </p>
          )}

          <Button
            type="submit"
            disabled={isConnecting || !clientId || !clientSecret}
            className="w-full rounded-full bg-[var(--accent-color)] font-bold text-black hover:bg-[var(--accent-hover)]"
          >
            {isConnecting ? 'Redirecting to Spotify…' : 'Connect Spotify'}
          </Button>
        </form>
      </div>
    </div>
  )
}
