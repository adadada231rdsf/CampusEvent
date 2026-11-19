#!/usr/bin/env bash
# CampusEvent 一键部署脚本（在服务器上以 root 执行）
#   bash /root/CampusEvent/tools/deploy.sh [端口]
# 默认端口 8080，与实验一 StudyTask（80）共存。
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8080}"
SERVICE="campusevent"
SECRET="$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 32)"

echo "== 1/6 安装系统依赖"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-venv python3-pip curl
fi

echo "== 2/6 创建虚拟环境并安装依赖"
cd "$APP_DIR"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt gunicorn

echo "== 3/6 初始化演示数据（已存在则跳过）"
if [ ! -f instance/campusevent.sqlite ]; then
  .venv/bin/python seed_demo.py --reset
else
  echo "   已有数据库，跳过（如需重置执行 .venv/bin/python seed_demo.py --reset）"
fi

echo "== 4/6 写入 systemd 服务（端口 $PORT）"
cat > "/etc/systemd/system/${SERVICE}.service" <<EOF
[Unit]
Description=CampusEvent 校园活动报名系统（软件工程实验二）
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
Environment=CAMPUSEVENT_SECRET=${SECRET}
ExecStart=${APP_DIR}/.venv/bin/gunicorn -w 2 -b 0.0.0.0:${PORT} "app:create_app()"
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "== 5/6 启动服务"
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null 2>&1 || true
systemctl restart "$SERVICE"
sleep 2
systemctl --no-pager --lines=5 status "$SERVICE" || true

echo "== 6/6 本机自检"
if curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/login"; then
  echo "OK: http://127.0.0.1:${PORT}/login 返回 200"
else
  echo "FAIL: 本机访问失败，请查看 journalctl -u ${SERVICE} -n 50"
  exit 1
fi

echo
echo "外网访问：http://<服务器公网IP>:${PORT}/login"
echo "（安全组需放行 ${PORT}）"
