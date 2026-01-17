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
只允许使用 JSON 中的字段（findings/primary_finding/verify_steps/fix_steps/evidence_snippet）。
如果缺证据或无法确认，请明确写“无法从JSON确认”。

请仅输出 JSON，字段结构如下（保持字段名一致）：
{{
  "summary": "string",
  "verify": ["step1", "step2"],
  "fix": ["step1", "step2"],
  "risk": "string",
  "rca": {{
    "phenomenon": "string",
    "impact": "string",
    "root_cause": "string",
    "fix": "string",
    "prevention": "string"
  }}
}}

要求：
1) summary：1 句话总结 primary_finding（包含 rule_id、root_cause）
2) verify：按顺序引用 primary_finding.verify_steps
3) fix：按顺序引用 primary_finding.fix_steps
4) risk：1 句话风险提示（仅基于 JSON）
5) rca：每个字段 1 句话（仅基于 JSON）

JSON：
{json.dumps(report, ensure_ascii=False)}
"""

    r = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=500
    )
    r.raise_for_status()
    answer = r.json().get("response", "")

    out_dir = report_path.parent
    out_json = out_dir / (report_path.stem + "_llm.json")
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        parsed = {"summary": "LLM 输出不是 JSON", "raw": answer}
    out_json.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK:", out_json)

if __name__ == "__main__":
    main()
