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
    inspector: 'Chi tiết',
    state: 'Trạng thái',
    measurements: 'Số đo',
    energization: 'Mang điện',
    anomalies: 'Bất thường',
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
  /** Ba bố cục dựng sẵn (ADR-0014 §3). */
  preset: {
    label: 'Bố cục',
    monitor: 'Giám sát',
    chat: 'Hội thoại',
    incident: 'Sự cố',
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
  },
  anomalies: {
    none: 'Không có bất thường vận hành.',
    stationWide: 'Toàn trạm — cố ý không lọc theo {scope}.',
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
    clean: 'đầy đủ',
    coverage: 'Độ phủ',
    points: 'điểm',
    source: 'Nguồn',
    at: 'Lúc',
    tool: 'Công cụ',
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
      ambiguous: '«{query}» ứng với {count} thứ: {options}. Bạn hỏi cái nào?',
      unknown: 'Trạm này không có gì tên «{query}».',
      denied: 'Tài khoản của bạn không có quyền «{missing}» nên câu này chưa trả lời được.',
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
