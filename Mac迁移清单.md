# Mac 迁移清单（2711 Editor）

## 1. 拉取代码

```bash
git clone <你的仓库 URL>
cd 小说沉浸式游戏   # 或实际仓库目录名
```

## 2. 环境变量（仅 DeepSeek）

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 AI_API_KEY（DeepSeek）等，勿提交 .env
```

## 3. 启动

**Windows：** 双击 `start.bat`（会释放 8010 并打开浏览器）

**Mac / 手动：**

```bash
cd backend
python -m venv ../.venv          # 可选
source ../.venv/bin/activate     # 可选
pip install -r requirements.txt
# 可选：node ../scripts/inject-env-config.mjs
uvicorn main:app --host 127.0.0.1 --port 8010 --reload --reload-dir . --reload-include .env
```

## 4. 本地地址

**http://127.0.0.1:8010/**

生产站（Cloudflare Pages）以仓库 README / Pages 控制台为准；本地改完后再自行 push / 部署即可。
