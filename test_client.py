#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kiểm thử đơn vị và E2E MCP stdio cho task-advisor-antigravity."""
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(BASE, "server.py")
sys.path.insert(0, BASE)

from router import advise_task
from skill_index import SkillIndex


def test_skill_index():
    idx = SkillIndex()
    stats = idx.refresh()
    print("index stats:", stats)
    assert stats["total_skills"] >= 100, stats

    # Xác minh parser multiline YAML (>) hoạt động đúng trên academy-guide
    academy_hits = idx.search("academy-guide", limit=3)
    assert academy_hits and academy_hits[0]["name"] == "academy-guide", academy_hits
    assert len(academy_hits[0]["description"]) > 40, academy_hits[0]

    # Tìm kiếm song ngữ Việt-Anh
    q1 = idx.search("thiết kế giao diện web đẹp bằng tailwind", limit=5)
    names1 = [x["name"] for x in q1]
    print("q1 (UI/Tailwind):", names1)
    assert any("tailwind" in n or "frontend" in n or "ui" in n for n in names1), names1

    q2 = idx.search("sua loi bug khong ro nguyen nhan", limit=5)
    names2 = [x["name"] for x in q2]
    print("q2 (Debug):", names2)
    assert any("systematic-debugging" in n or "debugger" in n or "debug" in n for n in names2), names2

    q3 = idx.search("tối ưu database postgres sql", limit=5)
    names3 = [x["name"] for x in q3]
    print("q3 (DB/SQL):", names3)
    assert any("postgresql" in n or "sql" in n for n in names3), names3


def test_router_logic():
    idx = SkillIndex()
    idx.ensure_loaded()

    # 1. Việc nhẹ (trivial) -> không pause mặc định, không swarm
    a_triv = advise_task(idx, "git status là gì?")
    print("trivial:", a_triv["complexity"], a_triv["score"], a_triv["should_pause_for_confirmation"])
    assert a_triv["complexity"] == "trivial", a_triv
    assert a_triv["should_pause_for_confirmation"] is False, a_triv
    assert a_triv["execution"]["recommend_swarm"] is False, a_triv

    # Nếu force_panel=True thì vẫn hiện bảng xác nhận
    a_forced = advise_task(idx, "git status là gì?", force_panel=True)
    assert a_forced["should_pause_for_confirmation"] is True

    # 2. Xử lý batch nhiều file -> đề xuất code_mode (py_exec)
    a_batch = advise_task(idx, "đọc 20 file json log trong thư mục rồi tổng hợp báo cáo lỗi")
    print("batch:", a_batch["complexity"], a_batch["execution"]["mode"])
    assert a_batch["execution"]["mode"] == "code_mode", a_batch["execution"]

    # 3. Dự án lớn nhiều mảng -> complex/massive, pause=True, recommend_swarm=True
    a_mass = advise_task(
        idx,
        "xây dựng ứng dụng web full-stack Next.js + PostgreSQL + đăng nhập auth + test E2E playwright và deploy lên Vercel",
    )
    print("massive:", a_mass["complexity"], a_mass["score"], a_mass["domains"], a_mass["execution"]["mode"])
    assert a_mass["complexity"] in ("complex", "massive"), a_mass
    assert a_mass["should_pause_for_confirmation"] is True
    assert a_mass["execution"]["recommend_swarm"] is True
    assert len(a_mass["execution"]["swarm_roster"]) >= 2

    # 4. Quota thấp -> nhắc đẩy sang XAI247
    a_quota = advise_task(idx, "refactor lại hệ thống API và viết thêm unit test", quota_percent=15)
    print("low quota note:", a_quota["models"]["quota_note"])
    assert a_quota["models"]["quota_note"] is not None
    assert "XAI247" in a_quota["models"]["xai247_recommendation"]


def test_mcp_stdio():
    proc = subprocess.Popen(
        [sys.executable, "-u", SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    def rpc(req_id, method, params=None):
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            msg["params"] = params
        proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("Server did not respond: %s" % proc.stderr.read())
        return json.loads(line)

    init = rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test"}})
    assert init["result"]["serverInfo"]["name"] == "task-advisor-antigravity", init
    print("initialize:", init["result"]["serverInfo"])

    tools = [t["name"] for t in rpc(2, "tools/list")["result"]["tools"]]
    print("tools:", tools)
    assert tools == ["advise_task", "search_skills", "refresh_skill_index"], tools

    r_ref = rpc(3, "tools/call", {"name": "refresh_skill_index", "arguments": {}})
    assert r_ref["result"]["isError"] is False
    ref_data = json.loads(r_ref["result"]["content"][0]["text"])
    assert ref_data["total_skills"] >= 100

    r_search = rpc(4, "tools/call", {"name": "search_skills", "arguments": {"query": "bảo mật xss đăng nhập", "limit": 5}})
    assert r_search["result"]["isError"] is False
    assert "Tìm thấy" in r_search["result"]["content"][0]["text"]

    r_adv = rpc(
        5,
        "tools/call",
        {
            "name": "advise_task",
            "arguments": {
                "prompt": "Xây dựng trang web bán hàng có giao diện Tailwind đẹp, API FastAPI, PostgreSQL và deploy Vercel",
                "quota_percent": 25,
            },
        },
    )
    assert r_adv["result"]["isError"] is False
    adv_text = r_adv["result"]["content"][0]["text"]
    assert "Bảng Gợi Ý Chiến Lược Thực Thi" in adv_text
    assert "<task_advisor_meta>" in adv_text
    assert "XAI247" in adv_text

    r_bad = rpc(6, "tools/call", {"name": "advise_task", "arguments": {"prompt": "   "}})
    assert r_bad["result"]["isError"] is True

    proc.stdin.close()
    proc.wait(timeout=10)
    print("server exit:", proc.returncode)
    assert proc.returncode == 0


def main():
    test_skill_index()
    test_router_logic()
    test_mcp_stdio()
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
