# 2711编辑器 · 2711 Editor

把小说/故事文本转化为**沉浸式分支互动游戏**：分析文本 → 生成分支剧情 → 视觉小说式游玩。

## 品牌命名

默认产品名为 **「2711编辑器」**（英文 *2711 Editor*）。

若要换用其他名称，改 `frontend/js/brand.js` 一处即可联动全站。

## 快速开始（一键启动，无需手动重启）

1. 复制 `backend/.env.example` 为 `backend/.env`，填入 `AI_API_KEY`（OpenAI 兼容接口均可，如 DeepSeek）
2. **双击 `start.bat`** — 会自动释放 8010 端口、安装依赖、启动服务并打开浏览器

```bash
# 或命令行等价：
cd backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8010 --reload --reload-dir . --reload-include .env
```

3. 浏览器访问 http://127.0.0.1:8010

### 开发与热更新

| 变更类型 | 是否需要手动重启 |
|----------|------------------|
| `backend/*.py` | **否** — uvicorn `--reload` 自动重启 |
| `backend/.env` | **否** — 已加入 `--reload-include .env` |
| `frontend/*.js` / `*.css` | **否** — 普通刷新即可（`index.html` 含 `Cache-Control: no-cache`；静态资源带 `?v=` 版本号） |

### DevOps 工具链（Ready to code）

```powershell
# 一键环境自测（lint + validate + pytest）
npm run smoke

# 分项
npm run validate          # 前端资源 + JS 语法
npm run lint              # ESLint
npm run test:backend      # pytest（需 .venv）
.\.venv\Scripts\python.exe -m ruff check backend/tests
```

Python 虚拟环境：项目根 `.venv`（**Python 3.12**，与 Docker 一致）。`start.bat` / `restart-server.ps1` 会优先使用。

Docker：`docker compose -f docker/docker-compose.yml up --build`

详细架构决策见 `infrastructure-blueprint.md`。

## 线上部署

前端托管在 **Cloudflare Pages**（静态站点），API 在 **Render**。详见 [`DEPLOY.md`](DEPLOY.md)。

- 生产前端：https://2711editor.pages.dev
- 生产 API：https://two711-editor-api.onrender.com


Agent / 脚本重启（无需用户操作）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/restart-server.ps1
# 或双击 restart.bat
```

可选兜底监听（一般不必，与 `--reload` 重复）：

```powershell
powershell -File scripts/dev-watch.ps1
```

## 功能（v0.2.5）

- 粘贴或上传故事：**TXT / Markdown / Word (.docx) / PDF / RTF / EPUB**，单文件最大 **50MB**
- 扫描版 PDF 自动 **OCR**
- **上传后全文写入文本框**（默认不截字、不采样）；如需控制生成长度，可在 `backend/.env` 配置采样字数
- **本地历史记录**：上传与生成自动保存，支持「载入文本」「直接游玩」，免重复上传 PDF
- 长篇可生成 **15～25 个场景节点**、2～3 种结局；短篇 **8～12** 节点
- **背景音乐**：启程台可选内置氛围曲或上传本地 mp3/ogg/wav（会话内有效）。QQ Music 等外链库需平台 API 与版权授权，当前不支持

### 大文件 / PDF 环境变量（`backend/.env`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `MAX_UPLOAD_MB` | 50 | 单文件上传上限 |
| `MAX_EXTRACT_CHARS` | **0**（不限） | 提取阶段正文上限；0 = 不截断 |
| `MAX_CREATE_CHARS` | **0**（不限） | 「开始转化」提交上限；0 = 不限制 |
| `LLM_INPUT_CHARS` | **0** | 0 时用 `LLM_MODEL_SAFE_CHARS`；>0 为显式采样上限 |
| `LLM_MODEL_SAFE_CHARS` | **0**（不采样） | 0 = 全文送入 AI；>0 且超长时智能采样 |
| `MAX_PDF_PAGES` | **0** | **0 = 处理全部页**（受 `PDF_PAGE_HARD_CAP` 保护） |
| `PDF_PAGE_HARD_CAP` | 2000 | `MAX_PDF_PAGES=0` 时的页数硬上限 |

保存 `.env` 后服务会在数秒内自动 reload，**无需**再双击 `start.bat`。

- 四种主流视觉风格 preset：古风仙侠 / 都市言情 / 悬疑推理 / 校园青春
- 流式 pipeline 进度（分析 → 大纲 → 分支节点，生成中显示场景数）
- **橙光式**游玩：短句对白、点击屏幕继续、仅分支处出现选项；底部半透明对话框
- 场景背景：内置 **60+ 张吉卜力水彩风 SVG 场景图** + mood 渐变兜底
- 若选项指向未生成节点，可调用 `/api/expand` 动态续写

## 目录

```
小说沉浸式游戏/
├── backend/          # FastAPI + LLM
├── frontend/         # 工作室 + 游戏界面
├── scripts/          # restart-server.ps1、dev-watch.ps1
├── presets/          # 示例文本
├── start.bat         # 一键冷启动（含 --reload）
└── restart.bat       # Agent 无交互重启
```

## 后续可扩展

- [ ] 接入生图 API，按 `image_prompt` 生成场景图（`/api/scene-image` 已预留）
- [ ] 角色立绘与状态（好感/物品）
- [ ] 长文本分章摘要 / map-reduce 全书分析
- [x] 存档 / 本地历史（`backend/data/history/`）

## 说明

示例 preset 为**原创短文**，灵感来自各风格类型，非商用原著摘录。上传文本请自行注意版权。
