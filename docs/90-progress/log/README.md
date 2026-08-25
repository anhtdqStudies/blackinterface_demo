# Nhật ký — mỗi phiên/PR một file

Trước 2026-08-10 mọi thứ ghi vào `status.md`. Với ba người, một luật buộc cả ba
ghi vào cùng một file là một luật tự phá: conflict mỗi ngày, rồi người ta bỏ qua.

Nên: **một file mới cho mỗi phiên hoặc mỗi PR.** Không ai sửa file của ai, không
bao giờ conflict.

## Đặt tên

```
YYYY-MM-DD-<slug-ngan>.md      2026-08-14-alarm-event-store.md
```

Cùng ngày nhiều file thì thêm hậu tố: `-2`, `-3`.

## Nội dung tối thiểu

```markdown
# <Đã làm gì> — YYYY-MM-DD

**Ai**: dev A · **Module**: M2 Domain API · **PR**: #12

## Đã xong
- ... (kèm đường dẫn file)

## Còn dở, vướng ở đâu
- ...

## Đo được gì
- Số nào cũng phải kèm **cách đo lại**. Chưa đo thì ghi `GIẢ ĐỊNH — chưa xác minh`
  (AGENTS.md §5.4).

## Việc kế tiếp
- ...
```

## Ba luật

1. **Có ngày `YYYY-MM-DD` gần đầu file** — `tools/check.py` mục 6 kiểm.
2. **Phân biệt sự thật đã đo và giả định.** Đây là luật riêng và quan trọng nhất
   của dự án này: manual của OneATS đã sai so với hệ chạy thật ít nhất một lần
   (alarm mô tả theo OPC UA A&C, thực tế là interface riêng).
3. **Không sửa file cũ của người khác.** Sai thì viết file mới đính chính, y như
   luật ADR immutable.

Bản tổng hợp lên `status.md` do **chủ dự án** làm, mỗi tuần một lần.

## Lưu trữ

[`2026-08-04_10-archive.md`](2026-08-04_10-archive.md) — toàn bộ tiến độ giai
đoạn một người, 04–10/08/2026, giữ nguyên từng chữ khi tách khỏi `status.md`.
