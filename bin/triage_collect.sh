#!/usr/bin/env bash
set -euo pipefail

TS="$(date +%F_%H%M%S)"
HOST="$(hostname -s)"
OUT_DIR="/tmp/triage_${HOST}_${TS}"
BUNDLE="/tmp/triage-bundle_${HOST}_${TS}.tar.gz"

mkdir -p "$OUT_DIR"

run_cmd () {
  local name="$1"
  shift
  {
    echo "### CMD: $*"
    echo "### TIME: $(date -Is)"
    "$@"
  } > "${OUT_DIR}/${name}.txt" 2>&1 || true
}

# 基础信息
run_cmd "00_uname" uname -a
run_cmd "01_os" cat /etc/os-release
run_cmd "02_time" date
run_cmd "03_uptime" uptime

# 网络与路由
run_cmd "10_ip_a" ip a
run_cmd "11_ip_r" ip r
run_cmd "12_resolv" cat /etc/resolv.conf
run_cmd "13_nmcli_dev" nmcli dev status
run_cmd "14_nmcli_con" nmcli con show

# 端口与服务
run_cmd "20_ss_listen" ss -lntp
run_cmd "21_systemctl_nginx" systemctl status nginx
run_cmd "22_systemctl_tomcat" systemctl status tomcat
run_cmd "23_systemctl_mysqld" systemctl status mysqld

# 防火墙与 SELinux
run_cmd "30_firewalld" firewall-cmd --list-all
run_cmd "31_selinux" getenforce
run_cmd "32_sebool" getsebool -a | egrep 'httpd_can_network_connect|httpd_can_network_relay|nis_enabled' || true

# Nginx 关键日志
if [ -f /var/log/nginx/error.log ]; then
  tail -n 200 /var/log/nginx/error.log > "${OUT_DIR}/40_nginx_error_tail.txt" 2>&1 || true
fi

# Tomcat 关键日志（按你实际路径调整）
if [ -f /opt/apache-tomcat-9.0.97/logs/catalina.out ]; then
  tail -n 300 /opt/apache-tomcat-9.0.97/logs/catalina.out > "${OUT_DIR}/41_tomcat_catalina_tail.txt" 2>&1 || true
fi

# MySQL 关键日志（按你实际路径调整）
if [ -f /tmp/mysqld.log ]; then
  tail -n 200 /tmp/mysqld.log > "${OUT_DIR}/42_mysqld_log_tail.txt" 2>&1 || true
fi

tar -czf "$BUNDLE" -C /tmp "$(basename "$OUT_DIR")"
echo "OK: $BUNDLE"

