#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Bộ phân tích độ phức tạp công việc và đề xuất Model, Skill, Swarm/XAI247, Slash Command."""
import os
import re
import shutil

from skill_index import strip_accents

_XAI247_DEFAULT_MODELS = [
    "xai247/gpt-6-luna",
    "xai247/gpt-6.1-sol",
    "xai247/gpt-6.1-terra",
]

_CLI_CACHE = None

# Ánh xạ domain -> danh sách cụm từ nhận diện (đã bỏ dấu)
_DOMAIN_RULES = (
    ("frontend_ui", (
        "frontend", "giao dien", "ui", "ux", "tailwind", "css", "html", "react",
        "nextjs", "next.js", "vue", "angular", "component", "landing page",
        "lam dep", "thiet ke web", "trang web", "responsive", "layout",
    )),
    ("backend_api", (
        "backend", "api", "fastapi", "express", "nestjs", "django", "flask",
        "graphql", "rest", "microservice", "microservices", "server", "endpoint",
        "webhook", "websocket", "mcp server",
    )),
    ("database", (
        "database", "co so du lieu", "csdl", "postgres", "postgresql", "mysql",
        "sqlite", "mongodb", "supabase", "prisma", "sql", "schema", "migration",
        "bigquery", "firestore",
    )),
    ("testing_qa", (
        "test", "testing", "unit test", "e2e", "pytest", "vitest", "jest",
        "kiem thu", "playwright", "tdd", "qa", "verification", "benchmark",
    )),
    ("devops_deploy", (
        "deploy", "trien khai", "vercel", "cloudflare", "netlify", "railway",
        "docker", "kubernetes", "k8s", "helm", "terraform", "ci cd", "ci/cd",
        "github actions", "pipeline",
    )),
    ("security", (
        "security", "bao mat", "auth", "authentication", "authorization",
        "dang nhap", "phan quyen", "oauth", "jwt", "xss", "csrf", "sast",
        "lo hong", "secrets", "hardening", "pci",
    )),
    ("debugging", (
        "debug", "sua loi", "bat loi", "tim loi", "chua loi", "bug", "crash",
        "treo", "trace", "stack trace", "incident", "khong hoat dong", "bi loi",
        "khong ro nguyen nhan",
    )),
    ("architecture_plan", (
        "kien truc", "architecture", "len ke hoach", "ke hoach", "thiet ke he thong",
        "roadmap", "tu dau", "from scratch", "full-stack", "fullstack", "system design",
    )),
    ("data_batch", (
        "csv", "json", "xlsx", "excel", "pdf", "docx", "pptx", "log", "logs",
        "nhieu file", "tat ca file", "hang loat", "batch", "phan tich du lieu",
        "etl", "spark", "databricks",
    )),
    ("browser_web", (
        "trinh duyet", "browser", "playwright", "click", "dang nhap web",
        "mo trang", "localhost", "web app", "cao du lieu web", "scrape",
    )),
    ("docs_diagram", (
        "tai lieu", "readme", "so do", "mermaid", "c4", "diagram", "thuyet trinh",
        "slide", "slides", "bao cao", "onboarding",
    )),
    ("ai_agent", (
        "ai", "llm", "agent", "langchain", "rag", "vector", "embedding",
        "prompt", "gemini", "chatbot", "mcp", "multi-agent",
    )),
    ("refactor_cleanup", (
        "refactor", "tai cau truc", "don code", "no ky thuat", "tech debt",
        "clean", "viet lai", "dai tu", "chuan hoa",
    )),
    ("mobile", (
        "mobile", "ios", "android", "flutter", "react native", "xcode", "swift",
    )),
)

_HEAVY_GROUPS = (
    ("tu dau", "from scratch", "full-stack", "fullstack"),
    ("kien truc", "architecture", "dai tu", "viet lai"),
    ("refactor lon", "toan bo codebase", "toan du an", "audit toan bo"),
    ("migration", "he thong"),
    ("multi-agent", "doi quan", "swarm", "song song", "parallel"),
)

_MEDIUM_GROUPS = (
    ("tinh nang", "feature", "tich hop", "integrate"),
    ("debug", "sua loi", "toi uu", "optimize"),
    ("bao mat", "security", "deploy", "trien khai"),
    ("review", "viet tool", "mcp server", "xay dung", "build", "tao app", "tao web"),
)

_BATCH_PHRASES = ("nhieu file", "tat ca file", "hang loat", "csv", "json", "log", "logs", "sqlite", "batch")
_TRIVIAL_PHRASES = ("la gi", "giai thich", "chay thu", "duoc khong", "co phai", "hoi chut", "typo", "chinh ta")


def _contains_phrase(norm_text, phrase):
    """Kiểm tra cụm từ khớp theo ranh giới ký tự chữ/số để tránh trùng một phần từ."""
    pattern = r"(?:^|[^a-z0-9])" + re.escape(phrase) + r"(?:$|[^a-z0-9])"
    return bool(re.search(pattern, norm_text))


def _has_any(norm_text, phrases):
    return any(_contains_phrase(norm_text, p) for p in phrases)


def detect_external_clis():
    """Kiểm tra sự sẵn sàng của các CLI điều phối (xai247, claude, codex)."""
    global _CLI_CACHE
    if _CLI_CACHE is not None:
        return dict(_CLI_CACHE)

    local_app = os.environ.get("LOCALAPPDATA", "")
    xai_fallback = os.path.join(local_app, "xai247", "bin", "xai247.cmd") if local_app else ""
    has_xai = bool(shutil.which("xai247")) or (bool(xai_fallback) and os.path.isfile(xai_fallback))
    has_claude = bool(shutil.which("claude"))
    has_codex = bool(shutil.which("codex"))

    _CLI_CACHE = {
        "xai247": has_xai,
        "claude": has_claude,
        "codex": has_codex,
        "xai247_models": list(_XAI247_DEFAULT_MODELS) if has_xai else [],
    }
    return dict(_CLI_CACHE)


def detect_domains(norm_prompt):
    """Phát hiện các mảng kỹ thuật độc lập có trong yêu cầu."""
    found = []
    for domain, phrases in _DOMAIN_RULES:
        if _has_any(norm_prompt, phrases):
            found.append(domain)
    return found


def classify_complexity(prompt, norm_prompt, domains, files_count=None):
    """Chấm điểm độ phức tạp và phân loại thành trivial / standard / complex / massive."""
    score = 0
    if len(domains) >= 2:
        score += len(domains) * 2 - 1
    elif len(domains) == 1:
        score += 1

    heavy_hits = sum(1 for grp in _HEAVY_GROUPS if _has_any(norm_prompt, grp))
    score += min(6, heavy_hits * 3)

    medium_hits = sum(1 for grp in _MEDIUM_GROUPS if _has_any(norm_prompt, grp))
    score += min(4, medium_hits * 2)

    if _has_any(norm_prompt, _BATCH_PHRASES):
        score += 2

    if files_count is not None:
        if files_count >= 10:
            score += 5
        elif files_count >= 4:
            score += 3
        elif files_count >= 2:
            score += 1

    words = re.findall(r"\S+", prompt.strip())
    bullet_lines = len(re.findall(r"(?m)^\s*(?:[-*]|\d+[.)])\s+", prompt))
    if bullet_lines >= 3 or len(words) >= 45:
        score += 2

    if heavy_hits == 0 and len(words) < 12 and _has_any(norm_prompt, _TRIVIAL_PHRASES):
        score -= 2

    if score <= 1:
        level = "trivial"
    elif score <= 4:
        level = "standard"
    elif score <= 7:
        level = "complex"
    else:
        level = "massive"
    return level, score


def recommend_models(complexity, domains, quota_percent=None, clis=None):
    """Đề xuất model trong Antigravity (có xét quota) và chiến lược đẩy sang XAI247."""
    clis = clis or detect_external_clis()
    low_quota = quota_percent is not None and quota_percent <= 35
    critical_quota = quota_percent is not None and quota_percent <= 30

    if complexity == "trivial":
        primary = "Gemini 3.8 Flash (Medium)"
        alternative = "Gemini 4 Hydrogen (Medium) nếu cần giải thích sâu hơn"
    elif complexity == "standard":
        if "frontend_ui" in domains or "refactor_cleanup" in domains:
            primary = "Claude Sonnet 5.5 (Medium/High)"
            alternative = "Gemini 4 Hydrogen (Medium) để tiết kiệm quota"
        elif "debugging" in domains or "architecture_plan" in domains:
            primary = "Gemini 4 Hydrogen (High)"
            alternative = "Gemini 3.8 Flash (High) nếu muốn phản hồi nhanh"
        else:
            primary = "Gemini 4 Hydrogen (Medium)"
            alternative = "Gemini 3.8 Flash (High) cho việc lặp lại nhẹ"
    elif complexity == "complex":
        if "frontend_ui" in domains and "architecture_plan" not in domains:
            primary = "Claude Sonnet 5.5 (High)"
            alternative = "Gemini 4 Neon (High) hoặc Gemini 4 Hydrogen (High)"
        else:
            primary = "Gemini 4 Neon (High)"
            alternative = "Claude Sonnet 5.5 (High) cho thiết kế UI/code dài"
    else:  # massive
        if "architecture_plan" in domains or "debugging" in domains:
            primary = "Gemini 4 Neon (XHigh)"
            alternative = "Claude Opus 5.5 (High) để đối chiếu kiến trúc"
        else:
            primary = "Claude Opus 5.5 (High)"
            alternative = "Gemini 4 Neon (XHigh) cho điều phối Swarm nhiều mảng"

    has_any_cli = clis.get("xai247") or clis.get("claude") or clis.get("codex")
    batch_or_heavy_work = (
        complexity in ("complex", "massive")
        or low_quota
        or any(d in domains for d in ("data_batch", "refactor_cleanup", "testing_qa"))
    )

    if not has_any_cli:
        xai_rec = "Máy chưa phát hiện CLI XAI247 / Claude Code / Codex; dùng trực tiếp model Antigravity ở trên."
    elif complexity == "trivial" and not low_quota:
        xai_rec = "Không cần đẩy XAI247 (Antigravity xử lý trực tiếp nhanh hơn)."
    elif batch_or_heavy_work:
        parts = []
        if clis.get("xai247"):
            if "debugging" in domains:
                parts.append('`xai247 run --agent debug -m "xai247/gpt-6.1-terra"` (điều tra & sửa lỗi sâu)')
            elif "architecture_plan" in domains:
                parts.append('`xai247 run --agent ask -m "xai247/gpt-6-luna"` (khảo sát codebase chỉ đọc)')
            else:
                parts.append('`xai247 run --agent code -m "xai247/gpt-6.1-sol"` (sinh/refactor nhiều tệp)')
        if clis.get("claude") and (complexity in ("complex", "massive") or "frontend_ui" in domains or "refactor_cleanup" in domains):
            parts.append("`claude -p` (khảo sát đa tệp / sinh component theo mẫu)")
        if clis.get("codex") and (complexity in ("complex", "massive") or "testing_qa" in domains or "debugging" in domains):
            parts.append("`codex exec` / `codex exec review --uncommitted --ephemeral` (viết test hàng loạt & review diff)")
        xai_rec = "Nên đẩy phần nặng qua XAI247 (Antigravity làm sếp kiểm diff): " + "; ".join(parts)
    else:
        xai_rec = 'Tùy chọn tiết kiệm token: có thể giao việc đọc/phân tích rộng cho `xai247 run --agent ask -m "xai247/gpt-6-luna"`.'

    quota_note = None
    if critical_quota:
        quota_note = (
            f"Cảnh báo quota Antigravity còn {quota_percent}% (<=30%): ưu tiên dùng model Flash/Medium để điều phối "
            "và đẩy các phần đọc rộng, refactor hoặc viết test sang gói XAI247."
        )
    elif low_quota:
        quota_note = f"Quota còn {quota_percent}%: cân nhắc đẩy bớt phần xử lý nhiều tệp sang XAI247 để giữ quota Antigravity."

    return {
        "antigravity_primary": primary,
        "antigravity_alternative": alternative,
        "xai247_recommendation": xai_rec,
        "quota_note": quota_note,
    }


def _build_swarm_roster(domains):
    """Sinh danh sách vai trò Swarm phù hợp theo các mảng kỹ thuật của tác vụ."""
    roster = []
    if any(d in domains for d in ("backend_api", "database", "security", "ai_agent")):
        roster.append({
            "role": "implementer-be",
            "workspace": "share",
            "reason": "Phụ trách backend/API, database và logic bảo mật độc lập.",
        })
    if any(d in domains for d in ("frontend_ui", "mobile", "docs_diagram")):
        roster.append({
            "role": "implementer-fe",
            "workspace": "share",
            "reason": "Phụ trách giao diện UI/UX hoặc tài liệu độc lập.",
        })
    if "devops_deploy" in domains:
        roster.append({
            "role": "devops-infra",
            "workspace": "share",
            "reason": "Cấu hình CI/CD, deploy hoặc hạ tầng tách biệt với code ứng dụng.",
        })
    if not roster:
        roster.append({
            "role": "worker-1",
            "workspace": "share",
            "reason": "Triển khai phần thay đổi chính trong workspace tách biệt.",
        })
        roster.append({
            "role": "worker-2",
            "workspace": "share",
            "reason": "Xử lý song song nhóm tệp / module độc lập thứ hai.",
        })
    roster.append({
        "role": "verifier",
        "workspace": "inherit",
        "reason": "Kiểm chứng độc lập: chạy test, lint, build và rà soát diff cuối.",
    })
    return roster


def recommend_execution_strategy(complexity, domains, norm_prompt, files_count=None):
    """Quyết định chiến lược thực thi: single / code_mode / subagent / swarm."""
    explicit_swarm = _has_any(norm_prompt, ("swarm", "doi quan", "song song", "teamwork", "nhieu agent"))
    build_domains = [d for d in domains if d not in ("data_batch", "docs_diagram")]
    is_pure_batch = "data_batch" in domains and len(build_domains) < 2

    many_files_edit = files_count is not None and files_count >= 8 and not is_pure_batch
    recommend_swarm = (
        explicit_swarm
        or many_files_edit
        or (complexity == "massive" and not is_pure_batch)
        or (complexity == "complex" and len(build_domains) >= 2)
    )

    if recommend_swarm:
        return {
            "mode": "swarm",
            "recommend_swarm": True,
            "reason": "Công việc trải rộng nhiều mảng độc lập hoặc nhiều tệp cần sửa song song, chia theo Swarm giúp làm nhanh và có verifier kiểm chéo.",
            "swarm_roster": _build_swarm_roster(domains),
            "subagent": None,
        }

    if is_pure_batch or (files_count is not None and files_count >= 3):
        return {
            "mode": "code_mode",
            "recommend_swarm": False,
            "reason": "Không cần mở Swarm (tránh overhead); dùng `py_exec` gom đọc/lọc nhiều tệp trong 1-2 lượt là nhanh và tiết kiệm nhất.",
            "swarm_roster": [],
            "subagent": None,
        }

    if "browser_web" in domains:
        return {
            "mode": "subagent",
            "recommend_swarm": False,
            "reason": "Không cần Swarm đầy đủ; giao thẳng cho subagent `browser` (model `flash`) thao tác giao diện web.",
            "swarm_roster": [],
            "subagent": {"name": "browser", "model": "flash"},
        }

    if _contains_phrase(norm_prompt, "review") and ("git" in norm_prompt or "pr" in norm_prompt or "code" in norm_prompt):
        return {
            "mode": "subagent",
            "recommend_swarm": False,
            "reason": "Không cần Swarm; có thể dùng subagent `code-reviewer` (hoặc `codex exec review`) để rà lỗi nhanh.",
            "swarm_roster": [],
            "subagent": {"name": "code-reviewer", "model": "inherit"},
        }

    if complexity == "complex":
        return {
            "mode": "subagent",
            "recommend_swarm": False,
            "reason": "Tác vụ tập trung 1 mảng: không cần Swarm, chỉ cần 1 subagent `research` khảo sát trước rồi triển khai tuần tự.",
            "swarm_roster": [],
            "subagent": {"name": "research", "model": "inherit"},
        }

    return {
        "mode": "single",
        "recommend_swarm": False,
        "reason": "Không cần Swarm hay subagent phụ (tránh độ trễ và tốn token điều phối); xử lý trực tiếp là tối ưu nhất.",
        "swarm_roster": [],
        "subagent": None,
    }


def recommend_slash_commands(complexity, domains, recommend_swarm, norm_prompt):
    """Đề xuất các slash command hữu ích nếu phù hợp với yêu cầu."""
    cmds = []
    if recommend_swarm:
        cmds.append("/teamwork — Khởi chạy đội ngũ agent phối hợp cho dự án nhiều mảng.")
    if "architecture_plan" in domains or complexity in ("complex", "massive"):
        cmds.append("/plan — Lập kế hoạch từng bước và rà soát trước khi sửa code.")
        if complexity == "massive" or _has_any(norm_prompt, ("thiet ke", "lua chon", "kien truc", "chua ro")):
            cmds.append("/grill-me — Phỏng vấn nhanh để chốt các quyết định thiết kế còn mở.")
    if complexity == "massive" or ("architecture_plan" in domains and "debugging" in domains):
        cmds.append("/boost — Bật chế độ suy nghĩ sâu, kiểm chứng nhiều góc độ cho bài toán khó.")
    if "browser_web" in domains:
        cmds.append("/browser — Tương tác và kiểm tra trực tiếp ứng dụng web trên trình duyệt.")
    if _has_any(norm_prompt, ("xuyen dem", "triet de", "chay dai", "den khi xong", "overnight")):
        cmds.append("/goal — Chạy bền bỉ không dừng giữa chừng tới khi hoàn thành mục tiêu.")
    return cmds


def _format_markdown(advice):
    """Tạo Bảng Gợi Ý Chiến Lược bằng tiếng Việt gọn, dễ đọc cho người dùng."""
    lines = ["### 🧭 Bảng Gợi Ý Chiến Lược Thực Thi", ""]
    domain_str = ", ".join(advice["domains"]) if advice["domains"] else "chung / tổng quát"
    lines.append(f"- **Độ phức tạp:** `{advice['complexity']}` (điểm: {advice['score']} | mảng: {domain_str})")

    models = advice["models"]
    lines.append(f"- **Model Antigravity gợi ý:** **{models['antigravity_primary']}** *(dự phòng: {models['antigravity_alternative']})*")
    lines.append(f"- **Điều phối XAI247:** {models['xai247_recommendation']}")
    if models.get("quota_note"):
        lines.append(f"- **Lưu ý Quota:** {models['quota_note']}")

    exe = advice["execution"]
    lines.append(f"- **Đội hình (`{exe['mode']}`):** {exe['reason']}")
    if exe["swarm_roster"]:
        roster_str = "; ".join(f"`{r['role']}` (`{r['workspace']}`: {r['reason']})" for r in exe["swarm_roster"])
        lines.append(f"  - *Đội hình Swarm đề xuất:* {roster_str}")
    elif exe.get("subagent"):
        sub = exe["subagent"]
        lines.append(f"  - *Subagent gợi ý:* `{sub['name']}` (model: `{sub['model']}`)")

    skills = advice["skills"]
    if skills:
        lines.append("- **Skill nên nạp (`SKILL.md`):**")
        for s in skills:
            lines.append(f"  - `{s['name']}` (score {s['score']}, nguồn `{s['source']}`): {s['description']} — `{s['path']}`")
    else:
        lines.append("- **Skill nên nạp:** Chưa có skill chuyên biệt khớp cao; có thể dùng `search_skills` với từ khóa tiếng Anh cụ thể hơn.")

    if advice["slash_commands"]:
        lines.append("- **Slash commands hữu ích:**")
        for c in advice["slash_commands"]:
            lines.append(f"  - {c}")

    if advice["should_pause_for_confirmation"]:
        lines.append("")
        lines.append("👉 **Chờ xác nhận:** Bạn chốt phương án trên (hoặc chọn model/hướng khác) rồi báo mình bắt đầu làm nhé!")
    return "\n".join(lines)


def advise_task(index, prompt, workspace_hint=None, quota_percent=None, files_count=None, force_panel=False):
    """Phân tích yêu cầu tổng thể và trả về chiến lược kèm bản trình bày Markdown."""
    if not prompt or not str(prompt).strip():
        raise ValueError("Missing required parameter 'prompt'.")

    norm_prompt = strip_accents(prompt).lower()
    domains = detect_domains(norm_prompt)
    complexity, score = classify_complexity(prompt, norm_prompt, domains, files_count=files_count)
    clis = detect_external_clis()
    models = recommend_models(complexity, domains, quota_percent=quota_percent, clis=clis)
    execution = recommend_execution_strategy(complexity, domains, norm_prompt, files_count=files_count)
    slash_commands = recommend_slash_commands(complexity, domains, execution["recommend_swarm"], norm_prompt)

    ws_dir = workspace_hint if workspace_hint and os.path.isdir(workspace_hint) else None
    skills = index.search(prompt, limit=5, workspace_dir=ws_dir)

    # Tự động cho việc vừa & lớn; việc nhẹ chỉ hiện bảng nếu được ép qua force_panel
    should_pause = bool(force_panel) or (complexity in ("standard", "complex", "massive"))

    advice = {
        "complexity": complexity,
        "score": score,
        "domains": domains,
        "should_pause_for_confirmation": should_pause,
        "models": models,
        "execution": execution,
        "skills": skills,
        "slash_commands": slash_commands,
        "clis": clis,
        "index_stats": index.stats(),
    }
    advice["formatted_markdown"] = _format_markdown(advice)
    return advice
