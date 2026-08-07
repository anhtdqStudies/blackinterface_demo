/**
 * English — for ATS engineers and anyone reviewing the system from outside.
 *
 * Same rule as the Vietnamese file: DataServer field names (`quality`,
 * `IsLive`, `Dbpos`, `ModelVersion`, `source_ref`) are not translated, because
 * they are how you find the value again in OneATS.
 */
export default {
  app: {
    brand: 'BLACK INTERFACE',
    reloadSource: 'Reload from source',
    reloading: 'Reloading…',
    loading: 'loading…',
    openOrCreateProject: 'open or create a project',
  },
  nav: {
    diagram: 'Diagram',
    engineering: 'Engineering',
    language: 'Language',
  },
  session: {
    capabilities: 'capabilities',
    signOut: 'Sign out',
  },
  login: {
    subtitle: 'Sign in to see the station',
    username: 'Username',
    password: 'Password',
    signIn: 'Sign in',
    signingIn: 'Signing in…',
  },
  /** Pane titles. The keys are spelled out in `app/layout/panes.ts`. */
  pane: {
    sld: 'Single-line diagram',
    inspector: 'Details',
    state: 'Switch state',
    measurements: 'Measurements',
    energization: 'Energisation',
    anomalies: 'Anomalies',
    evidence: 'Evidence',
    chat: 'Ask',
    connections: 'Connections',
    coverage: 'Coverage',
    modelIssues: 'Model issues',
    binding: 'Point binding',
    // A pinned pane does NOT follow the rest of the screen, and must say so.
    pinned: 'pinned {scope}',
    pinnedHint: 'This pane keeps its own scope and ignores the rest of the screen',
    later: 'Arrives in a later phase.',
    pickDevice: 'Bay {bay} — pick a device on the diagram to see its state.',
    pickBay: 'Pick a bay or a device on the diagram.',
    noEnergization: 'Energisation not solved yet — needs state from the station.',
    noEvidence: 'No evidence for this scope yet.',
    noMeasurements: 'This scope has no measurements — pick a bay or device with an MMXU.',
    noModel: 'No model loaded. Open or create a project.',
  },
  /** The three shipped layouts (ADR-0014 §3). */
  preset: {
    label: 'Layout',
    monitor: 'Monitor',
    chat: 'Conversation',
    incident: 'Incident',
  },
  station: {
    bays: 'bays',
    devices: 'devices',
    source: 'source',
    builtIn: 'built in',
  },
  link: {
    online: 'Online',
    onlinePartial: 'Online (points missing)',
    offline: 'Disconnected',
    snapshot: 'Snapshot',
    snapshotHint: 'Snapshot — not following the station',
    watching: 'Watching {count} points',
    watchingRejected: 'Watching {count} points · {rejected} unreadable',
    offlineHint: 'Disconnected',
    offlineHintWhy: 'Disconnected — {error}',
  },
  header: {
    meta: 'ModelVersion {version} · {bays} bays · {devices} devices · {source}',
  },
  inspector: {
    wholeStation: 'Whole station',
    stationMeta: '{bays} bays · {devices} devices',
    backToStation: '← Back to station',
  },
  anomalies: {
    none: 'No runtime anomalies.',
    stationWide: 'Whole station — deliberately not narrowed to {scope}.',
  },
  eng: {
    title: 'Engineering',
    // Not "Publish": publishing is ADR-0015 (a `releases` row, a pinned
    // ModelVersion) and does not exist yet. That word on a link that only
    // navigates would tell an engineer the model has been frozen.
    toOps: 'To the operator view',
  },
  ops: {
    noDiagram: 'No diagram to show yet.',
    backToOverview: '← Back to overview',
    modelIssues: 'Model build issues ({count})',
    noIssuesAllMatch: 'None. Every bay matched a template.',
  },
  issues: {
    title: 'Model build issues',
    intro:
      'What the system could not resolve while building the model. Nothing is dropped silently — that is invariant I7.',
    errors: 'Errors ({count})',
    warnings: 'Warnings ({count})',
    info: 'Info ({count})',
    noErrors: 'No errors.',
    noWarnings: 'No warnings.',
  },
  coverage: {
    title: 'Coverage',
    devices: 'Switching devices',
    positionGood: 'Position quality GOOD',
    determined: 'Position determined',
    nodes: 'Connectivity nodes',
    baysAt: 'Bays at {level}',
    noTemplate: 'no template',
  },
  energization: {
    title: 'Energisation',
    noComparison: "No bay could be compared against OneATS's IsLive.",
    agrees:
      'Agrees with OneATS on {n}/{total} bays — two independent calculations, same answer.',
    mismatch:
      "Disagrees with OneATS's IsLive on {n}/{total} bays. One of the two models is wrong — see the energization_mismatch issue below.",
    notable: 'Sections worth a look',
  },
  device: {
    title: 'Device',
    evnName: 'EVN name',
    bay: 'Bay',
    role: 'Role',
    state: 'State',
    quality: 'Quality',
    timestamp: 'Timestamp',
    connectsTo: 'Connects to',
    inBay: 'Bay {bay} — {count} devices',
  },
  bay: {
    voltageLevel: 'Voltage level',
    template: 'Template',
    isLive: 'IsLive',
    live: 'energised',
    notLive: 'de-energised',
    undetermined: 'undetermined (quality {quality})',
    logicalNodes: 'Logical nodes',
    devices: 'Switching devices ({count})',
    issues: 'Bay issues ({count})',
    columns: {
      evnName: 'EVN name',
      ln: 'LN',
      role: 'Role',
      state: 'State',
      quality: 'Quality',
      timestamp: 'Timestamp',
    },
  },
  projects: {
    newTitle: 'New project',
    newIntro:
      'Point at a OneATS DataServer — the diagram is derived from its address space, with no drawing by hand. A successful connection stores a snapshot, so the next open renders instantly without the DataServer running.',
    name: 'Project name',
    namePlaceholder: 'e.g. Binh Hoa 220kV',
    address: 'DataServer address',
    connect: 'Connect and build',
    connecting: 'Connecting…',
    existing: 'Existing projects',
    none: 'No projects yet. Create the first one above.',
    active: 'open',
    snapshot: 'snapshot: {when}',
    noSnapshot: 'no snapshot — the first connection did not succeed',
    open: 'Open',
    opening: 'Opening…',
    refresh: 'Reload from source',
    remove: 'Delete',
    confirmRemove: 'Delete project "{name}" and its snapshot?',
    sourceUnreadable: 'Could not read the source:',
    retryHint:
      'The project was saved — fix the network or address, then press «Reload from source».',
  },
  state: {
    CLOSED: 'CLOSED',
    OPEN: 'OPEN',
    INTERMEDIATE: 'INTERMEDIATE',
    UNDETERMINED: 'UNDETERMINED',
  },
  liveState: {
    LIVE: 'LIVE',
    DEAD: 'DE-ENERGISED',
    EARTHED: 'EARTHED',
    UNKNOWN: 'UNDETERMINED',
  },
  reason: {
    seeded_live: 'the busbar here measures as energised',
    seeded_dead: 'the busbar here measures as de-energised',
    through_transformer: 'fed through a power transformer',
    possible_via_uncertain:
      'a device position could not be read — this may be connected to a live section',
    earthed: 'an earth switch is closed',
    no_measurement: 'the busbar here has no readable IsLive',
    isolated: 'every path to a source is open',
  },
  quantity: {
    active_power: 'Active power',
    reactive_power: 'Reactive power',
    power_factor: 'Power factor',
    voltage: 'Line voltage',
    current: 'Highest phase current',
    frequency: 'Frequency',
    tap_position: 'Tap position',
  },
  measurement: {
    title: 'Measurements',
    columnQuantity: 'Quantity',
    columnValue: 'Value',
    unreadable: 'not readable (quality {quality})',
    from: 'from {point}',
    unitUnverified:
      'the DataServer publishes no engineering units — the scale is unverified, so only the number is shown',
    deadbandNote: 'Measurements are deadbanded: changes below the threshold are not pushed.',
    deadbandOverride: 'Threshold overridden to {pct}%.',
    fromScope: 'Readings for {scope} — this device has no MMXU of its own.',
  },
  evidence: {
    title: 'Evidence',
    clean: 'complete',
    coverage: 'Coverage',
    points: 'points',
    source: 'Source',
    at: 'At',
    tool: 'Tool',
  },
  sourceKind: {
    opcua: 'read live from the DataServer',
    snapshot: 'replayed from a stored snapshot',
    fixture: 'dump file (dev/test)',
    store: 'local store',
    derived: 'computed from another facet',
  },
  limit: {
    points_missing: 'Points were asked for that the model has no binding for',
    quality_not_good: 'Read, but quality is not GOOD — not usable as a state',
    data_stale: 'Stale: intact, but no longer the present tense',
    from_snapshot: 'Structure is remembered, not freshly browsed',
    link_down: 'Link is down — this is what we last knew, not what is true now',
    deadband_applied: 'Analog values passed a deadband filter',
    no_history: 'The window asked for predates what is stored',
    unit_unverified: 'The number is real, its scale is not measured — no unit is printed',
  },
  /** The assistant's **computed** answers — see the note in `vi.ts`. */
  agent: {
    answer: {
      summary:
        '{label} — {devices} devices: {closed} closed, {opened} open, {undetermined} undetermined. ' +
        '{live} sections live, {dead} dead, {unknown} not known. ' +
        '{measurements} readings, {issues} issues.',
      ambiguous: '“{query}” matches {count} things: {options}. Which one do you mean?',
      unknown: 'Nothing in this station is called “{query}”.',
      denied:
        'This account lacks the “{missing}” permission, so that question cannot be answered.',
    },
  },
  common: {
    empty: 'None.',
    dash: '—',
  },
  ui: {
    loading: 'Loading',
    errorTitle: 'Could not load',
    retry: 'Retry',
  },
}
