# Agent 指南 · 2711编辑器

## 启动与重启（禁止让用户手动操作）

## 本地访问（勿用 file://）

- **正确**：先运行 start.bat（或 Agent 执行 scripts/restart-server.ps1），浏览器打开 **http://127.0.0.1:8010**
- **错误**：双击 rontend/index.html 用 ile:// 打开 — 页面可能能显示，但 /api/* 请求会失败（无同源后端、CORS/路径均不对）
- 前端由 uvicorn 挂载 rontend/ 静态目录（main.py 中 VersionedStaticFiles，html=True），根路径 / 即 index.html

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

## 设计素材（全自动）

- 用户说「要什么图 + 放哪」→ 读 `.cursor/skills/auto-design-assets/SKILL.md`，直接 `GenerateImage` → `scripts/process-asset.py` → 写代码
- Prompt 模板：`scripts/art-prompt-templates.json` + `scripts/build-asset-prompt.py`；禁止让用户去外部生图/抠图

## 前端

- `frontend/index.html` 含 `Cache-Control: no-cache` meta；JS/CSS 使用 `?v=` 版本号
- 改前端后普通刷新即可，**不要**默认要求 Ctrl+F5
- UI 设计规范见根目录 `DESIGN.md`、`PRODUCT.md`
- 已安装外部设计 Skill（项目内 `.agents/skills/`）：
  - **Taste Skill** `design-taste-frontend` — `npx skills add leonxlnx/taste-skill --skill design-taste-frontend`
  - **Impeccable** `impeccable` — `npx skills add pbakaus/impeccable --skill impeccable`
- Impeccable Live 中文教程：`docs/impeccable-live使用说明.md`
- Impeccable Live 为 **opt-in**：默认不加载工具栏；设计会话打开 `http://127.0.0.1:8010/?impeccable=1`。若 `live.mjs` 误注入直链 `live.js`，运行 `node .agents/skills/impeccable/scripts/live-inject.mjs --remove` 清理。


## 叙事图谱 · 场景 · 角色色（Agent 须知）

- **场景匹配**：创建/解析节点后由 `backend/scene_match.py` 的 `assign_node_backgrounds` 按 `image_prompt`、`mood`、`style` 与 `node_id` 解析 `scene_id` / `bg_path`（`images/scenes/…`），避免全图同一张背景；单测见 `tests/test_scene_match.py`。
- **至少 3 个结局**：大纲与成品图谱经 `graph_validate.validate_outline_structure` 校验，默认 `min_endings=3`，且须含 reachable 的 `good` 与 `bad`/`neutral` 类结局；创建流 scale 字段 `endings_min` 可抬高下限。
- **角色对话色**：前端 `frontend/js/game.js` 的 `buildSpeakerColorMap` / `applySpeakerAppearance` 为不同说话人分配 `vn-name--*` 与 `vn-dialogue--*`（protagonist / sky / sakura / meadow / lavender / support / narration）；节点 `lines[].speaker` 须有多角色对白，勿全是「旁白」。

## 创建流 · 速度 vs 质量

**原则**：默认 env 在保持 `graph_validate.validate_outline_structure`（至少 3 个结局、含 reachable 的 good 与 bad/neutral）与场景对白生成的前提下加速。可调的是 **LLM 大纲规划**、批大小、并行度与 prompt 采样，**不要**关闭图谱校验来「提速」。

**预期耗时**（正常 API、`backend/narrative_service.py` 的 `estimate_create_eta_label`；本地 QA 见 Self-QA）：

| 原文字数 | 前端展示 ETA（约） | 典型路径 |
|---------|-------------------|---------|
| <1.5k | 约 1–3 分钟 | 圣经 + 场景批 |
| 1.5k–4k | 约 1–3 分钟 | 同上 |
| 4k–8k | 约 1–3 分钟 | 5k QA：节拍快路径，跳过 LLM 大纲，目标 <3 分钟 |
| 8k–15k | 约 2–4 分钟 | 可能 1 次 LLM 大纲 + 场景批 |
| ≥15k（如 20k） | 约 4–5 分钟 | 20k QA：约 5 分钟；≤20k 且 beats≥6 时常跳过 LLM 大纲 |

**快路径（跳过 LLM 大纲，用 bible `plot_beats` 骨架）触发条件**（满足其一即可，结局/抉择校验仍执行）：

- `char_count < NARRATIVE_FAST_PATH_CHARS`（默认 8000，别名 `SKIP_OUTLINE_BELOW_CHARS`）
- `char_count ≤ OUTLINE_SKIP_MAX_CHARS`（默认 20000）且 `plot_beats ≥ OUTLINE_SKIP_MIN_BEATS`（默认 6）
- `NARRATIVE_SPEED_MODE=fast`（强制跳过；仅建议本地 QA，生产慎用）

**调参指南**（不关闭校验）：

- **更快**：`LLM_BATCH_CONCURRENCY=6`、`SCENE_BATCH_SIZE=10`、`SCENE_BATCH_DELAY_SEC=0`；`FAST_OUTLINE=1` / `FAST_SCENES=1` / `BIBLE_FAST_MODEL=1` 并配置 `AI_MODEL_FAST`；略减 `SCENE_EXCERPT_*`、`BIBLE_INPUT_CHARS`、`OUTLINE_SOURCE_SAMPLE_CHARS`
- **更稳 / 长文质量**：提高 `OUTLINE_LLM_TIMEOUT_SEC`、`SCENE_LLM_TIMEOUT_SEC`；降低 `LLM_BATCH_CONCURRENCY`；略增节选字数；`OUTLINE_TIMEOUT_FAIL_FAST=0` 避免大纲超时立即回退（会更慢）
- **勿做**：为提速关闭 `validate_outline_structure` 或降低 `endings_min`；大纲重试当前实现仅 `OUTLINE_ATTEMPTS=1`

变量清单与默认值见 `backend/.env.example`（`FAST_OUTLINE`、`OUTLINE_SKIP_MAX_CHARS`、`LLM_BATCH_CONCURRENCY` 等）。


## Self-QA before handoff

改完 **主角识别 / 工坊布局 / 创建流程** 后，Agent 应先自测再交付：

1. **启动**：`start.bat` 或 `scripts/restart-server.ps1`；浏览器访问 **http://127.0.0.1:8010**（勿用 `file://` 打开 `frontend/index.html`）
2. **单元测试**：`cd backend && python -m pytest tests/ -q`（async 测试缺插件时可 `--ignore=tests/test_health.py --ignore=tests/test_sse.py`）
3. **主角提取**：`python -m pytest tests/test_character_extract.py -q`（含托尔斯泰碎片、POV、误报样本）
4. **后端健康**：`GET http://127.0.0.1:8010/api/health` 返回 200 且 `has_key: true`
5. **短创建流**：`python _qa_create_stream.py 5000` 应 PASS（目标 <3 分钟；节拍快路径跳过 LLM 大纲）
6. **长创建流（可选）**：`python _qa_create_stream.py 20000` 约 20k 字样本，预期 ~5 分钟（常跳过 LLM 大纲 + 并行场景批；大纲仅 1 次尝试）
7. **主角 API**：`POST /api/characters/preview` 对短样本返回无 garbage 名（如「尔斯泰」「伦斯基」）
8. **布局目测**：打开首页，风格预览区应占中栏主体，「开始游戏」下方无大块空白
9. **创建流 UX**：不得因 stall 自动 abort；SSE keepalive 须刷新活动计时并显示 ETA（stall 以连接活动为准，非进度百分比）；SSE `error` 事件须经 `errorMessage()` 映射后再展示
