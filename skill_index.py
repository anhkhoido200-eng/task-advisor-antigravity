#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Bộ lập chỉ mục và tìm kiếm song ngữ Việt-Anh cho kho SKILL.md cục bộ."""
import glob
import math
import os
import re
import time
import unicodedata

_STOPWORDS = frozenset({
    # Tiếng Anh cơ bản
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "at", "by",
    "with", "from", "as", "is", "are", "was", "were", "be", "been", "this",
    "that", "it", "its", "you", "your", "when", "where", "how", "what", "who",
    "use", "using", "used", "can", "will", "should", "must", "into", "about",
    # Tiếng Việt không dấu cơ bản
    "va", "la", "cua", "cho", "voi", "trong", "ngoai", "nhu", "de", "khi",
    "nao", "sao", "gi", "co", "khong", "duoc", "nhung", "cac", "mot", "hai",
    "nay", "do", "toi", "minh", "ban", "em", "anh", "chi", "giup", "hay",
    "nen", "can", "muon", "lam", "bang", "qua", "ve", "tu", "den", "thi",
    "ma", "neu", "boi", "vi", "da", "dang", "se", "roi", "nhe", "a", "nha",
})

# Ánh xạ cụm từ tiếng Việt (không dấu) sang từ khóa kỹ thuật tiếng Anh.
VI_TO_EN_SYNONYMS = (
    (("giao dien", "lam dep", "thiet ke web", "mau sac", "bo cuc"),
     ("ui", "ux", "frontend", "design", "styling", "tailwind")),
    (("tailwind", "css", "design system"),
     ("tailwind", "design", "system", "styling", "ui")),
    (("sua loi", "bat loi", "tim loi", "chua loi", "loi gi", "nguyen nhan loi", "bi loi", "crash", "treo"),
     ("debug", "debugging", "systematic", "error", "trace", "diagnostic", "fix", "troubleshoot")),
    (("khong ro nguyen nhan", "dieu tra loi", "phan tich loi", "stack trace"),
     ("systematic", "debugging", "debugger", "error", "analysis", "detective", "trace")),
    (("len ke hoach", "ke hoach", "kien truc", "thiet ke he thong", "phan ra", "lo trinh"),
     ("plan", "planning", "architecture", "architect", "design", "patterns", "brainstorming")),
    (("kiem thu", "viet test", "unit test", "chay test", "test tu dong"),
     ("test", "testing", "pytest", "vitest", "unit", "tdd")),
    (("trinh duyet", "playwright", "chrome", "devtools", "bam nut", "localhost", "kiem tra trang"),
     ("browser", "playwright", "webapp", "chrome", "devtools", "e2e")),
    (("co so du lieu", "csdl", "du lieu quan he", "bang du lieu", "truy van"),
     ("database", "sql", "postgresql", "schema", "query", "migration", "optimizer")),
    (("postgres", "postgresql"),
     ("postgresql", "sql", "database", "schema", "indexing")),
    (("migration", "chuyen doi bang", "nang cap db"),
     ("migration", "migrations", "database", "sql", "schema")),
    (("dang nhap", "xac thuc", "login", "oauth", "jwt", "session"),
     ("auth", "authentication", "login", "oauth", "jwt")),
    (("bao mat", "lo hong", "phan quyen", "mat khau", "bi mat", "xss", "sast"),
     ("security", "xss", "sast", "audit", "hardening", "secrets")),
    (("trien khai", "len mang", "dua len server", "cicd", "ci cd", "ong dan"),
     ("deploy", "deployment", "cicd", "vercel", "cloudflare", "netlify", "railway", "docker", "github")),
    (("hieu nang", "toc do", "bi cham", "toi uu", "nang ne", "bo nho", "cache"),
     ("performance", "optimization", "optimize", "caching", "cache", "bundle", "latency", "profiling")),
    (("api", "backend", "may chu", "dich vu nen", "diem cuoi"),
     ("backend", "api", "fastapi", "nodejs", "graphql", "microservices", "rest", "openapi")),
    (("react", "nextjs", "next js", "trang thai"),
     ("react", "nextjs", "state", "management", "frontend", "patterns")),
    (("python", "pip", "uv", "dong goi python", "bat dong bo"),
     ("python", "fastapi", "pytest", "async", "packaging", "uv")),
    (("typescript", "javascript", "node", "nodejs"),
     ("typescript", "javascript", "nodejs", "patterns", "async")),
    (("ai", "tri tue nhan tao", "agent", "tro ly ao", "prompt", "chatbot"),
     ("ai", "agent", "llm", "prompt", "langchain", "assistant", "gemini", "sdk")),
    (("rag", "vector", "nhung van ban", "tim kiem ngu nghia"),
     ("rag", "vector", "embedding", "similarity", "hybrid", "search")),
    (("mcp", "model context protocol", "ket noi tool"),
     ("mcp", "builder", "server", "app")),
    (("du lieu lon", "xu ly du lieu", "phan tich du lieu"),
     ("data", "pipeline", "etl", "bigquery", "spark", "analytics")),
    (("excel", "bang tinh", "csv"),
     ("xlsx", "csv", "spreadsheet")),
    (("pdf",),
     ("pdf",)),
    (("word", "docx"),
     ("docx",)),
    (("thuyet trinh", "slide", "slides", "powerpoint", "pptx"),
     ("slides", "pptx", "presentation", "storytelling")),
    (("git", "pull request", "review code", "merge", "nhanh git", "worktree"),
     ("git", "pr", "review", "branch", "worktrees", "workflow", "diff")),
    (("tai cau truc", "don code", "code sach", "no ky thuat", "don dep"),
     ("refactor", "refactoring", "cleanup", "tech", "debt", "clean")),
    (("seo", "bai viet", "viet bai", "tiep thi", "thuong hieu", "noi dung"),
     ("seo", "content", "marketing", "brand", "meta", "keyword")),
    (("eeat", "uy tin seo"),
     ("seo", "authority", "eeat", "audit", "content")),
    (("doi quan", "swarm", "song song", "nhieu agent", "chia viec"),
     ("swarm", "parallel", "agents", "dispatching", "subagent", "orchestration")),
    (("di dong", "dien thoai", "app mobile", "ung dung di dong"),
     ("mobile", "ios", "android", "flutter", "react", "native", "xcode")),
    (("thanh toan", "cong thanh toan", "hoa don", "goi cuoc"),
     ("payment", "stripe", "paypal", "billing", "pci", "checkout")),
    (("tao skill", "viet skill", "cai dat skill", "luong cong viec"),
     ("skill", "creator", "writing", "skills", "workflow")),
    (("tai lieu", "so do", "bieu do kien truc", "ve so do"),
     ("documentation", "docs", "diagram", "mermaid", "c4", "architecture")),
    (("sinh hoc", "hoa hoc", "phan tu", "protein", "gen", "bai bao khoa hoc"),
     ("biology", "chemistry", "protein", "genomics", "pubchem", "pdb", "literature", "science")),
    (("giam sat", "log", "theo doi loi", "canh bao", "observability"),
     ("observability", "monitoring", "logging", "tracing", "prometheus", "grafana", "slo")),
    (("container", "kubernetes", "k8s", "ha tang", "terraform", "dam may"),
     ("kubernetes", "k8s", "helm", "terraform", "cloud", "infrastructure", "mesh")),
    (("cloudflare", "worker", "durable object", "turnstile"),
     ("cloudflare", "workers", "durable", "objects", "turnstile")),
    (("firebase", "firestore", "cloud storage"),
     ("firebase", "firestore", "auth", "hosting", "rules")),
    (("vercel", "ai sdk", "workflow"),
     ("vercel", "deployments", "ai", "sdk", "workflow", "cdn")),
    (("databricks", "spark", "delta", "lakehouse"),
     ("databricks", "spark", "lakehouse", "pipelines", "unity")),
    (("truy cap mu", "nguoi khuyet tat", "doc man hinh"),
     ("accessibility", "wcag", "a11y", "screen", "reader")),
    (("thoi gian thuc", "hang doi", "su kien"),
     ("event", "queue", "queues", "cqrs", "saga", "streaming")),
    (("huan luyen mo hinh", "mlops", "machine learning"),
     ("ml", "mlops", "pipeline", "training", "evaluation")),
)

_META_SKILLS = frozenset({
    "using-superpowers",
    "academy-guide",
    "antigravity-guide",
    "diagnosing-superpowers",
})

# Ánh xạ vendor/nền tảng cụ thể: phạt điểm nếu skill gắn vendor mà user không nhắc tới
_VENDOR_RULES = (
    (("firebase",), ("firebase",), frozenset({"firebase", "firestore"})),
    (("databricks",), ("databricks",), frozenset({"databricks", "spark", "lakehouse", "dabs", "dbsql", "delta", "unity"})),
    (("cloudflare", "wrangler", "turnstile", "durable"), ("cloudflare",), frozenset({"cloudflare", "wrangler", "workers", "durable", "turnstile"})),
    (("netlify",), ("netlify",), frozenset({"netlify"})),
    (("vercel",), ("vercel-plugin", "vercel"), frozenset({"vercel"})),
    (("wix",), ("wix",), frozenset({"wix"})),
    (("wordpress",), ("wordpress",), frozenset({"wordpress", "wp"})),
    (("dt", "dynatrace"), ("dynatrace",), frozenset({"dynatrace", "dt"})),
    (("temporal",), (), frozenset({"temporal"})),
    (("canva",), ("canva",), frozenset({"canva"})),
    (("bigin",), ("zoho-bigin",), frozenset({"bigin", "zoho", "crm"})),
    (("auth0",), ("auth0",), frozenset({"auth0"})),
    (("stripe",), ("stripe",), frozenset({"stripe"})),
    (("paypal",), (), frozenset({"paypal"})),
    (("crowdstrike",), ("crowdstrike",), frozenset({"crowdstrike"})),
    (("intercom",), ("intercom",), frozenset({"intercom"})),
    (("base44",), ("base44",), frozenset({"base44"})),
    (("railway", "use-railway"), ("railway",), frozenset({"railway"})),
    (("semrush",), ("semrush",), frozenset({"semrush"})),
    (("coderabbit",), ("coderabbit",), frozenset({"coderabbit"})),
)

_TECH_REPLACEMENTS = (
    (re.compile(r"\bnext\.js\b", re.I), "nextjs"),
    (re.compile(r"\bnode\.js\b", re.I), "nodejs"),
    (re.compile(r"\bvue\.js\b", re.I), "vuejs"),
    (re.compile(r"\bnuxt\.js\b", re.I), "nuxtjs"),
    (re.compile(r"\bexpress\.js\b", re.I), "expressjs"),
    (re.compile(r"\bnest\.js\b", re.I), "nestjs"),
    (re.compile(r"\bthree\.js\b", re.I), "threejs"),
    (re.compile(r"\bchart\.js\b", re.I), "chartjs"),
    (re.compile(r"(?<![a-z0-9])c\+\+(?![a-z0-9])", re.I), "cpp"),
    (re.compile(r"(?<![a-z0-9])c#(?![a-z0-9])", re.I), "csharp"),
    (re.compile(r"(?<![a-z0-9])\.net\b", re.I), "dotnet"),
    (re.compile(r"\bci/cd\b", re.I), "cicd"),
    (re.compile(r"\be-e-a-t\b", re.I), "eeat"),
    (re.compile(r"\ba/b\b", re.I), "ab"),
    (re.compile(r"\breact\s+native\b", re.I), "react-native"),
)

_CACHE_TTL = 60.0
_MAX_READ_BYTES = 16384


def strip_accents(text):
    """Chuẩn hóa chuỗi tiếng Việt về dạng không dấu, giữ nguyên chữ Latin/số."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def normalize_tech_terms(text):
    """Chuẩn hóa tên công nghệ có dấu chấm/ký hiệu đặc biệt trước khi tách từ."""
    if not text:
        return ""
    res = text
    for pattern, repl in _TECH_REPLACEMENTS:
        res = pattern.sub(repl, res)
    return res


def tokenize(text):
    """Tách văn bản đã chuẩn hóa thành danh sách token chữ cái/số loại bỏ stopwords."""
    norm = normalize_tech_terms(strip_accents(text).lower())
    return [tok for tok in re.findall(r"[a-z0-9]+", norm) if tok not in _STOPWORDS and (len(tok) > 1 or tok.isdigit())]


def expand_query_terms(query):
    """Tách token trực tiếp từ query và mở rộng thêm từ khóa tiếng Anh từ tiếng Việt."""
    norm_query = normalize_tech_terms(strip_accents(query).lower())
    direct_terms = set(tokenize(norm_query))
    expanded_terms = set()

    for vi_phrases, en_words in VI_TO_EN_SYNONYMS:
        matched = False
        for phrase in vi_phrases:
            # Khớp cụm từ nguyên vẹn theo ranh giới ký tự chữ/số
            pattern = r"(?:^|[^a-z0-9])" + re.escape(phrase) + r"(?:$|[^a-z0-9])"
            if re.search(pattern, norm_query):
                matched = True
                break
        if matched:
            for word in en_words:
                if word not in direct_terms:
                    expanded_terms.add(word)

    return direct_terms, expanded_terms


def _clean_scalar(raw_value):
    """Loại bỏ dấu nháy bao quanh và gom khoảng trắng thừa của scalar YAML."""
    val = raw_value.strip()
    if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
        val = val[1:-1]
    return " ".join(val.split())


def _parse_frontmatter(frontmatter):
    """Phân tích nhẹ frontmatter YAML hỗ trợ cả scalar một dòng và multiline (> / |)."""
    lines = frontmatter.splitlines()
    name = ""
    desc_parts = []
    i = 0
    while i < len(lines):
        line = lines[i]
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not key_match:
            i += 1
            continue
        key = key_match.group(1).lower()
        rest = key_match.group(2).strip()
        if key == "name" and rest:
            name = _clean_scalar(rest)
            i += 1
            continue
        if key == "description":
            is_block = rest in (">", "|", ">-", "|-", ">+", "|+") or not rest
            if not is_block and rest:
                desc_parts.append(_clean_scalar(rest))
            i += 1
            # Thu thập các dòng thụt lề thuộc description multiline hoặc plain scalar nhiều dòng
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    i += 1
                    continue
                if nxt[0] in (" ", "\t"):
                    desc_parts.append(nxt.strip())
                    i += 1
                    continue
                break
            continue
        i += 1
    return name, " ".join(p for p in desc_parts if p).strip()


def _extract_body_fallback(body, max_chars=300):
    """Trích heading đầu và đoạn văn mở đầu khi SKILL.md thiếu frontmatter description."""
    lines = body.splitlines()
    collected = []
    for line in lines:
        s = line.strip()
        if not s:
            if collected:
                break
            continue
        if s.startswith("<!--") or s.startswith("```"):
            continue
        s = re.sub(r"^#{1,6}\s+", "", s)
        collected.append(s)
        if sum(len(x) for x in collected) >= max_chars:
            break
    text = " ".join(collected).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return text


def parse_skill_file(path, source, priority=2):
    """Đọc và trích xuất metadata tìm kiếm từ một tệp SKILL.md."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(_MAX_READ_BYTES)
        text = raw.decode("utf-8", errors="replace")
    except OSError:
        return None

    fallback_name = os.path.basename(os.path.dirname(path))
    name = ""
    description = ""
    body = text

    fm_match = re.match(r"^---\s*\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if fm_match:
        name, description = _parse_frontmatter(fm_match.group(1))
        body = text[fm_match.end():]

    if not name:
        name = fallback_name
    if not description:
        description = _extract_body_fallback(body)

    headings = []
    for hm in re.finditer(r"^#{1,3}\s+(.+)$", body, re.M):
        h = hm.group(1).strip()
        if h:
            headings.append(h)
        if len(headings) >= 8:
            break

    name_tokens = set(tokenize(name))
    desc_tokens = set(tokenize(description))
    heading_tokens = set(tokenize(" ".join(headings)))
    all_tokens = name_tokens | desc_tokens | heading_tokens

    return {
        "name": name,
        "source": source,
        "priority": priority,
        "path": os.path.abspath(path),
        "description": description,
        "name_tokens": name_tokens,
        "desc_tokens": desc_tokens,
        "heading_tokens": heading_tokens,
        "all_tokens": all_tokens,
    }


def _default_scan_specs(workspace_dir=None):
    """Tạo danh sách (source_label, priority, glob_pattern) mặc định theo thứ tự ưu tiên."""
    home = os.path.expanduser("~")
    specs = []
    if workspace_dir and os.path.isdir(workspace_dir):
        specs.append(("workspace", 1, os.path.join(workspace_dir, ".agent", "skills", "*", "SKILL.md")))
        specs.append(("workspace", 1, os.path.join(workspace_dir, ".gemini", "skills", "*", "SKILL.md")))
    specs.append(("global", 2, os.path.join(home, ".gemini", "config", "skills", "*", "SKILL.md")))
    specs.append(("plugin_glob", 3, os.path.join(home, ".gemini", "config", "plugins", "*", "skills", "*", "SKILL.md")))
    specs.append(("builtin", 4, os.path.join(home, ".gemini", "antigravity", "builtin", "skills", "*", "SKILL.md")))
    return specs


class SkillIndex:
    """Chỉ mục bộ nhớ các skill cục bộ kèm tìm kiếm IDF song ngữ và cache TTL."""

    def __init__(self, roots=None, ttl=_CACHE_TTL):
        self.roots = roots
        self.ttl = ttl
        self._records = []
        self._idf = {}
        self._built_at = 0.0
        self._last_workspace = None
        self._source_counts = {}
        self._last_elapsed_ms = 0

    def _collect_records(self, workspace_dir=None):
        by_name = {}
        if self.roots is not None:
            specs = [("custom", 1, os.path.join(root, "*", "SKILL.md")) for root in self.roots]
            # Hỗ trợ trường hợp truyền thẳng thư mục chứa SKILL.md hoặc thư mục cha
            direct_files = [os.path.join(root, "SKILL.md") for root in self.roots if os.path.isfile(os.path.join(root, "SKILL.md"))]
        else:
            specs = _default_scan_specs(workspace_dir)
            direct_files = []

        candidates = []
        for source, priority, pattern in specs:
            for path in sorted(glob.glob(pattern)):
                label = source
                if source == "plugin_glob":
                    # Lấy tên thư mục plugin làm nhãn nguồn: plugin:<name>
                    parts = os.path.normpath(path).split(os.sep)
                    try:
                        p_idx = parts.index("plugins")
                        label = "plugin:" + parts[p_idx + 1]
                    except (ValueError, IndexError):
                        label = "plugin"
                candidates.append((path, label, priority))

        for path in direct_files:
            candidates.append((path, "custom", 1))

        for path, label, priority in candidates:
            rec = parse_skill_file(path, label, priority)
            if rec is None:
                continue
            key = rec["name"].lower()
            existing = by_name.get(key)
            if existing is None:
                by_name[key] = rec
                continue
            # Giữ bản có priority cao hơn (số nhỏ hơn); nếu bản mới có mô tả dài hơn nhiều thì bổ sung mô tả
            if priority < existing["priority"]:
                if len(existing["description"]) > 1.5 * max(1, len(rec["description"])):
                    rec["description"] = existing["description"]
                    rec["desc_tokens"] = existing["desc_tokens"]
                    rec["all_tokens"] = rec["name_tokens"] | rec["desc_tokens"] | rec["heading_tokens"]
                by_name[key] = rec
            elif len(rec["description"]) > 1.5 * max(1, len(existing["description"])):
                existing["description"] = rec["description"]
                existing["desc_tokens"] = rec["desc_tokens"]
                existing["all_tokens"] = existing["name_tokens"] | existing["desc_tokens"] | existing["heading_tokens"]

        records = list(by_name.values())
        df = {}
        for rec in records:
            for tok in rec["all_tokens"]:
                df[tok] = df.get(tok, 0) + 1
        total_docs = len(records)
        idf = {tok: math.log((total_docs + 1.0) / (count + 1.0)) + 1.0 for tok, count in df.items()}

        source_counts = {}
        for rec in records:
            src = rec["source"].split(":")[0]
            source_counts[src] = source_counts.get(src, 0) + 1

        return records, idf, source_counts

    def ensure_loaded(self, workspace_dir=None):
        """Đảm bảo chỉ mục đã nạp và còn hạn cache."""
        norm_ws = os.path.abspath(workspace_dir) if workspace_dir and os.path.isdir(workspace_dir) else None
        now = time.monotonic()
        expired = (now - self._built_at) > self.ttl
        ws_changed = norm_ws != self._last_workspace
        if not self._records or expired or ws_changed:
            return self.refresh(norm_ws)
        return self.stats()

    def refresh(self, workspace_dir=None):
        """Ép quét lại toàn bộ tệp SKILL.md và tính lại IDF."""
        start = time.perf_counter()
        norm_ws = os.path.abspath(workspace_dir) if workspace_dir and os.path.isdir(workspace_dir) else None
        records, idf, source_counts = self._collect_records(norm_ws)
        self._records = records
        self._idf = idf
        self._source_counts = source_counts
        self._last_workspace = norm_ws
        self._built_at = time.monotonic()
        self._last_elapsed_ms = int((time.perf_counter() - start) * 1000)
        return self.stats()

    def stats(self):
        """Trả về thông tin thống kê chỉ mục hiện tại."""
        return {
            "total_skills": len(self._records),
            "sources": dict(self._source_counts),
            "elapsed_ms": self._last_elapsed_ms,
        }

    @staticmethod
    def _is_vendor_mismatch(skill_name_low, source, direct_terms):
        """Kiểm tra skill có gắn chặt với vendor/nền tảng mà câu truy vấn không nhắc đến hay không."""
        plugin_name = source[7:] if source.startswith("plugin:") else ""
        for prefixes, plugins, triggers in _VENDOR_RULES:
            matches_name = any(
                skill_name_low == p
                or skill_name_low.startswith(p + "-")
                or skill_name_low.startswith(p + "_")
                for p in prefixes
            )
            matches_plugin = bool(plugin_name) and plugin_name in plugins
            if matches_name or matches_plugin:
                if not (triggers & direct_terms):
                    return True
        return False

    def search(self, query, limit=8, workspace_dir=None):
        """Tìm kiếm top skill phù hợp với câu truy vấn tiếng Việt hoặc tiếng Anh."""
        if not query or not str(query).strip():
            return []
        self.ensure_loaded(workspace_dir)

        norm_query = normalize_tech_terms(strip_accents(query).lower())
        direct_terms, expanded_terms = expand_query_terms(query)
        if not direct_terms and not expanded_terms:
            return []

        results = []
        for rec in self._records:
            score = 0.0
            skill_name_low = rec["name"].lower()
            spaced_name = skill_name_low.replace("-", " ").replace("_", " ")

            # Khớp chính xác tên skill trong câu truy vấn
            if re.search(r"(?:^|[^a-z0-9])" + re.escape(skill_name_low) + r"(?:$|[^a-z0-9])", norm_query):
                score += 14.0
            elif spaced_name != skill_name_low and re.search(
                r"(?:^|[^a-z0-9])" + re.escape(spaced_name) + r"(?:$|[^a-z0-9])", norm_query
            ):
                score += 14.0

            direct_hits = 0
            for tok in direct_terms:
                w = self._idf.get(tok, 1.0)
                if tok in rec["name_tokens"]:
                    score += 3.2 * w
                    direct_hits += 1
                elif tok in rec["desc_tokens"]:
                    score += 1.4 * w
                    direct_hits += 1
                elif tok in rec["heading_tokens"]:
                    score += 0.6 * w
                    direct_hits += 1

            if direct_hits >= 2:
                score += 3.0

            for tok in expanded_terms:
                w = self._idf.get(tok, 1.0) * 0.50
                if tok in rec["name_tokens"]:
                    score += 3.0 * w
                elif tok in rec["desc_tokens"]:
                    score += 1.4 * w
                elif tok in rec["heading_tokens"]:
                    score += 0.6 * w

            # Giảm điểm các meta-skill quá chung chung trừ khi người dùng nhắc tên chúng
            if skill_name_low in _META_SKILLS:
                if not any(part in direct_terms for part in skill_name_low.split("-")):
                    score *= 0.35

            # Giảm điểm skill gắn vendor/nền tảng cụ thể khi người dùng không nhắc tên nền tảng đó
            if self._is_vendor_mismatch(skill_name_low, rec["source"], direct_terms):
                score *= 0.38

            if score >= 1.5:
                desc = rec["description"]
                if len(desc) > 240:
                    desc = desc[:237].rstrip() + "..."
                results.append({
                    "name": rec["name"],
                    "score": round(score, 2),
                    "source": rec["source"],
                    "priority": rec["priority"],
                    "path": rec["path"],
                    "description": desc,
                })

        results.sort(key=lambda item: (-item["score"], item["priority"], item["name"].lower()))
        trimmed = results[: max(1, min(int(limit), 20))]
        for item in trimmed:
            item.pop("priority", None)
        return trimmed
