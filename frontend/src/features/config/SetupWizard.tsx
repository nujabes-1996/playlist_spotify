import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useUpdateConfig } from '@/hooks/useConfig'

export default function SetupWizard() {
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const { mutate, isPending, error } = useUpdateConfig()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutate({ client_id: clientId, client_secret: clientSecret })
  }

  return (
    <div className="max-w-md mx-auto mt-16 space-y-6">
      <h1 className="text-2xl font-bold">Spotify Setup</h1>
      <p className="text-sm text-muted-foreground">
        Enter your Spotify app credentials to get started. Create an app at{' '}
        <span className="font-mono">developer.spotify.com</span>.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="client-id" className="text-sm font-medium">Client ID</label>
          <input
            id="client-id"
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            required
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="client-secret" className="text-sm font-medium">Client Secret</label>
          <input
            id="client-secret"
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            required
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {error && (
          <p className="text-sm text-red-600">{error.message}</p>
        )}
        <Button type="submit" disabled={isPending || !clientId || !clientSecret}>
          {isPending ? 'Saving…' : 'Save Credentials'}
        </Button>
      </form>
    </div>
  )
}
