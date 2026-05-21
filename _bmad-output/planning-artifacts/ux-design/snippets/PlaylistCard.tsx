// frontend/src/components/PlaylistCard.tsx
import { MoreHorizontal, Play, Check, ExternalLink, Eye, EyeOff, CircleCheck, X } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export interface Playlist {
  id: string;
  name: string;
  trackCount: number;
  coverUrl: string;
  included: boolean;
  hidden: boolean;
  isTarget?: boolean;       // the rolling Recent Adds playlist itself
}

interface Props {
  playlist: Playlist;
  dimmed?: boolean;
  onToggleInclude?: (id: string) => void;
  onToggleHide?: (id: string) => void;
  onOpenInSpotify?: (id: string) => void;
}

export function PlaylistCard({
  playlist: p, dimmed, onToggleInclude, onToggleHide, onOpenInSpotify,
}: Props) {
  return (
    <div
      className={cn(
        "group relative cursor-pointer rounded-lg bg-[var(--bg-elevated)] p-3.5 transition",
        "hover:bg-[var(--bg-hover)]",
        dimmed && "opacity-55 hover:opacity-100",
        p.included && "outline outline-2 -outline-offset-1 outline-[var(--accent-color)]",
      )}
    >
      <div className="relative mb-3.5 aspect-square overflow-hidden rounded-md shadow-[0_8px_24px_rgba(0,0,0,0.5)]">
        <img
          src={p.coverUrl}
          alt={p.name}
          className="h-full w-full object-cover"
          loading="lazy"
        />

        {p.included && (
          <div
            title="Included in sync"
            className="absolute left-2 top-2 z-[2] grid h-[22px] w-[22px] place-items-center
                       rounded-full bg-[var(--accent-color)] text-black shadow-[0_2px_6px_rgba(0,0,0,0.4)]"
          >
            <Check size={12} strokeWidth={3} />
          </div>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="More options"
            className="absolute right-2 top-2 z-[2] grid h-8 w-8 place-items-center rounded-full
                       bg-black/70 text-white opacity-0 transition group-hover:opacity-100 hover:bg-black/90"
          >
            <MoreHorizontal size={14} />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-[200px]">
            {!p.isTarget && (
              <DropdownMenuItem onClick={() => onToggleInclude?.(p.id)}>
                {p.included
                  ? <><X size={15} className="mr-2" />Remove from sync</>
                  : <><CircleCheck size={15} className="mr-2" />Include in sync</>}
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={() => onToggleHide?.(p.id)}>
              {p.hidden
                ? <><Eye size={15} className="mr-2" />Unhide</>
                : <><EyeOff size={15} className="mr-2" />Hide playlist</>}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onOpenInSpotify?.(p.id)}>
              <ExternalLink size={15} className="mr-2" />Open in Spotify
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <button
          aria-label="Preview"
          className="absolute bottom-2 right-2 grid h-11 w-11 translate-y-2 place-items-center
                     rounded-full bg-[var(--accent-color)] text-black opacity-0 shadow-lg
                     transition group-hover:translate-y-0 group-hover:opacity-100
                     hover:scale-[1.06] hover:bg-[var(--accent-hover)]"
        >
          <Play size={16} fill="currentColor" />
        </button>
      </div>

      <h3
        title={p.name}
        className="line-clamp-2 min-h-[2.6em] text-[14.5px] font-bold leading-tight text-white"
      >
        {p.name}
      </h3>

      <div className="mt-1 flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
        <span>{p.trackCount.toLocaleString()} tracks</span>
        {p.isTarget && (
          <>
            <span className="text-[var(--text-faint)]">•</span>
            <span className="font-bold text-[var(--accent-color)]">Sync target</span>
          </>
        )}
      </div>
    </div>
  );
}

// Grid wrapper used by Dashboard + HiddenPlaylistsAccordion
export function PlaylistGrid({
  playlists, dimmed, onToggleInclude, onToggleHide, onOpenInSpotify,
}: {
  playlists: Playlist[];
  dimmed?: boolean;
  onToggleInclude?: (id: string) => void;
  onToggleHide?: (id: string) => void;
  onOpenInSpotify?: (id: string) => void;
}) {
  return (
    <div
      className="grid gap-[18px]"
      style={{ gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))" }}
    >
      {playlists.map((p) => (
        <PlaylistCard
          key={p.id}
          playlist={p}
          dimmed={dimmed}
          onToggleInclude={onToggleInclude}
          onToggleHide={onToggleHide}
          onOpenInSpotify={onOpenInSpotify}
        />
      ))}
    </div>
  );
}
