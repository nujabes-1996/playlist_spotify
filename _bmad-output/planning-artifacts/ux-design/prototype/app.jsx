// Main App — wires shell + pages + tweaks panel.

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#1DB954",
  "density": "comfy",
  "sidebarWidth": 248,
  "hiddenExpanded": false,
  "headerStyle": "minimal"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  const [route, setRoute] = useState('dashboard');
  const [playlists, setPlaylists] = useState(window.playlists);
  const [syncing, setSyncing] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [lastSync, setLastSync] = useState('21 hours ago');
  const [syncOk, setSyncOk] = useState(true);

  // apply tweaks to CSS vars
  useEffect(() => {
    const accent = t.accent;
    document.documentElement.style.setProperty('--accent', accent);
    // derive lighter hover (just OKLCH brighten approximation)
    document.documentElement.style.setProperty('--accent-hover', accent);
    document.documentElement.style.setProperty('--accent-soft', accent + '22');
    document.documentElement.style.setProperty('--sidebar-w', t.sidebarWidth + 'px');
  }, [t.accent, t.sidebarWidth]);

  function toggleInclude(id) {
    setPlaylists(p => p.map(x => x.id === id ? { ...x, included: !x.included } : x));
  }
  function toggleHide(id) {
    setPlaylists(p => p.map(x => x.id === id ? { ...x, hidden: !x.hidden, included: x.hidden ? x.included : false } : x));
  }
  function doSync() {
    setSyncing(true);
    setTimeout(() => {
      setSyncing(false);
      setLastSync('just now');
      setSyncOk(true);
    }, 1400);
  }

  const pageTitle = {
    dashboard: 'Your library',
    recent: 'Recently Added',
    settings: 'Settings',
    logs: 'Logs',
  }[route];

  const includedCount = playlists.filter(p => p.included && p.kind !== 'target').length;
  const hiddenCount = playlists.filter(p => p.hidden).length;

  return (
    <div className="app">
      <Sidebar route={route} onNav={setRoute} hiddenCount={hiddenCount} />
      <section className="main">
        <Topbar
          title={pageTitle}
          scrolled={scrolled}
          onSync={doSync}
          syncing={syncing}
          lastSync={syncing ? 'syncing…' : lastSync}
          syncOk={syncOk}
          showSearch={route === 'dashboard'}
        />
        <div className="main-scroll" onScroll={(e) => setScrolled(e.currentTarget.scrollTop > 4)}>
          <div className="page">
            {route === 'dashboard' && (
              <Dashboard
                playlists={playlists}
                density={t.density}
                accentCount={includedCount}
                hiddenExpanded={t.hiddenExpanded}
                onToggleInclude={toggleInclude}
                onToggleHide={toggleHide}
              />
            )}
            {route === 'recent' && <RecentlyAdded />}
            {route === 'settings' && <SettingsPage />}
            {route === 'logs' && <LogsPage />}
          </div>
        </div>
      </section>

      <TweaksPanel title="Tweaks">
        <TweakSection title="Brand">
          <TweakColor
            label="Accent color"
            value={t.accent}
            onChange={(v) => setTweak('accent', v)}
            options={['#1DB954', '#22d3ee', '#ec4899', '#f0b400']}
          />
        </TweakSection>
        <TweakSection title="Grid density">
          <TweakRadio
            label="Cards per row"
            value={t.density}
            options={[
              { value: 'compact',  label: 'Compact' },
              { value: 'comfy',    label: 'Comfy' },
              { value: 'spacious', label: 'Spacious' },
            ]}
            onChange={(v) => setTweak('density', v)}
          />
        </TweakSection>
        <TweakSection title="Layout">
          <TweakSlider
            label="Sidebar width"
            value={t.sidebarWidth}
            min={200} max={320} step={4}
            onChange={(v) => setTweak('sidebarWidth', v)}
            suffix="px"
          />
          <TweakToggle
            label="Hidden playlists expanded by default"
            value={t.hiddenExpanded}
            onChange={(v) => setTweak('hiddenExpanded', v)}
          />
        </TweakSection>
        <TweakSection title="Jump to">
          <TweakButton onClick={() => setRoute('dashboard')}>Dashboard</TweakButton>
          <TweakButton onClick={() => setRoute('recent')}>Recently Added</TweakButton>
          <TweakButton onClick={() => setRoute('settings')}>Settings</TweakButton>
          <TweakButton onClick={() => setRoute('logs')}>Logs</TweakButton>
        </TweakSection>
      </TweaksPanel>

      <HandoffPanel />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
