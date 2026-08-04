# Kiến trúc — Tổng quan

## Nguyên tắc trung tâm: Neutral Station Model

> UI, AI, API **không bao giờ** chạm raw CIM / SCD / DataModel / OPC UA NodeId.

Mọi nguồn đi qua **Neutral Station Model** — domain model chuẩn hoá hợp nhất topology,
geometry, runtime binding, provenance, validation issues.

---

## Sáu lớp

| # | Lớp | Thư mục | Vai trò |
|---|---|---|---|
| 1 | Black Interface Web | `frontend/` | Chat shell, dynamic workspace, evidence display |
| 2 | BlackCore | `backend/src/blackinterface/agent/` | Intent, tool registry, planner, evidence, policy |
| 3 | Typed Domain API | `backend/src/blackinterface/api/` | Semantic operations qua HTTP/SSE |
| 4 | Neutral Station Model | `backend/src/blackinterface/domain/` | Contract hợp nhất, immutable |
| 5 | Integration Layer | `backend/src/blackinterface/integration/` | Importers + adapters (OPC UA, SLD) |
| 6 | Diagram Engine | `backend/src/blackinterface/diagram/` | Graph → layout → ViewModel → SVG |

Phụ trợ: `store/` (SQLite: release, catalog snapshot, event store).

### Chiều phụ thuộc — một chiều, không vòng

```
frontend ──────────────┐
                       ├──> api ──> domain <── integration ──> [OPC UA]
        agent ─────────┘              ^
                                      └── diagram
                                      └── store
```

- `domain/` **không import** bất cứ lớp nào khác. Đây là contract thuần.
- Chỉ `integration/` được biết NodeId, CIM mRID, path 61850 (invariant I6).
- `agent/` gọi `api/`, **không** gọi thẳng `integration/` hay `diagram/`.

---

## Frontend gọi thẳng Domain API (invariant I5)

```
Web ──┬──────────────────────────> Domain API   (deterministic: view, data, SSE)
      └──> BlackCore ────────────> Domain API   (chỉ cho lượt hội thoại NL)
```

BlackCore dùng **đúng** API mà UI dùng — không đường riêng, không quyền cao hơn.

Lý do:
- **Bảo mật** — AI về mặt cấu trúc không làm được gì mà user không tự làm được qua UI.
  Không phải tin vào prompt.
- **Testability** — test end-to-end không cần LLM.
- **Degradation** — LLM chết thì mất chat, còn nguyên HMI.

Phản mẫu (đã bác bỏ): mọi tương tác UI đi qua LLM agent → chậm, tốn token,
non-deterministic ở chỗ cần deterministic, và UI chết khi LLM chết.

---

## AI làm gì — và không làm gì

**BlackCore ĐƯỢC:**
- Hiểu intent ("bay D06", "alarm critical")
- Gọi semantic tool deterministic: `get_bay_snapshot()`, `get_active_alarms()`, `list_bays()`
- Chọn view phù hợp (mini-SLD, alarm panel, measurement)
- Tóm tắt trạng thái, giải thích alarm/event **kèm evidence**

**BlackCore KHÔNG ĐƯỢC:**
- Bịa topology, connectivity, mapping
- Ghi trực tiếp OPC UA NodeId
- Thực thi điều khiển (MVP read-only)
- Biến giả thuyết thành sự thật
- **Tự soạn nội dung evidence** (invariant I3)

Logic deterministic — parse model, build graph, layout, validation, render SVG,
dựng chuỗi nhân quả sự cố — do backend Python làm. AI chỉ orchestrate và diễn đạt.

---

## Neutral Station Model — nội dung

| Thành phần | Ghi chú |
|---|---|
| **Identity** | `black_id` ổn định + `source_refs[]` (opcua_nodeid, cim_mrid, sld_element_id). **NodeId không bao giờ là primary key** — nó đổi khi project OneATS recompile |
| **Topology** | node-breaker (connectivity node + terminals), khớp mô hình OneATS (manual A.5) nên import không mất mát. Bus-branch chỉ derive khi cần phân tích |
| **Geometry** | lớp riêng, tham chiếu id topology → re-layout không đụng topology |
| **Binding** | `point_ref = {black_id, measurement_kind, node_id, snapshot_id, bound_by}` |
| **Provenance** | theo từng field: importer nào, file nào, rule nào |
| **Validation issues** | gắn vào object, có severity |

**Immutable + versioned + content-addressed.** Release = hash của model.
Evidence trích dẫn release hash.

---

## Evidence — typed object

Mỗi tool trả `(payload, EvidenceRecord)`. Evidence do **tool** sinh, không phải model.

```python
EvidenceRecord(
    tool="get_bay_snapshot", args={"bay": "D03"}, called_at=...,
    source=Source(kind="opcua", endpoint="…:48050",
                  node_ids=[...], catalog_snapshot="sha256:a3f…"),
    release="sha256:91c…", model_version=654,
    coverage=Coverage(requested=7, resolved=5, missing=["ES36", "DS9"]),
    quality=[PointQ(point="D03.XCBR1.PosSt", value="CLOSED",
                    quality="GOOD", ts_source=..., age_ms=1200)],
    limits=["2 điểm không resolve trong snapshot hiện tại",
            "chưa có dữ liệu lịch sử"],
)
```

UI render evidence từ record. Prose LLM nằm **cạnh**, không nằm **trong**.

---

## Snapshot vs live (invariant I7)

Câu hỏi đúng không phải *file vs browse* mà là **snapshot vs live**.

```
build-time :  browse DataServer  →  freeze catalog_snapshot (có hash)
                                 →  pin vào release + OADataModel.ModelVersion
runtime    :  chỉ lấy GIÁ TRỊ live; validate NodeId còn resolve
              không resolve  →  DRIFT  →  nổi lên UI như sự cố hệ thống
```

Không snapshot thì mọi evidence đã trả lời trở thành nói dối hồi tố khi ai đó sửa
project OneATS. Snapshot cũng cho phép engineering offline (trạm thường air-gapped).

---

## Triển khai

Sản phẩm **local**, cài trên **một server tại trạm**, nhiều người truy cập qua browser.

```
┌─ Windows Server tại trạm ────────────────────┐
│  Black Interface (Windows Service)           │
│    FastAPI  ──serve──> Nuxt static SPA       │
│      │                                        │
│      ├── asyncua client (read-only) ──> OneATS DataServer :48050
│      ├── SQLite (release, snapshot, events)  │
│      └── LLM: Ollama local | OpenRouter (dev)│
└──────────────────────────────────────────────┘
        ▲ HTTP
   nhiều workstation vận hành
```

- **Một** OPC UA subscription phía server → fan-out SSE cho N client.
  Không tạo subscription theo từng browser.
- Nuxt build static → FastAPI serve → **một process**, không cần Node runtime.
- Không Docker (chính sách IT + độ tin cậy trên Windows Server tại trạm).

Chi tiết lựa chọn: ADR-0006.
