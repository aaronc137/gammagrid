#!/usr/bin/env bash
# 首次部署(VM 上以运行用户执行, 不要 sudo): venv → 依赖(只装轮子) → 单元软链 → enable。
# 前提: 系统 Postgres 已装, ~/.config/gammagrid/env 已有 DATABASE_URL / SNAPSHOT_HISTORY_DAYS / GG_MB_OUT(600)。
set -euo pipefail
cd "$(dirname "$0")/.."
test -f "$HOME/.config/gammagrid/env" || { echo "缺 ~/.config/gammagrid/env"; exit 1; }
[ -d .venv ] || /usr/bin/python3 -m venv .venv
.venv/bin/pip install -q --only-binary=:all: -r requirements.txt
mkdir -p out "$HOME/.config/systemd/user"
for unit in gg-app.service gg-ingest.service gg-ingest.path; do
  ln -sf "$PWD/deploy/systemd/$unit" "$HOME/.config/systemd/user/$unit"
done
git rev-parse HEAD > BUILD
systemctl --user daemon-reload
systemctl --user enable --now gg-ingest.path gg-app.service
systemctl --user --no-pager --plain list-units 'gg-*'
