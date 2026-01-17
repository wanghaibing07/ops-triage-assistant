#!/usr/bin/env python3
import re, sys, tarfile, tempfile, os, json, datetime
from pathlib import Path

# ===== 1) 规则定义：加 priority & severity =====
# priority 数字越小越优先（更可能/更关键）
RULES = [
    {
        "id": "NGINX_UPSTREAM_SELINUX",
        "priority": 10,
        "severity": "P0",
        "pattern": re.compile(r"connect\(\) .* failed \(13: Permission denied\)", re.I),
        "cause": "Nginx 反代被 SELinux 拦截（httpd_t 默认禁止主动网络连接）",
        "verify": ["getenforce", "tail -n 50 /var/log/nginx/error.log"],
        "fix": ["setsebool -P httpd_can_network_connect 1", "systemctl restart nginx"],
    },
    {
        "id": "NGINX_UPSTREAM_REFUSED",
        "priority": 30,
        "severity": "P1",
        "pattern": re.compile(r"connect\(\) failed \(111: Connection refused\)", re.I),
        "cause": "上游端口拒绝：上游服务未监听/宕机/端口不对",
        "verify": ["curl -I http://<upstream>:8080/", "ss -lntp | grep 8080"],
        "fix": ["确认 Tomcat/应用监听 8080", "检查防火墙/安全组放行 8080"],
    },
    {
        "id": "NGINX_UPSTREAM_TIMEOUT",
        "priority": 40,
        "severity": "P1",
        "pattern": re.compile(r"upstream timed out|Connection timed out", re.I),
        "cause": "上游超时：网络不通/防火墙丢包/上游卡死",
        "verify": ["ping <upstream>", "curl -I http://<upstream>:8080/", "firewall-cmd --list-all"],
        "fix": ["放行端口/检查路由", "排查上游服务性能/卡死"],
    },
    {
        "id": "NGINX_DNS_FAIL",
        "priority": 50,
        "severity": "P2",
        "pattern": re.compile(r"host not found in upstream", re.I),
        "cause": "上游域名解析失败：DNS/hosts 配置问题",
        "verify": ["getent hosts node2.itcast.cn", "cat /etc/resolv.conf"],
        "fix": ["修复 /etc/hosts 或 DNS", "改用上游 IP 进行验证"],
    },
    {
        "id": "TOMCAT_DB_ACCESS_DENIED",
        "priority": 20,
        "severity": "P0",
        "pattern": re.compile(r"Access denied for user .*@'localhost'|CannotGetJdbcConnectionException", re.I),
        "cause": "应用启动失败：数据库认证/账号密码错误导致连接池初始化失败",
        "verify": ["tail -n 200 catalina.out", "/opt/mysql/bin/mysql -uroot -p --socket=/tmp/mysql.sock"],
        "fix": ["修正 application.yml 数据库账号密码", "建议创建业务账号替代 root"],
    },
    {
        "id": "TOMCAT_DEPLOY_FAIL",
        "priority": 60,
        "severity": "P2",
        "pattern": re.compile(r"Error deploying web application archive|LifecycleException", re.I),
        "cause": "WAR 部署/启动失败（常由依赖或数据库连接导致）",
        "verify": ["tail -n 200 catalina.out", "ls -l webapps/"],
        "fix": ["结合上面的具体异常先修根因，再重启 Tomcat"],
    },
    {
        "id": "MYSQL_LIBNCURSES_MISSING",
        "priority": 25,
        "severity": "P0",
        "pattern": re.compile(r"libncurses\.so\.5.*cannot open shared object file", re.I),
        "cause": "MySQL 客户端依赖缺失（CentOS 9 常见：libncurses.so.5）",
        "verify": ["ldd /opt/mysql/bin/mysql | grep ncurses", "dnf provides '*/libncurses.so.5'"],
        "fix": ["启用 epel/crb 后安装 ncurses-compat-libs"],
    },
]

# ===== 2) tar 安全解压：解决你看到的 tarfile 警告，并避免路径穿越 =====
def safe_extract(tar: tarfile.TarFile, path: Path):
    base = str(path.resolve())
    for m in tar.getmembers():
        target = (path / m.name).resolve()
        if not str(target).startswith(base):
            raise RuntimeError(f"Unsafe path in tar: {m.name}")
    tar.extractall(path)

def read_all_texts(root: Path) -> str:
    parts = []
    for p in sorted(root.rglob("*.txt")):
        try:
            parts.append(f"\n===== {p.name} =====\n")
            parts.append(p.read_text(errors="ignore"))
        except Exception:
            pass
    return "\n".join(parts)

# 只截取命中附近的“证据片段”，避免把一大坨日志都塞给 LLM
def extract_snippet(text: str, pattern: re.Pattern, window: int = 20) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if pattern.search(line):
            start = max(0, i - window)
            end = min(len(lines), i + window + 1)
            return "\n".join(lines[start:end])
    return ""

def main():
    if len(sys.argv) != 2:
        print("Usage: triage_analyze.py <triage-bundle.tar.gz>")
        sys.exit(2)

    bundle = sys.argv[1]
    if not os.path.exists(bundle):
        print("Bundle not found:", bundle)
        sys.exit(2)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with tarfile.open(bundle, "r:gz") as tar:
            safe_extract(tar, td_path)

        subdirs = [p for p in td_path.iterdir() if p.is_dir()]
        if not subdirs:
            print("No extracted directory")
            sys.exit(1)
        root = subdirs[0]
        hostdir = root.name

        text = read_all_texts(root)

        findings = []
        for r in RULES:
            if r["pattern"].search(text):
                findings.append({
                    "rule_id": r["id"],
                    "priority": r["priority"],
                    "severity": r["severity"],
                    "root_cause": r["cause"],
                    "verify_steps": r["verify"],
                    "fix_steps": r["fix"],
                    "evidence_snippet": extract_snippet(text, r["pattern"], window=15),
                })

        findings.sort(key=lambda x: x["priority"])

        report = {
            "bundle": bundle,
            "hostdir": hostdir,
            "generated_at": datetime.datetime.now().isoformat(),
            "findings": findings,
            "primary_finding": findings[0] if findings else None,
        }

        # 输出到 output/
        out_dir = Path(__file__).resolve().parent.parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_json = out_dir / f"report_{hostdir}_{ts}.json"
        out_txt = out_dir / f"report_{hostdir}_{ts}.txt"

        with out_json.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 仍保留文本输出（方便人看）
        with out_txt.open("w", encoding="utf-8") as f:
            f.write("=== TRIAGE REPORT ===\n")
            f.write(f"Bundle: {bundle}\nHostDir: {hostdir}\n\n")
            if not findings:
                f.write("No known patterns matched.\n")
            else:
                pf = report["primary_finding"]
                f.write(f"Primary: {pf['rule_id']} ({pf['severity']})\nCause: {pf['root_cause']}\n\n")
                for i, it in enumerate(findings, 1):
                    f.write(f"[{i}] {it['rule_id']} {it['severity']}\n")
                    f.write(f"Cause: {it['root_cause']}\n")
                    f.write("Verify:\n" + "\n".join([f"  - {v}" for v in it["verify_steps"]]) + "\n")
                    f.write("Fix:\n" + "\n".join([f"  - {x}" for x in it["fix_steps"]]) + "\n")
                    f.write("Evidence snippet:\n" + it["evidence_snippet"] + "\n\n")

        print("OK:")
        print("  JSON:", out_json)
        print("  TXT :", out_txt)

if __name__ == "__main__":
    main()
