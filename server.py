#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Task Advisor Antigravity MCP server — tư vấn Model, Skill và Đội hình qua MCP stdio."""
import json
import os
import sys

from router import advise_task
from skill_index import SkillIndex

SERVER_NAME = "task-advisor-antigravity"
SERVER_VERSION = "1.0.0"
DEFAULT_PROTOCOL = "2025-06-18"

sys.stdout.reconfigure(encoding="utf-8", newline="\n")
sys.stdin.reconfigure(encoding="utf-8")

INDEX = SkillIndex()

TOOLS = [
    {
        "name": "advise_task",
        "description": (
            "Analyze a user task before execution: classify complexity, search 700+ local SKILL.md files "
            "(Vietnamese & English), recommend Antigravity model (considering quota) + XAI247 routing, "
            "decide whether Swarm/Subagent/Code Mode is needed, and suggest slash commands."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The user's request or task description to analyze.",
                },
                "workspace_hint": {
                    "type": "string",
                    "description": "Optional active workspace path to also scan project-local skills.",
                },
                "quota_percent": {
                    "type": "number",
                    "description": "Optional remaining Antigravity quota percentage (0-100).",
                },
                "files_count": {
                    "type": "integer",
                    "description": "Optional estimated number of files involved in the task.",
                },
                "force_panel": {
                    "type": "boolean",
                    "description": "If true, force presenting the confirmation strategy panel even for trivial tasks.",
                    "default": False,
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "search_skills",
        "description": (
            "Search across all locally installed SKILL.md files (global, plugins, builtin, and workspace) "
            "using Vietnamese or English keywords."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in Vietnamese or English.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-20, default 8).",
                    "default": 8,
                },
                "workspace_dir": {
                    "type": "string",
                    "description": "Optional workspace path to include workspace-local skills.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "refresh_skill_index",
        "description": "Force-rebuild the local SKILL.md index and return skill counts by source.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_dir": {
                    "type": "string",
                    "description": "Optional workspace path to include in the scan.",
                },
            },
        },
    },
]


def text_result(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}


def _parse_optional_float(val, min_v, max_v):
    if val is None or val == "":
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    return max(min_v, min(max_v, num))


def _parse_optional_int(val, min_v, max_v):
    if val is None or val == "":
        return None
    try:
        num = int(val)
    except (TypeError, ValueError):
        return None
    return max(min_v, min(max_v, num))


def do_advise_task(args):
    prompt = args.get("prompt") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return text_result("Missing required parameter 'prompt'.", True)

    workspace_hint = args.get("workspace_hint") or None
    if workspace_hint is not None and not isinstance(workspace_hint, str):
        workspace_hint = None
    quota_percent = _parse_optional_float(args.get("quota_percent"), 0.0, 100.0)
    files_count = _parse_optional_int(args.get("files_count"), 0, 100000)
    force_panel = bool(args.get("force_panel", False))

    advice = advise_task(
        INDEX,
        prompt=prompt,
        workspace_hint=workspace_hint,
        quota_percent=quota_percent,
        files_count=files_count,
        force_panel=force_panel,
    )
    summary_meta = {
        "complexity": advice["complexity"],
        "score": advice["score"],
        "should_pause_for_confirmation": advice["should_pause_for_confirmation"],
        "mode": advice["execution"]["mode"],
        "recommend_swarm": advice["execution"]["recommend_swarm"],
        "antigravity_primary": advice["models"]["antigravity_primary"],
        "skill_names": [s["name"] for s in advice["skills"]],
        "index_stats": advice["index_stats"],
    }
    output = (
        advice["formatted_markdown"]
        + "\n\n<task_advisor_meta>\n"
        + json.dumps(summary_meta, ensure_ascii=False, indent=2)
        + "\n</task_advisor_meta>"
    )
    return text_result(output, False)


def do_search_skills(args):
    query = args.get("query") or ""
    if not isinstance(query, str) or not query.strip():
        return text_result("Missing required parameter 'query'.", True)
    limit = _parse_optional_int(args.get("limit"), 1, 20) or 8
    workspace_dir = args.get("workspace_dir") or None
    if workspace_dir is not None and not isinstance(workspace_dir, str):
        workspace_dir = None

    hits = INDEX.search(query, limit=limit, workspace_dir=workspace_dir)
    if not hits:
        return text_result(f"Không tìm thấy skill phù hợp cho '{query}'.", False)

    lines = [f"Tìm thấy {len(hits)} skill phù hợp cho '{query}':"]
    for item in hits:
        lines.append(
            f"- `{item['name']}` (score {item['score']}, `{item['source']}`): "
            f"{item['description']} — `{item['path']}`"
        )
    return text_result("\n".join(lines), False)


def do_refresh_skill_index(args):
    workspace_dir = args.get("workspace_dir") or None
    if workspace_dir is not None and (not isinstance(workspace_dir, str) or not os.path.isdir(workspace_dir)):
        workspace_dir = None
    stats = INDEX.refresh(workspace_dir=workspace_dir)
    return text_result(json.dumps(stats, ensure_ascii=False, indent=2), False)


def handle_call(name, args):
    if name == "advise_task":
        return do_advise_task(args)
    if name == "search_skills":
        return do_search_skills(args)
    if name == "refresh_skill_index":
        return do_refresh_skill_index(args)
    return text_result("Unknown tool '%s'." % name, True)


def send(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle_request(req):
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        requested = params.get("protocolVersion") or DEFAULT_PROTOCOL
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": requested,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Task Advisor: call advise_task before medium/large tasks to recommend "
                    "Antigravity/XAI247 models, matching skills, and Swarm/Subagent strategies."
                ),
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name") or ""
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            args = {}
        return {"jsonrpc": "2.0", "id": req_id, "result": handle_call(name, args)}
    if method in ("resources/list", "resources/templates/list"):
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}}
    if method == "logging/setLevel":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "completion/complete":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"completion": {"values": []}}}
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": "Method not found: %s" % method},
    }


def main():
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue
        if not isinstance(message, dict) or "method" not in message:
            continue
        if "id" not in message:  # notification
            continue
        try:
            response = handle_request(message)
        except Exception as exc:  # pragma: no cover - defensive
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {"code": -32603, "message": "Internal error: %s" % exc},
            }
        send(response)


if __name__ == "__main__":
    main()
