#!/usr/bin/env bash
# 更新到 origin/morning-bites 最新提交: 拉 → 装依赖 → 写 BUILD(页脚 AGPL 源码链接用) → 重启页面。人工跑。
set -euo pipefail
cd "$(dirname "$0")/.."
git fetch -q origin
git reset -q --hard "${1:-origin/morning-bites}"
.venv/bin/pip install -q --only-binary=:all: -r requirements.txt
git rev-parse HEAD > BUILD
systemctl --user daemon-reload
systemctl --user restart gg-app.service
sleep 3
curl -sf http://127.0.0.1:8903/gamma/_stcore/health && echo " gg-app $(cat BUILD | cut -c1-9) up"
