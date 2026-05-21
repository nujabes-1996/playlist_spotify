import { Sparkles } from 'lucide-react'
import { usePlaylists } from '@/hooks/usePlaylists'
import PlaylistCard from './PlaylistCard'

const GRID_TEMPLATE_COLUMNS = 'repeat(auto-fill, minmax(190px, 1fr))'

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-lg bg-[var(--bg-elevated)] p-3.5">
      <div className="mb-3.5 aspect-square rounded-md bg-white/5" />
      <div className="h-4 w-3/4 rounded bg-white/5" />
      <div className="mt-2 h-3 w-1/3 rounded bg-white/5" />
    </div>
  )
}

function openInSpotify(spotifyId: string) {
  const url =
    spotifyId === 'liked_songs'
      ? 'https://open.spotify.com/collection/tracks'
      : `https://open.spotify.com/playlist/${spotifyId}`
  window.open(url, '_blank', 'noopener,noreferrer')
}

export default function PlaylistGrid() {
  const { data: playlists, isPending, isError } = usePlaylists()

  if (isPending) {
    return (
      <div className="grid gap-[18px]" style={{ gridTemplateColumns: GRID_TEMPLATE_COLUMNS }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
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

  const visible = playlists.filter((p) => !p.is_hidden)

  if (visible.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-[60px] text-center">
        <Sparkles size={28} className="text-[var(--text-secondary)]" />
        <h3 className="mt-3 text-[18px] font-bold text-white">No playlists yet</h3>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Connect your Spotify account in Settings to start picking source playlists.
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-[18px]" style={{ gridTemplateColumns: GRID_TEMPLATE_COLUMNS }}>
      {visible.map((p) => (
        <PlaylistCard key={p.spotify_id} playlist={p} onOpenInSpotify={openInSpotify} />
      ))}
    </div>
  )
}
