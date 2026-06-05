# Agent 指南 · 2711编辑器

## 启动与重启（禁止让用户手动操作）

- **冷启动**：`start.bat` 或 `scripts/restart-server.ps1 -Foreground`
- **改 backend 后**：运行 `scripts/restart-server.ps1`（或 `restart.bat`），**不要**告诉用户「请双击 start.bat 重启」
- 日常开发已启用 `uvicorn --reload --reload-include .env`；小改动通常会自动生效，Agent 在批量修改或不确定时仍应主动调用 restart 脚本

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/restart-server.ps1
```

成功标准：`GET http://127.0.0.1:8010/api/health` 返回 200。

## 何时才需要用户介入

- `backend/.env` 不存在或 `AI_API_KEY` 未配置
- 8010 端口被非本项目进程占用且脚本无法释放
- Python / pip 未安装

## 前端

- `frontend/index.html` 含 `Cache-Control: no-cache` meta；JS/CSS 使用 `?v=` 版本号
- 改前端后普通刷新即可，**不要**默认要求 Ctrl+F5
