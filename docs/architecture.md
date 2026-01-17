# 架构与流程说明

以下是 ops-triage-assistant 的核心流程：

```
[collect] bin/triage_collect.sh
      │
      ▼
打包现场证据 (tar.gz)
      │
      ▼
[analyze] bin/triage_analyze.py
      │
      ▼
报告 JSON (output/report_*.json)
      │
      ├────────────┐
      ▼            ▼
[llm] bin/triage_llm.py  [docs] docs/index.html
      │            │
      ▼            ▼
Runbook JSON       静态报告查看器
```

## 核心产物

- **现场采集包**：`/tmp/triage-bundle_<HOST>_<TS>.tar.gz`
- **规则分析报告**：`output/report_<HOST>_<TS>.json`
- **LLM Runbook**：`output/report_<HOST>_<TS>_llm.json`

## 关键约束

- 诊断结论以规则匹配为准，LLM 仅负责可读性总结。
- 证据不足时必须输出“无法从JSON确认”。
