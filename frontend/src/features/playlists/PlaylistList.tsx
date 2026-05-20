import { usePlaylists } from '@/hooks/usePlaylists'
import PlaylistToggle from './PlaylistToggle'

function SkeletonCard() {
  return (
    <div className="flex flex-col gap-3 p-4 rounded-xl border border-[var(--border)] bg-[var(--card)] animate-pulse">
      <div className="h-4 w-3/4 rounded bg-[var(--muted)]" />
      <div className="h-4 w-1/2 rounded bg-[var(--muted)]" />
      <div className="h-3 w-16 rounded bg-[var(--muted)]" />
    </div>
  )
}

export default function PlaylistList() {
  const { data: playlists, isPending, isError } = usePlaylists()

  if (isPending) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-red-500 p-3">
        Failed to load playlists. Make sure you are connected to Spotify.
      </p>
    )
  }

  if (playlists.length === 0) {
    return (
      <p className="text-sm text-[var(--muted-foreground)] p-3">
        No playlists found. Make sure your Spotify account has playlists.
      </p>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {playlists.map((p) => (
        <PlaylistToggle key={p.spotify_id} {...p} />
      ))}
    </div>
  )
}
