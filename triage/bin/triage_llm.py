#!/usr/bin/env python3
import json, sys, requests
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: triage_llm.py <report.json>")
        sys.exit(2)

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))

    # 只给模型“结构化结论”，减少幻觉
    prompt = f"""
你是资深运维值班工程师。请严格基于下面 JSON 报告输出，不要编造不存在的信息。
要求：
1) 用 1 句话总结 primary_finding（包含 rule_id、root_cause）
2) 给出验证步骤（按顺序，引用 verify_steps）
3) 给出最小风险修复步骤（按顺序，引用 fix_steps，并写一句风险提示）
4) 输出一段 RCA 复盘（5 行以内：现象/影响/根因/修复/预防）

JSON：
{json.dumps(report, ensure_ascii=False)}
"""

    r = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": "qwen2.5:3b", "prompt": prompt, "stream": False},
        timeout=500
    )
    r.raise_for_status()
    answer = r.json().get("response", "")

    out_dir = report_path.parent
    out_md = out_dir / (report_path.stem + "_runbook.md")
    out_md.write_text(answer, encoding="utf-8")
    print("OK:", out_md)

if __name__ == "__main__":
    main()

