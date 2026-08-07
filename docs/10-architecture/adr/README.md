# Architecture Decision Records

Mỗi quyết định kiến trúc = một file `NNNN-<slug>.md`.

## Quy tắc

- **ADR là immutable.** Muốn đổi → viết ADR mới với `Supersedes: NNNN`,
  và đánh dấu ADR cũ `Status: Superseded by NNNN`. **Không sửa nội dung ADR cũ.**
- Ghi cả **phương án đã bác bỏ** và **lý do**. Đây là phần giá trị nhất —
  nó ngăn phiên sau đề xuất lại thứ đã cân nhắc và loại.
- Nếu quyết định dựa trên số đo, **trích nguồn** (`docs/30-integration/…` + ngày đo).

## Mẫu

```markdown
# ADR-NNNN — <Tiêu đề>

- **Status**: Accepted | Superseded by NNNN | Proposed
- **Date**: YYYY-MM-DD
- **Supersedes**: (nếu có)

## Bối cảnh
## Quyết định
## Phương án đã bác bỏ
## Hệ quả
```

## Danh sách

| # | Tiêu đề | Status |
|---|---|---|
| [0001](0001-neutral-station-model.md) | Neutral Station Model là contract trung tâm | Accepted |
| [0002](0002-topology-from-dataserver.md) | Topology suy từ DataServer, SLD ra khỏi MVP | Accepted |
| [0003](0003-no-drawing-canvas.md) | Không làm canvas vẽ; template + view sinh tự động | Accepted |
| [0004](0004-evidence-typed-object.md) | Evidence là typed object do tool sinh | Accepted |
| [0005](0005-ai-off-correctness-path.md) | AI không nằm trên đường đi của tính đúng đắn | Accepted |
| [0006](0006-local-deployment-stack.md) | Stack triển khai local trên server tại trạm | Accepted |
| [0007](0007-proprietary-alarm-interface.md) | Alarm dùng interface riêng của OneATS | Accepted |
| [0008](0008-bay-template-schema.md) | Schema template ngăn (YAML) | Accepted |
| [0009](0009-frontend-vite-vue.md) | Frontend là Vite + Vue 3 + TS, không Nuxt | Accepted |
| [0010](0010-scope-and-facet.md) | Scope + facet là trục địa chỉ hoá của toàn hệ | Accepted |
| [0011](0011-single-gated-write-path.md) | Một đường ghi duy nhất qua `control/`; agent không có tool ghi | Accepted |
| [0012](0012-stream-cadences.md) | Tách nhịp state / measurement / alarm trên một stream | Accepted |
| [0013](0013-evidence-envelope.md) | Evidence envelope trên mọi facet | Accepted |
| [0014](0014-frontend-workspace.md) | shadcn-vue, workspace nhiều pane, nhiều hội thoại, i18n | Accepted |
| [0015](0015-engineer-authored-templates.md) | Template do engineer soạn, có phiên bản, phải chứng minh trước khi dùng | Accepted |
| [0016](0016-roles-and-capabilities.md) | Vai và quyền: quyền là đơn vị, vai chỉ là gói; kiểm ở tầng facet | Accepted |
| [0017](0017-local-accounts-and-sessions.md) | Tài khoản cục bộ, Argon2id, phiên phía máy chủ bằng cookie | Accepted |
