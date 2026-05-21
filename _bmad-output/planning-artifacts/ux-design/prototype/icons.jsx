// Minimal inline SVG icon set (original — generic line icons, not branded marks).
// Each icon is a React function component accepting size + extra props.

const Icon = ({ d, size = 18, fill = 'none', stroke = 'currentColor', sw = 1.8, ...rest }) =>
  React.createElement('svg', { width: size, height: size, viewBox: '0 0 24 24', fill, stroke, strokeWidth: sw, strokeLinecap: 'round', strokeLinejoin: 'round', ...rest }, d);

const I = {};

I.Dashboard = (p) => <Icon {...p} d={<>
  <path d="M3 12 L12 4 L21 12"/>
  <path d="M5 10 V20 H10 V14 H14 V20 H19 V10"/>
</>}/>;

I.Recent = (p) => <Icon {...p} d={<>
  <circle cx="12" cy="12" r="9"/>
  <path d="M12 7 V12 L15.5 14"/>
</>}/>;

I.Settings = (p) => <Icon {...p} d={<>
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>
</>}/>;

I.Logs = (p) => <Icon {...p} d={<>
  <rect x="4" y="3" width="16" height="18" rx="2"/>
  <path d="M8 8 H16 M8 12 H16 M8 16 H13"/>
</>}/>;

I.Play = (p) => <Icon {...p} fill="currentColor" stroke="none" d={<polygon points="6,4 6,20 20,12" />}/>;
I.Pause = (p) => <Icon {...p} fill="currentColor" stroke="none" d={<><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></>}/>;
I.More = (p) => <Icon {...p} fill="currentColor" stroke="none" d={<><circle cx="5" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/><circle cx="19" cy="12" r="1.7"/></>}/>;
I.Check = (p) => <Icon {...p} sw={2.4} d={<polyline points="4,12 10,18 20,6"/>}/>;
I.X = (p) => <Icon {...p} d={<><line x1="5" y1="5" x2="19" y2="19"/><line x1="19" y1="5" x2="5" y2="19"/></>}/>;
I.ChevDown = (p) => <Icon {...p} d={<polyline points="6,9 12,15 18,9"/>}/>;
I.ChevRight = (p) => <Icon {...p} d={<polyline points="9,6 15,12 9,18"/>}/>;
I.ChevLeft = (p) => <Icon {...p} d={<polyline points="15,6 9,12 15,18"/>}/>;
I.Search = (p) => <Icon {...p} d={<><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></>}/>;
I.RotateCw = (p) => <Icon {...p} d={<><polyline points="21,4 21,10 15,10"/><path d="M3.5 14a8.5 8.5 0 0 0 15.4 3.5 8.5 8.5 0 0 0 .5-7L21 8"/></>}/>;
I.Sparkles = (p) => <Icon {...p} d={<>
  <path d="M12 3 L13.5 8 L18.5 9.5 L13.5 11 L12 16 L10.5 11 L5.5 9.5 L10.5 8 Z"/>
  <path d="M18 16 L18.7 18 L20.7 18.7 L18.7 19.5 L18 21.5 L17.3 19.5 L15.3 18.7 L17.3 18 Z"/>
</>}/>;
I.External = (p) => <Icon {...p} d={<><path d="M14 4 H20 V10"/><path d="M20 4 L10 14"/><path d="M18 13 V19 A1 1 0 0 1 17 20 H5 A1 1 0 0 1 4 19 V7 A1 1 0 0 1 5 6 H11"/></>}/>;
I.EyeOff = (p) => <Icon {...p} d={<>
  <path d="M3 3 L21 21"/>
  <path d="M10.6 5.1 A11 11 0 0 1 12 5 c5.5 0 9.5 5 10 7-.2 .9-1.3 2.6-3 4.2"/>
  <path d="M6.6 6.6 C4.1 8.4 2.4 11.1 2 12c.5 2 4.5 7 10 7 1.5 0 2.9-.4 4.1-1"/>
  <path d="M9.9 9.9 a3 3 0 0 0 4.2 4.2"/>
</>}/>;
I.Eye = (p) => <Icon {...p} d={<><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></>}/>;
I.PlusCheck = (p) => <Icon {...p} d={<><circle cx="12" cy="12" r="9"/><polyline points="8,12 11,15 16,9"/></>}/>;
I.Spotify = (p) => <Icon {...p} fill="currentColor" stroke="none" d={<>
  {/* original wave/disk mark, not the Spotify logo */}
  <path d="M3 8 Q12 4 21 8" stroke="currentColor" strokeWidth="2.2" fill="none"/>
  <path d="M4.5 12 Q12 8.5 19.5 12" stroke="currentColor" strokeWidth="2" fill="none"/>
  <path d="M6 16 Q12 13 18 16" stroke="currentColor" strokeWidth="1.8" fill="none"/>
</>}/>;
I.Link = (p) => <Icon {...p} d={<><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1.5-1.5"/></>}/>;
I.Calendar = (p) => <Icon {...p} d={<><rect x="3" y="5" width="18" height="16" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/></>}/>;
I.Clock = (p) => <Icon {...p} d={<><circle cx="12" cy="12" r="9"/><polyline points="12,7 12,12 16,14"/></>}/>;
I.Code = (p) => <Icon {...p} d={<><polyline points="16,18 22,12 16,6"/><polyline points="8,6 2,12 8,18"/></>}/>;

window.I = I;
