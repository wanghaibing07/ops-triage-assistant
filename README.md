# ops-triage-assistant

运维故障分诊工具：**一键采集现场 → 规则匹配根因 → 输出 JSON → LLM 生成 Runbook → 静态页面回看报告**。适用于常见故障场景：SELinux 拦截、连接拒绝（Connection refused）、超时（Timeout）、DNS 解析失败等。

打开仓库即可理解流程，复制文件即可复现，支持 GitHub Pages 演示。

---

## 目标与适用场景

**一句话简介**：快速把一线运维排障的“证据、根因、验证、修复”变成结构化产出，方便复盘与交付。

**常见故障场景**：
- SELinux（安全增强 Linux）导致 Nginx 反代无法连接上游
- Connection refused：上游服务未监听/宕机/端口不对
- Timeout：网络不通、防火墙丢包、上游卡死
- DNS 解析失败：域名解析或 hosts 配置异常

---

## 架构/流程图

```
[collect] triage_collect.sh
      │
      ▼
打包现场证据 (tar.gz)
      │
      ▼
[analyze] triage_analyze.py
      │
      ▼
报告 JSON (report_*.json)
      │
      ├────────────┐
      ▼            ▼
[llm] triage_llm.py  [docs] docs/index.html
      │            │
      ▼            ▼
Runbook JSON       静态报告查看器
```

---

## Quick Start（3 条命令跑通）

> 假设你本地有 Python 3，并且运行了 Ollama（本地 LLM 服务）。

```bash
# 1) 采集现场
./triage/bin/triage_collect.sh

# 2) 规则分析（把采集包变成 JSON 报告）
python3 triage/bin/triage_analyze.py /tmp/triage-bundle_<HOST>_<TS>.tar.gz

# 3) LLM 生成 Runbook（结构化 JSON）
python3 triage/bin/triage_llm.py triage/out/report_<HOST>_<TS>.json
```

小贴士：如果你只是想快速体验静态报告，可以直接打开 `docs/index.html`。

---

## Demo（样例报告 + GitHub Pages）

- 样例报告（JSON）：
  - `docs/reports/report.json`
  - `docs/reports/report_connection_refused.json`
- GitHub Pages 演示链接（占位）：
  - `https://<YOUR_GITHUB_USERNAME>.github.io/ops-triage-assistant/`

**开启 Pages 步骤**：
1. GitHub → 仓库 Settings → Pages
2. Source 选择 **main** 分支
3. 目录选择 **/docs**
4. 保存后稍等 1～2 分钟即可访问

---

## Security（安全边界与脱敏）

- **不提交密钥**：不要把 `.env`、API Key、密码写入仓库。
- **日志脱敏原则**：IP/域名/用户信息需要脱敏，例如：
  - `10.1.2.3` → `UPSTREAM_IP`
  - `alice` → `USER_NAME`
- **最小化采集**：只采集排障必要的日志与系统信息。

---

## Limitations（局限性）

- **诊断以规则为准**：LLM 只负责可读性总结，不负责做诊断判断。
- **证据驱动**：如果 JSON 中没有证据，LLM 必须明确写“无法从JSON确认”。

---

## 推荐目录结构（MVP）

```
.
├── bin/                 # 可执行入口（collect/analyze/llm）
├── docs/                # GitHub Pages 静态展示
│   ├── index.html
│   └── reports/
├── samples/             # 样例采集包/报告
├── .github/workflows/   # CI
├── README.md
└── .gitignore
```

> 当前仓库中 `triage/bin` 对应 **bin/**；`docs/` 已用于静态报告；`docs/reports/` 可视为 **samples** 的展示集合。

---

## License

MIT
