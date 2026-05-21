// frontend/src/components/HiddenPlaylistsAccordion.tsx
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";
import { PlaylistCard, Playlist } from "./PlaylistCard";

interface Props {
  hidden: Playlist[];
  onToggleHide: (id: string) => void;
  onOpenInSpotify?: (id: string) => void;
}

export function HiddenPlaylistsAccordion({ hidden, onToggleHide, onOpenInSpotify }: Props) {
  if (hidden.length === 0) return null;

  return (
    <Accordion type="single" collapsible className="mt-2 border-t border-white/5 pt-6">
      <AccordionItem value="hidden" className="border-0">
        <AccordionTrigger
          className="py-1 text-[22px] font-extrabold tracking-tight text-white hover:no-underline
                     [&_svg]:text-[var(--text-secondary)] [&_svg]:h-4 [&_svg]:w-4"
        >
          Hidden playlists ({hidden.length})
        </AccordionTrigger>
        <AccordionContent>
          <p className="my-3 max-w-[720px] text-[13px] text-[var(--text-muted)]">
            Hidden playlists are excluded from sync and removed from the main grid. Unhide to bring them back.
          </p>
          <div
            className="grid gap-[18px]"
            style={{ gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))" }}
          >
            {hidden.map((p) => (
              <PlaylistCard
                key={p.id}
                playlist={p}
                dimmed
                onToggleHide={onToggleHide}
                onOpenInSpotify={onOpenInSpotify}
              />
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
