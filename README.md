# ⚡ Task Advisor Antigravity

MCP server & Plugin Rules không phụ thuộc thư viện ngoài (zero-dependency Python 3.8+) giúp Antigravity tự động phân tích yêu cầu công việc trước khi bắt tay thực thi các tác vụ vừa và lớn.

## ✨ Tính năng chính

- **Lập chỉ mục toàn bộ 700+ Skill cục bộ**: Quét tất cả `SKILL.md` trong `~/.gemini/config/skills/`, `~/.gemini/config/plugins/*/skills/`, `~/.gemini/antigravity/builtin/skills/` và skill trong workspace — giúp agent tìm đúng skill dù danh sách trong system prompt bị cắt bởi giới hạn context budget.
- **Tìm kiếm song ngữ Việt – Anh**: Chuẩn hóa dấu tiếng Việt (`strip_accents`), ánh xạ đồng nghĩa từ các cụm từ tiếng Việt phổ biến sang từ khóa kỹ thuật tiếng Anh (`VI_TO_EN_SYNONYMS`) và xếp hạng theo trọng số IDF.
- **Tư vấn Model Antigravity + Điều phối XAI247**: Đánh giá độ phức tạp (`trivial`, `standard`, `complex`, `massive`), xét mức quota còn lại (`quota_percent`), gợi ý model phù hợp trong Antigravity lẫn khi nào nên đẩy việc nặng sang `xai247` / `claude -p` / `codex exec`.
- **Chiến lược Đội hình & Slash Commands**: Đề xuất rõ khi nào chỉ cần làm trực tiếp (`single`), gom batch qua `py_exec` (`code_mode`), gọi `subagent`, hay bung đội quân `swarm` (kèm gợi ý các vai trò cụ thể) và slash command tương ứng (`/plan`, `/teamwork`, `/boost`, `/browser`, `/goal`).
- **Tự động cho việc vừa & lớn**: Câu hỏi nhanh / sửa nhỏ làm thẳng luôn; việc vừa & lớn hiển thị **Bảng Gợi Ý Chiến Lược** và chờ bạn chốt trước khi chạy.

## 🧩 Các MCP Tool

| Tool | Công dụng |
|---|---|
| `advise_task` | Phân tích prompt, đánh giá độ phức tạp, tìm top skills, gợi ý Model (Antigravity + XAI247), Đội hình và Slash Commands |
| `search_skills` | Tìm kiếm skill trong toàn bộ kho `SKILL.md` cục bộ (hỗ trợ tiếng Việt & tiếng Anh) |
| `refresh_skill_index` | Ép làm mới chỉ mục skill ngay lập tức (hữu ích sau khi mới cài thêm skill/plugin) |

## 🚀 Cài đặt vào Antigravity

Yêu cầu **Python 3.8+**. Chạy lệnh sau trong thư mục dự án:

```powershell
# Xem trước cấu hình sẽ thay đổi (dry-run)
python install_antigravity.py

# Cài đặt thật (tự động backup .bak-* trước khi sửa config)
python install_antigravity.py --write
```

*(Có thể thêm `--no-plugin` nếu chỉ muốn cài MCP server mà không cài rule tự động vào `~/.gemini/config/plugins/task-advisor`.)*

Sau khi cài xong, **khởi động lại Antigravity** để nạp MCP server `task-advisor` và plugin rules.

## 🧪 Chạy kiểm thử

```powershell
python -u test_client.py
```

Kiểm thử bao gồm: phân tích YAML multiline/non-frontmatter trên kho skill thật, tìm kiếm tiếng Việt có dấu & không dấu, chấm điểm chiến lược `router.advise_task`, và kiểm thử end-to-end giao thức MCP stdio JSON-RPC 2.0.
