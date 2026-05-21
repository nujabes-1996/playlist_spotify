// Dummy data for the playlist_spotify prototype.
// Original cover art (gradient SVG); original artist/track strings (not real Spotify metadata).

(function () {
  const palettes = [
    ['#ff5b2e', '#ffd166', '#1a1a1a'],
    ['#7b5cff', '#21d4fd', '#0d0d0d'],
    ['#1DB954', '#0aa14d', '#0c2a18'],
    ['#ff3d68', '#7a1c40', '#fff0a6'],
    ['#ffe66d', '#1a1a1a', '#ff8c42'],
    ['#5b8cff', '#0e2f63', '#a3d9ff'],
    ['#ec4899', '#6e56cf', '#0d0d0d'],
    ['#ff8c42', '#1a1a1a', '#ffe66d'],
    ['#2dd4bf', '#0f172a', '#a7f3d0'],
    ['#f43f5e', '#0f0f10', '#fda4af'],
    ['#1a1a1a', '#525252', '#e5e5e5'],
    ['#22d3ee', '#312e81', '#fef3c7'],
    ['#facc15', '#1e293b', '#fda4af'],
    ['#1DB954', '#fde047', '#0d0d0d'],
    ['#a3e635', '#365314', '#fff'],
  ];

  // Build an inline data:image/svg+xml URL with a tilted gradient + diagonal grain.
  function abstractCover(palette, label, variant = 0) {
    const [a, b, c] = palette;
    const angle = (variant * 37) % 360;
    let shapes = '';
    if (variant % 3 === 0) {
      shapes = `<circle cx="60" cy="240" r="120" fill="${c}" fill-opacity="0.6"/>
                <circle cx="280" cy="80" r="80" fill="${b}" fill-opacity="0.45"/>`;
    } else if (variant % 3 === 1) {
      shapes = `<rect x="-20" y="180" width="380" height="120" fill="${c}" transform="rotate(-12 160 240)" fill-opacity="0.55"/>
                <rect x="40" y="40" width="120" height="120" fill="${b}" fill-opacity="0.35"/>`;
    } else {
      shapes = `<path d="M 0 220 Q 160 120 320 240 L 320 320 L 0 320 Z" fill="${c}" fill-opacity="0.55"/>
                <path d="M 0 60 Q 120 180 320 80" stroke="${b}" stroke-width="14" fill="none" stroke-opacity="0.55"/>`;
    }
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320">
      <defs>
        <linearGradient id="g" gradientTransform="rotate(${angle})">
          <stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/>
        </linearGradient>
        <pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.6" fill="rgba(255,255,255,0.06)"/>
        </pattern>
      </defs>
      <rect width="320" height="320" fill="url(#g)"/>
      ${shapes}
      <rect width="320" height="320" fill="url(#dots)"/>
    </svg>`;
    return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
  }

  const playlistDefs = [
    { name: 'Recent Adds',        tracks: 50,  included: true,  hidden: false, accent: 2, kind: 'target' },
    { name: 'Late Night Drives',  tracks: 142, included: true,  hidden: false, accent: 0 },
    { name: 'Discover French Rap',tracks: 86,  included: true,  hidden: false, accent: 1 },
    { name: 'Workout Heat',       tracks: 64,  included: true,  hidden: false, accent: 3 },
    { name: 'Sunday Morning',     tracks: 38,  included: false, hidden: false, accent: 4 },
    { name: 'Indie Sleaze 2026',  tracks: 91,  included: true,  hidden: false, accent: 5 },
    { name: 'For deep focus',     tracks: 220, included: false, hidden: false, accent: 6 },
    { name: 'Old Eminem',         tracks: 47,  included: true,  hidden: false, accent: 7 },
    { name: 'Saved from Discover',tracks: 412, included: true,  hidden: false, accent: 8 },
    { name: 'Liked Songs (mirror)', tracks: 1287, included: false, hidden: false, accent: 9 },
    { name: 'Sophieanne radar',   tracks: 26,  included: true,  hidden: false, accent: 11 },
    { name: 'Y2K nostalgia',      tracks: 73,  included: false, hidden: false, accent: 12 },
    // hidden
    { name: 'Christmas 2023',     tracks: 41,  included: false, hidden: true, accent: 13 },
    { name: 'Bachelor party DJ',  tracks: 158, included: false, hidden: true, accent: 14 },
    { name: 'Audio book test',    tracks: 4,   included: false, hidden: true, accent: 10 },
  ];

  window.playlists = playlistDefs.map((p, i) => ({
    id: 'pl_' + i,
    ...p,
    cover: abstractCover(palettes[p.accent], p.name, i),
  }));

  // Track list (Recently Added). Strings are invented for the prototype.
  const trackArt = (variant, palette) => abstractCover(palettes[palette], '', variant);

  window.tracks = [
    { id: 't1',  title: 'Lights Off',       artist: 'Mauve Echo',         album: 'Lights Off',          addedAgo: '21 hours ago', addedAbs: 'May 19, 2026', duration: '1:43', explicit: true,  hasVideo: false, art: trackArt(1, 11) },
    { id: 't2',  title: 'Neon Lane',        artist: 'KOI 99',             album: 'Neon Lane',           addedAgo: '21 hours ago', addedAbs: 'May 19, 2026', duration: '3:42', explicit: true,  hasVideo: false, art: trackArt(2, 5) },
    { id: 't3',  title: 'Bouwéy',           artist: '1T1, Theomaa',       album: 'Bouwéy',              addedAgo: '2 days ago',   addedAbs: 'May 18, 2026', duration: '2:37', explicit: false, hasVideo: false, art: trackArt(7, 0) },
    { id: 't4',  title: 'Without a Map',    artist: 'Vesper, Klein',      album: 'The Long Year',       addedAgo: '4 days ago',   addedAbs: 'May 16, 2026', duration: '4:50', explicit: true,  hasVideo: true,  art: trackArt(3, 3), isNew: true, isActive: true },
    { id: 't5',  title: 'Escapism. (Edit)', artist: 'Aurelle, Sage 70',   album: 'My 21st Year',        addedAgo: '1 week ago',   addedAbs: 'May 12, 2026', duration: '4:32', explicit: true,  hasVideo: true,  art: trackArt(4, 7) },
    { id: 't6',  title: 'En ce moment',     artist: 'Ewen btx, Sophieanne', album: 'En ce moment',      addedAgo: '2 weeks ago',  addedAbs: 'May 04, 2026', duration: '3:29', explicit: false, hasVideo: false, art: trackArt(5, 4) },
    { id: 't7',  title: 'Freestyle 8',      artist: 'SDM',                album: 'Freestyle 8',         addedAgo: '2 weeks ago',  addedAbs: 'May 04, 2026', duration: '1:43', explicit: true,  hasVideo: false, art: trackArt(6, 10) },
    { id: 't8',  title: 'ALLIGATOR',        artist: 'Will LCK',           album: '7/7',                 addedAgo: '3 weeks ago', addedAbs: 'Apr 28, 2026', duration: '1:59', explicit: true,  hasVideo: false, art: trackArt(7, 13) },
    { id: 't9',  title: 'Nouvelle Défaite', artist: 'Sophieanne',         album: 'Nouvelle Défaite',    addedAgo: 'Apr 22, 2026', addedAbs: 'Apr 22, 2026', duration: '3:40', explicit: false, hasVideo: false, art: trackArt(8, 1) },
    { id: 't10', title: 'No One Like You (2015)', artist: 'Halberd',      album: 'Blackout',            addedAgo: 'Apr 14, 2026', addedAbs: 'Apr 14, 2026', duration: '3:59', explicit: false, hasVideo: false, art: trackArt(9, 12) },
    { id: 't11', title: 'Cold Hold',        artist: 'Yara M., Drift',     album: 'Cold Hold EP',        addedAgo: 'Apr 09, 2026', addedAbs: 'Apr 09, 2026', duration: '2:54', explicit: true,  hasVideo: false, art: trackArt(10, 2) },
    { id: 't12', title: 'Garde-fou',        artist: 'Lazone, Petra K.',   album: 'Garde-fou',           addedAgo: 'Apr 03, 2026', addedAbs: 'Apr 03, 2026', duration: '3:18', explicit: false, hasVideo: false, art: trackArt(11, 6) },
    { id: 't13', title: 'Stockholm Bus',    artist: 'Cohen Daly',         album: 'Northbound',          addedAgo: 'Mar 28, 2026', addedAbs: 'Mar 28, 2026', duration: '4:11', explicit: false, hasVideo: false, art: trackArt(12, 8) },
    { id: 't14', title: 'Bleach (Demo)',    artist: 'Maline',             album: 'Bleach',              addedAgo: 'Mar 18, 2026', addedAbs: 'Mar 18, 2026', duration: '2:21', explicit: true,  hasVideo: false, art: trackArt(13, 9) },
    { id: 't15', title: 'Telephone',        artist: 'Kid Saplin',         album: 'Telephone',           addedAgo: 'Mar 11, 2026', addedAbs: 'Mar 11, 2026', duration: '3:02', explicit: true,  hasVideo: true,  art: trackArt(14, 11) },
    { id: 't16', title: 'Pas le temps',     artist: 'Cleyo, Maes 92',     album: 'Pas le temps',        addedAgo: 'Mar 02, 2026', addedAbs: 'Mar 02, 2026', duration: '2:46', explicit: true,  hasVideo: false, art: trackArt(15, 3) },
    { id: 't17', title: 'Sublunar',         artist: 'Hexen Tape',         album: 'Sublunar',            addedAgo: 'Feb 24, 2026', addedAbs: 'Feb 24, 2026', duration: '5:08', explicit: false, hasVideo: false, art: trackArt(16, 4) },
    { id: 't18', title: 'Mannequin',        artist: 'Joëlle Eaux',        album: 'Mannequin / Vide',    addedAgo: 'Feb 14, 2026', addedAbs: 'Feb 14, 2026', duration: '3:55', explicit: false, hasVideo: false, art: trackArt(17, 5) },
    { id: 't19', title: 'Anti-pop',         artist: 'Frère Jardin',       album: 'Single',              addedAgo: 'Feb 08, 2026', addedAbs: 'Feb 08, 2026', duration: '2:12', explicit: true,  hasVideo: false, art: trackArt(18, 0) },
    { id: 't20', title: 'Hibou de minuit',  artist: 'Ondine, Bruel',      album: 'Hibou de minuit',     addedAgo: 'Feb 01, 2026', addedAbs: 'Feb 01, 2026', duration: '4:00', explicit: false, hasVideo: false, art: trackArt(19, 7) },
  ];

  // Logs (newest first)
  window.logs = [
    { id: 'l1', ts: '2026-05-20 14:02:11', status: 'ok',  added: 3, removed: 1, msg: 'Sync complete · 50 tracks in target playlist', detail: '→ added: Mauve Echo — Lights Off\n→ added: KOI 99 — Neon Lane\n→ added: 1T1, Theomaa — Bouwéy\n→ removed: Halberd — No One Like You (rotated out, > 50)' },
    { id: 'l2', ts: '2026-05-20 13:00:01', status: 'ok',  added: 0, removed: 0, msg: 'No new additions across 8 source playlists', detail: 'Scanned 8 playlists · 1,234 tracks · no diff to apply.' },
    { id: 'l3', ts: '2026-05-20 12:00:01', status: 'warn',added: 2, removed: 0, msg: 'Sync OK with warnings · 1 track skipped',  detail: 'WARN: track "Y. Brisson — ∅" has no preview URL; metadata-only.\nadded: Vesper, Klein — Without a Map\nadded: Aurelle, Sage 70 — Escapism. (Edit)' },
    { id: 'l4', ts: '2026-05-20 11:00:14', status: 'err', added: 0, removed: 0, msg: 'Spotify API · 429 rate limited (retry-after 30s)', detail: 'ERR: HTTP 429 from /v1/me/playlists\nRetry queued at 2026-05-20 11:01:44\n   trace_id=8a31f0…b62d' },
    { id: 'l5', ts: '2026-05-20 10:00:02', status: 'ok',  added: 1, removed: 1, msg: 'Sync complete · 50 tracks in target playlist', detail: 'added: Ewen btx, Sophieanne — En ce moment\nremoved: Hibou de minuit (oldest, > 50)' },
    { id: 'l6', ts: '2026-05-20 09:00:01', status: 'ok',  added: 0, removed: 0, msg: 'No new additions', detail: '' },
    { id: 'l7', ts: '2026-05-20 08:00:02', status: 'ok',  added: 4, removed: 4, msg: 'Sync complete · 50 tracks in target playlist', detail: 'added 4, removed 4 (rotation).' },
    { id: 'l8', ts: '2026-05-20 07:00:01', status: 'err', added: 0, removed: 0, msg: 'Auth · refresh token expired',                detail: 'ERR: refresh_token rejected (401)\nUser action required: Settings → Reconnect Spotify' },
  ];
})();
