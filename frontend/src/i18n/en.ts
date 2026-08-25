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
  workspace: {
    nav: 'Workspace navigation',
    navCollapse: 'Collapse navigation rail',
    navExpand: 'Expand navigation rail',
    details: 'Scope details',
    detailsTitle: 'Quick state',
    detailsClose: 'Hide details',
    detailsReopen: 'Show quick state beside diagram',
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
    state: 'Switch state',
    measurements: 'Measurements',
    energization: 'Energisation',
    anomalies: 'Anomalies',
    alarms: 'Incidents',
    alarmList: 'Alarms',
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
    backToBay: '← Back to bay {bay}',
  },
  alarms: {
    scopeLine: 'Scope in view: {scope}',
    notAsked: 'The server has not been asked about this scope yet.',
    noneInScope: 'No open incidents in {scope}.',
    none: 'No open incidents.',
    unknownYet: 'The alarm list has not been read yet — this is not "nothing is wrong".',
    stationCounts: 'Station: {fault} faults · {status} status · {unknown} unclassified',
    seed: 'Highest-severity alarm',
    faults: 'Alarms in this cluster',
    evidence: 'Supporting evidence',
    flapping: 'Flapping',
    flappingHint:
      'This point keeps going in and out — collapsed to one entry, not many incidents.',
    scopes: 'Scopes affected',
    span: 'Spanned {ms} ms',
    byOperator: 'Caused by {actor}',
    notCause:
      'These alarms share a moment and an electrical area — this is not yet a causal chain.',
    guidance: 'Handling guidance',
    noGuidance: 'No guidance exists for this kind of alarm.',
    draft: 'DRAFT — not approved',
    draftHint:
      'Composed by the system and reviewed by nobody with operational authority. Reference only; it does not replace the station procedure.',
    caution: 'Caution',
    references: 'Sources',
    klass: {
      fault: 'Fault',
      status: 'Status',
      config: 'Configuration',
      action: 'Operator action',
      unknown: 'Unclassified',
    },
  },
  alarmList: {
    tabActive: 'Active',
    tabHistory: 'Handled',
    filters: 'Filters',
    rowCount: '{count} rows',
    time: 'Time',
    severity: 'Sev',
    klass: 'Class',
    message: 'Message',
    point: 'Point',
    search: 'Search',
    searchPlaceholder: 'message, point, severity…',
    all: 'All',
    includeStatus: 'Show switch positions',
    noneInScope: 'No alarms in {scope}.',
    noHistory: 'No handled incidents in {scope}.',
    historyHint:
      'Incidents land here after Done on the Incidents tab. Local workflow only — not OneATS acknowledgement.',
    done: 'Done — handled',
    dismissing: 'Saving…',
    dismissedAt: 'Done at {time}',
  },
  anomalies: {
    none: 'No runtime anomalies.',
    stationWide: 'Whole station — deliberately not narrowed to {scope}.',
    scopeLine: 'Runtime anomalies — always whole station',
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
    scopeLine: 'Energisation — always whole station',
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
    stationOverview: 'Whole station',
    openSld: 'Open single-line diagram',
    baysAtLevel: '{level} — {count} bays',
    bayOverview: 'Bay {bay}',
    scopeUnsupported: 'Pick the station, a bay, or a device to see switch state.',
    scopeLine: 'Switch positions — scope: {scope}',
  },
  sld: {
    fit: 'Fit view',
    zoomIn: 'Zoom in',
    zoomOut: 'Zoom out',
    fullscreen: 'Full screen',
    exitFullscreen: 'Exit full screen',
    hint: 'Scroll · drag to pan · f key',
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
    scopeLine: 'Measurements — scope: {scope}',
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
    scopeLine: 'Evidence coverage — scope: {scope}',
    clean: 'complete',
    noPoints: 'no points read',
    coverage: 'Coverage',
    points: 'points',
    source: 'Source',
    at: 'At',
    subject: 'Subject',
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
  /** Choosing the language model — engineer surface (ADR-0020). */
  assistant: {
    title: 'Language model',
    intro:
      'Choose the model behind the assistant. The station still answers with this off — ' +
      'figures and evidence come from tools; the model only decides what to read and how ' +
      'to word it. The key is stored encrypted in SQLite and never returned by the API.',
    fromEnv: 'coming from the environment',
    provider: 'Provider',
    providerOff: 'Off — computed answers only',
    providerOpenai: 'OpenAI-compatible endpoint (OpenRouter, Ollama…)',
    baseUrl: 'Endpoint',
    model: 'Model name',
    apiKey: 'API key',
    keyStored: '•••••••• stored — leave blank to keep it',
    keyPlaceholder: 'paste the key here',
    noSecretKey:
      'BI_SECRET_KEY is not set, so no key can be stored. Generate a random string and set ' +
      'that variable, or use BI_LLM_API_KEY.',
    save: 'Save',
    saving: 'Saving…',
    test: 'Test connection',
    testing: 'Calling the model…',
    clearKey: 'Remove key',
    confirmClearKey: 'Remove the stored key?',
    // Saved is not working. Only a real call can set this.
    verified: 'Last reached a model',
    neverVerified: 'never — press "Test connection"',
    updated: 'Last changed',
    probeOk: 'Reached {provider}. It replied: "{reply}"',
    probeFailed: 'Could not reach it: {error}',
  },
  /** The chat pane's own chrome. Its answers live under `agent.answer`. */
  scope: {
    chip: 'About {scope}',
    chipHint: 'Questions without a name resolve against this scope. Click to widen.',
  },
  chat: {
    empty: 'Ask about the station…',
    placeholder: 'Ask about the station…',
    send: 'Ask',
    sending: 'Asking…',
    thinking: 'Reading the station…',
    status: {
      callingModel: 'Calling the model…',
      resolving: 'Looking up the name…',
      reading: 'Reading {scope}…',
      readingGeneric: 'Reading station data…',
      writing: 'Writing interpretation…',
    },
    // Says what a nameless question resolves against, before it is sent.
    about: 'about {scope}',
    // Conversations store **words**, never readings (ADR-0022 §2). Said out
    // loud, because an old turn shown without evidence looks exactly like one
    // whose evidence went missing.
    historical:
      'Asked at {at} — figures and evidence are not stored. Ask again for current values.',
    threads: {
      new: 'New conversation',
      recent: 'Recent',
      none: 'No conversations stored yet.',
      untitled: 'New conversation',
      delete: 'Delete conversation',
      turns: 'no turns | {n} turn | {n} turns',
    },
    // Model prose always sits in its own labelled block, never mixed with facts (I3).
    interpretation: 'Interpretation',
    model: 'Model: {provider}',
    noModel: 'No language model — this answer is computed.',
    modelFailed: 'The model could not write an explanation ({error}). The figures above stand.',
    notAllowed: 'Your account may not talk to the assistant.',
    collapse: 'Collapse chat',
    expand: 'Expand chat',
    openTab: {
      sld: 'View on diagram',
      measurements: 'Open measurements',
    },
  },
  /** The assistant's **computed** answers — see the note in `vi.ts`. */
  agent: {
    answer: {
      summary:
        '{label} — {devices} devices: {closed} closed, {opened} open, {undetermined} undetermined. ' +
        '{live} sections live, {dead} dead, {unknown} not known. ' +
        '{measurements} readings, {issues} issues.',
      unconfigured:
        'No language model is configured, so the conversation tab cannot answer. ' +
        'The diagram and the monitoring panels are unaffected.',
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
