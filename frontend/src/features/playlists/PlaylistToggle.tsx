import { useTogglePlaylist } from '@/hooks/usePlaylists'

interface Props {
  spotify_id: string
  name: string
  is_included: boolean
}

export default function PlaylistToggle({ spotify_id, name, is_included }: Props) {
  const toggle = useTogglePlaylist()
  const isPending = toggle.isPending && toggle.variables?.spotifyId === spotify_id

  return (
    <div className="flex items-center justify-between py-2 px-3 rounded hover:bg-muted/50">
      <span className="text-sm">{name}</span>
      <button
        onClick={() => toggle.mutate({ spotifyId: spotify_id, is_included: !is_included })}
        disabled={isPending}
        aria-pressed={is_included}
        aria-label={`${is_included ? 'Exclude' : 'Include'} ${name}`}
        className={`relative w-10 h-6 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
          is_included ? 'bg-primary' : 'bg-input'
        } disabled:opacity-50`}
      >
        <span
          className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-background shadow transition-transform ${
            is_included ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )
}
