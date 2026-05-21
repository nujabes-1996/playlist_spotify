// frontend/src/components/TrackRow.tsx
import { MoreHorizontal, Play, ExternalLink, EyeOff } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export interface Track {
  id: string;
  title: string;
  artist: string;
  album: string;
  artUrl: string;
  durationLabel: string;    // "3:42"
  addedAgo: string;         // "3 days ago"
  addedAbs: string;         // "May 18, 2026"
  explicit?: boolean;
  hasVideo?: boolean;
  isNew?: boolean;
  isActive?: boolean;       // currently-playing visual (cosmetic)
}

const cols =
  "grid grid-cols-[36px_minmax(220px,4fr)_minmax(160px,3fr)_minmax(140px,2fr)_60px_40px] gap-3.5 items-center";

export function TrackListHeader() {
  return (
    <div
      className={cn(
        cols,
        "sticky top-0 z-[5] border-b border-white/5 bg-[var(--bg-app)]/90 px-4 py-2",
        "text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] backdrop-blur",
      )}
    >
      <div className="text-center">#</div>
      <div>Title</div>
      <div>Album</div>
      <div>Date added</div>
      <div className="text-right">⏱</div>
      <div />
    </div>
  );
}

interface TrackRowProps {
  track: Track;
  index: number;
  onHide?: (id: string) => void;
  onOpenInSpotify?: (id: string) => void;
}

export function TrackRow({ track, index, onHide, onOpenInSpotify }: TrackRowProps) {
  return (
    <div
      className={cn(
        "group relative",
        cols,
        "rounded-sm px-4 py-2 text-sm text-[var(--text-secondary)]",
        track.isActive
          ? "bg-[var(--bg-row-active)]"
          : "hover:bg-[var(--bg-row-hover)]",
      )}
    >
      {/* index ↔ play */}
      <div className="relative grid place-items-center text-[var(--text-muted)]">
        <span className="group-hover:hidden">{index + 1}</span>
        <Play
          size={12}
          fill="currentColor"
          className="hidden text-white group-hover:block"
        />
      </div>

      {/* title + artist */}
      <div className="flex min-w-0 items-center gap-3">
        <img
          src={track.artUrl}
          alt=""
          className="h-10 w-10 flex-shrink-0 rounded-sm object-cover"
        />
        <div className="min-w-0">
          <div
            className={cn(
              "truncate text-[14.5px] font-medium",
              track.isActive ? "text-[var(--accent-color)]" : "text-white",
            )}
          >
            {track.title}
            {track.isNew && (
              <span className="ml-2 rounded bg-[var(--accent-soft)] px-1.5 py-0.5
                               text-[10px] font-bold uppercase tracking-wider text-[var(--accent-color)]">
                New
              </span>
            )}
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-[12.5px] text-[var(--text-muted)]">
            {track.explicit && (
              <span className="rounded-sm bg-[#535353] px-1 py-px text-[8px] font-bold tracking-wider text-[#d4d4d4]">
                E
              </span>
            )}
            {track.hasVideo && <ExternalLink size={12} className="opacity-70" />}
            <a className="cursor-pointer hover:text-white hover:underline">{track.artist}</a>
          </div>
        </div>
      </div>

      <div className="truncate text-[13.5px]">{track.album}</div>

      <Tooltip>
        <TooltipTrigger asChild>
          <div className="truncate text-[13.5px]">{track.addedAgo}</div>
        </TooltipTrigger>
        <TooltipContent>{track.addedAbs}</TooltipContent>
      </Tooltip>

      <div className="text-right text-[13.5px] tabular-nums">{track.durationLabel}</div>

      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="More"
          className="grid h-8 w-8 place-items-center rounded-full text-[var(--text-secondary)]
                     opacity-0 transition group-hover:opacity-100 hover:bg-[var(--bg-hover)] hover:text-white"
        >
          <MoreHorizontal size={14} />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => onHide?.(track.id)}>
            <EyeOff size={15} className="mr-2" />Hide from Recent Adds
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onOpenInSpotify?.(track.id)}>
            <ExternalLink size={15} className="mr-2" />Open in Spotify
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
