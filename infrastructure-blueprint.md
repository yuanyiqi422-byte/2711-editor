# Infrastructure Blueprint · 2711 Editor

> 生成时间：2026-06-05  
> 目标项目：`小说沉浸式游戏/`（2711 Editor — AI 驱动沉浸式分支叙事游戏平台）  
> 范围：在现有 FastAPI + SSE 流式管线基础上，搭建**生产级 DevOps 基础设施**。**Planned / Roadmap（未上线）：** 场景生图、长文本 map-reduce、角色状态等核心扩展，不视为已交付能力。

---

## 1. 任务定义（由项目上下文推断）

用户模板中任务占位符未填；根据**最近修改时间**与 README「后续可扩展」清单，锁定核心任务为：

**构建 2711 Editor 的生产就绪开发栈** — 涵盖 SSE 流式生成管线、多格式文档摄取（PDF/OCR）、可选场景生图、本地历史，以及完整的测试 / Lint / Docker / CI 工作流。

---

## 2. SOTA 技术栈选型（2025–2026 业界最优）

### 2.1 后端运行时

| 层级 | 选型 | 理由 |
|------|------|------|
| 框架 | **FastAPI 0.115+** | 原生 async、OpenAPI、Pydantic v2 集成；项目已采用 |
| ASGI 服务器 | **Uvicorn[standard]**（dev） / **Gunicorn + UvicornWorker**（prod） | Dev 热重载；Prod 多 worker 利用多核 |
| 校验 / 配置 | **Pydantic v2 + pydantic-settings** | 类型安全 `.env`；替代裸 `os.getenv` |
| HTTP 客户端 | **httpx** | 异步 LLM 调用 + 测试 AsyncClient |
| 文档提取 | **PyMuPDF + RapidOCR + python-docx + EbookLib** | 已验证；扫描 PDF OCR 链路 |
| 流式 | **StreamingResponse + SSE** | 比 WebSocket 更简单；单向 pipeline 进度足够 |
| 结构化日志 | **structlog**（可选渐进） | JSON 日志便于生产观测 |

### 2.2 测试与质量

| 工具 | 用途 |
|------|------|
| **pytest + pytest-asyncio** | 异步 API 集成测试 |
| **httpx ASGITransport** | 官方推荐替代 sync TestClient |
| **pytest-cov** | 覆盖率基线 |
| **ruff** | Lint + Format（替代 black/isort/flake8 全家桶） |
| **mypy** | 静态类型（渐进 strict） |

### 2.3 前端（保持 Vanilla JS，不强行 React 化）

| 工具 | 用途 |
|------|------|
| **Node 22 LTS** | `--check` 语法校验（已有 frontend-build.mjs） |
| **ESLint 9 flat config** | JS 质量门禁 |
| **Prettier** | 统一格式 |

> 不迁移 Vite/React：现有 vanilla 架构运行良好（规模随功能迭代变化）；迁移成本 >> 收益。后续若组件复杂度上升再评估。

### 2.4 容器与 CI

| 工具 | 用途 |
|------|------|
| **Docker multi-stage** |  reproducible 部署 |
| **docker-compose** | 本地一键 `docker compose up` |
| **GitHub Actions** | push/PR 自动 lint + test + frontend validate |

### 2.5 刻意不引入（YAGNI）

- **Redis / Celery / ARQ**：当前无后台任务队列需求；`BackgroundTasks` + SSE 足够 MVP
- **PostgreSQL**：历史记录用本地 JSON 文件；规模上来再迁移
- **WebSocket**：SSE 已满足 pipeline 进度推送

---

## 3. 现状审计 vs 理想状态

### 3.1 已有 ✅

- FastAPI + uvicorn `--reload --reload-include .env`
- SSE `/api/create/stream` 流式叙事生成
- 文档摄取 PDF/OCR/docx/epub
- `backend/.env.example`、健康检查 `/api/health`
- `scripts/restart-server.ps1` Agent 无交互重启
- `scripts/frontend-build.mjs` 前端资源校验
- 零散 `test_pdf_extract.py`（非 pytest 结构）

### 3.2 缺失 ❌ → 本次补齐

| 缺失项 | 优先级 |
|--------|--------|
| Python 虚拟环境 `.venv` | P0 |
| `pyproject.toml`（ruff/pytest/mypy） | P0 |
| `requirements-dev.txt` | P0 |
| `backend/tests/` + conftest + smoke tests | P0 |
| `Dockerfile` + `docker-compose.yml` | P1 |
| `.github/workflows/ci.yml` | P1 |
| ESLint + Prettier（前端） | P1 |
| `pydantic-settings` 类型化配置 | P2 |
| 统一 smoke 脚本 `scripts/smoke-test.ps1` | P0 |
| 根级 `.env.example` 说明文档 | P1 |

---

## 4. 安装清单

### 4.1 Python（backend）

**运行时**（`backend/requirements.txt`，已有）：
```
fastapi, uvicorn[standard], httpx, python-dotenv, pydantic,
python-multipart, pymupdf, python-docx, rapidocr-onnxruntime, EbookLib
```

**开发**（`backend/requirements-dev.txt`，新增）：
```
-r requirements.txt
pytest>=8.3.0
pytest-asyncio>=0.24.0
pytest-cov>=6.0.0
httpx>=0.27.0
ruff>=0.8.0
mypy>=1.13.0
pydantic-settings>=2.6.0
types-python-dateutil
```

### 4.2 Node（根 package.json，新增 devDependencies）

```
eslint@^9, @eslint/js, globals, prettier
```

### 4.3 系统

- Python **3.12**（`.venv` 已创建；3.13 与 rapidocr 1.3+ 不兼容）✅
- Node v22.22.0 ✅
- `rapidocr-onnxruntime` 已修正为 `>=1.2.3`（兼容 3.12/3.13）

---

## 5. 配置文件矩阵

| 文件 | 作用 |
|------|------|
| `pyproject.toml` | ruff / pytest / mypy / coverage 集中配置 |
| `backend/requirements-dev.txt` | 开发依赖 |
| `backend/tests/conftest.py` | httpx AsyncClient fixture |
| `backend/tests/test_health.py` | 健康检查 smoke |
| `backend/tests/test_sse.py` | SSE 格式 smoke（不调用 LLM） |
| `backend/tests/test_document_extract.py` | PDF 采样 pytest 化 |
| `docker/Dockerfile` | 生产镜像 |
| `docker/docker-compose.yml` | 本地容器化 |
| `eslint.config.js` | 前端 ESLint flat |
| `.prettierrc` | 前端格式 |
| `.github/workflows/ci.yml` | CI 流水线 |
| `scripts/smoke-test.ps1` | 一键环境自测 |

---

## 6. 边缘情况预判

| 坑 | 对策 |
|----|------|
| Windows 路径 / 中文目录 | 脚本用 `$PSScriptRoot`；Docker WORKDIR `/app` |
| `.env` 未配置 API Key | health 返回 `ok: false`；测试 mock 不依赖真实 LLM |
| SSE 被 Nginx 缓冲 | 已有 `X-Accel-Buffering: no` |
| CORS | 已 `allow_origins=["*"]`；生产 compose 可收紧 |
| PyMuPDF + RapidOCR 体积大 | Docker 分层缓存 requirements |
| 8010 端口占用 | restart-server.ps1 自动释放 |
| 前端无 bundler | ESLint 只 lint `frontend/js/**/*.js` |

---

## 7. Ready-to-Code 验收标准

本地应能跑通：

```powershell
cd 小说沉浸式游戏
.\scripts\smoke-test.ps1          # 全绿
npm run validate                  # 前端资源 + JS 语法
npm run lint                      # ESLint
cd backend && ..\.venv\Scripts\python -m pytest tests/ -q
.\start.bat                       # 或 restart.bat
```

主要业务入口：
- `backend/narrative_service.py` — LLM 叙事逻辑
- `backend/image_service.py` — 场景生图（**Planned / Roadmap**；接口预留）
- `frontend/js/workshop/` — 工作室 UI
- `frontend/js/game.js` — 游玩体验

---

## 8. 后续扩展路线（不在本次范围）

1. **pydantic-settings** 全面替换 `os.getenv`（已装包，渐进迁移）
2. **lifespan** 替代 `@app.on_event("startup")`（FastAPI 0.109+ 弃用警告）
3. **Redis + ARQ** 当并发生图 / 长文本 map-reduce 需要队列时
4. **Playwright E2E** 当 UI 流程稳定后
5. **Prometheus metrics** `/metrics` 端点

---

*基础设施决策备忘（DevOps / 本地栈）；扩展项见上文 Planned / Roadmap。*
