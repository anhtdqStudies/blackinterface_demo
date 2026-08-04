# ADR-0009 — Frontend là Vite + Vue 3 + TypeScript, không dùng Nuxt

**Status**: Accepted · **Date**: 2026-08-04
**Supersedes**: dòng "Frontend" trong ADR-0006 (phần còn lại của ADR-0006 giữ nguyên)

---

## Bối cảnh

ADR-0006 chốt stack triển khai local và ghi frontend là **Nuxt build static (SPA)**.
Lúc đó chưa viết dòng frontend nào, và lý do chọn Nuxt là "framework Vue đầy đủ,
build ra tĩnh được".

Sau khi dựng xong module #1 và một viewer 282 dòng để kiểm chứng API, đã rõ hơn
sản phẩm này thật sự cần gì ở frontend:

- **Một console nội bộ**, chạy trong mạng trạm, không public
- **Không SSR** — FastAPI serve file tĩnh, không có Node runtime ở production
  (chính ADR-0006 cấm Node runtime ở production)
- **Không SEO**, không share link ra ngoài
- **Ít route** — sơ đồ trạm, ngăn, sự kiện, hội thoại. Cỡ 4–6 màn
- **Đóng gói offline** bằng Inno Setup: mọi dependency phải vendor được, và mỗi
  dependency là một thứ có thể vỡ khi build không có mạng

Giá trị lớn nhất của Nuxt — SSR, Nitro server routes, file-based routing, hệ
module — thì hai cái đầu ta cấm dùng, hai cái sau tiết kiệm được vài chục dòng.

---

## Quyết định

**Frontend là Vite + Vue 3 + TypeScript**, không Nuxt.

```
frontend/
  index.html
  vite.config.ts
  src/
    main.ts
    router.ts
    api/
      schema.d.ts      # SINH TỰ ĐỘNG từ OpenAPI của backend - không sửa tay
      client.ts        # fetch wrapper có type
    stores/            # Pinia
    components/
      diagram/         # SldCanvas, DeviceSymbol, BusbarRail
      panels/
    views/
```

Build: `npm run build` → `frontend/dist/` → FastAPI serve tĩnh. Một process.

### Điều kiện kèm theo: type của API phải được SINH, không viết tay

`src/api/schema.d.ts` sinh từ `openapi.json` của FastAPI bằng
`openapi-typescript`. Frontend gọi sai tên field hay sai kiểu → **lỗi lúc build**,
không phải `undefined` lúc chạy.

Đây là lý do kỹ thuật quan trọng nhất của ADR này. Nó áp cùng một nguyên tắc mà
`tools/check.py` và `tests/unit/test_architecture.py` đang áp cho backend: ràng
buộc kiến trúc phải được **máy cưỡng chế**, không phải con người nhớ.

---

## Phương án đã bác bỏ

### A. Giữ Nuxt (ADR-0006)
Không sai, chỉ là trả giá cho thứ không dùng: lớp build Nitro, nhiều dependency
bắc cầu hơn phải vendor cho bản cài offline, thời gian build lâu hơn.
**Bác bỏ** vì không có lợi ích nào bù lại trong bối cảnh này.

### B. React
Không có lý do kỹ thuật nào để chọn hơn Vue ở đây. **Bác bỏ** — quyết định theo
thói quen của nhóm, mà nhóm ATS quen Vue.

### C. Không framework, giữ HTML/JS thuần như `frontend/dev/index.html`
Đã chạy được thật, và đó là bằng chứng nó **đủ cho một màn hình**. Nhưng module
tiếp theo cần: state chia sẻ giữa nhiều view, cập nhật realtime tại chỗ, timeline
sự kiện, panel evidence, chat. Làm những thứ đó bằng thao tác DOM tay là tự viết
lại một framework tệ hơn. **Bác bỏ.**

### D. Web Components thuần
Ít dependency nhất, nhưng thiếu hệ sinh thái (router, store, devtools) và nhóm
không quen. **Bác bỏ.**

---

## Hệ quả

**Tốt**

- Ít dependency hơn → bản cài offline ít vỡ hơn, build nhanh hơn
- Type an toàn xuyên biên giới frontend/backend, cưỡng chế bằng máy
- `dist/` là file tĩnh thuần, FastAPI serve trực tiếp, không cần Node ở trạm

**Phải chấp nhận**

- Tự viết router config và cấu trúc thư mục thay vì theo quy ước Nuxt.
  Với 4–6 màn thì đây là vài chục dòng.
- Không có auto-import → phải viết `import` rõ ràng. Thực ra dễ đọc hơn cho
  người mới vào dự án, và cho AI agent đọc lại ở phiên sau.
- **Node vẫn cần lúc build**, chỉ không cần lúc chạy. Điều này đúng với cả Nuxt.
  Bản cài cuối cùng chỉ chứa `dist/`.

**Việc phải làm để ADR này không mục**

- `frontend/dev/index.html` giữ làm bản tham chiếu hành vi cho tới khi bản mới
  đủ tính năng, rồi **xoá**. Không để tồn tại hai frontend.
- Sinh lại `schema.d.ts` phải là một bước trong quy trình, không phải việc nhớ
  làm bằng tay. Xem `frontend/README.md`.
