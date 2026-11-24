# Task Advisor (`advise_task` & `search_skills`)

- **Tự động cho việc vừa & lớn:**
  - Nếu là câu hỏi ngắn, giải thích khái niệm, sửa nhỏ 1–2 chỗ hiển nhiên, hoặc lượt tiếp nối công việc đã chốt → **làm thẳng luôn**, không cần gọi `advise_task`.
  - Nếu yêu cầu là xây tính năng mới, thiết kế/kiến trúc, sửa lỗi chưa rõ nguyên nhân, refactor nhiều tệp, audit/review codebase, xử lý dữ liệu đa tệp, tích hợp dịch vụ, hoặc khi người dùng chủ động hỏi tư vấn chọn model/skill/swarm (hoặc gõ `/advise`) → **gọi `advise_task` trước khi sửa code hoặc gọi subagent/swarm** (nếu người dùng nhắc từ khóa tư vấn rõ ràng cho câu đơn giản, đặt `force_panel: true`).
- **Trình bày bảng gợi ý & chờ người dùng chốt:**
  - Khi `advise_task` trả về `should_pause_for_confirmation: true`, trình bày gọn **Bảng Gợi Ý Chiến Lược** (Model Antigravity + điều phối XAI247, Top Skills kèm đường dẫn `SKILL.md`, Đội hình Swarm / Subagent / `py_exec`, Slash commands gợi ý) rồi **dừng lại chờ người dùng chốt** trước khi chỉnh sửa code hoặc mở Swarm.
  - Khi người dùng đã chốt phương án (hoặc dặn rõ *"làm luôn đi không cần hỏi"*), thực thi ngay và dùng `read_file` nạp các `SKILL.md` được gợi ý.
- **Tận dụng `search_skills`:**
  - Kho cục bộ có hơn 700 skill (nhiều skill bị cắt khỏi system prompt do giới hạn ngữ cảnh). Khi cần tìm skill chuyên ngành cho một bước cụ thể, gọi `search_skills` thay vì đoán tên skill.
