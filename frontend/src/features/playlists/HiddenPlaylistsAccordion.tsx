import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { usePlaylists } from '@/hooks/usePlaylists'
import PlaylistCard from './PlaylistCard'

const GRID_TEMPLATE_COLUMNS = 'repeat(auto-fill, minmax(190px, 1fr))'

function openInSpotify(spotifyId: string) {
  const url =
    spotifyId === 'liked_songs'
      ? 'https://open.spotify.com/collection/tracks'
      : `https://open.spotify.com/playlist/${spotifyId}`
  window.open(url, '_blank', 'noopener,noreferrer')
}

export default function HiddenPlaylistsAccordion() {
  const { data: playlists, isPending, isError } = usePlaylists()

  if (isPending || isError) return null

  const hidden = playlists.filter((p) => p.is_hidden)
  if (hidden.length === 0) return null

  return (
    <Accordion
      type="single"
      collapsible
      className="mt-2 border-t border-[var(--border-soft)] pt-6"
    >
      <AccordionItem value="hidden" className="border-0">
        <AccordionTrigger className="py-1 text-[22px] font-extrabold tracking-tight text-white hover:no-underline">
          Hidden playlists ({hidden.length})
        </AccordionTrigger>
        <AccordionContent>
          <p className="my-[18px] mt-[10px] max-w-[720px] text-[13px] text-[var(--text-muted)]">
            Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back.
          </p>
          <div
            className="grid gap-[18px]"
            style={{ gridTemplateColumns: GRID_TEMPLATE_COLUMNS }}
          >
            {hidden.map((p) => (
              <PlaylistCard
                key={p.spotify_id}
                playlist={p}
                dimmed
                onOpenInSpotify={openInSpotify}
              />
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
