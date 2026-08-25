/**
 * Vietnamese — the default, and the one written first.
 *
 * Domain terms stay in the form operators use on site: "ngăn", "thanh cái",
 * "dao tiếp địa". `quality`, `IsLive`, `Dbpos`, `ModelVersion` and `source_ref`
 * stay in English because that is what the DataServer calls them, and a
 * translated field name would break the trail back to OneATS.
 */
export default {
  app: {
    brand: 'BLACK INTERFACE',
    reloadSource: 'Tải lại từ nguồn',
    reloading: 'Đang tải lại…',
    loading: 'đang tải…',
    openOrCreateProject: 'mở hoặc tạo một project',
  },
  nav: {
    diagram: 'Sơ đồ',
    engineering: 'Kỹ thuật',
    language: 'Ngôn ngữ',
  },
  workspace: {
    nav: 'Điều hướng workspace',
    navCollapse: 'Thu gọn thanh điều hướng',
    navExpand: 'Mở rộng thanh điều hướng',
    details: 'Chi tiết phạm vi',
    detailsTitle: 'Trạng thái nhanh',
    detailsClose: 'Ẩn chi tiết',
    detailsReopen: 'Hiện trạng thái nhanh bên cạnh sơ đồ',
  },
  session: {
    // Hiện ở góc phải: ai đang đăng nhập, giữ vai nào (ADR-0016, ADR-0017).
    capabilities: 'quyền',
    signOut: 'Đăng xuất',
  },
  login: {
    subtitle: 'Đăng nhập để xem trạm',
    username: 'Tên đăng nhập',
    password: 'Mật khẩu',
    signIn: 'Đăng nhập',
    signingIn: 'Đang đăng nhập…',
  },
  /** Tên từng ô trong workspace. Khoá viết thẳng ở `app/layout/panes.ts`. */
  pane: {
    sld: 'Sơ đồ một sợi',
    state: 'Trạng thái',
    measurements: 'Số đo',
    energization: 'Mang điện',
    anomalies: 'Bất thường',
    alarms: 'Sự cố',
    alarmList: 'Alarm',
    evidence: 'Bằng chứng',
    chat: 'Hỏi đáp',
    connections: 'Kết nối',
    coverage: 'Độ phủ',
    modelIssues: 'Cảnh báo dựng model',
    binding: 'Gán điểm',
    // Ô đã ghim: nó KHÔNG đi theo phần còn lại của màn hình, và phải nói ra.
    pinned: 'ghim {scope}',
    pinnedHint: 'Ô này giữ nguyên phạm vi, không đi theo màn hình',
    later: 'Có ở giai đoạn sau.',
    pickDevice: 'Ngăn {bay} — chọn một thiết bị trên sơ đồ để xem trạng thái.',
    pickBay: 'Chọn một ngăn hoặc một thiết bị trên sơ đồ.',
    noEnergization: 'Chưa tính được mang điện — cần trạng thái từ trạm.',
    noEvidence: 'Chưa có bằng chứng cho phạm vi này.',
    noMeasurements: 'Phạm vi này không mang số đo — chọn ngăn hoặc thiết bị có MMXU.',
    noModel: 'Chưa có model. Mở hoặc tạo một project.',
  },
  station: {
    bays: 'ngăn',
    devices: 'thiết bị',
    source: 'nguồn',
    builtIn: 'dựng trong',
  },
  link: {
    online: 'Trực tuyến',
    onlinePartial: 'Trực tuyến (thiếu điểm)',
    offline: 'Mất kết nối',
    snapshot: 'Ảnh chụp',
    snapshotHint: 'Ảnh chụp — không theo thời gian thực',
    watching: 'Theo dõi {count} điểm',
    watchingRejected: 'Theo dõi {count} điểm · {rejected} điểm không đọc được',
    offlineHint: 'Mất kết nối',
    offlineHintWhy: 'Mất kết nối — {error}',
  },
  header: {
    meta: 'ModelVersion {version} · {bays} ngăn · {devices} thiết bị · {source}',
  },
  inspector: {
    wholeStation: 'Toàn trạm',
    stationMeta: '{bays} ngăn · {devices} thiết bị',
    backToStation: '← Về toàn trạm',
    backToBay: '← Về ngăn {bay}',
  },
  alarms: {
    scopeLine: 'Đang xét phạm vi: {scope}',
    notAsked: 'Chưa hỏi máy chủ về phạm vi này.',
    noneInScope: 'Không có sự cố nào trong {scope}.',
    none: 'Không có sự cố nào đang mở.',
    unknownYet: 'Chưa đọc được danh sách alarm — không phải "không có sự cố".',
    stationCounts: 'Toàn trạm: {fault} sự cố · {status} trạng thái · {unknown} chưa phân loại',
    seed: 'Alarm nặng nhất',
    faults: 'Alarm trong cụm',
    evidence: 'Bằng chứng đi kèm',
    flapping: 'Đang dao động',
    flappingHint: 'Điểm này vào ra liên tục — gộp thành một mục, không phải nhiều sự cố.',
    scopes: 'Phạm vi ảnh hưởng',
    span: 'Kéo dài {ms} ms',
    byOperator: 'Do {actor} thao tác',
    notCause: 'Đây là nhóm alarm cùng thời điểm và cùng vùng điện — chưa phải chuỗi nhân quả.',
    guidance: 'Hướng dẫn xử lý',
    noGuidance: 'Chưa có hướng dẫn cho loại alarm này.',
    draft: 'BẢN NHÁP — chưa được duyệt',
    draftHint:
      'Nội dung do hệ thống soạn, chưa có người có thẩm quyền vận hành duyệt. Dùng để tham khảo, không thay quy trình của trạm.',
    caution: 'Lưu ý',
    references: 'Nguồn',
    klass: {
      fault: 'Sự cố',
      status: 'Trạng thái',
      config: 'Cấu hình',
      action: 'Thao tác',
      unknown: 'Chưa phân loại',
    },
  },
  alarmList: {
    tabActive: 'Đang active',
    tabHistory: 'Đã xử lý',
    filters: 'Bộ lọc',
    rowCount: '{count} dòng',
    time: 'Thời gian',
    severity: 'Mức',
    klass: 'Loại',
    message: 'Nội dung',
    point: 'Điểm',
    search: 'Tìm',
    searchPlaceholder: 'message, point, severity…',
    all: 'Tất cả',
    includeStatus: 'Hiện trạng thái đóng cắt',
    noneInScope: 'Không có alarm nào trong {scope}.',
    noHistory: 'Chưa có sự cố đã xử lý trong {scope}.',
    historyHint:
      'Sự cố chuyển vào đây sau khi ấn Done trên tab Sự cố. Đây là ghi nhận nội bộ — không phải ack trên OneATS.',
    done: 'Done — đã xử lý',
    dismissing: 'Đang lưu…',
    dismissedAt: 'Done lúc {time}',
  },
  anomalies: {
    none: 'Không có bất thường vận hành.',
    stationWide: 'Toàn trạm — cố ý không lọc theo {scope}.',
    scopeLine: 'Bất thường vận hành — luôn toàn trạm',
  },
  eng: {
    title: 'Kỹ thuật',
    // Không phải "Chốt bản": chốt bản là ADR-0015 (bảng `releases`, pin
    // ModelVersion) và chưa tồn tại. Nhãn đó trên một link chỉ điều hướng sẽ
    // khiến engineer tin là mô hình đã được đóng băng.
    toOps: 'Sang màn vận hành',
  },
  ops: {
    noDiagram: 'Chưa có sơ đồ để hiển thị.',
    backToOverview: '← Về tổng quan',
    modelIssues: 'Cảnh báo dựng model ({count})',
    noIssuesAllMatch: 'Không có. Mọi ngăn khớp template.',
  },
  issues: {
    title: 'Cảnh báo dựng model',
    intro:
      'Những gì hệ thống không giải quyết được khi dựng model. Không có mục nào bị bỏ qua âm thầm — đây là invariant I7.',
    errors: 'Lỗi ({count})',
    warnings: 'Cảnh báo ({count})',
    info: 'Thông tin ({count})',
    noErrors: 'Không có lỗi.',
    noWarnings: 'Không có cảnh báo.',
  },
  coverage: {
    title: 'Độ phủ',
    devices: 'Thiết bị đóng cắt',
    positionGood: 'Vị trí quality GOOD',
    determined: 'Xác định được',
    nodes: 'Connectivity node',
    baysAt: 'Ngăn tại {level}',
    noTemplate: 'không có template',
  },
  energization: {
    title: 'Mang điện',
    scopeLine: 'Mang điện — luôn toàn trạm',
    noComparison: 'Không có ngăn nào đối chiếu được với IsLive của OneATS.',
    agrees: 'Khớp OneATS {n}/{total} ngăn — hai cách tính độc lập ra cùng kết quả.',
    mismatch:
      'Lệch {n}/{total} ngăn so với IsLive của OneATS. Một trong hai mô hình sai — xem cảnh báo energization_mismatch bên dưới.',
    notable: 'Vùng cần để ý',
  },
  device: {
    title: 'Thiết bị',
    evnName: 'Tên EVN',
    bay: 'Ngăn',
    role: 'Vai trò',
    state: 'Trạng thái',
    quality: 'Quality',
    timestamp: 'Timestamp',
    connectsTo: 'Nối tới',
    inBay: 'Ngăn {bay} — {count} thiết bị',
  },
  bay: {
    voltageLevel: 'Cấp điện áp',
    template: 'Template',
    isLive: 'IsLive',
    live: 'có điện',
    notLive: 'không điện',
    undetermined: 'không xác định (quality {quality})',
    logicalNodes: 'Logical nodes',
    devices: 'Thiết bị đóng cắt ({count})',
    issues: 'Cảnh báo của ngăn ({count})',
    columns: {
      evnName: 'Tên EVN',
      ln: 'LN',
      role: 'Vai trò',
      state: 'Trạng thái',
      quality: 'Quality',
      timestamp: 'Timestamp',
    },
  },
  projects: {
    newTitle: 'Project mới',
    newIntro:
      'Trỏ vào một OneATS DataServer — sơ đồ được dựng tự động từ address space, không vẽ tay. Kết nối thành công sẽ lưu một snapshot: lần mở sau hiển thị ngay, không cần DataServer đang chạy.',
    name: 'Tên project',
    namePlaceholder: 'ví dụ: Trạm 220kV Bình Hoà',
    address: 'Địa chỉ DataServer',
    connect: 'Kết nối và dựng sơ đồ',
    connecting: 'Đang kết nối…',
    existing: 'Project đã có',
    none: 'Chưa có project nào. Tạo project đầu tiên ở trên.',
    active: 'đang mở',
    snapshot: 'snapshot: {when}',
    noSnapshot: 'chưa có snapshot — lần kết nối đầu chưa thành công',
    open: 'Mở',
    opening: 'Đang mở…',
    refresh: 'Tải lại từ nguồn',
    remove: 'Xoá',
    confirmRemove: 'Xoá project "{name}" và snapshot của nó?',
    sourceUnreadable: 'Không đọc được nguồn:',
    retryHint: 'Project đã được lưu — sửa mạng/địa chỉ rồi bấm «Tải lại từ nguồn» để thử lại.',
  },
  /** Switch position. Upper case: these are read at a glance, not in a sentence. */
  state: {
    CLOSED: 'ĐÓNG',
    OPEN: 'MỞ',
    INTERMEDIATE: 'TRUNG GIAN',
    UNDETERMINED: 'KHÔNG XÁC ĐỊNH',
    stationOverview: 'Toàn trạm',
    openSld: 'Mở sơ đồ một sợi',
    baysAtLevel: '{level} — {count} ngăn',
    bayOverview: 'Ngăn {bay}',
    scopeUnsupported: 'Chọn toàn trạm, một ngăn hoặc một thiết bị để xem trạng thái.',
    scopeLine: 'Vị trí đóng cắt — phạm vi: {scope}',
  },
  sld: {
    fit: 'Vừa màn hình',
    zoomIn: 'Phóng to',
    zoomOut: 'Thu nhỏ',
    fullscreen: 'Toàn màn hình',
    exitFullscreen: 'Thoát toàn màn hình',
    hint: 'Lăn chuột · kéo để di chuyển · phím f',
  },
  liveState: {
    LIVE: 'CÓ ĐIỆN',
    DEAD: 'KHÔNG ĐIỆN',
    EARTHED: 'ĐÃ TIẾP ĐỊA',
    UNKNOWN: 'KHÔNG XÁC ĐỊNH',
  },
  /** Why the solver reached its verdict. Codes from `domain/energization.py`. */
  reason: {
    seeded_live: 'thanh cái ở đây đo được có điện',
    seeded_dead: 'thanh cái ở đây đo được không điện',
    through_transformer: 'lấy điện qua máy biến áp',
    possible_via_uncertain:
      'có thiết bị không đọc được vị trí — có thể đang nối vào vùng có điện',
    earthed: 'có dao tiếp địa đang đóng',
    no_measurement: 'thanh cái ở đây không đọc được IsLive',
    isolated: 'mọi đường tới nguồn đều đang mở',
  },
  /** Đại lượng đo. Tên đại lượng luôn biết chắc — đơn vị thì không, xem `measurement`. */
  quantity: {
    active_power: 'Công suất tác dụng',
    reactive_power: 'Công suất phản kháng',
    power_factor: 'Hệ số công suất',
    voltage: 'Điện áp dây',
    current: 'Dòng điện lớn nhất',
    frequency: 'Tần số',
    tap_position: 'Nấc MBA',
  },
  measurement: {
    title: 'Số đo',
    scopeLine: 'Số đo — phạm vi: {scope}',
    columnQuantity: 'Đại lượng',
    columnValue: 'Giá trị',
    unreadable: 'không đọc được (quality {quality})',
    from: 'từ {point}',
    unitUnverified: 'DataServer không công bố đơn vị — chưa xác minh thang đo, nên chỉ hiện số',
    deadbandNote: 'Số đo có áp deadband: thay đổi nhỏ hơn ngưỡng sẽ không được đẩy lên.',
    deadbandOverride: 'Ngưỡng đang bị đặt đè: {pct}%.',
    fromScope: 'Số đo của {scope} — thiết bị không mang MMXU riêng.',
  },
  /** Bằng chứng — vì sao một câu trả lời đáng tin tới đâu (ADR-0013). */
  evidence: {
    title: 'Bằng chứng',
    scopeLine: 'Độ phủ bằng chứng — phạm vi: {scope}',
    clean: 'đầy đủ',
    /** Khác «đầy đủ»: tool này không đọc điểm nào, nên nó không bảo chứng cho
     * một con số nào — chỉ cho xuất xứ (trạm nào, ModelVersion nào). */
    noPoints: 'không đọc điểm nào',
    coverage: 'Độ phủ',
    points: 'điểm',
    source: 'Nguồn',
    at: 'Lúc',
    subject: 'Đối tượng',
  },
  sourceKind: {
    opcua: 'đọc trực tiếp từ DataServer',
    snapshot: 'ảnh chụp đã lưu',
    fixture: 'file dump (dev/test)',
    store: 'kho cục bộ',
    derived: 'suy ra từ facet khác',
  },
  /** Vì sao câu trả lời kém giá trị hơn vẻ ngoài. Mã từ `domain/evidence.py`. */
  limit: {
    points_missing: 'Có điểm được hỏi nhưng model không có binding',
    quality_not_good: 'Đọc được nhưng quality không GOOD — không dùng làm trạng thái',
    data_stale: 'Số liệu cũ: nguyên vẹn nhưng không còn là hiện tại',
    from_snapshot: 'Cấu trúc lấy từ snapshot, không phải vừa duyệt lại',
    link_down: 'Mất kết nối — đây là điều biết được lần cuối, không phải hiện tại',
    deadband_applied: 'Số đo đã qua lọc deadband',
    no_history: 'Khoảng thời gian hỏi nằm ngoài dữ liệu đang lưu',
    unit_unverified: 'Số đúng nhưng thang đo chưa xác minh — không in đơn vị',
  },
  /** Cài đặt mô hình ngôn ngữ — bề mặt engineer (ADR-0020). */
  assistant: {
    title: 'Mô hình ngôn ngữ',
    intro:
      'Chọn mô hình cho trợ lý. Trạm vẫn trả lời được khi tắt — số liệu và bằng chứng ' +
      'do tool tính, mô hình chỉ chọn cách đọc dữ liệu và diễn đạt. Key lưu mã hoá ' +
      'trong SQLite và không bao giờ được API trả về.',
    fromEnv: 'đang lấy từ biến môi trường',
    provider: 'Nhà cung cấp',
    providerOff: 'Tắt — chỉ dùng câu tính sẵn',
    providerOpenai: 'Endpoint kiểu OpenAI (OpenRouter, Ollama…)',
    baseUrl: 'Địa chỉ endpoint',
    model: 'Tên model',
    apiKey: 'API key',
    keyStored: '•••••••• đã lưu — để trống nếu giữ nguyên',
    keyPlaceholder: 'dán key vào đây',
    noSecretKey:
      'Chưa đặt BI_SECRET_KEY nên không lưu được key. Sinh một chuỗi ngẫu nhiên rồi đặt ' +
      'biến môi trường đó, hoặc dùng BI_LLM_API_KEY.',
    save: 'Lưu',
    saving: 'Đang lưu…',
    test: 'Thử kết nối',
    testing: 'Đang gọi mô hình…',
    clearKey: 'Xoá key',
    confirmClearKey: 'Xoá key đã lưu?',
    // Lưu được ≠ chạy được. Chỉ một lần gọi thật mới đặt được mốc này.
    verified: 'Đã gọi thật lần cuối',
    neverVerified: 'chưa bao giờ — bấm «Thử kết nối»',
    updated: 'Sửa lần cuối',
    probeOk: 'Gọi được {provider}. Mô hình trả lời: «{reply}»',
    probeFailed: 'Không gọi được: {error}',
  },
  /** Ô hỏi đáp: phần vỏ. Câu trả lời tính được nằm ở `agent.answer` bên dưới. */
  scope: {
    chip: 'Về {scope}',
    chipHint: 'Câu không nêu tên được hiểu là hỏi về phạm vi này. Bấm để mở rộng.',
  },
  chat: {
    empty: 'Hỏi về trạm…',
    placeholder: 'Hỏi về trạm…',
    send: 'Hỏi',
    sending: 'Đang hỏi…',
    thinking: 'Đang đọc trạm…',
    status: {
      callingModel: 'Đang gọi mô hình…',
      resolving: 'Đang tra tên thiết bị / ngăn…',
      reading: 'Đang đọc {scope}…',
      readingGeneric: 'Đang đọc dữ liệu trạm…',
      writing: 'Đang viết diễn giải…',
    },
    // Nói trước câu hỏi sẽ được hiểu là hỏi về đâu, để không phải đoán.
    about: 'về {scope}',
    // Hội thoại lưu **lời**, không lưu số (ADR-0022 §2). Nói thẳng ra, vì một
    // lượt cũ hiện không kèm bằng chứng trông y hệt một lượt bị mất bằng chứng.
    historical:
      'Đã hỏi lúc {at} — số liệu và bằng chứng không được lưu lại. Hỏi lại để xem số hiện tại.',
    threads: {
      new: 'Hội thoại mới',
      recent: 'Gần đây',
      none: 'Chưa có hội thoại nào được lưu.',
      untitled: 'Hội thoại mới',
      delete: 'Xoá hội thoại',
      turns: 'không có lượt nào | {n} lượt | {n} lượt',
    },
    // Chữ do mô hình viết luôn nằm khối riêng, có nhãn — không trộn vào số liệu (I3).
    interpretation: 'Diễn giải',
    model: 'Mô hình: {provider}',
    noModel: 'Không có mô hình ngôn ngữ — câu trả lời là số liệu đã tính.',
    modelFailed: 'Mô hình không viết được lời giải thích ({error}). Số liệu ở trên vẫn đúng.',
    notAllowed: 'Tài khoản của bạn không có quyền hỏi trợ lý.',
    collapse: 'Thu gọn hội thoại',
    expand: 'Mở rộng hội thoại',
    openTab: {
      sld: 'Xem trên sơ đồ',
      measurements: 'Mở bảng số đo',
    },
  },
  /**
   * Câu trả lời **tính được** của trợ lý, dùng khi không có mô hình ngôn ngữ
   * (`BI_LLM=off`, hoặc mô hình chết). Backend gửi khoá + tham số chứ không gửi
   * câu — nó không biết người đọc muốn tiếng Việt hay tiếng Anh. Khoá sinh ở
   * `agent/brief.py`; `check.py` mục 5 so hai danh sách, thiếu là đỏ.
   */
  agent: {
    answer: {
      summary:
        '{label} — {devices} thiết bị: {closed} đóng, {opened} mở, {undetermined} không xác định. ' +
        '{live} đoạn mang điện, {dead} mất điện, {unknown} chưa rõ. ' +
        '{measurements} số đo, {issues} vấn đề.',
      unconfigured:
        'Chưa cấu hình mô hình ngôn ngữ, nên tab hội thoại chưa trả lời được. ' +
        'Sơ đồ và các bảng giám sát vẫn hoạt động bình thường.',
    },
  },
  common: {
    empty: 'Không có.',
    dash: '—',
  },
  ui: {
    loading: 'Đang tải',
    errorTitle: 'Không tải được',
    retry: 'Thử lại',
  },
}
