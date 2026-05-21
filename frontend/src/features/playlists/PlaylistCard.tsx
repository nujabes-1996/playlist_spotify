import { memo, useState } from 'react'
import {
  Check,
  CircleCheck,
  ExternalLink,
  Eye,
  EyeOff,
  MoreHorizontal,
  Play,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import { useHidePlaylist, useTogglePlaylist } from '@/hooks/usePlaylists'
import type { Playlist } from '@/types'

interface Props {
  playlist: Playlist
  dimmed?: boolean
  onOpenInSpotify?: (spotifyId: string) => void
}

function placeholderGradient(spotifyId: string, name: string): {
  background: string
  initials: string
} {
  const hue =
    Array.from(spotifyId || 'x').reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % 360
  const background = `linear-gradient(135deg, hsl(${hue} 60% 25%) 0%, hsl(${(hue + 40) % 360} 60% 12%) 100%)`
  const words = (name || '').trim().split(/\s+/).filter(Boolean)
  const initials = words.length === 0
    ? '?'
    : words.slice(0, 2).map((w) => w[0]!.toUpperCase()).join('')
  return { background, initials }
}

function PlaylistCard({
  playlist,
  dimmed,
  onOpenInSpotify,
}: Props) {
  const toggle = useTogglePlaylist()
  const hide = useHidePlaylist()
  const [imgFailed, setImgFailed] = useState(false)

  const showPlaceholder = !playlist.image_url || imgFailed
  const { background, initials } = placeholderGradient(playlist.spotify_id, playlist.name)

  const handleToggleInclude = () => {
    toggle.mutate({
      spotifyId: playlist.spotify_id,
      is_included: !playlist.is_included,
    })
  }

  return (
    <div
      className={cn(
        'group relative cursor-pointer rounded-lg bg-[var(--bg-elevated)] p-3.5 transition',
        'hover:bg-[var(--bg-hover)]',
        dimmed && 'opacity-55 hover:opacity-100',
        playlist.is_included &&
          'outline outline-2 -outline-offset-1 outline-[var(--accent-color)]',
      )}
    >
      <div className="relative mb-3.5 aspect-square overflow-hidden rounded-md shadow-[0_8px_24px_rgba(0,0,0,0.5)]">
        {showPlaceholder ? (
          <div
            className="grid h-full w-full place-items-center"
            style={{ background }}
            aria-label={playlist.name}
          >
            <span className="text-3xl font-extrabold text-white/90">{initials}</span>
          </div>
        ) : (
          <img
            src={playlist.image_url!}
            alt={playlist.name}
            loading="lazy"
            decoding="async"
            width={300}
            height={300}
            onError={() => setImgFailed(true)}
            className="h-full w-full object-cover"
          />
        )}

        {playlist.is_included && (
          <div
            title="Included in sync"
            className="absolute left-2 top-2 z-[2] grid h-[22px] w-[22px] place-items-center rounded-full bg-[var(--accent-color)] text-black shadow-[0_2px_6px_rgba(0,0,0,0.4)]"
          >
            <Check size={12} strokeWidth={3} />
          </div>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`More options for ${playlist.name}`}
            className="absolute right-2 top-2 z-[2] grid h-8 w-8 place-items-center rounded-full bg-black/70 text-white opacity-0 transition group-hover:opacity-100 hover:bg-black/90 focus:opacity-100"
          >
            <MoreHorizontal size={14} />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-56 rounded-md border-0 bg-[#282828] p-1 shadow-[0_16px_24px_rgba(0,0,0,0.5),0_6px_8px_rgba(0,0,0,0.4)]"
          >
            <DropdownMenuGroup>
              <DropdownMenuItem
                className="cursor-pointer gap-3 rounded-sm px-3 py-2.5 text-[13px] text-white/90 focus:bg-white/10 focus:text-white [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-white/70"
                onSelect={handleToggleInclude}
              >
                {playlist.is_included ? (
                  <>
                    <X />
                    Remove from sync
                  </>
                ) : (
                  <>
                    <CircleCheck />
                    Include in sync
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                className="cursor-pointer gap-3 rounded-sm px-3 py-2.5 text-[13px] text-white/90 focus:bg-white/10 focus:text-white [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-white/70"
                onSelect={() => {
                  hide.mutate(
                    { spotifyId: playlist.spotify_id, is_hidden: !playlist.is_hidden },
                    {
                      onError: () => {
                        const verb = playlist.is_hidden ? 'unhide' : 'hide'
                        toast.error(`Could not ${verb} "${playlist.name}". Please try again.`)
                      },
                    },
                  )
                }}
              >
                {playlist.is_hidden ? (
                  <>
                    <Eye />
                    Unhide
                  </>
                ) : (
                  <>
                    <EyeOff />
                    Hide playlist
                  </>
                )}
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator className="-mx-1 my-1 h-px bg-white/10" />
            <DropdownMenuItem
              className="cursor-pointer gap-3 rounded-sm px-3 py-2.5 text-[13px] text-white/90 focus:bg-white/10 focus:text-white [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-white/70"
              onSelect={() => onOpenInSpotify?.(playlist.spotify_id)}
            >
              <ExternalLink />
              Open in Spotify
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <button
          type="button"
          aria-label="Preview"
          tabIndex={-1}
          className="absolute bottom-2 right-2 grid h-11 w-11 translate-y-2 place-items-center rounded-full bg-[var(--accent-color)] text-black opacity-0 shadow-lg transition group-hover:translate-y-0 group-hover:opacity-100 hover:scale-[1.06] hover:bg-[var(--accent-hover)]"
        >
          <Play size={16} fill="currentColor" />
        </button>
      </div>

      <h3
        title={playlist.name}
        className="line-clamp-2 min-h-[2.6em] text-[14.5px] font-bold leading-tight text-white"
      >
        {playlist.name}
      </h3>

      <div className="mt-1 flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
        <span>{playlist.track_count.toLocaleString()} tracks</span>
      </div>
    </div>
  )
}

export default memo(PlaylistCard)
