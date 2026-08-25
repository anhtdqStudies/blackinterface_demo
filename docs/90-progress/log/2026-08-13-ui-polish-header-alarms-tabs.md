# 2026-08-13 — UI polish: header, workspace tabs, alarm cards

## Đã xong

- **Header** (`frontend/src/app/layout/Header.vue`): logo icon, station badge, link status pill, nav hover pills, shadcn `Select` ngôn ngữ, reload icon-only, backdrop blur, meta row mobile.
- **Scope header** (`ScopeHeader.vue`): nút back có ChevronLeft, badge loại scope, typography lớn hơn.
- **Workspace tabs** (`WorkspaceTabs.vue`): panel bo góc + shadow, tab bar scroll ngang, badge sự cố màu primary nhẹ, padding pane `p-4`.
- **Incident card** (`IncidentCard.vue`): shadcn `Card` full layout, danh sách alarm trong box, icon section headers, Alert draft/not-cause, bước playbook đánh số tròn, nút Done primary.
- **Alarm pane** (`AlarmPane.vue`): intro scope có icon, max-width căn giữa.
- **Alarm list** (`AlarmListPane.vue`): scope banner thống nhất.
- **Empty** (`Empty.vue`): icon Inbox trong vòng tròn dashed.
- **Chat** (phiên trước): AskBox, TurnBlock, ChatPane.

`npm run check` xanh.

## Cách xem lại

```bash
cd frontend && npm run build
cd ../backend && uv run uvicorn blackinterface.api.app:app --port 8080
```

Mở tab **Sự cố** / **Alarm** trên DEMO_SAS.

## Việc kế tiếp (nếu muốn tiếp)

- ~~LoginView / EngView cùng phong cách~~ → LoginView xong 2026-08-13 pm
- ~~DataTable alarm list: row hover, zebra nhẹ~~ → `DataTable` prop `framed` xong
- ~~EngView cùng phong cách~~ → xong 2026-08-13 pm (EngView + 4 engineer panes)
- SLD pane chrome (toolbar zoom/fit) → xong 2026-08-13 pm
- State tab Card layout → xong 2026-08-13 pm
- MeasurementPane / EnergizationPane / EvidencePane cùng pattern (chưa làm)

## Bổ sung phiên 3 (EngView)

- **EngView**: gradient nền, icon Settings2, meta station + badge version, nút quay vận hành.
- **ConnectionsPane**: Card form tạo project, project cards highlight active.
- **AssistantPane**: Card cấu hình LLM, khối OpenAI riêng, Alert probe.
- **CoveragePane**: stat grid 4 ô, danh sách ngăn link hover.
- **ModelIssuesPane**: Card + `IssueList` embedded.
- **IssueList**: prop `embedded` bỏ Panel trùng title.


## Bổ sung phiên 2 (Login + Alarm list)

- **LoginView**: gradient nền, logo Zap, card `rounded-2xl` shadow, input cao hơn, nút LogIn icon.
- **AlarmListPane**: filter Card luôn hiện, search có icon, tabs pill, severity badge, history Alert.
- **DataTable**: prop `framed` — border, sticky header, zebra rows.

## Bổ sung phiên 4 (State + SLD)

- **State tab**: `StatePane.vue` scope banner; `StationStateContent` / `BayStateContent` / `DeviceStateContent` dùng Card, bay rows clickable, `SwitchStateBadge` (`st-*` tokens).
- **SLD**: `SldPane.vue` toolbar Fit / Zoom ± trong Card; `SldCanvas` expose `zoomIn`/`zoomOut`, bỏ nút float trên canvas; legend gọn dưới SVG.
- **i18n**: `state.scopeLine`, `sld.{fit,zoomIn,zoomOut,hint}` vi + en.

`python tools/check.py` xanh (2026-08-13 pm).
