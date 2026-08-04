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
