# Task Advisor (`advise_task` & `search_skills`)

- **Tự động cho việc vừa & lớn:** Câu hỏi ngắn, giải thích khái niệm, sửa 1–2 chỗ nhỏ hoặc việc đã chốt → làm thẳng luôn. Việc mới, thiết kế/kiến trúc, sửa lỗi chưa rõ nguyên nhân, refactor nhiều tệp, xử lý đa tệp hoặc khi người dùng hỏi tư vấn → gọi `advise_task` trước (đặt `force_panel: true` nếu người dùng hỏi tư vấn cho câu đơn giản).
- **Tiết kiệm token & quota:** Không gọi `swarm(action="models")` lặp lại ở mọi lượt; chỉ truyền `quota_percent` vào `advise_task` khi đã biết hoặc nghi sắp hết quota.
- **Chờ chốt & nạp đúng skill:** Khi `pause=true` (`should_pause_for_confirmation`), hiện gọn **Bảng Gợi Ý Chiến Lược** rồi chờ người dùng chốt. Khi thực thi, chỉ `read_file` **1–2 `SKILL.md` sát nhất** thay vì đọc tràn lan; dùng `search_skills` nếu cần tìm skill chuyên ngành khác trong kho 700+ skill.
