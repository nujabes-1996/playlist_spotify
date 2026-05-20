import { usePlaylists } from '@/hooks/usePlaylists'
import PlaylistToggle from './PlaylistToggle'

function SkeletonRow() {
  return (
    <div className="flex items-center justify-between py-2 px-3">
      <div className="h-4 w-48 rounded bg-muted animate-pulse" />
      <div className="h-6 w-10 rounded-full bg-muted animate-pulse" />
    </div>
  )
}

export default function PlaylistList() {
  const { data: playlists, isPending, isError } = usePlaylists()

  if (isPending) {
    return (
      <div className="divide-y border rounded-lg overflow-hidden">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonRow key={i} />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-red-600 p-3">
        Failed to load playlists. Make sure you are connected to Spotify.
      </p>
    )
  }

  if (playlists.length === 0) {
    return (
      <p className="text-sm text-muted-foreground p-3">
        No playlists found. Make sure your Spotify account has playlists.
      </p>
    )
  }

  return (
    <div className="divide-y border rounded-lg overflow-hidden">
      {playlists.map((p) => (
        <PlaylistToggle key={p.spotify_id} {...p} />
      ))}
    </div>
  )
}
