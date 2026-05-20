import React, { useState, useEffect } from 'react'
import { useConfig, usePatchConfig } from '@/hooks/useConfig'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

function isValidCron(expr: string): boolean {
  return /^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$/.test(expr.trim())
}

export default function ConfigForm() {
  const config = useConfig()
  const patchConfig = usePatchConfig()

  const [playlistSize, setPlaylistSize] = useState<string>('')
  const [cronExpr, setCronExpr] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config.data) {
      setPlaylistSize(String(config.data.playlist_size))
      setCronExpr(config.data.cron_expr ?? '')
    }
  }, [config.data])

  function handleSave() {
    setError(null)
    setSaved(false)

    const size = parseInt(playlistSize, 10)
    if (isNaN(size) || size < 1 || size > 500) {
      setError('Playlist size must be a number between 1 and 500')
      return
    }

    const cron = cronExpr.trim()
    if (cron && !isValidCron(cron)) {
      setError('Invalid cron expression (example: "0 * * * *")')
      return
    }

    patchConfig.mutate(
      { playlist_size: size, cron_expr: cron || null },
      {
        onSuccess: () => setSaved(true),
        onError: (e) => setError(e instanceof Error ? e.message : 'Save failed'),
      },
    )
  }

  if (config.isPending) return <div className="p-6 text-sm text-muted-foreground">Loading…</div>
  if (config.isError) return <div className="p-6 text-sm text-red-600">Failed to load configuration.</div>

  return (
    <div className="p-6 max-w-md space-y-6">
      <h2 className="text-xl font-semibold">Sync Configuration</h2>

      <div className="space-y-2">
        <Label htmlFor="playlist-size">Playlist size (number of tracks)</Label>
        <Input
          id="playlist-size"
          type="number"
          min={1}
          max={500}
          value={playlistSize}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setPlaylistSize(e.target.value); setSaved(false) }}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="cron-expr">Sync schedule (cron expression)</Label>
        <Input
          id="cron-expr"
          type="text"
          placeholder="0 * * * *"
          value={cronExpr}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setCronExpr(e.target.value); setSaved(false) }}
        />
        <p className="text-xs text-muted-foreground">
          Leave empty to disable automatic sync. Example: <code>0 */6 * * *</code> = every 6 hours.
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {saved && <p className="text-sm text-green-600">Configuration saved.</p>}

      <Button onClick={handleSave} disabled={patchConfig.isPending}>
        {patchConfig.isPending ? 'Saving…' : 'Save'}
      </Button>
    </div>
  )
}
